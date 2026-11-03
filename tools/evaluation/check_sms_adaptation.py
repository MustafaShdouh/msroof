"""Check frozen adaptation evidence without fitting or reserved inference."""
import hashlib

from training.transactions.completion_adaptation import (ROOT, CACHE, PROTOCOL, ATTEMPT, REPORT, FAILURE,
    prepare, read, gate, counts, selected)
from training.transactions.completion_encoder import digest


def check():
    from safetensors.torch import load_file
    import numpy as np
    p, training, evaluations, reserved = prepare()
    report, attempt = read(REPORT), read(ATTEMPT)
    assert not FAILURE.exists(), "Failure record exists"
    assert attempt["binding"] == report["binding"]
    binding = report["binding"]
    assert digest(PROTOCOL) == binding["protocolSha256"]
    assert digest(ROOT / "training/transactions/completion_adaptation.py") == binding["producerSha256"]
    assert attempt["rowIds"] == [r["recordId"] for r in training]
    assert len(attempt["epochRowOrders"]) == 3
    for order in attempt["epochRowOrders"]:
        assert sorted(order) == list(range(len(training)))
    assert report["optimizerSteps"] == 435
    assert len(report["trainingLosses"]) == 3
    assert report["initialScoreGap"] <= 2e-5
    assert report["reloadScoresExact"] and report["frozenParametersUnchanged"]
    before = binding["initialEncoderTensorHashes"]
    after = report["finalEncoderTensorHashes"]
    assert before.keys() == after.keys()
    assert all(sha == after[name] for name, sha in before.items() if not selected(name))
    delta_path = CACHE / "final.safetensors"
    assert digest(delta_path) == report["checkpointSha256"]
    delta = load_file(str(delta_path))
    expected = {"backbone."+name for name in before if selected(name)} | {"head.weight", "head.bias"}
    assert delta.keys() == expected
    assert sum(t.numel() for t in delta.values()) == 3549313
    for name in before:
        if selected(name):
            assert hashlib.sha256(delta["backbone."+name].numpy().tobytes()).hexdigest() == after[name]
    assert all(bool(t.isfinite().all()) for t in delta.values())
    if report["reservedInferred"]:
        assert report["preReservedGatePassed"]
        evaluations["scopeReserved"] = reserved
        groups = dict(report["evaluations"], scopeReserved=report["reservedEvaluation"])
        assert sorted(r["recordId"] for r in reserved) == report["reservedScoredRecordIds"]
    else:
        groups = report["evaluations"]
        assert report["reservedEvaluation"] is None and not report["reservedScoredRecordIds"]
    assert set(groups) == set(evaluations)
    for name, cohort in groups.items():
        assert [r["recordId"] for r in cohort["rows"]] == [r["recordId"] for r in evaluations[name]]
        for row in cohort["rows"]:
            assert all(np.isfinite(row[k]) for k in ("candidate", "encoder", "word", "context"))
        for language, metrics in cohort["metrics"].items():
            subset = [r for r in cohort["rows"] if language == "all" or r["language"] == language]
            assert all(counts(subset, key) == value for key, value in metrics.items())
        assert sum(r["target"] == "uncertain" for r in cohort["rows"]) == cohort["uncertainNotBinaryScored"]
    violations = gate(report["evaluations"])
    assert violations == report["preReservedViolations"]
    assert (not violations) == report["preReservedGatePassed"]
    assert report["reservedInferred"] == (not violations)
    if violations:
        assert not report["continuationGatePassed"]
    supervision = read(CACHE / "supervision.json")
    assert supervision["exitCode"] == 0 and supervision["stopReason"] is None
    audit = read(ROOT / "data/reports/transactions/sms_completion_adaptation_v1_resource_audit.json")
    assert digest(CACHE / "supervision.json") == audit["originalSupervisionSha256"]
    assert audit["memoryBudgetVerified"] is False
    assert audit["actualTrainingPeakWorkingSetBytes"] is None
    assert audit["trainingWithinWallBudget"]
    assert not report["productionIntegrated"] and not report["studentTrained"] and not report["independentAccuracy"]
    return dict(optimizerSteps=435, checkpointParameters=3549313, frozenHashesVerified=True,
        preReservedGatePassed=report["preReservedGatePassed"], reservedInferred=report["reservedInferred"],
        continuationGatePassed=report["continuationGatePassed"], memoryBudgetVerified=False,
        resourceMonitorNonconformant=True)


if __name__ == "__main__":
    import json
    print(json.dumps(check()))
