"""Source-bound weak review outcomes and barriers against label/admission leakage."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from training.corpus.review_semantics import build, validate_layer, expand_decision, validate_prepared_bytes, DECISIONS
from training.corpus.semantics import prepare, DATASET, digest


class SmsSemanticsReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows, cls.report, _ = build()
        cls.drafts, cls.queue, _, _, _ = prepare()
        cls.sources = json.loads(DATASET.read_text(encoding="utf-8"))
        cls.by_id = {row["recordId"]: row for row in cls.rows}

    def test_all80_text_reviews_are_weak_with_expected_outcomes(self):
        self.assertEqual(self.report["reviewedRecords"], 80)
        self.assertEqual(self.report["weakFieldAnnotations"], 791)
        self.assertEqual(self.report["statusCounts"], {"completed": 24, "non_transaction": 55, "uncertain": 1})
        self.assertEqual(self.report["trackingCounts"], {"review": 14, "include": 11, "exclude": 55})
        for row in self.rows:
            self.assertTrue(all(entry["state"] == "weak" and entry["reviewer"] == "assistant" for entry in row["annotations"].values()))
            self.assertFalse(row["trainingEligible"])
            self.assertFalse(row["independentEvaluationEligible"])

    def test_no_student_or_merchant_model_calls(self):
        with patch("src.python.engine.MasroofEngine.predict", side_effect=AssertionError("student inference forbidden")), \
             patch("src.python.engine.MasroofEngine.predict_detailed", side_effect=AssertionError("student inference forbidden")), \
             patch("src.python.research.merchant_category.predict", side_effect=AssertionError("reserved inference forbidden")):
            _, report, _ = build()
        self.assertFalse(report["studentRuntimePredictionsUsed"])
        self.assertFalse(report["teacherPredictionsTreatedAsGold"])

    def test_ownership_and_unknown_purpose_are_not_invented(self):
        relations = [row["annotations"].get("transferRelationship", {}).get("value") for row in self.rows]
        self.assertEqual(relations.count("unknown"), 13)
        self.assertNotIn("own_accounts", relations)
        self.assertNotIn("other_person", relations)
        self.assertEqual(self.report["purposeAssignments"], {"Cash Withdrawals": 1})
        for row in self.rows:
            if row["admissionBlockers"]:
                self.assertIsNone(row["annotations"].get("expenseCategory", {}).get("value"))

    def test_partial_roles_stay_unannotated_and_quoted_money_is_not_posted(self):
        role = self.by_id[self.queue[7]["recordId"]]["annotations"]
        fragment = self.by_id[self.queue[44]["recordId"]]["annotations"]
        self.assertNotIn("merchantOrCounterparty", role)
        self.assertEqual(set(fragment), {"transactionStatus", "trackingDecision"})
        otp = self.by_id[self.queue[28]["recordId"]]["annotations"]
        self.assertEqual(otp["transactionStatus"]["value"], "non_transaction")
        self.assertIsNone(otp["amount"]["value"])
        self.assertIsNone(otp["currency"]["value"])

    def test_blockers_and_folds_cannot_be_removed(self):
        blocked = next(row for row in self.rows if row["admissionBlockers"])
        for field, value in (("admissionBlockers", []), ("fold", "validation"), ("trainingEligible", True),
                             ("textSha256", "0" * 64)):
            changed = deepcopy(self.rows)
            next(row for row in changed if row["recordId"] == blocked["recordId"])[field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                validate_layer(changed, self.drafts, self.queue, self.sources)
        self.assertEqual(self.report["blockedReviewedRecords"], 13)
        self.assertEqual(self.report["unblockedReviewedRecords"], 67)

    def test_duplicate_or_nonqueued_reviews_rejected(self):
        duplicated = self.rows[:-1] + [deepcopy(self.rows[0])]
        with self.assertRaises(ValueError):
            validate_layer(duplicated, self.drafts, self.queue, self.sources)

    def test_changed_evidence_or_human_claim_rejected(self):
        for field, value in (("reviewer", "human"), ("evidence", [])):
            changed = deepcopy(self.rows)
            changed[0]["annotations"]["transactionStatus"][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                validate_layer(changed, self.drafts, self.queue, self.sources)

    def test_wrong_party_or_balance_as_primary_amount_cannot_silently_bind(self):
        decisions = json.loads(DECISIONS.read_text(encoding="utf-8"))["reviews"]
        decision = next(row for row in decisions if row["queueIndex"] == 1)
        draft = next(row for row in self.drafts if row["recordId"] == decision["recordId"])
        text = self.sources[draft["sourceIndex"]]["text"]
        for change in ({"partyText": "THIS PARTY DOES NOT APPEAR"}, {"amountText": "746.964"}):
            with self.assertRaises(ValueError):
                expand_decision({**decision, **change}, text)

    def test_nontransaction_amount_and_category_state_contradictions_rejected(self):
        for index, field, value in ((28, "amount", 90.680), (1, "categoryStatus", "uncertain")):
            changed = deepcopy(self.rows)
            record_id = self.queue[index]["recordId"]
            next(row for row in changed if row["recordId"] == record_id)["annotations"][field]["value"] = value
            with self.subTest(index=index, field=field), self.assertRaises(ValueError):
                validate_layer(changed, self.drafts, self.queue, self.sources)

    def test_prepared_bytes_are_verified_without_newline_normalization(self):
        with tempfile.TemporaryDirectory(prefix="masroof-review-integrity-") as directory:
            folder = Path(directory)
            for name in ("drafts.jsonl", "review_queue.jsonl"):
                (folder / name).write_bytes(b"{}\n")
            manifest = {"artifacts": {name: digest("{}\n") for name in ("drafts.jsonl", "review_queue.jsonl")}}
            validate_prepared_bytes(manifest, folder)
            (folder / "drafts.jsonl").write_bytes(b"{}\r\n")
            with self.assertRaises(ValueError):
                validate_prepared_bytes(manifest, folder)
