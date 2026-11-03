"""Draft evidence, admission, reservation and deterministic split safeguards."""
from copy import deepcopy
import json
import unittest
from unittest.mock import patch

from tools.contracts.validate_sms_semantics import validate_annotations, validate_record, derive_tracking
from training.corpus.semantics import prepare, choose_queue, reservation_forms, group_blockers, digest
from training.corpus_io import DATASET


def weak(text, value):
    return {"state": "weak", "value": value, "origin": "assistant_reviewed_text", "reviewer": "assistant",
            "evidence": [{"kind": "text_span", "start": 0, "end": len(text), "text": text}],
            "note": "Assistant interpretation of this exact synthetic text; not human gold."}


class SmsSemanticsPreparationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.drafts, cls.queue, cls.manifest, cls.report, _ = prepare()
        cls.sources = json.loads(DATASET.read_text(encoding="utf-8"))

    def test_training_coverage_and_no_duplicate_text_export(self):
        self.assertEqual(len(self.drafts), 1702)
        self.assertEqual(len(self.queue), 80)
        self.assertEqual(self.report["untouchedValidationRecords"], 418)
        self.assertEqual(len({row["recordId"] for row in self.drafts}), 1702)
        self.assertEqual(len({row["sourceExpressionId"] for row in self.queue}), 80)
        for row in self.drafts:
            self.assertEqual(row["fold"], "train")
            self.assertEqual(row["annotations"], {})
            self.assertNotIn("text", row)
            self.assertFalse(row["trainingEligible"])
            self.assertFalse(row["independentEvaluationEligible"])
        self.assertEqual(choose_queue(list(reversed(self.drafts))), self.queue)

    def test_preparation_does_not_call_models(self):
        with patch("src.python.engine.MasroofEngine.predict", side_effect=AssertionError("inference forbidden")), \
             patch("src.python.engine.MasroofEngine.predict_detailed", side_effect=AssertionError("inference forbidden")), \
             patch("src.python.research.merchant_category.predict", side_effect=AssertionError("reserved model inference forbidden")):
            _, _, manifest, _, _ = prepare()
        self.assertFalse(manifest["modelPredictionsUsed"])

    def test_group_reservation_and_related_brand_propagation(self):
        businesses = [{"businessId": "reserved", "name": "Alpha Shop", "aliases": ["متجر ألفا"]},
                      {"businessId": "train", "name": "Beta Shop", "aliases": []}]
        forms = reservation_forms(businesses, {"reserved": "test", "train": "train"},
                                  [{"familyId": "shared-parent", "members": ["Alpha Shop", "Beta Shop"]}])
        records = [{"text": "Payment to Beta Shop"}, {"text": "A different record"}]
        blocked = group_blockers(records, [{"groupId": "g", "indices": [0, 1]}], forms)
        self.assertEqual(blocked["g"], ["protected_brand_family:shared-parent"])
        self.assertTrue(any(row["admissionBlockers"] for row in self.drafts))

    def test_known_control_overlap_blocks_whole_group(self):
        records = [{"text": "EXAMPLE MESSAGE"}, {"text": "other example"}]
        result = group_blockers(records, [{"groupId": "g", "indices": [0, 1]}], {},
                                {digest("example message"): {"frozen_or_control_text_overlap"}})
        self.assertEqual(result["g"], ["frozen_or_control_text_overlap"])

    def test_binding_and_admission_tampering_rejected(self):
        row = self.drafts[0]
        source = self.sources[row["sourceIndex"]]
        for field, value in (("sourceIndex", True), ("textSha256", "0" * 64), ("fold", "validation"),
                             ("trainingEligible", True), ("independentEvaluationEligible", True), ("extra", 1)):
            with self.subTest(field=field), self.assertRaises(ValueError):
                validate_record({**row, field: value}, source, row["sourceIndex"], "train", row["leakageGroupId"])
        modified = deepcopy(row)
        modified["legacyClaims"]["class"] = "TRANSACTION_CREDIT"
        with self.assertRaises(ValueError):
            validate_record(modified, source, row["sourceIndex"], "train", row["leakageGroupId"])

    def test_unannotated_is_not_uncertain_and_legacy_null_is_not_absence(self):
        validate_annotations({}, "message")
        unknown = {"state": "unannotated", "value": None, "origin": None, "reviewer": None, "evidence": [], "note": None}
        validate_annotations({"transactionStatus": unknown}, "message")
        with self.assertRaises(ValueError):
            validate_annotations({"transactionStatus": {**unknown, "value": "uncertain"}}, "message")
        validate_annotations({"transactionStatus": weak("message", "uncertain")}, "message")
        row = next(row for row in self.drafts if row["legacyClaims"]["amount"] is None)
        self.assertNotIn("amount", row["annotations"])

    def test_evidence_offsets_and_exact_party_are_bound(self):
        text = "😀 سُوق النور"
        start = text.index("س")
        entry = weak(text, text[start:])
        entry["evidence"] = [{"kind": "text_span", "start": start, "end": len(text), "text": text[start:]}]
        validate_annotations({"merchantOrCounterparty": entry}, text)
        for changed in ({**entry, "value": "سوق النور"},
                        {**entry, "evidence": [{**entry["evidence"][0], "start": start + 1}]}):
            with self.assertRaises(ValueError):
                validate_annotations({"merchantOrCounterparty": changed}, text)

    def test_weak_facts_do_not_grant_human_gold_or_legacy_decisions(self):
        for changed in ({"state": "human_reviewed"}, {"reviewer": "human"}, {"origin": "model_prediction"}, {"evidence": []}):
            with self.assertRaises(ValueError):
                validate_annotations({"transactionStatus": {**weak("message", "completed"), **changed}}, "message")
        with self.assertRaises(ValueError):
            validate_annotations({"trackingDecision": weak("message", "include")}, "message")

    def test_decisions_need_supported_facts_and_correct_citations(self):
        text = "completed movement"
        facts = {field: weak(text, value) for field, value in
                 {"transactionStatus": "completed", "amount": 12.5, "direction": "outgoing", "transferRelationship": "unknown"}.items()}
        self.assertEqual(derive_tracking(facts), "review")
        facts["transferRelationship"]["value"] = "not_transfer"
        self.assertEqual(derive_tracking(facts), "include")
        decision = {"state": "weak", "value": "include", "origin": "derived_policy", "reviewer": "assistant",
                    "evidence": [{"kind": "annotation_field", "field": field} for field in facts], "note": "Canonical policy applied to cited weak facts."}
        validate_annotations({**facts, "trackingDecision": decision}, text)
        with self.assertRaises(ValueError):
            validate_annotations({**facts, "trackingDecision": {**decision, "evidence": [{"kind": "annotation_field", "field": "amount"}]}}, text)
        facts["transferRelationship"]["value"] = "own_accounts"
        del facts["amount"]
        self.assertEqual(derive_tracking(facts), "exclude")

    def test_invalid_money_and_ineligible_category_rejected(self):
        for value in (True, 0, -1, float("nan"), float("inf")):
            with self.assertRaises(ValueError):
                validate_annotations({"amount": weak("message", value)}, "message")
        with self.assertRaises(ValueError):
            validate_annotations({"expenseCategory": weak("message", "Food")}, "message")
