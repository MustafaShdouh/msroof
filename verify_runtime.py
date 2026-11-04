"""Portable runtime conformance without private or research dependencies."""
import json
from pathlib import Path
import subprocess
import sys

from src.python.engine import MasroofEngine
from tools.node_runtime import node_executable

ROOT = Path(__file__).resolve().parent


def main():
    cases = []
    for name in ("core_money_v1.json", "category_purchase_cases.json"):
        obj = json.loads((ROOT / "tests/fixtures" / name).read_text(encoding="utf-8"))
        cases.extend(obj["cases"])
    process = subprocess.run(
        [node_executable(), str(ROOT / "tools/evaluation/probe_detailed.ts")],
        input=json.dumps({"cases": cases}), capture_output=True,
        text=True, encoding="utf-8", cwd=ROOT, check=True,
    )
    outputs = json.loads(process.stdout)["rows"]
    engine = MasroofEngine()
    failures = []
    for case, other in zip(cases, outputs, strict=True):
        result = engine.predict_detailed(case["input"])
        if result != other["typescript"] or result != other["browser"]:
            failures.append(case["id"] + ": runtime outputs differ")
        for field, expected in case.get("expected", case.get("expect", {})).items():
            if result[field] != expected:
                failures.append(f"{case['id']}: {field} expected {expected!r}, got {result[field]!r}")
    if failures:
        print("\n".join(failures))
        return 1
    print(f"Passed {len(cases)} development controls in Python, TypeScript and the bundled tester.")
    print("Independent accuracy and target-device performance remain unverified.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
