"""Before/after complete-result proof for the R3 structural extraction."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
from src.python.engine import MasroofEngine
from training.corpus_io import ROOT,write_immutable
from training.evaluation.behavior import canonical_result
from tools.node_runtime import node_executable

AREA=ROOT/".local-backups/core_money_r3"


def legacy_result(engine,inp):
    try:return canonical_result(engine.predict(inp.get("sender") or "",inp["text"],inp.get("isContact",False)))
    except (TypeError,ValueError) as error:return dict(legacyError=type(error).__name__,message=str(error))


def snapshot(phase, policy_report=None):
    sources=["tests/fixtures/core_money_v1.json","tests/fixtures/detailed_assessment_cases.json",
        "tests/fixtures/transaction_behavior_cases.json","tests/fixtures/authorization_request_cases.json",
        "tests/fixtures/quoted_example_cases.json","tests/fixtures/sanitized_v1/test_suite_cases.json",
        "tests/fixtures/sanitized_v1/qa_adversarial_cases.json"]
    cases=[];seen=set()
    for relative in sources:
        data=json.loads((ROOT/relative).read_text(encoding="utf-8"))
        for i,row in enumerate(data.get("cases",data.get("testCases")) if isinstance(data,dict) else data):
            request=row.get("input",dict(text=row.get("text",row.get("body"))))
            if "text" not in request:request=dict(request,text=request.get("body"))
            if request["text"] is None and not relative.endswith("core_money_v1.json"):raise ValueError("Unsupported snapshot case shape: "+relative)
            scripts=("0123456789","٠١٢٣٤٥٦٧٨٩","۰۱۲۳۴۵۶۷۸۹") if relative.endswith("core_money_v1.json") else ("0123456789",)
            for script in scripts:
                inp=dict(request)
                if isinstance(inp["text"],str):inp["text"]=inp["text"].translate(str.maketrans("0123456789",script))
                key=json.dumps(inp,ensure_ascii=False,sort_keys=True)
                if key in seen:continue
                seen.add(key);cases.append(dict(id=str(len(cases)),input=inp))
    result=subprocess.run([node_executable(),str(ROOT/"tools/evaluation/probe_detailed.ts")],input=json.dumps(dict(cases=cases)),capture_output=True,text=True,encoding="utf-8",cwd=ROOT,check=True)
    other=json.loads(result.stdout)["rows"];engine=MasroofEngine();outputs=[]
    for case,row in zip(cases,other,strict=True):
        py=engine.predict_detailed(case["input"])
        assert py==row["typescript"]==row["browser"],case["id"]
        inp=case["input"]
        outputs.append(dict(input=inp,python=py,typescript=row["typescript"],browser=row["browser"],
            legacyPython=legacy_result(engine,inp),
            legacyTypescript=row["legacyTypescript"],legacyBrowser=row["legacyBrowser"]))
    models={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT/"data/models").glob("*") if p.is_file()}
    output=dict(rows=outputs,models=models,fixtureHashes={r:hashlib.sha256((ROOT/r).read_bytes()).hexdigest() for r in sources})
    AREA.mkdir(parents=True,exist_ok=True)
    if phase=="after":assert output==json.loads((AREA/"before.json").read_text(encoding="utf-8")),"Structural refactor changed complete results, fixture or model bytes"
    if phase=="policy":
        before=json.loads((AREA/"before.json").read_text(encoding="utf-8"))
        assert output['models']==before['models'] and output['fixtureHashes']==before['fixtureHashes']
        assert len(outputs)==len(before['rows'])
        for a,b in zip(outputs,before['rows']):
            assert a['input']==b['input']
            for key in ('legacyPython','legacyTypescript','legacyBrowser'):assert a[key]==b[key]
        summary=dict(cases=len(outputs),structuralFullOutputEqualities=len(outputs)*6,
            postPolicyDetailedChangedInputIndices=[i for i,(a,b) in enumerate(zip(outputs,before['rows'])) if a['python']!=b['python']],
            legacyOutputsUnchanged=True,modelArtifactsUnchanged=len(models),independentAccuracy=False,reservedInferred=False)
        write_immutable(policy_report or ROOT/'data/reports/behavior/core_money_r3_integrity.json',json.dumps(summary,indent=2)+'\n')
    write_immutable(AREA/(phase+".json"),json.dumps(output,ensure_ascii=False,indent=2)+"\n")
    print(json.dumps(dict(phase=phase,cases=len(outputs),completeOutputsPerCase=6,models=len(models),equalToBefore=phase=="after")))


if __name__=="__main__":
    parser=argparse.ArgumentParser();parser.add_argument("phase",choices=("before","after","policy"));snapshot(parser.parse_args().phase)
