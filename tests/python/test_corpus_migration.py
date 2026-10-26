"""Current consumers use sanitized inputs; historical evidence stays reproducible."""
import json
import tempfile
import unittest
from pathlib import Path

from training import corpus_io
from training.retire_legacy_corpus import checked_targets
from training.check_seed_copies import contains_seed
from src.python.verify_engine import MasroofEngine

ROOT = corpus_io.ROOT


class CorpusMigrationTests(unittest.TestCase):
    def test_seed_scanner_handles_nested_json_escapes_and_partial_text(self):
        seed = "payment jod 12.500 complete for synthetic client"
        content = json.dumps({"nested": [{"text": "Payment JOD 12.500\ncomplete for SYNTHETIC CLIENT"}]})
        self.assertTrue(contains_seed(content, [seed]))
        self.assertFalse(contains_seed("Payment JOD 12.500", [seed]))

    def test_replacement_preserves_legacy_strict_core_checks(self):
        # The retired runner compared amount/currency/direction exactly. Keep
        # those checks on all 106 accepted cases, alongside the standard suite.
        # Two historical expectations spell currencies as $/€; retain the truth
        # and compare their documented ISO aliases rather than changing fixtures.
        engine = MasroofEngine()
        count = 0
        for name in ("test_suite_cases.json", "qa_adversarial_cases.json"):
            cases = json.loads((corpus_io.FIXTURES / name).read_text(encoding="utf-8"))["testCases"]
            for case in cases:
                result = engine.predict(case["sender"], case["body"])
                self.assertEqual(result["isValidTransaction"], case["expected"]["isValidTransaction"], case["id"])
                if result["isValidTransaction"]:
                    for field in ("amount", "currency", "type"):
                        expected = case["expected"][field]
                        if field == "currency":
                            expected = {"$": "USD", "€": "EUR", "£": "GBP"}.get(expected, expected)
                        self.assertEqual(result["data"][field], expected, (case["id"], field))
                    count += 1
        self.assertEqual(count, 106)

    def test_split_rejects_cross_fold_groups_and_wrong_dataset(self):
        records = json.loads(corpus_io.DATASET.read_text(encoding="utf-8"))
        train, val, split = corpus_io.load_development_split(records)
        self.assertEqual((len(train), len(val)), (1702, 418))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "split.json"
            bad = json.loads(json.dumps(split))
            bad["groups"][0]["indices"] = [train[0], val[0]]
            path.write_text(json.dumps(bad), encoding="utf-8")
            with self.assertRaises(ValueError):
                corpus_io.load_development_split(records, split_path=path)
            bad = split | {"datasetSha256": "wrong"}
            path.write_text(json.dumps(bad), encoding="utf-8")
            with self.assertRaises(ValueError):
                corpus_io.load_development_split(records, split_path=path)

    def test_existing_artifacts_cannot_be_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "artifact.json"
            corpus_io.write_immutable(path, "one\n")
            corpus_io.write_immutable(path, "one\n")
            with self.assertRaises(ValueError):
                corpus_io.write_immutable(path, "different\n")
            self.assertEqual(path.read_text(), "one\n")

    def test_report_input_snapshots_deduplicate_and_detect_tampering(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.py"
            source.write_text("version one", encoding="utf-8")
            expected = corpus_io.sha256(source)
            hashes = {"source.py": expected}
            corpus_io.snapshot_report_inputs("one", hashes, root)
            corpus_io.snapshot_report_inputs("two", hashes, root)
            blobs = root / "data/private/report_inputs/blobs"
            self.assertEqual(len(list(blobs.iterdir())), 1)
            (blobs / expected).write_text("tampered", encoding="utf-8")
            with self.assertRaises(ValueError):
                corpus_io.snapshot_report_inputs("three", hashes, root)

    def test_bio_is_traceable_unreviewed_sanitized_derivative(self):
        bio = json.loads(corpus_io.BIO.read_text(encoding="utf-8"))
        meta = bio["metadata"]
        source = ROOT / meta["source"]
        self.assertEqual(meta["sourceSha256"], corpus_io.sha256(source))
        self.assertEqual(meta["builderSha256"], corpus_io.sha256(ROOT / "training/build_bio_training_set.py"))
        self.assertFalse(meta["humanReviewed"])
        self.assertFalse(meta["independentEvaluationEligible"])
        originals = {row["id"]: row["body"] for row in json.loads(source.read_text(encoding="utf-8"))["testCases"]}
        self.assertEqual(len(bio["examples"]), 83)
        for row in bio["examples"]:
            self.assertEqual(row["text"], originals[row["id"]])
            self.assertEqual(len(row["tokens"]), len(row["tags"]))

    @unittest.skipUnless((ROOT / corpus_io.ARCHIVES[1] / "manifest.json").exists(), "Private archives are local-only")
    def test_retired_copies_have_verified_private_recovery(self):
        _, targets = checked_targets()
        self.assertTrue(all(not path.exists() for path in targets))
        # Unregistered/malicious input paths cannot fall back to working files.
        with self.assertRaises(FileNotFoundError):
            corpus_io.historical_path("../../outside.txt")


if __name__ == "__main__":
    unittest.main()
