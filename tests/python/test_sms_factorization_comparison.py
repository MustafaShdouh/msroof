"""Exercise the declared loss and gate without fitting either task-model arm."""
import math
from types import SimpleNamespace
import unittest

from training.transactions.factorization_comparison import row_losses,metrics,gate,MODELS,cohort_result


class FactorizationComparisonTests(unittest.TestCase):
    def test_unreduced_class_balanced_heads_have_declared_equal_loss_share(self):
        import torch
        arm=SimpleNamespace(torch=torch,classes={"context":[str(i) for i in range(6)],"event":[str(i) for i in range(4)]},
            alphas={"context":torch.tensor([21.5,1,1,1,1,1]),"event":torch.tensor([1.25,1,1,1])})
        logits={"context":torch.zeros(1,6,requires_grad=True),"event":torch.zeros(1,4,requires_grad=True)}
        losses=row_losses(arm,logits,[dict(context="0",event="0")])
        self.assertEqual(tuple(losses.shape),(1,))
        self.assertAlmostEqual(float(losses.detach()[0]),.5*(21.5*math.log(6)+1.25*math.log(4)),places=5)
        losses.sum().backward()
        self.assertTrue(all(torch.isfinite(x.grad).all() for x in logits.values()))

    def test_uncertain_is_neither_correct_rejection_nor_completed_success(self):
        rows=[dict(target="completed",outputs={"factorized":dict(status="uncertain")}),
              dict(target="non_transaction",outputs={"factorized":dict(status="uncertain")}),
              dict(target="uncertain",outputs={"factorized":dict(status="non_transaction")})]
        stats=metrics(rows,"factorized")
        self.assertEqual(stats["missedCompleted"],1)
        self.assertEqual(stats["unnecessaryUncertain"],1)
        self.assertEqual(stats["wrongCertainty"],1)
        self.assertEqual(stats["correct"],0)

    def test_gate_requires_unique_control_fix_and_no_control_regression(self):
        raw=[dict(recordId="one",text="A fictional test input",target="non_transaction",language="en")]
        outputs={m:[dict(status="non_transaction")] for m in MODELS}
        outputs["direct_status"][0]["status"]="completed"
        cohort=cohort_result(raw,outputs)
        failures,fixes=gate({"test":cohort},dict(allExact=True))
        self.assertEqual(failures,[])
        self.assertEqual(fixes,1)
        outputs["direct_status"][0]["status"]="non_transaction"
        failures,_=gate({"test":cohort_result(raw,outputs)},dict(allExact=True))
        self.assertIn("No unique primary status improvement versus direct control",failures)
        outputs["factorized"][0]["status"]="uncertain"
        failures,_=gate({"test":cohort_result(raw,outputs)},dict(allExact=False))
        self.assertTrue(any("matched-control regression" in reason for reason in failures))
        self.assertTrue(any("not rejected" in reason for reason in failures))
        self.assertIn("Component development labels not all exact",failures)


if __name__=="__main__": unittest.main()
