"""One supervised, resource-bounded encoder adaptation; research only."""
import argparse
from collections import Counter, defaultdict
import ctypes
from ctypes import wintypes
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

from training.transactions import completion_encoder as previous
from src.python.research.sms_semantics import normalize

ROOT = previous.ROOT
RUN = "sms_completion_adaptation_v1"
PROTOCOL = ROOT / "config/experiments" / (RUN + ".json")
CACHE = ROOT / ".local-backups" / RUN
AREA = ROOT / "data/reports/transactions"
ATTEMPT, REPORT, FAILURE = (AREA / (RUN + s + ".json") for s in ("_attempt", "", "_failure"))
MODEL_DIR = previous.CACHE / "model"


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_new(path, value):
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.write("\n")


def refuse_repeat():
    if any(p.exists() for p in (ATTEMPT, REPORT, FAILURE, CACHE / "final.safetensors")):
        raise ValueError("Adaptation already attempted; no retry or additional training")


def prepare():
    p = read(PROTOCOL)
    if not p["ownerApproval"] or p["trainingRunsAuthorized"] != 1:
        raise ValueError("One-run owner approval required")
    for name, expected in p["frozenInputs"].items():
        if previous.digest(ROOT / name) != expected:
            raise ValueError("Frozen input changed: " + name)
    _, rows, evaluations = previous.prepare()
    scope = previous.read("data/training/authored_sms_scope_v1/messages.jsonl")
    rows += [dict(recordId=r["recordId"], text=r["text"], target=r["target"], weight=1/6, group=r["authoringGroupId"])
             for r in scope if r["fold"] == "proposed_training" and r["target"] != "uncertain"]
    encoded = json.dumps(rows, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    if hashlib.sha256(encoded).hexdigest() != p["cohort"]["trainingViewSha256"]:
        raise ValueError("Training view changed")
    weights = defaultdict(float)
    for row in rows:
        weights[row["group"]] += row["weight"]
    if len(rows) != 1158 or Counter(r["target"] for r in rows) != p["cohort"]["targets"] or len(weights) != 129 or any(abs(w-1) > 1e-12 for w in weights.values()):
        raise ValueError("Training counts/weights changed")
    prohibited = {r["recordId"] for r in scope if r["fold"] != "proposed_training" or r["target"] == "uncertain"}
    if prohibited & {r["recordId"] for r in rows}:
        raise ValueError("Held-out/uncertain record in training")
    evaluations["scopeDevelopment"] = [r for r in scope if r["fold"] == "development"]
    reserved = [r for r in scope if r["fold"] == "reserved_diagnostic"]
    return p, rows, evaluations, reserved


def selected(name):
    return name.startswith("encoder.layer.10.") or name.startswith("encoder.layer.11.")


def configure(backbone, head):
    backbone.eval()
    head.eval()
    for name, parameter in backbone.named_parameters():
        parameter.requires_grad_(selected(name))
    head.requires_grad_(True)
    return [p for p in backbone.parameters() if p.requires_grad], list(head.parameters())


def tensor_hashes(backbone):
    return {name: hashlib.sha256(p.detach().cpu().contiguous().numpy().tobytes()).hexdigest() for name, p in backbone.named_parameters()}


def counts(rows, key):
    result = dict(TP=0, TN=0, FP=0, FN=0)
    for row in rows:
        if row["target"] not in ("completed", "non_transaction"):
            continue
        positive, predicted = row["target"] == "completed", row[key] > 0
        result[("T" if positive == predicted else "F") + ("P" if predicted else "N")] += 1
    return result


def gate(evaluations):
    failures = []
    for cohort, data in evaluations.items():
        for language, metric in data["metrics"].items():
            if metric["candidate"]["FP"]:
                failures.append(f"{cohort}/{language}: false completion")
            if metric["candidate"]["FN"] > min(metric[r]["FN"] for r in ("word", "context", "encoder")):
                failures.append(f"{cohort}/{language}: misses worse than best reference")
    return failures


def worker():
    refuse_repeat()
    import random
    import importlib.metadata
    import numpy as np
    import torch
    from transformers import AutoModel, AutoTokenizer
    from safetensors.torch import save_file, load_file
    from src.python.research.sms_semantics import SmsSemanticsModel
    from src.python.research.sms_completion_context import SmsCompletionContextModel
    p, training, evaluations, reserved = prepare()
    settings = p["training"]
    random.seed(settings["seed"])
    np.random.seed(settings["seed"])
    torch.manual_seed(settings["seed"])
    torch.set_num_threads(p["architecture"]["threads"])
    torch.use_deterministic_algorithms(True)
    if previous.digest(MODEL_DIR / "model.safetensors") != p["architecture"]["baseSafetensorsSha256"]:
        raise ValueError("Base checksum changed")
    old_flight = read(previous.CACHE / "preflight.json")
    for name, binding in old_flight["assets"].items():
        if previous.digest(MODEL_DIR / name) != binding["sha256"]:
            raise ValueError("Tokenizer/config asset changed: " + name)
    tokenizer = AutoTokenizer.from_pretrained(MODEL_DIR, local_files_only=True, trust_remote_code=False)
    all_preflight = training + [r for group in evaluations.values() for r in group] + reserved
    token_lengths = [len(tokenizer(normalize(r["text"]), truncation=False)["input_ids"]) for r in all_preflight]
    if max(token_lengths) > p["inputs"]["maxTokensIncludingSpecials"]:
        raise ValueError("Token overflow; no truncation authorized")
    backbone = AutoModel.from_pretrained(MODEL_DIR, local_files_only=True, trust_remote_code=False, dtype=torch.float32).cpu().eval()
    old_head = previous.read("data/models/sms_completion_encoder_v1_candidate.json")
    head = torch.nn.Linear(384, 1).eval()
    with torch.no_grad():
        head.weight.copy_(torch.tensor([old_head["weights"]], dtype=torch.float32))
        head.bias.copy_(torch.tensor([old_head["intercept"]], dtype=torch.float32))
    encoder_params, head_params = configure(backbone, head)
    if sum(x.numel() for x in encoder_params) != 3548928 or sum(x.numel() for x in head_params) != 385:
        raise ValueError("Trainable parameter count differs")
    initial_hashes = tensor_hashes(backbone)

    def embed(texts):
        tokens = tokenizer([normalize(t) for t in texts], truncation=False, padding=True, return_tensors="pt")
        hidden = backbone(**tokens).last_hidden_state
        mask = tokens["attention_mask"].unsqueeze(-1).expand(hidden.size()).float()
        return (hidden * mask).sum(1) / mask.sum(1).clamp(min=1e-9)

    scored_ids = set()

    def candidate_scores(rows):
        scored_ids.update(r["recordId"] for r in rows)
        scores = []
        with torch.inference_mode():
            for i in range(0, len(rows), 16):
                scores.extend(head(embed([r["text"] for r in rows[i:i+16]])).flatten().tolist())
        if not all(np.isfinite(scores)):
            raise ValueError("Non-finite candidate logits")
        return scores

    initial_rows = [r for name, group in evaluations.items() if name != "scopeDevelopment" for r in group]
    initial_scores = candidate_scores(initial_rows)
    old_report = previous.read("data/reports/transactions/sms_completion_encoder_v1.json")
    old_scores = [r["score"] for group in old_report["evaluations"].values() for r in group["rows"]]
    initial_gap = max(abs(a-b) for a, b in zip(initial_scores, old_scores))
    if len(initial_scores) != len(old_scores) or initial_gap > 2e-5 or any((a > 0) != (b > 0) for a, b in zip(initial_scores, old_scores)):
        raise ValueError("Copied head initial scores differ")
    generator = torch.Generator(device="cpu").manual_seed(settings["seed"])
    orders = [torch.randperm(len(training), generator=generator).tolist() for _ in range(settings["epochs"])]
    environment = {name: importlib.metadata.version(name) for name in ("torch", "transformers", "numpy", "safetensors", "tokenizers")}
    binding = dict(protocolSha256=previous.digest(PROTOCOL), producerSha256=previous.digest(Path(__file__)),
        frozenInputs=p["frozenInputs"], environment=environment, initialEncoderTensorHashes=initial_hashes,
        tokenizerAssets=old_flight["assets"], baseSha256=p["architecture"]["baseSafetensorsSha256"])
    optimizer = torch.optim.AdamW([dict(params=encoder_params, lr=settings["backboneLearningRate"]), dict(params=head_params, lr=settings["headLearningRate"])],
        betas=tuple(settings["betas"]), eps=settings["epsilon"], weight_decay=settings["weightDecay"], foreach=False, fused=False, amsgrad=False)
    optimizer_ids = {id(x) for group in optimizer.param_groups for x in group["params"]}
    if optimizer_ids != {id(x) for x in encoder_params + head_params}:
        raise ValueError("Optimizer parameter selection mismatch")
    write_new(ATTEMPT, dict(runId=RUN, ownerApproval=p["ownerApproval"], trainingRuns=1, binding=binding,
        rowIds=[r["recordId"] for r in training], epochRowOrders=orders, initialHead=old_head, initialScoreGap=initial_gap,
        maximumTokenizerLength=max(token_lengths), trainingStartedMonotonic=time.monotonic()))
    epoch_losses, steps = [], 0
    for epoch, order in enumerate(orders):
        loss_sum = 0.0
        for start in range(0, len(order), settings["batchSize"]):
            batch = [training[k] for k in order[start:start+settings["batchSize"]]]
            optimizer.zero_grad(set_to_none=True)
            logits = head(embed([r["text"] for r in batch])).flatten()
            target = torch.tensor([int(r["target"] == "completed") for r in batch], dtype=torch.float32)
            weight = torch.tensor([r["weight"] for r in batch], dtype=torch.float32)
            weighted = weight * torch.nn.functional.binary_cross_entropy_with_logits(logits, target, reduction="none")
            loss = weighted.sum() * (len(training) / (129 * len(batch)))
            if not torch.isfinite(loss):
                raise ValueError("Non-finite training loss")
            loss.backward()
            if any(x.grad is not None for name, x in backbone.named_parameters() if not selected(name)):
                raise ValueError("Frozen tensor received gradient")
            if any(x.grad is None or not torch.isfinite(x.grad).all() for x in encoder_params + head_params):
                raise ValueError("Missing/non-finite trainable gradient")
            torch.nn.utils.clip_grad_norm_(encoder_params + head_params, settings["clipGlobalGradientNorm"], error_if_nonfinite=True)
            optimizer.step()
            if any(not torch.isfinite(x).all() for x in encoder_params + head_params):
                raise ValueError("Non-finite updated tensor")
            loss_sum += float(weighted.detach().sum())
            steps += 1
        epoch_losses.append(loss_sum / 129)
        print(json.dumps(dict(epoch=epoch+1, optimizerSteps=steps, trainingLoss=epoch_losses[-1])), flush=True)
    if steps != settings["maximumOptimizerSteps"]:
        raise ValueError("Incomplete prescribed training")
    write_new(CACHE / "training_done.json", dict(finishedMonotonic=time.monotonic(), steps=steps))
    final_hashes = tensor_hashes(backbone)
    if any(final_hashes[name] != sha for name, sha in initial_hashes.items() if not selected(name)):
        raise ValueError("Frozen encoder parameters changed")
    delta = {"backbone."+name: value.detach().contiguous() for name, value in backbone.named_parameters() if selected(name)}
    delta.update({"head."+name: value.detach().contiguous() for name, value in head.named_parameters()})
    save_file(delta, str(CACHE / "final.safetensors"), metadata={"baseSha256": binding["baseSha256"], "runId": RUN})
    before_reload = candidate_scores(initial_rows)
    loaded = load_file(str(CACHE / "final.safetensors"))
    if set(loaded) != set(delta) or any(not torch.equal(loaded[name], value) for name, value in delta.items()):
        raise ValueError("Delta reload differs")
    # Rebuild from the pinned base and apply only declared replacement tensors.
    del optimizer, encoder_params, head_params, delta
    import gc
    del backbone
    gc.collect()
    backbone = AutoModel.from_pretrained(MODEL_DIR, local_files_only=True, trust_remote_code=False, dtype=torch.float32).cpu().eval()
    with torch.no_grad():
        for name, value in backbone.named_parameters():
            if selected(name): value.copy_(loaded["backbone."+name])
        for name, value in head.named_parameters(): value.copy_(loaded["head."+name])
    if candidate_scores(initial_rows) != before_reload:
        raise ValueError("Reconstructed candidate logits differ")
    word = SmsSemanticsModel(previous.read("data/models/sms_semantics_followup_v1_word_candidate.json"))
    context = SmsCompletionContextModel(previous.read("data/models/sms_completion_context_v1_candidate.json"))
    import numpy as np
    # Old embeddings are not reusable after adaptation; reload the pinned base for reference only.
    candidate_backbone = backbone
    reference_backbone = AutoModel.from_pretrained(MODEL_DIR, local_files_only=True, trust_remote_code=False, dtype=torch.float32).cpu().eval()
    manual_texts = {r["text"] for r in evaluations["exposedManual"]}

    def evaluate(group):
        nonlocal backbone
        backbone = candidate_backbone
        candidate = candidate_scores(group)
        backbone = reference_backbone
        frozen_scores = []
        with torch.inference_mode():
            for i in range(0, len(group), 16):
                vectors = embed([r["text"] for r in group[i:i+16]]).numpy()
                for vector in vectors:
                    score = old_head["intercept"]
                    for w, v in zip(old_head["weights"], vector): score += w * float(v)
                    frozen_scores.append(score)
        backbone = candidate_backbone
        outputs = []
        for row, cand, frozen in zip(group, candidate, frozen_scores):
            outputs.append(dict(recordId=row["recordId"], target=row["target"], language=row.get("language") or ("ar" if any("\u0600" <= c <= "\u06ff" for c in row["text"]) else "en"),
                candidate=cand, encoder=frozen, word=word.predict(row["text"])["heads"]["completion"]["score"],
                context=context.predict(row["text"])["heads"]["completion"]["score"], duplicatesManual=row["text"] in manual_texts,
                authoringGroupId=row.get("authoringGroupId"), semanticState=row.get("semanticState"), theme=row.get("theme")))
        metrics = {language: {name: counts([r for r in outputs if language == "all" or r["language"] == language], name) for name in ("candidate", "encoder", "word", "context")} for language in ("all", "ar", "en")}
        contrast_groups = []
        for group_id in sorted({r["authoringGroupId"] for r in outputs if r["authoringGroupId"]}):
            for language in ("ar", "en"):
                members = [r for r in outputs if r["authoringGroupId"] == group_id and r["language"] == language and r["target"] != "uncertain"]
                positive = [r["candidate"] for r in members if r["target"] == "completed"]
                negative = [r["candidate"] for r in members if r["target"] == "non_transaction"]
                contrast_groups.append(dict(group=group_id, language=language, definiteRows=len(members),
                    allCorrect=all((r["candidate"] > 0) == (r["target"] == "completed") for r in members),
                    positiveRanksAboveNegative=min(positive) > max(negative) if positive and negative else None))
        return dict(rows=outputs, metrics=metrics, contrastGroups=contrast_groups, uncertainNotBinaryScored=sum(r["target"] == "uncertain" for r in outputs))

    output = {name: evaluate(group) for name, group in evaluations.items()}
    violations = gate(output)
    reserved_output = None
    if not violations:
        reserved_output = evaluate(reserved)
    reserved_violations = [] if reserved_output is None else gate({"scopeReserved": reserved_output})
    reserved_scored_ids = sorted({r["recordId"] for r in reserved} & scored_ids)
    if violations and reserved_scored_ids:
        raise ValueError("Reserved inference occurred despite failed initial gate")
    backbone = candidate_backbone
    warm = []
    for _ in range(10):
        start = time.perf_counter()
        candidate_scores(initial_rows[:1])
        warm.append((time.perf_counter()-start)*1000)
    write_new(REPORT, dict(runId=RUN, binding=binding, optimizerSteps=steps, trainingLosses=epoch_losses,
        finalEncoderTensorHashes=final_hashes, checkpointSha256=previous.digest(CACHE / "final.safetensors"), checkpointBytes=(CACHE / "final.safetensors").stat().st_size,
        reloadScoresExact=True, frozenParametersUnchanged=True, initialScoreGap=initial_gap, evaluations=output,
        preReservedGatePassed=not violations, preReservedViolations=violations, reservedInferred=reserved_output is not None,
        reservedEvaluation=reserved_output, reservedViolations=reserved_violations, reservedScoredRecordIds=reserved_scored_ids,
        continuationGatePassed=not violations and not reserved_violations, warmCpuMilliseconds=warm,
        independentAccuracy=False, productionIntegrated=False, studentTrained=False))
    print(json.dumps(dict(preReservedGatePassed=not violations, reservedInferred=reserved_output is not None, violations=violations)), flush=True)


class MemoryCounters(ctypes.Structure):
    _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD)] + [(name, ctypes.c_size_t) for name in
        ("PeakWorkingSetSize", "WorkingSetSize", "QuotaPeakPagedPoolUsage", "QuotaPagedPoolUsage", "QuotaPeakNonPagedPoolUsage", "QuotaNonPagedPoolUsage", "PagefileUsage", "PeakPagefileUsage")]


