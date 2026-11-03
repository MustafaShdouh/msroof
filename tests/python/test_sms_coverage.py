"""Weak authored data provenance, exact evidence, paired grouping and quarantine."""
from copy import deepcopy
import json
import unittest
from unittest.mock import patch

from training.corpus import coverage
from training.corpus.review_semantics import build as review_build


class SmsCoverageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows, cls.report = coverage.build()
        cls.reviewed = review_build()[0]
        cls.events = json.loads(coverage.EVENTS.read_text(encoding="utf-8"))

    def test_distinct_weak_training_only_messages_and_bilingual_groups(self):
        self.assertEqual(len(self.rows), 74)
        self.assertEqual(len({row["textSha256"] for row in self.rows}), 74)
        self.assertEqual(len({row["authoringGroupId"] for row in self.rows}), 37)
        self.assertEqual(self.report["authoredBatch"]["languageCounts"], {"ar": 37, "en": 37})
        self.assertEqual(self.report["authoredBatch"]["statusCounts"], {"completed": 54, "non_transaction": 16, "uncertain": 4})
        self.assertTrue(all(row["origin"] == "assistant_authored_training_only" and not row["trainingEligible"] and not row["independentEvaluationEligible"] for row in self.rows))

    def test_current_arabic_outgoing_support_really_is_bill_only(self):
        support = self.report["currentTrainingCoverage"]
        positive = {event: cell["arabicContaining"]["direction"] for event, cell in support.items()
                    if cell["arabicContaining"]["direction"]["targets"].get("outgoing", 0)}
        self.assertEqual(set(positive), {"bill_payment"})
        self.assertEqual(positive["bill_payment"]["expressions"], 2)
        self.assertEqual(positive["bill_payment"]["rows"], 50)
        for event in ("card_purchase", "merchant_payment", "refund", "cashback", "fee", "installment", "salary_credit"):
            self.assertEqual(sum(cell["completion"]["expressions"] for cell in support[event].values()), 0)

    def test_semantic_contrasts_keep_completion_separate_from_tracking(self):
        for row in self.rows:
            fields = row["annotations"]
            if row["eventType"] == "own_account_transfer":
                self.assertEqual(fields["transactionStatus"]["value"], "completed")
                self.assertEqual(fields["trackingDecision"]["value"], "exclude")
                self.assertEqual(fields["direction"]["value"], "not_applicable")
            elif row["eventType"] == "ambiguous_transfer":
                self.assertEqual(fields["trackingDecision"]["value"], "review")
                self.assertEqual(fields["direction"]["value"], "uncertain")
            elif row["eventType"] == "cashback":
                self.assertEqual(fields["amount"]["value"] is not None, True)
                self.assertEqual(fields["direction"]["value"], "incoming")
            elif row["eventType"] in ("loyalty", "personal_conversation", "declined_or_failed", "pending_or_requested"):
                self.assertIsNone(fields["amount"]["value"])
                self.assertEqual(fields["transactionStatus"]["value"], "non_transaction")
            elif row["eventType"] == "settlement_uncertain":
                self.assertEqual(set(fields), {"transactionStatus", "trackingDecision"})

    def test_currency_and_missing_amount_do_not_invent_posted_facts(self):
        foreign = [row for row in self.rows if row["annotations"].get("currency", {}).get("value") == "USD"]
        self.assertEqual(len(foreign), 2)
        self.assertTrue(all(row["annotations"]["currencyResolution"]["value"] == "explicit" for row in foreign))
        missing = [row for row in self.rows if row["authoringGroupId"].endswith("missing-amount")]
        self.assertEqual(len(missing), 2)
        for row in missing:
            fields = row["annotations"]
            self.assertIsNone(fields["amount"]["value"])
            self.assertEqual(fields["currencyResolution"]["value"], "default_missing")
            self.assertEqual(fields["trackingDecision"]["value"], "review")

    def test_batch_cannot_claim_human_gold_admission_old_ids_or_fake_amount(self):
        for change in ("human", "train", "final", "oldId", "amount", "group", "hash"):
            rows = deepcopy(self.rows)
            if change == "human":
                rows[0]["annotations"]["transactionStatus"]["reviewer"] = "human"
            elif change == "train":
                rows[0]["trainingEligible"] = True
            elif change == "final":
                rows[0]["independentEvaluationEligible"] = True
            elif change == "oldId":
                rows[0]["sourceExpressionId"] = "literal-L448-C15"
            elif change == "amount":
                rows[0]["annotations"]["amount"]["value"] = 999
            elif change == "group":
                rows[0]["authoringGroupId"] = "authored-v1-detached"
            else:
                rows[0]["text"] += " changed"
            with self.subTest(change=change), self.assertRaises(ValueError):
                coverage.validate_batch(rows)

    def test_one_overlap_blocks_both_counterparts_and_numeric_copies(self):
        rows = [{"recordId": "a", "authoringGroupId": "pair", "text": "Paid JOD 9 successfully."},
                {"recordId": "b", "authoringGroupId": "pair", "text": "دفع مكتمل"}]
        blocked = coverage.overlap_blocks(rows, ["Paid JOD 7 successfully."], {})
        self.assertTrue(all("old_source_or_control_numeric_proxy_overlap" in value for value in blocked.values()))
        rows[0]["text"] = "Paid at Reserved Shop."
        blocked = coverage.overlap_blocks(rows, [], {"reserved shop": {"protected_identity"}})
        self.assertTrue(all("protected_identity" in value for value in blocked.values()))
        rows[0]["text"], rows[1]["text"] = "Fee JOD 4", "Fee JOD 5"
        self.assertTrue(all("authored_numeric_proxy_duplicate" in value for value in coverage.overlap_blocks(rows, [], {}).values()))

    def test_source_event_reviews_cannot_relabel_or_lose_bindings(self):
        for change in ("duplicate", "hash", "human", "event"):
            events = deepcopy(self.events)
            if change == "duplicate":
                events["reviews"][1] = deepcopy(events["reviews"][0])
            elif change == "hash":
                events["reviews"][0]["textSha256"] = "0" * 64
            elif change == "human":
                events["reviews"][0]["state"] = "human_gold"
            else:
                events["reviews"][0]["eventType"] = "guessed-purpose"
            with self.subTest(change=change), self.assertRaises(ValueError):
                coverage.validate_event_reviews(events, self.reviewed)

    def test_coverage_does_not_score_any_student_or_reserved_category_model(self):
        with patch("src.python.engine.MasroofEngine.predict", side_effect=AssertionError("forbidden inference")), \
             patch("src.python.engine.MasroofEngine.predict_detailed", side_effect=AssertionError("forbidden inference")), \
             patch("src.python.research.sms_semantics.SmsSemanticsModel.predict", side_effect=AssertionError("forbidden student")), \
             patch("src.python.research.merchant_category.predict", side_effect=AssertionError("forbidden final inference")):
            _, report = coverage.build()
        self.assertFalse(report["modelFitted"])
        self.assertFalse(report["studentPredictionsUsed"])


if __name__ == "__main__":
    unittest.main()
