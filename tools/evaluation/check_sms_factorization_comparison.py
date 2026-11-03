"""Verify the paired experiment's saved evidence without fitting or encoding texts."""
import hashlib
from pathlib import Path

from training.transactions import factorization_comparison as trial
from training.transactions.completion_encoder import digest


def check_failure(trial=trial):
    """Audit retained partial evidence; never encode, resume, or fit a candidate."""
    import json
    from safetensors.torch import load_file

    _, training, cohorts, reserved = trial.protocol()
    master = trial.old.read(trial.MASTER)
    failure = trial.old.read(trial.FAILURE)
    assert master["binding"] == trial.binding()
    assert failure["completedMonitors"] == {}
    assert failure["error"].startswith("FileNotFoundError(")
    assert not trial.REPORT.exists()
    assert not (trial.CACHE / "supervision.json").exists()
    assert not (trial.CACHE / "direct_status_monitor/result.json").exists()
    assert not (trial.CACHE / "direct_status/result.json").exists()
    assert not (trial.CACHE / "factorized").exists()
    assert not (trial.CACHE / "factorized_monitor").exists()
    assert not (trial.CACHE / "evaluation_monitor").exists()
    root = trial.CACHE / "direct_status"
    attempt = trial.old.read(root / "attempt.json")
    assert attempt["binding"] == trial.binding()
    assert attempt["zeroHeads"]
    assert attempt["trainingRecordIds"] == [r["recordId"] for r in training]
    assert len(attempt["epochOrders"]) == 3
    for order in attempt["epochOrders"]:
        assert sorted(order) == list(range(len(training)))
    log = trial.CACHE / "direct_status_monitor/output.log"
    epochs = [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines()
              if line.startswith('{"arm":')]
    assert [row["epoch"] for row in epochs] == [1, 2, 3]
    assert [row["steps"] for row in epochs] == [148, 296, 444]
    import math
    assert all(math.isfinite(row["trainingLoss"]) for row in epochs)
    checkpoint = root / "final.safetensors"
    tensors = load_file(str(checkpoint))
    expected = {"backbone." + n for n in attempt["initialEncoderHashes"] if trial.old.selected(n)}
    expected |= {"head.status.weight", "head.status.bias"}
    assert tensors.keys() == expected
    assert sum(t.numel() for t in tensors.values()) == 3550083
    assert tuple(tensors["head.status.weight"].shape) == (3, 384)
    assert tuple(tensors["head.status.bias"].shape) == (3,)
    assert all(bool(t.isfinite().all()) for t in tensors.values())
    journal = [json.loads(line) for line in (trial.CACHE/"inference_journal.jsonl").read_text(encoding="utf-8").splitlines()]
    assert len(journal) == 1
    assert journal[0] == dict(model="direct_status", cohort="training_sentinels",
                              intendedRecordIds=[r["recordId"] for r in training[:8]])
    exposed = {rid for row in journal for rid in row["intendedRecordIds"]}
    assert not exposed & {r["recordId"] for rows in cohorts.values() for r in rows}
    assert not exposed & {r["recordId"] for r in reserved}
    try:
        trial.run()
    except ValueError as error:
        assert str(error) == "Comparison already attempted; no retry"
    else:
        raise AssertionError("Consumed attempt did not refuse reexecution")
    audit = dict(
        runId=trial.RUN, outcome="infrastructure_failure_before_comparison",
        trainingViewAndFrozenInputsVerified=True, loggedControlOptimizerSteps=444,
        controlTrainingLosses=[row["trainingLoss"] for row in epochs],
        controlCheckpointSha256=digest(checkpoint), controlCheckpointBytes=checkpoint.stat().st_size,
        controlCheckpointTrainableParameters=3550083, checkpointTensorSetAndFinitenessVerified=True,
        checkpointReloadVerified=False, frozenParameterPostTrainingHashesVerified=False,
        factorizedArmStarted=False, diagnosticEvaluationStarted=False,
        reservedInferred=False, reservedScoredRecordIds=[],
        resourcePeaksAndElapsedVerified=False, comparisonQualityMeasured=False,
        productionIntegrated=False, studentTrained=False, independentAccuracy=False,
        originalEvidencePreserved=True, retryRefusalVerified=True,
        originalMonitorSha256=digest(trial.ROOT/"tools/evaluation/python_worker_monitor.py"))
    path = trial.AREA / (trial.RUN + "_failure_audit.json")
    if path.exists():
        assert trial.old.read(path) == audit
    else:
        trial.write_new(path, audit)
    return audit


