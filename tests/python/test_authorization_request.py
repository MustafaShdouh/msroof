"""Code requests are blocked before scoring; completed-code receipts survive."""
import json
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch

from src.python.authorization_request import is_authorization_request, AUTHORIZATION_REQUEST_REASON
from src.python.verify_engine import MasroofEngine
from training.evaluate_behavior import canonical_result

ROOT = Path(__file__).resolve().parents[2]
NODE = r"C:\Program Files\nodejs\node.exe"


class AuthorizationRequestTests(unittest.TestCase):
    def test_bilingual_requests_receipt_contrasts_and_runtime_parity(self):
        cases = json.loads((ROOT / "tests/fixtures/authorization_request_cases.json").read_text(encoding="utf-8"))["cases"]
        helper_script = """import fs from 'node:fs';
import { isAuthorizationRequest } from './src/typescript/AuthorizationRequest.ts';
console.log(JSON.stringify(JSON.parse(fs.readFileSync(0, 'utf8')).map(row => isAuthorizationRequest(row.body))));"""
        helpers = subprocess.run([NODE, "--input-type=module", "-e", helper_script], input=json.dumps(cases), capture_output=True, text=True, encoding="utf-8", cwd=ROOT)
        self.assertEqual(helpers.returncode, 0, helpers.stderr)
        self.assertEqual(json.loads(helpers.stdout), [case["request"] for case in cases])
        inputs = {"cases": [{"id": row["id"], "input": {"sender": "", "text": row["body"]}} for row in cases], "categoryProbes": []}
        process = subprocess.run([NODE, str(ROOT / "tools/evaluation/probe_runtime.ts")], input=json.dumps(inputs), capture_output=True, text=True, encoding="utf-8", cwd=ROOT)
        self.assertEqual(process.returncode, 0, process.stderr)
        outputs = json.loads(process.stdout)
        engine = MasroofEngine()
        for row, ts, web in zip(cases, outputs["typescript"], outputs["browser"]):
            with self.subTest(case=row["id"]):
                self.assertEqual(is_authorization_request(row["body"]), row["request"])
                result = canonical_result(engine.predict("", row["body"]))
                self.assertEqual(ts["result"], result)
                self.assertEqual(web["result"], result)
                if row["request"]:
                    self.assertEqual(result, {"isValidTransaction": False, "confidence": 0, "reason": AUTHORIZATION_REQUEST_REASON, "data": None})
                elif "accepted" in row:
                    self.assertEqual(result["isValidTransaction"], row["accepted"])

    def test_code_request_does_not_reach_model_scoring(self):
        body = "Your code to complete your payment of JOD 17.350 is 684291."
        engine = MasroofEngine()
        with patch.object(engine, "_score_tokens", side_effect=AssertionError("Must reject before scoring")):
            self.assertEqual(engine.predict("", body)["reason"], AUTHORIZATION_REQUEST_REASON)
        # With no TS model initialized, reaching inference would try an invalid
        # require instead of returning the structural rejection.
        script = """import { MasroofEngine } from './src/typescript/MasroofEngine.ts';
console.log(JSON.stringify(MasroofEngine.analyze({sender:'', body:process.argv[1]})));"""
        process = subprocess.run([NODE, "--input-type=module", "-e", script, body], capture_output=True, text=True, encoding="utf-8", cwd=ROOT)
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertEqual(json.loads(process.stdout)["reason"], AUTHORIZATION_REQUEST_REASON)
