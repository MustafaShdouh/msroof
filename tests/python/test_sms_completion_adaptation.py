"""No task-model fitting: cohort, gradient boundary, gate and resource safeguards."""
import os
import unittest
from collections import Counter

from training.transactions.completion_adaptation import prepare, configure, gate, resource_reason, working_set


class AdaptationTests(unittest.TestCase):
    def test_exact_view_excludes_reserved_and_uncertain(self):
        p, training, evaluation, reserved = prepare()
        self.assertEqual(Counter(r["target"] for r in training), {"completed": 611, "non_transaction": 547})
        self.assertEqual(len(training), 1158)
        train_ids = {r["recordId"] for r in training}
        for row in reserved + evaluation["scopeDevelopment"]:
            self.assertNotIn(row["recordId"], train_ids)
        self.assertEqual(len(reserved), 32)
        self.assertEqual(p["training"]["maximumOptimizerSteps"], 435)

    def test_gradient_boundary_on_toy_encoder(self):
        import torch
        class ToyEncoder(torch.nn.Module):
            def __init__(self):
                super().__init__()
                self.encoder = torch.nn.Module()
                self.encoder.layer = torch.nn.ModuleList([torch.nn.Linear(4, 4) for _ in range(12)])
                self.dropout = torch.nn.Dropout(0.5)

            def forward(self, x):
                for layer in self.encoder.layer:
                    x = layer(x)
                return self.dropout(x)
        model, head = ToyEncoder(), torch.nn.Linear(4, 1)
        before = {name: value.detach().clone() for name, value in model.named_parameters()}
        selected, head_params = configure(model, head)
        head(model(torch.ones(2, 4))).sum().backward()
        self.assertFalse(model.training)
        self.assertFalse(model.dropout.training)
        self.assertEqual(len(selected), 4)
        self.assertTrue(all(p.grad is not None for p in selected + head_params))
        for name, value in model.named_parameters():
            if not name.startswith(("encoder.layer.10.", "encoder.layer.11.")):
                self.assertIsNone(value.grad)
            self.assertTrue(torch.equal(before[name], value))

    def test_gate_rejects_false_acceptance_and_excess_misses(self):
        metric = {k: dict(TP=1, TN=1, FP=0, FN=0) for k in ("word", "context", "encoder", "candidate")}
        rows = {"example": {"metrics": {"all": metric}}}
        self.assertEqual(gate(rows), [])
        metric["candidate"]["FP"] = 1
        self.assertTrue(gate(rows))
        metric["candidate"]["FP"] = 0
        metric["candidate"]["FN"] = 1
        self.assertTrue(gate(rows))

    def test_resource_limits_and_real_windows_sampler(self):
        b = dict(trainingWallClockSeconds=1200, processWorkingSetLimitBytes=6*1024**3, additionalArtifactLimitBytes=2*1024**3)
        self.assertGreater(working_set(os.getpid()), 0)
        self.assertIsNone(resource_reason(None, 1000, 1000, b))
        self.assertEqual(resource_reason(1200, 1000, 1000, b), "training_time_limit")
        self.assertEqual(resource_reason(1, b["processWorkingSetLimitBytes"]+1, 1000, b), "working_set_limit")
        self.assertEqual(resource_reason(1, 1000, b["additionalArtifactLimitBytes"]+1, b), "artifact_limit")


if __name__ == "__main__":
    unittest.main()
