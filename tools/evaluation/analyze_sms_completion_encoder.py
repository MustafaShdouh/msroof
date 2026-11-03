"""Audit frozen encoder scores and training neighbours; never fit or re-encode."""
import json
from collections import Counter
from pathlib import Path

import numpy as np

from training.transactions.completion_encoder import CACHE, ROOT, RUN, digest, prepare


def analyze():
    protocol, training, cohorts = prepare()
    report_path = ROOT / "data/reports/transactions" / (RUN + ".json")
    model_path = ROOT / "data/models" / (RUN + "_candidate.json")
    report = json.loads(report_path.read_text(encoding="utf-8"))
    model = json.loads(model_path.read_text(encoding="utf-8"))
    binding = report["binding"]
    if model["binding"] != binding or digest(CACHE / "vectors.npy") != binding["vectorsSha256"] or digest(ROOT / "config/experiments" / (RUN + ".json")) != binding["protocolSha256"]:
        raise ValueError("Frozen model/vector/protocol binding changed")
    if digest(ROOT / "training/transactions/completion_encoder.py") != binding["producerSha256"]:
        raise ValueError("Original producer changed")
    vectors = np.load(CACHE / "vectors.npy").astype(np.float64)
    rows = training + [r for group in cohorts.values() for r in group]
    if vectors.shape != (len(rows), 384) or not np.isfinite(vectors).all():
        raise ValueError("Invalid vector cache")
    scores = []
    for vector in vectors:
        score = model["intercept"]
        for weight, value in zip(model["weights"], vector):
            score += weight * float(value)
        scores.append(score)
    norms = np.linalg.norm(vectors, axis=1)
    if (norms == 0).any():
        raise ValueError("Zero vector")
    unit = vectors / norms[:, None]  # Diagnostic similarity only; classifier input unchanged.
    n = len(training)
    train_errors = [dict(recordId=r["recordId"], group=r["group"], target=r["target"], score=scores[i], text=r["text"], weight=r["weight"])
                    for i, r in enumerate(training) if (scores[i] > 0) != (r["target"] == "completed")]
    analyses, offset = {}, n
    for name, group in cohorts.items():
        cases = []
        saved = report["evaluations"][name]["rows"]
        if len(saved) != len(group):
            raise ValueError("Cohort size changed")
        for j, row in enumerate(group):
            i = offset + j
            if row["recordId"] != saved[j]["recordId"] or scores[i] != saved[j]["score"]:
                raise ValueError("Saved identity/score mismatch")
            if row["target"] not in ("completed", "non_transaction"):
                continue
            similarity = unit[:n] @ unit[i]
            neighbours = {}
            for target in ("completed", "non_transaction"):
                ordered = sorted((k for k, r in enumerate(training) if r["target"] == target), key=lambda k: (-float(similarity[k]), training[k]["recordId"]))
                selected, seen = [], set()
                for k in ordered:
                    if training[k]["group"] in seen:
                        continue
                    seen.add(training[k]["group"])
                    selected.append(dict(recordId=training[k]["recordId"], group=training[k]["group"], text=training[k]["text"], cosine=float(similarity[k]), score=scores[k]))
                    if len(selected) == 3:
                        break
                neighbours[target] = selected
            cases.append(dict(**saved[j], text=row["text"], correct=saved[j]["candidate"] == row["target"], neighbours=neighbours))
        analyses[name] = cases
        offset += len(group)
    # Pair only the pre-existing matched authored probes; do not invent contrasts.
    pairs = []
    probes = cohorts["authoredProbe"]
    start = n + len(cohorts["oldExposedValidation"]) + len(cohorts["exposedManual"])
    for j, row in enumerate(probes):
        if row["target"] != "completed":
            continue
        k = next(k for k, other in enumerate(probes) if other["authoringGroupId"] == row["authoringGroupId"] and other["language"] == row["language"] and other["target"] == "non_transaction")
        pairs.append(dict(group=row["authoringGroupId"], language=row["language"], positiveId=row["recordId"], negativeId=probes[k]["recordId"],
            positiveScore=scores[start+j], negativeScore=scores[start+k], correctScoreOrdering=scores[start+j] > scores[start+k],
            cosine=float(unit[start+j] @ unit[start+k]), bothCorrect=scores[start+j] > 0 and scores[start+k] <= 0))
    result = dict(runId=RUN + "_failure_analysis", fitCalls=0, newInference=False, sourceSha256={str(p.relative_to(ROOT)): digest(p) for p in (report_path, model_path, Path(__file__))},
        caveats="All diagnostics exposed/weak. Cosine neighbours are similarities, not causal attribution or confidence. Training resubstitution is not accuracy. No threshold search.",
        trainingErrors=train_errors, trainingErrorCounts=dict(Counter(r["target"] for r in train_errors)),
        trainingErrorWeight=sum(r["weight"] for r in train_errors), cohorts=analyses, pairedProbes=pairs)
    target = ROOT / "data/reports/transactions" / (RUN + "_failure_analysis.json")
    content = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if target.exists() and target.read_text(encoding="utf-8") != content:
        raise ValueError("Analysis differs from saved result")
    if not target.exists():
        with target.open("x", encoding="utf-8") as handle:
            handle.write(content)
    print(json.dumps(dict(trainingErrors=result["trainingErrorCounts"], trainingErrorWeight=result["trainingErrorWeight"], pairedProbeBothCorrect=sum(r["bothCorrect"] for r in pairs), pairedProbeCorrectOrdering=sum(r["correctScoreOrdering"] for r in pairs), pairs=len(pairs)), ensure_ascii=False))


if __name__ == "__main__":
    analyze()
