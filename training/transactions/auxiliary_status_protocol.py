"""Validate the proposed objective and inputs; no task model construction or fit."""
from collections import Counter
from fractions import Fraction
import json
from pathlib import Path

from training.transactions import factorization_comparison_v2 as previous
from training.evaluation.content_preflight import preflight

ROOT = previous.ROOT
PROTOCOL = ROOT / "config/experiments/sms_auxiliary_status_v1.json"
OUTPUT = ROOT / "data/reports/transactions/sms_auxiliary_status_v1_design_preflight.json"


def combine_losses(per_head):
    """Combine unreduced, already class-balanced CE; apply group weights afterward."""
    if set(per_head) != {"status", "context", "event"}:
        raise ValueError("Exactly three declared losses required")
    if len({tuple(x.shape) for x in per_head.values()}) != 1:
        raise ValueError("Per-head loss shapes must match; broadcasting forbidden")
    return per_head["status"] * (5/6) + per_head["context"] * (1/12) + per_head["event"] * (1/12)


def validate():
    p = previous.old.read(PROTOCOL)
    old = previous.old.read(previous.PROTOCOL)
    for path, expected in p["frozenInputs"].items():
        if previous.encoder.digest(ROOT/path) != expected:
            raise ValueError("Frozen input changed: " + path)
    _, rows, cohorts, _ = previous.protocol()
    assert p["architecture"] == old["architecture"]
    assert p["cohort"]["trainingViewSha256"] == old["cohort"]["trainingViewSha256"]
    assert p["training"]["classReweighting"] == old["training"]["classReweighting"]
    for field in ("status", "context", "event"):
        assert p["heads"][field] == next(a[field+"Classes"] for a in old["arms"] if field+"Classes" in a)
    for key in ("seed", "epochs", "batchSize", "encoderLearningRate", "headLearningRate", "optimizer", "betas", "epsilon", "weightDecay", "gradientClipGlobalNorm"):
        assert p["training"][key] == old["training"][key]
    assert p["lossCoefficients"] == dict(status="5/6", context="1/12", event="1/12")
    assert sum(Fraction(x) for x in p["lossCoefficients"].values()) == 1
    assert 3548928 + sum((384+1)*len(labels) for labels in p["heads"].values()) == p["parameters"]["totalTrainable"] == 3553933
    assert p["training"]["maximumOptimizerSteps"] == 444 and p["proposedTrainingRuns"] == 1
    assert p["trainingRunsAuthorized"] == 0 and p["ownerApproval"] is None
    assert not p["evaluation"]["reservedInferenceAuthorized"] and not p["evaluation"]["merchantFinalInferenceAuthorized"]
    metadata = preflight(rows, [dict(r, cohort=name) for name, values in cohorts.items() for r in values],
                         previous.old.read(ROOT/p["evaluation"]["contract"]))
    attempt = previous.old.read(ROOT/".local-backups/sms_factorization_comparison_v2/direct_status/attempt.json")
    result = previous.old.read(ROOT/".local-backups/sms_factorization_comparison_v2/direct_status/result.json")
    assert attempt["trainingRecordIds"] == [r["recordId"] for r in rows]
    assert result["optimizerSteps"] == 444 and result["reloadExact"] and result["frozenParametersUnchanged"]
    assert previous.encoder.digest(ROOT/".local-backups/sms_factorization_comparison_v2/direct_status/final.safetensors") == result["checkpointSha256"]
    assert not (ROOT/p["outputs"]["cache"]).exists()
    return dict(runId=p["runId"], status="design_preflight_only", trainingRows=len(rows),
        trainingViewSha256=p["cohort"]["trainingViewSha256"], diagnosticEntries=len(metadata),
        roles=dict(Counter(r["role"] for r in metadata)), totalTrainableParameters=3553933,
        proposedOptimizerSteps=444, proposedTrainingRuns=1, trainingRunsAuthorized=0,
        training=False, newModelInference=False, reservedInferred=False,
        protocolSha256=previous.encoder.digest(PROTOCOL), validatorSha256=previous.encoder.digest(Path(__file__)))


if __name__ == "__main__":
    result = validate()
    content = json.dumps(result, indent=2) + "\n"
    if OUTPUT.exists():
        assert OUTPUT.read_bytes() == content.encode("utf-8"), "Design preflight differs"
    else:
        with OUTPUT.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
    print(json.dumps(result))
