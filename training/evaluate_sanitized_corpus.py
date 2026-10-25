"""Versioned diagnostic of a prepared corpus; no training or gate migration."""
import argparse
import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from training.prepare_sanitized_corpus import FIXTURE_DIR, VERSION, digest, json_text

def evaluate_python_fixture_outputs(outputs):
    """Diagnostic on transformed compatibility cases; never a selection holdout."""
    from src.python.verify_engine import MasroofEngine
    from tests.python.test_suite_runner import normalize_str, normalize_curr
    engine = MasroofEngine()
    counts = Counter()
    failures = []
    for name in ("test_suite_cases.json", "qa_adversarial_cases.json"):
        for case in json.loads(outputs[f"{FIXTURE_DIR}/{name}"])["testCases"]:
            expected = case["expected"]
            result = engine.predict(case["sender"], case["body"])
            counts["cases"] += 1
            if result["isValidTransaction"] != expected["isValidTransaction"]:
                kind = "falsePositive" if result["isValidTransaction"] else "falseNegative"
                counts[kind] += 1
                failures.append({"caseId": case["id"], "field": "classification", "kind": kind})
                continue
            counts["classificationCorrect"] += 1
            if not expected["isValidTransaction"]:
                continue
            data = result.get("data") or {}
            for field in ("type", "amount", "currency", "merchantOrParty", "accountMask", "balance"):
                wanted, actual = expected.get(field), data.get(field)
                if wanted is None:
                    continue
                if field in ("amount", "balance"):
                    ok = actual is not None and abs(wanted - actual) < .001
                elif field == "currency":
                    ok = normalize_curr(wanted) == normalize_curr(actual)
                else:
                    a, b = normalize_str(wanted), normalize_str(actual)
                    ok = b is not None and (a == b or (field in ("merchantOrParty", "accountMask") and (a in b or b in a)))
                if not ok:
                    counts["entityMismatches"] += 1
                    failures.append({"caseId": case["id"], "field": field})
    return {"scope": "Legacy Python model on transformed development regression; not independent accuracy",
            **{key: counts[key] for key in ("cases", "classificationCorrect", "falsePositive", "falseNegative", "entityMismatches")},
            "failures": failures}


NODE = Path(r"C:\Program Files\nodejs\node.exe")


def evaluate():
    paths = [f"{FIXTURE_DIR}/test_suite_cases.json", f"{FIXTURE_DIR}/qa_adversarial_cases.json"]
    inputs = {path: (ROOT / path).read_text(encoding="utf-8") for path in paths}
    python = evaluate_python_fixture_outputs(inputs)
    python.pop("scope")
    cases = [case for path in paths for case in json.loads(inputs[path])["testCases"]]
    probe = ROOT / "tools/evaluation/probe_sanitized_corpus.ts"
    process = subprocess.run([str(NODE), str(probe)], input=json_text({"cases": cases}),
                             capture_output=True, text=True, encoding="utf-8", cwd=ROOT)
    if process.returncode:
        raise ValueError("TypeScript diagnostic failed: " + process.stderr.strip())
    typescript = json.loads(process.stdout)
    evidence_paths = paths + ["data/models/masroof_model.json", "src/python/verify_engine.py", "src/python/preprocessing.py",
                             "src/typescript/MasroofEngine.ts", "src/typescript/Preprocessing.ts",
                             "tools/evaluation/probe_sanitized_corpus.ts", "training/evaluate_sanitized_corpus.py"]
    return {"corpusVersion": VERSION, "scope": "Legacy-model development compatibility diagnostic; no independent accuracy claim",
            "inputSha256": {path: digest((ROOT / path).read_bytes()) for path in evidence_paths},
            "python": python, "typescript": typescript, "runtimeMetricParity": python == typescript,
            "migrationGatePassed": python == typescript and not python["failures"] and not typescript["failures"],
            "runtimeOrModelModified": False, "finalTestInferred": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", default="legacy_v1")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if not re.fullmatch(r"[a-z0-9_]{1,40}", args.run_id):
        raise ValueError("Invalid evaluation run ID")
    report = evaluate()
    path = ROOT / f"data/reports/sanitized_corpus_v1_{args.run_id}_evaluation.json"
    content = json_text(report)
    if args.check:
        if not path.exists() or path.read_text(encoding="utf-8") != content:
            raise ValueError("Evaluation missing or stale")
    else:
        if path.exists() and path.read_text(encoding="utf-8") != content:
            raise ValueError("Changed evaluation inputs/results require a new run ID")
        path.write_text(content, encoding="utf-8", newline="\n")
    counts = report["python"]
    print(f"Sanitized compatibility: {counts['classificationCorrect']}/{counts['cases']}; FP={counts['falsePositive']}, FN={counts['falseNegative']}, entity mismatches={counts['entityMismatches']}; Python/TS parity={report['runtimeMetricParity']}; migration gate={'PASS' if report['migrationGatePassed'] else 'BLOCKED'}")
    if not report["runtimeMetricParity"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
