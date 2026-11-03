"""Proposed comparison view, research projection and train/evaluation separation."""
from collections import defaultdict
from fractions import Fraction
import math
import unittest

from training.transactions.factorization_protocol import prepare_view,development_reviews,compose_status,ROOT
from training.corpus.factorization_pilot import read,digest

PROTOCOL=ROOT/"config/experiments/sms_factorization_comparison_v1.json"


class FactorizationProtocolTests(unittest.TestCase):
    def test_same_view_for_both_arms_and_recomputed_group_weights(self):
        rows,summary,evaluations,reserved=prepare_view()
        p=read(PROTOCOL)
        self.assertEqual(summary["trainingViewSha256"],p["cohort"]["trainingViewSha256"])
        self.assertEqual(len(rows),1177)
        self.assertEqual(summary["targets"],{"completed":611,"non_transaction":532,"uncertain":34})
        weights=defaultdict(float)
        for row in rows: weights[row["group"]]+=row["weight"]
        self.assertEqual(len(weights),129)
        self.assertTrue(all(abs(w-1)<1e-12 for w in weights.values()))
        scope=[r for r in rows if r["group"]=="scope-v1-reward-credit"]
        self.assertEqual(len(scope),8)
        self.assertTrue(all(r["weight"]==1/8 for r in scope))
        self.assertNotIn("literal-L751-C8",weights)
        self.assertNotIn("authored-v1-conflict",weights)
        self.assertIn("authored-v1-authorization",weights)
        train_ids={r["recordId"] for r in rows}
        self.assertFalse(train_ids & {r["recordId"] for group in evaluations.values() for r in group})
        self.assertFalse(train_ids & {r["recordId"] for r in reserved})
        self.assertEqual(math.ceil(len(rows)/8)*3,444)

    def test_projection_preserves_context_and_uncertainty(self):
        self.assertEqual(compose_status("personal_conversation","completed"),"non_transaction")
        self.assertEqual(compose_status("instruction_or_example","completed"),"non_transaction")
        self.assertEqual(compose_status("unknown","no_event"),"uncertain")
        self.assertEqual(compose_status("financial_notice","unknown"),"uncertain")
        self.assertEqual(compose_status("financial_notice","completed"),"completed")
        self.assertEqual(compose_status("financial_notice","no_event"),"non_transaction")
        with self.assertRaises(ValueError): compose_status("invented_context","completed")

    def test_training_only_class_weights_and_zero_authorization(self):
        p=read(PROTOCOL)
        self.assertIn(p["trainingRunsAuthorized"],(0,2))
        if p["trainingRunsAuthorized"]==0:
            self.assertIsNone(p["ownerApproval"])
        else:
            self.assertTrue(p["ownerApproval"])
        self.assertEqual(p["proposedTrainingRuns"],2)
        for path,expected in p["frozenInputs"].items(): self.assertEqual(digest(ROOT/path),expected,path)
        for head in p["training"]["classReweighting"]["heads"].values():
            k=len(head["groupWeightedClassMass"])
            for label,mass in head["groupWeightedClassMass"].items():
                factor=Fraction(head["factorRationals"][label])
                self.assertEqual(Fraction(mass)*factor,Fraction(129,k))
        self.assertEqual(p["training"]["classReweighting"]["heads"]["context"]["factors"]["unknown"],21.5)

    def test_component_gold_is_development_only_and_truth_unchanged(self):
        labels=development_reviews()
        _,_,cohorts,_=prepare_view()
        by_id={r["recordId"]:r for r in cohorts["scopeDevelopment"]}
        self.assertEqual(len(labels),32)
        for row in labels:
            self.assertEqual(row["sourceFold"],"development_diagnostic_only")
            self.assertFalse(row["trainingWeightAssigned"])
            self.assertFalse(row["modelFittingAllowed"])
            self.assertEqual(row["originalCompletionTarget"],by_id[row["recordId"]]["target"])
            self.assertEqual(compose_status(row["messageContext"]["value"],row["describedEventState"]["value"]),row["originalCompletionTarget"])


if __name__=="__main__": unittest.main()
