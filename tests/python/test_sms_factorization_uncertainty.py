"""Explicit uncertainty stays separate from frozen binary training and diagnostic data."""
import json
import unittest

from training.corpus import factorization_uncertainty as appendix
from training.transactions.completion_adaptation import prepare


class FactorizationUncertaintyTests(unittest.TestCase):
    def test_separate_training_only_slice_has_no_binary_admission(self):
        rows,report,outputs=appendix.build()
        for path,content in outputs.items():
            self.assertEqual(path.read_bytes(),content.encode("utf-8"))
        _,training,cohorts,reserved=prepare()
        excluded={r["recordId"] for r in training+reserved} | {r["recordId"] for group in cohorts.values() for r in group}
        self.assertEqual(len(rows),36)
        self.assertTrue(all(r["recordId"] not in excluded for r in rows))
        for row in rows:
            self.assertEqual(row["originalCompletionTarget"],"uncertain")
            self.assertFalse(row["selectedInFrozen1158"])
            self.assertFalse(row["trainingWeightAssigned"])
            self.assertFalse(row["modelFittingAllowed"])
        self.assertFalse(report["newTrainingViewAuthorized"])
        self.assertFalse(report["original1158CohortChanged"])

    def test_reviewed_unknown_does_not_erase_interpretation_holds(self):
        rows,report,_=appendix.build()
        self.assertEqual(report["combinedAnnotatedRows"],1194)
        self.assertEqual(report["combinedHeldRows"],17)
        self.assertEqual(report["combinedNonheldRows"],1177)
        self.assertEqual(report["combinedNonheldContexts"]["unknown"],8)
        self.assertEqual(report["missingObservedContextClasses"],[])
        held=[r for r in rows if r["reviewState"]=="hold"]
        self.assertEqual({r["recordId"] for r in held},{"authored-sms-v1-067","authored-sms-v1-068"})
        self.assertTrue(all(r["holdReasons"]==["conflicting_event_focus"] for r in held))
        base=[json.loads(line) for line in appendix.full.ANNOTATIONS.read_text(encoding="utf-8").splitlines()]
        self.assertEqual(sum(r["reviewState"]=="hold" for r in base),15)


if __name__=="__main__": unittest.main()
