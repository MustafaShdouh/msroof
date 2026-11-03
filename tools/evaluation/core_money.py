"""Measure core conformance across existing runtimes; no fitting or promotion."""
import argparse
from collections import Counter
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import subprocess

from src.python.engine import MasroofEngine
from tools.node_runtime import node_executable

ROOT=Path(__file__).resolve().parents[2]
FIXTURE=ROOT/"tests/fixtures/core_money_v1.json"
FIELDS=("transactionStatus","trackingDecision","amount","currency","currencyResolution","direction","transferRelationship")


def equal(field,actual,expected):
    if field=="amount" and expected is not None:
        return type(actual) in (int,float) and Decimal(str(actual)).is_finite() and Decimal(str(actual))==Decimal(str(expected))
    return actual==expected


def field_errors(value,expected):
    return {k:dict(expected=v,actual=value[k] if k in value else "<missing>")
            for k,v in expected.items() if k not in value or not equal(k,value[k],v)}


def evaluate():
    fixture=json.loads(FIXTURE.read_text(encoding="utf-8"))
    cases=fixture["cases"]
    engine=MasroofEngine()
    request=json.dumps(dict(cases=cases),ensure_ascii=False)
    child=subprocess.run([node_executable(),str(ROOT/"tools/evaluation/probe_detailed.ts")],
        input=request,text=True,encoding="utf-8",capture_output=True,cwd=ROOT,check=True)
    cross={r["id"]:r for r in json.loads(child.stdout)["rows"]}
    results=[];totals={k:Counter() for k in ("python","typescript","browser")};parity=[]
    for case in cases:
        py=engine.predict_detailed(case["input"])
        outputs=dict(python=py,typescript=cross[case["id"]]["typescript"],browser=cross[case["id"]]["browser"])
        mismatches={}
        for runtime,value in outputs.items():
            errors=field_errors(value,case["expected"])
            mismatches[runtime]=errors
            totals[runtime]["passed" if not errors else "failed"]+=1
        if any(any(not equal(k,value.get(k),py.get(k)) for k in FIELDS) for value in outputs.values()):parity.append(case["id"])
        results.append(dict(id=case["id"],family=case["family"],language=case["language"],
            expected=case["expected"],outputs={runtime:{k:v.get(k) for k in FIELDS} for runtime,v in outputs.items()},mismatches=mismatches))
    sources=[FIXTURE,Path(__file__),ROOT/"src/python/engine.py",ROOT/"src/python/detailed_assessment.py",
             ROOT/"src/typescript/MasroofEngine.ts",ROOT/"src/typescript/DetailedAssessment.ts",
             ROOT/"config/contracts/transaction_evidence.json",ROOT/"tools/browser/tester.html"]
    return dict(schemaVersion="1.0.0",kind=fixture["kind"],cases=len(cases),
        counts={k:dict(v) for k,v in totals.items()},coreParityMismatches=parity,
        familyCounts=dict(Counter(c["family"] for c in cases)),results=results,
        pendingPolicyCases=fixture["pendingPolicyCases"],
        inputs={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sources},
        training=False,reservedInferred=False,independentAccuracy=False,
        limits=["Assistant-authored exposed conformance; expected fields are a new scope-specific evaluation subset, not human gold.",
                "No category or party-name scoring. Existing category computation/API is unchanged.",
                "Partial expected-field cases measure only asserted fields; zero mismatches does not prove full correctness.",
                "All text origin is unauthenticated; no runtime can authenticate a bank from text alone."])


if __name__=="__main__":
    parser=argparse.ArgumentParser();parser.add_argument("--strict",action="store_true")
    parser.add_argument("--report",default="data/reports/behavior/core_money_v1_baseline.json")
    args=parser.parse_args();result=evaluate();path=ROOT/args.report
    content=json.dumps(result,ensure_ascii=False,indent=2)+"\n"
    if path.exists():
        if path.read_bytes()!=content.encode("utf-8"):raise ValueError("Report differs; choose a new versioned --report path")
    else:
        with path.open("x",encoding="utf-8",newline="\n") as handle:handle.write(content)
    print(json.dumps({k:result[k] for k in ("cases","counts","coreParityMismatches")}))
    if args.strict and (result["coreParityMismatches"] or any(v.get("failed",0) for v in result["counts"].values())):raise SystemExit(1)