def working_set(pid):
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    psapi = ctypes.WinDLL("psapi", use_last_error=True)
    kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    psapi.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.POINTER(MemoryCounters), wintypes.DWORD]
    handle = kernel.OpenProcess(0x0410, False, pid)
    if not handle: raise ctypes.WinError(ctypes.get_last_error())
    try:
        data = MemoryCounters()
        data.cb = ctypes.sizeof(data)
        if not psapi.GetProcessMemoryInfo(handle, ctypes.byref(data), data.cb): raise ctypes.WinError(ctypes.get_last_error())
        return int(data.WorkingSetSize)
    finally:
        kernel.CloseHandle(handle)


def resource_reason(elapsed, memory, disk, budget):
    if elapsed is not None and elapsed >= budget["trainingWallClockSeconds"]: return "training_time_limit"
    if memory > budget["processWorkingSetLimitBytes"]: return "working_set_limit"
    if disk > budget["additionalArtifactLimitBytes"]: return "artifact_limit"
    return None


def supervise():
    refuse_repeat()
    p, _, _, _ = prepare()
    CACHE.mkdir(parents=True, exist_ok=True)
    # If OS memory sampling is unavailable, stop before starting any training.
    working_set(os.getpid())
    started, peak, reason = time.monotonic(), 0, None
    env = dict(os.environ, HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1", TOKENIZERS_PARALLELISM="false")
    child = subprocess.Popen([sys.executable, "-X", "utf8", "-m", "training.transactions.completion_adaptation", "--worker"], cwd=ROOT, env=env)
    try:
        while child.poll() is None:
            try: peak = max(peak, working_set(child.pid))
            except OSError:
                if child.poll() is None: raise
            elapsed = None
            if ATTEMPT.exists() and not (CACHE / "training_done.json").exists():
                try: elapsed = time.monotonic() - read(ATTEMPT)["trainingStartedMonotonic"]
                except json.JSONDecodeError: pass  # Exclusive ledger is still being written.
            disk = sum(path.stat().st_size for path in CACHE.rglob("*") if path.is_file())
            reason = resource_reason(elapsed, peak, disk, p["budget"])
            if reason:
                child.kill()
                break
            time.sleep(1)
    except BaseException:
        child.kill()
        child.wait()
        raise
    code = child.wait()
    supervision = dict(runId=RUN, exitCode=code, stopReason=reason, peakSampledWorkingSetBytes=peak, totalElapsedSeconds=time.monotonic()-started)
    write_new(CACHE / "supervision.json", supervision)
    if reason or code or not REPORT.exists():
        if not FAILURE.exists(): write_new(FAILURE, supervision)
        raise RuntimeError("Adaptation stopped: " + str(supervision))
    print(json.dumps(supervision), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--worker", action="store_true")
    args = parser.parse_args()
    if args.worker:
        refuse_repeat()
        try: worker()
        except BaseException as error:
            if not FAILURE.exists(): write_new(FAILURE, dict(runId=RUN, error=repr(error), attempted=ATTEMPT.exists()))
            raise
    else:
        supervise()
