"""Human confirmation is message-bound, conservative and identical in all runtimes."""
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import unittest

from src.python.engine import MasroofEngine
from tools.contracts.validate_ownership_context import validate_request, validate_response
from tools.node_runtime import node_executable
from tests.python.direction_review import reviewed_direction
from tests.python.nontransaction_review import reviewed_nontransaction

ROOT = Path(__file__).resolve().parents[2]


def controls():
    from training.evaluation.ownership import ownership_controls
    return ownership_controls()


def probe(rows):
    process = subprocess.run([node_executable(), str(ROOT / "tools/evaluation/probe_detailed.ts")],
                             input=json.dumps({"cases": [], "ownershipCases": rows}),
                             capture_output=True, text=True, encoding="utf-8", cwd=ROOT)
    if process.returncode:
        raise AssertionError(process.stderr)
    return json.loads(process.stdout)["ownershipRows"]


class OwnershipContextTests(unittest.TestCase):
    def test_no_context_matches_pre_feature_assessor_on_all_development_cases(self):
        from training.evaluation.ownership import baseline_assessor, no_context_cases
        engine, old = MasroofEngine(), baseline_assessor()
        old_engine = old.baseline_engine
        for case in no_context_cases():
            with self.subTest(case=case["id"]):
                expected = old(case["input"], lambda body, direction: old_engine.extract_entities(body, direction, categorize=False),
                               old_engine.parse_number, lambda text: old_engine._score_tokens(old_engine.tokenize(old_engine.preprocess(text)))[0] >= 0.70)
                expected = reviewed_direction(case['input']['text'],expected)
                expected = reviewed_nontransaction(case['input']['text'],expected)
                self.assertEqual(engine.predict_detailed(case["input"]), expected)
                for context in ({}, {"ownershipContext": None}):
                    result = engine.predict_with_ownership({"ownerScopeId": "owner", "messageId": case["id"],
                                                           "message": case["input"], **context})
                    self.assertEqual(result["assessment"], expected)
                    self.assertEqual(result["contextStatus"], "absent")

    def test_acceptance_and_three_runtime_parity(self):
        rows = controls()
        engine = MasroofEngine()
        for row, other in zip(rows, probe(rows), strict=True):
            with self.subTest(case=row["id"]):
                request = deepcopy(row["request"])
                result = engine.predict_with_ownership(request)
                validate_response(result)
                self.assertEqual(result, other["typescript"])
                self.assertEqual(result, other["browser"])
                self.assertEqual(result["contextStatus"], row["contextStatus"])
                self.assertEqual(result["contextReason"], row["contextReason"])
                for key, value in row["expect"].items():
                    self.assertEqual(result["assessment"][key], value, key)
                if row["sameAsBody"]:
                    self.assertEqual(result["assessment"], engine.predict_detailed(request["message"]))
                if result["contextStatus"] == "invalid":
                    with self.assertRaises(ValueError):
                        validate_request(request)
                else:
                    validate_request(request)
                self.assertEqual(request, row["request"], "confirmation must not mutate caller data")

    def test_identifier_whitespace_and_exact_binding(self):
        base = controls()[0]["request"]
        rows = []
        for index, blank in enumerate(["", " ", "\t\n", "\u0085", "\ufeff", "\u001c", "\u3000"]):
            for key in ("ownerScopeId", "messageId"):
                request = deepcopy(base)
                request[key] = request["ownershipContext"][key] = blank
                rows.append({"id": f"blank-{index}-{key}", "request": request})
        request = deepcopy(base)
        request["ownerScopeId"] = request["ownershipContext"]["ownerScopeId"] = " owner-1 "
        rows.append({"id": "literal-id", "request": request})
        request = deepcopy(request)
        request["ownershipContext"]["ownerScopeId"] = "owner-1"
        rows.append({"id": "no-trim-binding", "request": request})
        engine = MasroofEngine()
        for row, other in zip(rows, probe(rows), strict=True):
            result = engine.predict_with_ownership(row["request"])
            validate_response(result)
            self.assertEqual(result, other["typescript"])
            self.assertEqual(result, other["browser"])
            self.assertEqual(result["contextReason"], "confirmed_relationship" if row["id"] == "literal-id"
                             else "owner_mismatch" if row["id"] == "no-trim-binding" else "invalid_request")

    def test_response_contract_rejects_extras_and_diagnostic_mismatch(self):
        result = MasroofEngine().predict_with_ownership(controls()[0]["request"])
        for change in ({"extra": True}, {"ownershipContractVersion": "2"}, {"contextReason": "not_provided"},
                       {"assessment": {**result["assessment"], "contextStatus": "applied"}}):
            with self.assertRaises(ValueError):
                validate_response({**result, **change})
