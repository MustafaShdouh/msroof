"""Check the fixed objective and proposed budget without fitting task models."""
import unittest
from training.transactions.auxiliary_status_protocol import combine_losses, validate


class AuxiliaryStatusProtocolTests(unittest.TestCase):
    def test_declared_primary_and_auxiliary_gradient_coefficients(self):
        import torch
        losses={k:torch.tensor([2.,4.],requires_grad=True) for k in ("status","context","event")}
        mixed=combine_losses(losses)
        torch.testing.assert_close(mixed,torch.tensor([2.,4.]))
        mixed.sum().backward()
        for key, expected in (("status",5/6),("context",1/12),("event",1/12)):
            torch.testing.assert_close(losses[key].grad,torch.full((2,),expected))

    def test_missing_head_and_broadcasting_are_rejected(self):
        import torch
        with self.assertRaises(ValueError): combine_losses({"status":torch.ones(2)})
        with self.assertRaises(ValueError):
            combine_losses(dict(status=torch.ones(2),context=torch.ones(1),event=torch.ones(2)))

    def test_frozen_view_baseline_metadata_and_unapproved_budget(self):
        from tests.python.auxiliary_proposal_snapshot import run_proposal_test
        result=run_proposal_test()
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)

    def test_dedicated_shuffle_reproduces_frozen_control(self):
        import torch
        from training.transactions.auxiliary_status_protocol import ROOT
        import json
        stored=json.loads((ROOT/".local-backups/sms_factorization_comparison_v2/direct_status/attempt.json").read_text())
        generator=torch.Generator(device="cpu").manual_seed(20261028)
        self.assertEqual([torch.randperm(1177,generator=generator).tolist() for _ in range(3)],stored["epochOrders"])
