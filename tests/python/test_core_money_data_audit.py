"""Audit logic and immutable-data boundaries; no model or training calls."""
import unittest
from tools.evaluation.audit_core_money_data import duplicate_inventory,spans_valid,build
from src.python.research.sms_semantics import normalize


class CoreMoneyDataAuditTests(unittest.TestCase):
    def test_numeric_variants_with_same_targets_are_not_label_conflicts(self):
        rows=[dict(recordId=str(i),group="one",text=f"JOD {i} debited",status="completed",context="financial_notice",event="completed") for i in (10,20)]
        self.assertEqual(duplicate_inventory(rows)["duplicateGroups"],0)
        normalized=duplicate_inventory(rows,normalize)
        self.assertEqual(normalized["duplicateGroups"],1)
        self.assertEqual(normalized["conflictingGroups"],0)
        rows[1].update(context="instruction_or_example",group="two")
        conflict=duplicate_inventory(rows,normalize)
        self.assertEqual(conflict["groups"][0]["conflictingFields"],["context"])
        self.assertEqual(conflict["crossSourceGroupDuplicates"],1)

    def test_source_spans_use_codepoints_and_exact_text(self):
        self.assertTrue(spans_valid("📩 ١٢ دينار",[dict(start=2,end=4,text="١٢")]))
        self.assertFalse(spans_valid("📩 ١٢ دينار",[dict(start=2,end=5,text="١٢")]))
        self.assertFalse(spans_valid("text",[dict(start=-1,end=2,text="te")]))

    def test_real_manifest_never_admits_or_moves_reserved_records(self):
        report,manifest=build()
        self.assertEqual(report["trainingRows"],1177)
        self.assertEqual(report["normalizedDuplicates"]["duplicateGroups"],61)
        self.assertEqual(report["rawDuplicates"]["conflictingGroups"],0)
        self.assertEqual(report["normalizedDuplicates"]["conflictingGroups"],0)
        self.assertEqual(report["bioInventory"]["foldCounts"],dict(train=63,validation=16,quarantined=4))
        self.assertFalse(manifest["trainingEligible"])
        self.assertFalse(manifest["modelFittingAllowed"])
        self.assertFalse(report["reservedInferred"])
        self.assertEqual(len(manifest["existingHeldIds"]),17)
        permitted={r["recordId"] for r in report["bioInventory"]["records"] if r["fold"]=="train"}
        self.assertTrue(set(manifest["bioReviewCandidates"])<=permitted)
        self.assertEqual(len(manifest["excludedDevelopmentFixtureIds"]),52)
