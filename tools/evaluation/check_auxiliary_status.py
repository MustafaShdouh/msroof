"""Audit saved execution evidence without fitting or encoder inference."""
import hashlib
import json
import math
from training.transactions import auxiliary_status as t
from training.transactions import factorization_comparison_v2 as prior


def check():
    from safetensors.torch import load_file
    p,training,cohorts,reserved=t.protocol()
    r=t.old.read(t.REPORT); result=t.old.read(t.CACHE/"direct_status/result.json")
    attempt=t.old.read(t.CACHE/"direct_status/attempt.json")
    assert r["binding"]==result["binding"]==attempt["binding"]==t.binding()==t.old.read(t.MASTER)["binding"]
    assert not t.FAILURE.exists() and result==r["training"]
    control=t.old.read(prior.CACHE/"direct_status/attempt.json")
    assert attempt["initialEncoderHashes"]==control["initialEncoderHashes"]
    assert attempt["epochOrders"]==control["epochOrders"]
    assert attempt["trainingRecordIds"]==control["trainingRecordIds"]==[x["recordId"] for x in training]
    assert result["optimizerSteps"]==444 and result["reloadExact"] and result["frozenParametersUnchanged"]
    assert result["trainableParameters"]==3553933 and attempt["zeroHeads"]
    assert len(result["trainingLosses"])==3 and all(math.isfinite(x) for x in result["trainingLosses"])
    assert all(result["finalEncoderHashes"][n]==sha for n,sha in attempt["initialEncoderHashes"].items() if not t.old.selected(n))
    checkpoint=t.CACHE/"direct_status/final.safetensors"
    assert t.encoder.digest(checkpoint)==result["checkpointSha256"]
    tensors=load_file(str(checkpoint))
    expected={"backbone."+n for n in attempt["initialEncoderHashes"] if t.old.selected(n)}
    expected|={"head."+field+"."+suffix for field in p["heads"] for suffix in ("weight","bias")}
    assert set(tensors)==expected and sum(v.numel() for v in tensors.values())==3553933
    assert all(bool(x.isfinite().all()) for x in tensors.values())
    for field,classes in p["heads"].items():
        assert tuple(tensors["head."+field+".weight"].shape)==(len(classes),384)
        assert tuple(tensors["head."+field+".bias"].shape)==(len(classes),)
    for n in attempt["initialEncoderHashes"]:
        if t.old.selected(n):assert hashlib.sha256(tensors["backbone."+n].numpy().tobytes()).hexdigest()==result["finalEncoderHashes"][n]
    original=t.old.read(prior.REPORT); proxy={}
    for name,raws in cohorts.items():
        cohort=r["evaluations"][name];rows=cohort["rows"]
        assert len(rows)==len(raws)
        for raw,row,reference in zip(raws,rows,original["evaluations"][name]["rows"]):
            assert row["recordId"]==raw["recordId"] and row["target"]==raw["target"]
            assert row["textSha256"]==hashlib.sha256(raw["text"].encode()).hexdigest()
            for model in prior.MODELS:assert row["outputs"][model]==reference["outputs"][model]
            candidate=row["outputs"]["candidate"]
            for field,values in candidate["logits"].items():
                assert all(math.isfinite(v) for v in values)
                assert candidate["labels"][field]==p["heads"][field][max(range(len(values)),key=values.__getitem__)]
            assert candidate["status"]==candidate["labels"]["status"]
        for lang,metrics in cohort["metrics"].items():
            selected=[x for x in rows if lang=="all" or x["language"]==lang]
            for model,counts in metrics.items():assert counts==t.metrics(selected,model)
        outputs={m:[x["outputs"]["candidate" if m=="factorized" else m] for x in rows] for m in prior.MODELS}
        proxy[name]=prior.cohort_result(raws,outputs)
    failures,fixes=prior.gate(proxy,components=None)
    assert failures==r["gateViolations"] and fixes==r["uniquePrimaryFixes"]
    assert r["developmentGatePassed"]==(not failures)
    assert prior.component_metrics(proxy["scopeDevelopment"]["rows"],t.view.development_reviews())==r["componentDevelopment"]
    from training.evaluation.content_preflight import preflight
    metadata=preflight(training,[dict(x,cohort=name) for name,rows in cohorts.items() for x in rows],t.old.read(t.ROOT/p["evaluation"]["contract"]))
    assert metadata==r["metadata"]
    index={(x["cohort"],x["recordId"]):x for x in metadata}
    for field,slices in r["savedScoreSlices"].items():
        assert set(slices)=={x[field] for x in metadata if x[field] is not None}
        for value,langs in slices.items():
            rows=[x for name,c in r["evaluations"].items() for x in c["rows"] if index[(name,x["recordId"])][field]==value]
            for lang,models in langs.items():
                for model,counts in models.items():assert counts==t.metrics([x for x in rows if lang=="all" or x["language"]==lang],model)
    entries=[json.loads(l) for l in (t.CACHE/"inference_journal.jsonl").read_text().splitlines()]
    assert not {x["recordId"] for x in reserved}&{rid for e in entries for rid in e["intendedRecordIds"]}
    assert not r["reservedInferred"] and not r["reservedScoredRecordIds"]
    supervision=t.old.read(t.CACHE/"supervision.json")
    for name,m in supervision["workers"].items():
        assert m["identityVerified"] and m["workerPid"]==t.old.read(t.CACHE/(name+"_monitor/identity.json"))["pid"]
        assert m["exitCode"]==0 and m["stopReason"] is None
        assert 0<m["peakSampledWorkerWorkingSetBytes"]<=6*1024**3
        assert m["peakSampledArtifactBytes"]<=2*1024**3 and m["elapsedSeconds"]<=(480 if name=="training" else 240)
    assert supervision["totalWorkerElapsedSeconds"]<=720
    return dict(checkpointsAndFrozenTensorsVerified=True,baselineAndOrdersMatched=True,metricsAndGatesVerified=True,resourcesVerified=True,reservedInferred=False,developmentGatePassed=r["developmentGatePassed"])


if __name__=="__main__":print(json.dumps(check()))
