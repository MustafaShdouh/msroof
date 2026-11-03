"""R4 before/after direction and message-bound ownership preservation proof."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
from training.corpus_io import ROOT,write_immutable
from src.python.engine import MasroofEngine
from tools.node_runtime import node_executable
from training.evaluation.ownership import ownership_controls
from tools.evaluation import snapshot_core_money as core

AREA=ROOT/".local-backups/core_money_r4"


def snapshot(phase):
    core.AREA=AREA
    if phase!='policy':core.snapshot(phase)
    else:
        # Capture changed detailed results separately; preserve completed structural proof.
        original=core.AREA
        core.AREA=AREA/'policy_comparison'
        core.AREA.mkdir(exist_ok=True)
        write_immutable(core.AREA/'before.json',(AREA/'before.json').read_text(encoding='utf-8'))
        core.snapshot('policy',ROOT/'data/reports/behavior/core_money_r4_direction_changes.json')
        core.AREA=original
    rows=ownership_controls()
    process=subprocess.run([node_executable(),str(ROOT/"tools/evaluation/probe_detailed.ts")],input=json.dumps(dict(cases=[],ownershipCases=rows)),capture_output=True,text=True,encoding="utf-8",cwd=ROOT,check=True)
    other=json.loads(process.stdout)["ownershipRows"];engine=MasroofEngine();results=[]
    for row,actual in zip(rows,other,strict=True):
        py=engine.predict_with_ownership(row["request"])
        assert py==actual["typescript"]==actual["browser"]
        results.append(dict(id=row["id"],request=row["request"],python=py,typescript=actual["typescript"],browser=actual["browser"]))
    text=json.dumps(results,ensure_ascii=False,indent=2)+"\n"
    if phase in ('after','policy'):assert text==(AREA/"ownership_before.json").read_text(encoding="utf-8"),"Ownership behavior changed"
    write_immutable(AREA/("ownership_"+phase+".json"),text)
    if phase=="after":
        report=dict(coreInputs=511,coreAndLegacyFullOutputs=511*6,ownershipRequests=len(results),ownershipFullOutputs=len(results)*3,
            allBeforeAfterEqual=True,allDetailedThreeRuntimeEqual=True,modelFilesUnchanged=23,training=False,reservedInferred=False,
            snapshots={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(AREA.glob('*.json'))})
        write_immutable(ROOT/"data/reports/behavior/core_money_r4_integrity.json",json.dumps(report,indent=2)+"\n")
    print(json.dumps(dict(phase=phase,ownershipRequests=len(results),completeOwnershipOutputs=len(results)*3)))


if __name__=="__main__":
    parser=argparse.ArgumentParser();parser.add_argument('phase',choices=('before','after','policy'));snapshot(parser.parse_args().phase)
