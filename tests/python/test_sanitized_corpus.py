"""Sanitization/provenance/split invariants, not model-accuracy assertions."""
import copy
import json
import random
import re
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

from training import prepare_sanitized_corpus as corpus
from training import audit_sms_provenance as source_audit
from tests.python.validate_test_corpus import validate_baseline


class SanitizedCorpusTests(unittest.TestCase):
    def test_repeated_amount_balance_and_zero_keep_their_relationship(self):
        text = "Purchase amount JOD 10.870 on card *1234. Balance JOD 10.870."
        expected = {"amount": 10.87, "balance": 10.87, "accountMask": "*1234", "type": "EXPENSE", "currency": "JOD"}
        original = copy.deepcopy(expected)
        body, fields, _, _ = corpus.sanitize_record(text, "repeat", [], expected)
        self.assertEqual(fields["amount"], fields["balance"])
        self.assertNotEqual(fields["amount"], 10.87)
        self.assertNotEqual(fields["accountMask"], "*1234")
        self.assertIn(fields["accountMask"], body)
        self.assertEqual(expected, original)
        _, zero, _, _ = corpus.sanitize_record("Purchase JOD 10.00. Balance JOD 0.00.", "zero", [], {"amount": 10, "balance": 0})
        self.assertEqual(zero["balance"], 0)

    def test_counterparty_phone_structure_and_script_survive(self):
        text = "تم تحويل 10.000 JOD إلى محفظة 0791234567 (محمد اختباري) من حسابك *1234."
        expected = {"amount": 10, "merchantOrParty": "محمد اختباري", "accountMask": "*1234"}
        body, fields, _, _ = corpus.sanitize_record(text, "wallet", ["محمد اختباري"], expected)
        self.assertNotIn("محمد اختباري", body)
        self.assertNotIn("0791234567", body)
        self.assertRegex(body, r"079\d{7}")
        self.assertIn(fields["merchantOrParty"], body)
        self.assertRegex(fields["merchantOrParty"], r"[\u0621-\u064a]")

    def test_deterministic_values_and_varying_neutral_names(self):
        text = "JOD 10.00 transferred to EXAMPLE PERSON."
        args = (text, "one", ["EXAMPLE PERSON"], {"amount": 10, "merchantOrParty": "EXAMPLE PERSON"})
        before_rng = random.getstate()
        first = corpus.sanitize_record(*args)
        self.assertEqual(first, corpus.sanitize_record(*args))
        second = corpus.sanitize_record(text, "two", args[2], args[3])
        self.assertNotEqual(first[1]["merchantOrParty"], second[1]["merchantOrParty"])
        self.assertNotIn("RECIPIENT", first[1]["merchantOrParty"])
        self.assertEqual(random.getstate(), before_rng)

    def test_money_formatting_covers_western_arabic_and_persian(self):
        for token in ("1,234.567", "١٬٢٣٤٫٥٦٧", "۱٬۲۳۴٫۵۶۷", "1'234.567", "1.234,56"):
            with self.subTest(token=token):
                value, _, _ = corpus.decimal_shape(token)
                body, fields, _, _ = corpus.sanitize_record("Purchase JOD " + token, "format", [], {"amount": float(value)})
                rendered = corpus.NUMBERS.search(body).group()
                parsed, _, _ = corpus.decimal_shape(rendered)
                self.assertEqual(parsed, Decimal(str(fields["amount"])))
                self.assertEqual([c for c in token if not c.isdecimal()], [c for c in rendered if not c.isdecimal()])
                if token.startswith("١"):
                    self.assertRegex(rendered, r"^[٠-٩٬٫]+$")

    def test_ending_in_account_expectation_is_remapped_consistently(self):
        body, fields, _, _ = corpus.sanitize_record("Purchase JOD 10.00 with card ending in 5412.", "ending", [], {"amount": 10, "accountMask": "ending in 5412"})
        self.assertNotIn("5412", fields["accountMask"])
        self.assertIn(fields["accountMask"], body)

    def test_trace_identifies_chosen_literal_without_changing_rows_or_rng(self):
        source = """import random
random.seed(5)
NAMES = ['EXAMPLE PERSON']
def generate_samples():
    dataset = []
    for _ in range(8):
        dataset.append({'text': random.choice(['First template', 'Second template']), 'label': 'NOISE'})
    return dataset
"""
        rng = random.Random(5)
        expected = [{"text": rng.choice(["First template", "Second template"]), "label": "NOISE"} for _ in range(8)]
        before = random.getstate()
        rows, names = corpus.traced_generation(source, Path("synthetic_source.py"), expected)
        self.assertEqual(len({row["sourceTemplateId"] for row in rows}), 2)
        self.assertEqual(names, ["EXAMPLE PERSON"])
        self.assertEqual(random.getstate(), before)
        with self.assertRaises(ValueError):
            corpus.traced_generation(source, Path("synthetic_source.py"), expected[:-1])

    def test_global_groups_join_duplicates_across_providers(self):
        rows = [{"text": text, "label": label, "provider": provider, "sourceTemplateId": f"t{i}", "expected_merchant": None}
                for i, (text, label, provider) in enumerate([
                    ("First alert 10 JOD", "A", "one"), ("First alert 10 JOD", "A", "two"),
                    ("Different alert wording", "A", "one"), ("Another alert wording", "A", "two"),
                    ("Credit arrives today", "B", "one"), ("Deposit was completed", "B", "two"),
                    ("Money was received", "B", "one"), ("Account balance credited", "B", "two")])]
        clean = copy.deepcopy(rows)
        clean[0]["text"], clean[1]["text"] = "First alert 25 JOD", "First alert 83 JOD"
        before = copy.deepcopy(rows)
        split = corpus.grouped_split(rows, clean, "dataset-hash")
        group = next(group for group in split["groups"] if 0 in group["indices"])
        self.assertIn(1, group["indices"])
        self.assertEqual(rows, before)
        train, val = set(split["trainIndices"]), set(split["validationIndices"])
        self.assertFalse(train & val)
        self.assertEqual(train | val, set(range(len(rows))))
        self.assertTrue(set(group["indices"]) <= train or set(group["indices"]) <= val)

    def test_private_archive_is_immutable(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.assertTrue(root.resolve().is_relative_to(Path(tempfile.gettempdir()).resolve()))
            (root / "one.txt").write_text("private historical value", encoding="utf-8")
            with patch.object(corpus, "HISTORICAL", ["one.txt"]):
                corpus.archive_inputs(root)
                (root / "one.txt").write_text("changed", encoding="utf-8")
                corpus.archive_inputs(root)
                self.assertEqual((root / corpus.ARCHIVE / "one.txt").read_text(encoding="utf-8"), "private historical value")
                (root / corpus.ARCHIVE / "one.txt").write_text("tampered", encoding="utf-8")
                with self.assertRaises(ValueError):
                    corpus.archive_inputs(root)

    def test_prepared_public_artifact_hashes_and_partitions(self):
        report = json.loads((corpus.ROOT / corpus.REPORT).read_text(encoding="utf-8"))
        for relative, expected_hash in report["artifactSha256"].items():
            self.assertEqual(corpus.digest((corpus.ROOT / relative).read_bytes()), expected_hash)
        self.assertEqual(validate_baseline(corpus.ROOT / corpus.FIXTURE_DIR), [])
        split = json.loads((corpus.ROOT / corpus.SPLIT).read_text(encoding="utf-8"))
        rows = json.loads((corpus.ROOT / corpus.DATA).read_text(encoding="utf-8"))
        self.assertTrue(all(not row["independentEvaluationEligible"] for row in rows))
        self.assertTrue(all(counts["train"] > 0 and counts["validation"] > 0 for counts in split["labelCounts"].values()))
        for group in split["groups"]:
            folds = {"train" if i in set(split["trainIndices"]) else "validation" for i in group["indices"]}
            self.assertEqual(len(folds), 1)
        self.assertTrue(all(value == 0 for value in report["checks"]["crossPartitionOverlapCounts"].values()))
        self.assertFalse(report["activeLegacyGateChanged"])
        self.assertFalse(report["currentRepositoryPrivacyRemediationComplete"])

    def test_maintenance_case_retains_negative_truth(self):
        cases = json.loads((corpus.ROOT / corpus.FIXTURE_DIR / "qa_adversarial_cases.json").read_text(encoding="utf-8"))["testCases"]
        case = next(row for row in cases if row["id"] == "TC_EDGE_MAINTENANCE_TRAP_001")
        self.assertFalse(case["expected"]["isValidTransaction"])
        self.assertIn("unavailable", case["body"])
        self.assertIn("upgrade", case["body"])

    @unittest.skipUnless((corpus.ROOT / source_audit.PRIVATE).exists(), "Private seed evidence is local-only")
    def test_known_original_seed_text_and_person_spans_do_not_survive_in_prepared_corpus(self):
        texts = [row["text"] for row in json.loads((corpus.ROOT / corpus.DATA).read_text(encoding="utf-8"))]
        for name in ("test_suite_cases.json", "qa_adversarial_cases.json"):
            texts += [row["body"] for row in json.loads((corpus.ROOT / corpus.FIXTURE_DIR / name).read_text(encoding="utf-8"))["testCases"]]
        normalized = {source_audit.canonical(text) for text in texts}
        combined = "\n".join(texts)
        evidence = json.loads((corpus.ROOT / source_audit.PRIVATE).read_text(encoding="utf-8"))
        for row in evidence["records"]:
            source = (corpus.ROOT / row["sourcePath"]).read_bytes().decode("utf-8-sig")
            locator = row["sourceLocator"]
            original = source[locator["startChar"]:locator["endChar"]]
            self.assertFalse(source_audit.canonical(original) in normalized, msg=row["id"])
            for span in row["redactions"]:
                if span["kind"] == "PERSON":
                    person = original[span["sourceStart"]:span["sourceEnd"]]
                    self.assertFalse(bool(corpus.phrase_pattern(person).search(combined)), msg=row["id"])


if __name__ == "__main__":
    unittest.main()
