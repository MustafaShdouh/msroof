"""Isolated frozen-encoder research: hash-bound data and nontruncating preflight."""
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

from src.python.research.sms_semantics import normalize
from training.transactions.completion_context import expand_batch

ROOT = Path(__file__).resolve().parents[2]
RUN = "sms_completion_encoder_v1"
CACHE = ROOT / ".local-backups" / RUN
PROTOCOL = ROOT / "config/experiments" / (RUN + ".json")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(relative):
    path = ROOT / relative
    if path.suffix == ".jsonl":
        return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    return json.loads(path.read_text(encoding="utf-8"))


def prepare():
    protocol = read(PROTOCOL)
    if not protocol["ownerApproval"] or protocol["fitCallsAuthorized"] != 1:
        raise ValueError("Explicit one-fit approval required")
    for path, expected in protocol["frozenInputs"].items():
        if digest(ROOT / path) != expected:
            raise ValueError("Frozen input changed: " + path)
    cohort = read(protocol["cohort"]["priorSelection"])
    sources = {}
    training = []
    for row in cohort["training"]["completion"]:
        if row["sourceArtifact"] not in sources:
            sources[row["sourceArtifact"]] = read(row["sourceArtifact"])
        source = sources[row["sourceArtifact"]]
        text = source[row["originIndex"]]["text"]
        if hashlib.sha256(text.encode()).hexdigest() != row["textSha256"]:
            raise ValueError("Training text binding changed")
        training.append(dict(recordId=row["recordId"], text=text, target=row["target"], weight=row["weight"], group=row["weightGroup"]))
    contrasts = expand_batch(read(protocol["cohort"]["additionalSource"]))
    training += [dict(recordId=r["recordId"], text=r["text"], target=r["target"], weight=r["weight"], group="context:" + r["authoringGroupId"]) for r in contrasts if r["fold"] == "research_training"]
    encoded = json.dumps(training, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    if hashlib.sha256(encoded).hexdigest() != protocol["cohort"]["trainingViewSha256"]:
        raise ValueError("Training view differs from approved view")
    weights = defaultdict(float)
    for row in training:
        weights[row["group"]] += row["weight"]
    if len(weights) != 113 or any(abs(w - 1) > 1e-12 for w in weights.values()):
        raise ValueError("Weight groups changed")
    originals = read("data/training/sanitized_v1/transactions.json")
    validation = []
    for row in cohort["validation"]["completion"]:
        text = originals[row["sourceIndex"]]["text"]
        if hashlib.sha256(text.encode()).hexdigest() != row["textSha256"]:
            raise ValueError("Validation text binding changed")
        validation.append({**row, "text": text})
    manual = read(".local-backups/sms_research_manual_v1/cases.json")["cases"]
    quotes = read("tests/fixtures/quoted_example_cases.json")["cases"]
    evaluations = {
        "oldExposedValidation": validation,
        "exposedManual": [dict(recordId=r["id"], text=r["text"], target=r["expected"]["transactionStatus"]) for r in manual],
        "authoredProbe": [r for r in contrasts if r["fold"] == "authored_probe"],
        "quoteControls": [dict(recordId=r["id"], text=r["text"], target=r["status"]) for r in quotes],
    }
    return protocol, training, evaluations


def preflight():
    from huggingface_hub import snapshot_download
    from transformers import AutoTokenizer
    protocol, training, evaluations = prepare()
    encoder = protocol["encoder"]
    directory = snapshot_download(encoder["modelId"], revision=encoder["revision"],
        local_dir=str(CACHE / "model"), allow_patterns=["*.json", "*.model", "*.txt", "README.md"], token=False)
    tokenizer = AutoTokenizer.from_pretrained(directory, local_files_only=True, trust_remote_code=False)
    cases = [("training", row) for row in training] + [(name, row) for name, rows in evaluations.items() for row in rows]
    lengths = []
    for name, row in cases:
        tokens = tokenizer(normalize(row["text"]), truncation=False, add_special_tokens=True)["input_ids"]
        lengths.append(dict(cohort=name, recordId=row["recordId"], tokens=len(tokens)))
    overflow = [r for r in lengths if r["tokens"] > encoder["maxTokensIncludingSpecialTokens"]]
    assets = {p.relative_to(Path(directory)).as_posix(): {"sha256": digest(p), "bytes": p.stat().st_size} for p in Path(directory).rglob("*") if p.is_file() and ".cache" not in p.parts}
    report = dict(runId=RUN, status="stopped_token_overflow" if overflow else "preflight_passed", fitCalls=0,
        protocolSha256=digest(PROTOCOL), trainingRows=len(training), targets=dict(Counter(r["target"] for r in training)),
        maximumTokens=max(r["tokens"] for r in lengths), overflow=overflow, lengths=lengths, assets=assets)
    CACHE.mkdir(parents=True, exist_ok=True)
    (CACHE / "preflight.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k not in ("lengths", "assets")}, ensure_ascii=False))
    return report


def benchmark():
    import importlib.metadata
    import time
    import warnings
    import numpy as np
    import torch
    from huggingface_hub import hf_hub_download
    from transformers import AutoModel, AutoTokenizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.exceptions import ConvergenceWarning
    from src.python.research.sms_semantics import SmsSemanticsModel
    from src.python.research.sms_completion_context import SmsCompletionContextModel
    area = ROOT / "data/reports/transactions"
    attempt = area / (RUN + "_attempt.json")
    report_path = area / (RUN + ".json")
    model_path = ROOT / "data/models" / (RUN + "_candidate.json")
    if any(p.exists() for p in (attempt, report_path, model_path)):
        raise ValueError("Trial already attempted: no second fit")
    flight = preflight()
    if flight["overflow"]:
        return
    protocol, training, evaluations = prepare()
    encoder = protocol["encoder"]
    path = hf_hub_download(encoder["modelId"], "model.safetensors", revision=encoder["revision"], local_dir=str(CACHE / "model"), token=False)
    if digest(Path(path)) != encoder["expectedSafetensorsSha256"]:
        raise ValueError("Encoder checksum mismatch")
    torch.set_num_threads(2)
    torch.use_deterministic_algorithms(True)
    tokenizer = AutoTokenizer.from_pretrained(CACHE / "model", local_files_only=True, trust_remote_code=False)
    backbone = AutoModel.from_pretrained(CACHE / "model", local_files_only=True, trust_remote_code=False, dtype=torch.float32).cpu().eval()
    backbone.requires_grad_(False)

    def encode(texts):
        values = []
        with torch.inference_mode():
            for start in range(0, len(texts), 16):
                tokens = tokenizer(texts[start:start + 16], padding=True, truncation=False, return_tensors="pt")
                hidden = backbone(**tokens).last_hidden_state
                mask = tokens["attention_mask"].unsqueeze(-1).expand(hidden.size()).float()
                values.append(((hidden * mask).sum(1) / mask.sum(1).clamp(min=1e-9)).numpy())
        return np.concatenate(values)

    rows = training + [r for group in evaluations.values() for r in group]
    texts = [normalize(r["text"]) for r in rows]
    started = time.perf_counter()
    vectors = encode(texts)
    elapsed = time.perf_counter() - started
    if vectors.shape != (len(rows), 384) or not np.isfinite(vectors).all() or not np.array_equal(vectors[:16], encode(texts[:16])):
        raise ValueError("Encoder shape/finite/determinism check failed")
    np.save(CACHE / "vectors.npy", vectors)
    environment = {p: importlib.metadata.version(p) for p in ("torch", "transformers", "huggingface-hub", "numpy", "scikit-learn", "scipy", "tokenizers")}
    binding = dict(protocolSha256=digest(PROTOCOL), producerSha256=digest(Path(__file__)), inputSha256=protocol["frozenInputs"],
        environment=environment, encoderSha256=digest(Path(path)), vectorsSha256=digest(CACHE / "vectors.npy"),
        normalizedInputsSha256=hashlib.sha256(json.dumps(texts, ensure_ascii=False).encode()).hexdigest(), tokenizerAssets=flight["assets"])
    (CACHE / "vector_bindings.json").write_text(json.dumps(binding, indent=2) + "\n", encoding="utf-8")
    x = vectors.astype(np.float64)
    settings = protocol["classifier"]
    estimator = LogisticRegression(solver="liblinear", C=settings["C"], l1_ratio=settings["l1Ratio"], dual=False,
        fit_intercept=True, intercept_scaling=1, tol=settings["tolerance"], max_iter=settings["maxIterations"],
        random_state=settings["seed"], class_weight=None)
    # Exclusive creation permanently consumes the trial budget, including failed fits.
    with attempt.open("x", encoding="utf-8") as handle:
        json.dump(dict(runId=RUN, ownerApproval=protocol["ownerApproval"], fitCallsAuthorized=1, binding=binding), handle, indent=2)
    with warnings.catch_warnings():
        warnings.simplefilter("error", ConvergenceWarning)
        estimator.fit(x[:len(training)], [int(r["target"] == "completed") for r in training], sample_weight=[r["weight"] for r in training])
    weights, bias = estimator.coef_[0].tolist(), float(estimator.intercept_[0])
    scores = []
    for vector in x:
        score = bias
        for weight, value in zip(weights, vector):
            score += weight * float(value)
        scores.append(score)
    expected = estimator.decision_function(x)
    gap = float(np.max(np.abs(expected - scores)))
    if gap > 1e-10 or any((a > 0) != (b > 0) for a, b in zip(expected, scores)):
        raise ValueError("Ordered flat head differs from solver")
    model = dict(runId=RUN, researchOnly=True, standaloneSmsModel=False, encoder=encoder, binding=binding, weights=weights, intercept=bias)
    with model_path.open("x", encoding="utf-8") as handle:
        json.dump(model, handle, indent=2)
    word = SmsSemanticsModel(read("data/models/sms_semantics_followup_v1_word_candidate.json"))
    context = SmsCompletionContextModel(read("data/models/sms_completion_context_v1_candidate.json"))
    def counts(items, key):
        result = dict(TP=0, TN=0, FP=0, FN=0)
        for r in items:
            if r["target"] not in ("completed", "non_transaction"):
                continue
            positive, actual = r["target"] == "completed", r[key] == "completed"
            result[("T" if actual == positive else "F") + ("P" if actual else "N")] += 1
        return result
    output, offset, gate = {}, len(training), True
    for name, group in evaluations.items():
        items = []
        for row, score in zip(group, scores[offset:offset + len(group)]):
            language = row.get("language") or ("ar" if any("\u0600" <= c <= "\u06ff" for c in row["text"]) else "en")
            items.append(dict(recordId=row["recordId"], language=language, target=row["target"], score=score,
                candidate="completed" if score > 0 else "non_transaction",
                word=word.predict(row["text"])["heads"]["completion"]["prediction"],
                context=context.predict(row["text"])["heads"]["completion"]["prediction"],
                duplicatesManual=any(row["text"] == r["text"] for r in evaluations["exposedManual"]) if name == "quoteControls" else False))
        metrics = {slice_name: {key: counts([r for r in items if slice_name == "all" or r["language"] == slice_name], key) for key in ("word", "context", "candidate")} for slice_name in ("all", "ar", "en")}
        for metric in metrics.values():
            gate = gate and metric["candidate"]["FP"] == 0 and (name == "quoteControls" or metric["candidate"]["FN"] <= metric["context"]["FN"])
        output[name] = dict(metrics=metrics, rows=items, uncertainNotBinaryScored=sum(r["target"] not in ("completed", "non_transaction") for r in items))
        offset += len(group)
    latencies = []
    for _ in range(10):
        start = time.perf_counter()
        encode(texts[:1])
        latencies.append((time.perf_counter() - start) * 1000)
    report = dict(runId=RUN, fitCalls=1, iterations=estimator.n_iter_.tolist(), maximumExportGap=gap,
        researchContinuationGatePassed=bool(gate), independentAccuracy=False, productionIntegrated=False,
        encodingSeconds=elapsed, warmSingleMessageMilliseconds=latencies,
        encoderBytes=Path(path).stat().st_size, binding=binding, evaluations=output)
    with report_path.open("x", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2)
    print(json.dumps(dict(gate=gate, metrics={k: v["metrics"]["all"] for k, v in output.items()})))


if __name__ == "__main__":
    import sys
    benchmark() if "--run" in sys.argv else preflight()
