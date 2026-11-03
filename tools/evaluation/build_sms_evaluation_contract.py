"""Versioned metadata/saved-score slices; no fitting or new inference."""
from collections import Counter
import json
from pathlib import Path
from training.transactions import factorization_comparison_v2 as trial
from training.evaluation.content_preflight import preflight, sha

CONTRACT = trial.ROOT / "config/contracts/sms_diagnostic_evaluation_v1.json"
OUTPUT = trial.AREA / "sms_diagnostic_evaluation_v1.json"


def build():
    _, training, cohorts, _ = trial.protocol()
    report = trial.old.read(trial.REPORT)
    assert report["binding"] == trial.binding()
    assert not report["reservedInferred"] and not report["reservedScoredRecordIds"]
    diagnostics, saved = [], {}
    for name, rows in cohorts.items():
        scored = report["evaluations"][name]["rows"]
        assert len(rows) == len(scored)
        for raw, result in zip(rows, scored):
            assert raw["recordId"] == result["recordId"]
            assert sha(raw["text"]) == result["textSha256"] and raw["target"] == result["target"]
            diagnostics.append(dict(raw, cohort=name))
            saved[name + "/" + raw["recordId"]] = result
    metadata = preflight(training, diagnostics, trial.old.read(CONTRACT))
    slices = {}
    for field in ("role", "uncertaintyReason"):
        slices[field] = {}
        for value in sorted({r[field] for r in metadata if r[field] is not None}):
            selected = [saved[r["cohort"]+"/"+r["recordId"]] for r in metadata if r[field] == value]
            slices[field][value] = {
                lang: {model: trial.metrics([r for r in selected if lang == "all" or r["language"] == lang], model)
                       for model in ("direct_status", "factorized")}
                for lang in ("all", "ar", "en")}
    duplicates = Counter(r["textSha256"] for r in metadata)
    result = dict(schemaVersion="1.0.0", records=metadata, savedScoreSlices=slices,
        rows=len(metadata), uniqueTexts=len(duplicates),
        crossCohortDuplicateTexts={k:v for k,v in duplicates.items() if v > 1},
        inputs={p.relative_to(trial.ROOT).as_posix():trial.encoder.digest(p) for p in
            (CONTRACT, trial.REPORT, Path(__file__), trial.ROOT/"training/evaluation/content_preflight.py")},
        trainingViewSha256=trial.old.read(trial.PROTOCOL)["cohort"]["trainingViewSha256"],
        labelsChanged=0, fitting=False, newInference=False, reservedInferred=False,
        historicalMetricsAndGatesUnchanged=True, independentAccuracy=False,
        limitations=["Slices count cohort entries; two manual/quote duplicate texts are listed, not independent samples.",
                     "Raw/normalized disjointness does not establish template/family or real-world independence.",
                     "Reason metadata are assistant-reviewed weak evaluation descriptions, not human gold or model features.",
                     "This is a new evaluation view; it does not retroactively alter gates or measured historical results."])
    content = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if OUTPUT.exists():
        assert OUTPUT.read_bytes() == content.encode("utf-8"), "Saved evaluation metadata changed"
    else:
        with OUTPUT.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
    return result


if __name__ == "__main__":
    r = build()
    print(json.dumps(dict(rows=r["rows"], uniqueTexts=r["uniqueTexts"],
        roles=dict(Counter(x["role"] for x in r["records"])),
        uncertaintyReasons=dict(Counter(x["uncertaintyReason"] for x in r["records"] if x["uncertaintyReason"])))))