def check(trial=trial):
    if trial.FAILURE.exists():
        return check_failure(trial)
    import numpy as np
    from safetensors.torch import load_file
    p,training,cohorts,reserved=trial.protocol()
    report=trial.old.read(trial.REPORT)
    master=trial.old.read(trial.MASTER)
    assert not trial.FAILURE.exists()
    assert report["binding"]==master["binding"]==trial.binding()
    arm_ledgers=[]
    for name in ("direct_status","factorized"):
        root=trial.CACHE/name
        attempt=trial.old.read(root/"attempt.json")
        result=trial.old.read(root/"result.json")
        assert result==report["arms"][name]
        assert attempt["binding"]==result["binding"]==trial.binding()
        assert result["optimizerSteps"]==444 and len(result["trainingLosses"])==3
        assert np.isfinite(result["trainingLosses"]).all()
        assert result["reloadExact"] and result["frozenParametersUnchanged"] and attempt["zeroHeads"]
        assert attempt["trainingRecordIds"]==[r["recordId"] for r in training]
        assert len(attempt["epochOrders"])==3
        for order in attempt["epochOrders"]: assert sorted(order)==list(range(1177))
        initial,final=attempt["initialEncoderHashes"],result["finalEncoderHashes"]
        assert initial.keys()==final.keys()
        assert all(final[n]==sha for n,sha in initial.items() if not trial.old.selected(n))
        checkpoint=root/"final.safetensors"
        assert digest(checkpoint)==result["checkpointSha256"]
        tensors=load_file(str(checkpoint))
        expected={"backbone."+n for n in initial if trial.old.selected(n)}
        expected|={"head."+field+"."+suffix for field in attempt["classes"] for suffix in ("weight","bias")}
        assert tensors.keys()==expected
        assert sum(t.numel() for t in tensors.values())==result["trainableParameters"]
        for field,labels in attempt["classes"].items():
            assert tuple(tensors["head."+field+".weight"].shape)==(len(labels),384)
            assert tuple(tensors["head."+field+".bias"].shape)==(len(labels),)
        for n in initial:
            if trial.old.selected(n): assert hashlib.sha256(tensors["backbone."+n].numpy().tobytes()).hexdigest()==final[n]
        assert all(bool(t.isfinite().all()) for t in tensors.values())
        arm_ledgers.append(attempt)
    assert arm_ledgers[0]["initialEncoderHashes"]==arm_ledgers[1]["initialEncoderHashes"]
    assert arm_ledgers[0]["epochOrders"]==arm_ledgers[1]["epochOrders"]
    groups=dict(report["evaluations"])
    if report["reservedInferred"]:
        assert report["preReservedGatePassed"]
        groups["scopeReserved"]=report["reservedEvaluation"]
        cohorts["scopeReserved"]=reserved
    else:
        assert report["reservedEvaluation"] is None and not report["reservedScoredRecordIds"]
    assert groups.keys()==cohorts.keys()
    for name,cohort in groups.items():
        assert [r["recordId"] for r in cohort["rows"]]==[r["recordId"] for r in cohorts[name]]
        for row,raw in zip(cohort["rows"],cohorts[name]):
            assert row["target"]==raw["target"]
            assert row["textSha256"]==hashlib.sha256(raw["text"].encode()).hexdigest()
            for model in ("direct_status","factorized"):
                detail=row["outputs"][model]
                classes=next(a for a in p["arms"] if a["id"]==model)
                for field,values in detail["logits"].items():
                    assert np.isfinite(values).all()
                    assert detail["labels"][field]==classes[field+"Classes"][int(np.argmax(values))]
                expected=detail["labels"]["status"] if model=="direct_status" else trial.view.compose_status(detail["labels"]["context"],detail["labels"]["event"])
                assert detail["status"]==expected
            for model in trial.REFERENCES:
                assert row["outputs"][model]["uncertaintySupported"] is False
                if "score" in row["outputs"][model]:
                    score=row["outputs"][model]["score"]
                    assert np.isfinite(score)
                    assert row["outputs"][model]["status"]==("completed" if score>0 else "non_transaction")
        for lang,metrics in cohort["metrics"].items():
            selected=[r for r in cohort["rows"] if lang=="all" or r["language"]==lang]
            for model,value in metrics.items(): assert trial.metrics(selected,model)==value
    components=trial.component_metrics(groups["scopeDevelopment"]["rows"],trial.view.development_reviews())
    assert components==report["componentDevelopment"]
    violations,fixes=trial.gate(report["evaluations"],components)
    assert violations==report["preReservedViolations"] and fixes==report["uniqueStatusFixesVsControl"]
    assert report["preReservedGatePassed"]==(not violations)
    assert report["reservedInferred"]==(not violations)
    journal=[trial.json.loads(l) for l in (trial.CACHE/"inference_journal.jsonl").read_text(encoding="utf-8").splitlines()]
    reserved_ids={r["recordId"] for r in reserved}
    all_scored={rid for entry in journal for rid in entry["intendedRecordIds"]}
    assert sorted(reserved_ids&all_scored)==report["reservedScoredRecordIds"]
    if violations: assert not reserved_ids&all_scored and not report["continuationGatePassed"]
    supervision=trial.old.read(trial.CACHE/"supervision.json")
    for name,monitor in supervision["workers"].items():
        identity=trial.old.read(trial.CACHE/(name+"_monitor")/"identity.json")
        assert monitor["identityVerified"] and monitor["workerPid"]==identity["pid"]
        assert monitor["exitCode"]==0 and monitor["stopReason"] is None
        assert 0<monitor["peakSampledWorkerWorkingSetBytes"]<=6*1024**3
        assert monitor["peakSampledArtifactBytes"]<=2*1024**3
        assert monitor["elapsedSeconds"]<=(240 if name=="evaluation" else 480)
    assert supervision["totalWorkerElapsedSeconds"]<=1200
    assert not report["productionIntegrated"] and not report["studentTrained"] and not report["independentAccuracy"]
    return dict(optimizerSteps=888,initialEncoderAndEpochOrdersMatched=True,checkpointsAndFrozenTensorsVerified=True,
        metricsAndGatesVerified=True,actualInterpreterMonitoringVerified=True,reservedInferred=report["reservedInferred"],
        preReservedGatePassed=report["preReservedGatePassed"])


if __name__=="__main__":
    import json
    print(json.dumps(check()))
