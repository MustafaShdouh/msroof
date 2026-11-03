"""Check content isolation and reason metadata without model inference."""
import unittest
from training.evaluation.content_preflight import preflight, sha


def contract():
    return dict(inSampleControls={}, uncertaintyReasons={}, reasonDefinitions={"outcome":"Unconfirmed outcome"})


class DiagnosticEvaluationTests(unittest.TestCase):
    def setUp(self):
        self.training = [dict(recordId="train", text="JOD 13 was debited.")]
        self.row = dict(cohort="dev", recordId="test", text="JOD 13 was debited.", target="completed")

    def test_raw_and_normalized_overlap_fail_without_explicit_binding(self):
        for text in (self.row["text"], "  JOD 13 was debited.  ", "JOD 99 was debited."):
            with self.subTest(text=text), self.assertRaises(ValueError):
                preflight(self.training, [dict(self.row, text=text)], contract())

    def test_explicit_control_is_in_sample_and_stale_bindings_fail(self):
        c = contract()
        c["inSampleControls"]["dev/test"] = dict(textSha256=sha(self.row["text"]), trainingRecordIds=["train"], rationale="Known copy")
        result = preflight(self.training, [self.row], c)
        self.assertEqual(result[0]["role"], "in_sample_conformance")
        self.assertFalse(result[0]["independentEvaluationEligible"])
        for change in (dict(text="An unrelated message"), dict(recordId="another")):
            with self.assertRaises(ValueError):
                preflight(self.training, [dict(self.row, **change)], c)
        c["inSampleControls"]["dev/test"]["trainingRecordIds"] = ["wrong-source"]
        with self.assertRaises(ValueError):
            preflight(self.training, [self.row], c)

    def test_reason_required_for_uncertain_and_forbidden_for_definite(self):
        row = dict(self.row, text="Outcome unspecified", target="uncertain")
        c = contract()
        with self.assertRaises(ValueError): preflight(self.training, [row], c)
        c["uncertaintyReasons"]["dev/test"] = "outcome"
        self.assertEqual(preflight(self.training, [row], c)[0]["target"], "uncertain")
        with self.assertRaises(ValueError):
            preflight(self.training, [dict(row, target="non_transaction")], c)

    def test_duplicate_keys_and_stale_reason_metadata_fail(self):
        row = dict(self.row, text="An unrelated message")
        with self.assertRaises(ValueError): preflight(self.training, [row, row], contract())
        c = contract(); c["uncertaintyReasons"]["missing/id"] = "outcome"
        with self.assertRaises(ValueError): preflight(self.training, [row], c)

    def test_text_disjoint_is_still_exposed_weak_evidence(self):
        row = dict(self.row, text="An unrelated message")
        result = preflight(self.training, [row], contract())[0]
        self.assertEqual(result["role"], "text_disjoint_exposed_diagnostic")
        self.assertFalse(result["independentEvaluationEligible"])

    def test_same_id_with_changed_text_and_unknown_target_fail(self):
        row = dict(self.row, recordId="train", text="Unrelated")
        with self.assertRaises(ValueError): preflight(self.training, [row], contract())
        with self.assertRaises(ValueError):
            preflight(self.training, [dict(row, recordId="test", target="invented")], contract())

    def test_saved_metadata_preserves_every_historical_record(self):
        from tools.evaluation.build_sms_evaluation_contract import build
        result = build()
        self.assertEqual(result["rows"], 112)
        self.assertEqual(result["uniqueTexts"], 110)
        self.assertEqual(sum(r["role"] == "in_sample_conformance" for r in result["records"]), 1)
        self.assertEqual(sum(r["uncertaintyReason"] is not None for r in result["records"]), 14)
        self.assertEqual(result["labelsChanged"], 0)
        self.assertFalse(result["reservedInferred"])
