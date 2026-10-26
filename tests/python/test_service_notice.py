"""English/Arabic structural controls and full Python/TS/browser result parity."""
import json
import subprocess
import unittest
from pathlib import Path

from src.python.service_notice import is_service_notice, SERVICE_NOTICE_REASON
from src.python.engine import MasroofEngine
from tools.node_runtime import node_executable

ROOT = Path(__file__).resolve().parents[2]


class ServiceNoticeTests(unittest.TestCase):
    def test_notices_and_completed_receipts_across_runtimes(self):
        cases = json.loads((ROOT / "tests/fixtures/service_notice_cases.json").read_text(encoding="utf-8"))["cases"]
        engine = MasroofEngine()
        outputs = []
        for case in cases:
            with self.subTest(case=case["id"]):
                notice = is_service_notice(case["body"])
                self.assertEqual(notice, case["isServiceNotice"])
                result = engine.predict("SERVICE", case["body"])
                if notice:
                    self.assertEqual(result, {"isValidTransaction": False, "confidence": 0, "reason": SERVICE_NOTICE_REASON, "data": None})
                if "isValidTransaction" in case:
                    self.assertEqual(result["isValidTransaction"], case["isValidTransaction"])
                if result.get("data"):
                    # Python retains compatibility aliases absent from the TS API.
                    for alias, canonical in (("merchant_or_party", "merchantOrParty"), ("account_mask", "accountMask"), ("category_confidence", "categoryConfidence")):
                        self.assertEqual(result["data"].pop(alias), result["data"][canonical])
                outputs.append({"id": case["id"], "notice": notice, "result": result})
        process = subprocess.run([node_executable(), str(ROOT / "tests/typescript/test_service_notice.ts")],
                                 capture_output=True, text=True, encoding="utf-8", cwd=ROOT)
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertEqual(json.loads(process.stdout), outputs)


if __name__ == "__main__":
    unittest.main()
