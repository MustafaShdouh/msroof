"""Source-span truth, protected folds and exported BIO evaluation safeguards."""
import copy
import json
from pathlib import Path
import subprocess
import unittest

from training.corpus_io import BIO, ROOT, sha256
from training.entities import prepare_labels as preparation
from training.entities.evaluate import decode_spans, metrics, slots, same_slot
from src.python.research.bio_sequence import FlatBioModel, TAGS, normalize_token
from tools.node_runtime import node_executable


def blank_model():
    count = len(TAGS)
    return {"version": "1.0.0", "tagCount": count, "featureIndex": {},
            "emissionWeights": [], "transitionWeights": [0.] * (count * count), "bias": [0.] * count}


class BioLabelsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.before = sha256(BIO)
        cls.outputs, cls.report = preparation.build()
        cls.artifact = json.loads(cls.outputs[preparation.DATA])
        cls.split = json.loads(cls.outputs[preparation.SPLIT])

    def test_versioned_repairs_preserve_sources_and_conventions(self):
        self.assertEqual(sha256(BIO), self.before)
        self.assertEqual(len(self.artifact["examples"]), 83)
        self.assertEqual(len(self.report["changedEntitySpans"]), 11)
        changes = self.report["changedEntitySpans"]
        accounts = [change for change in changes if change["label"] == "ACCT"]
        self.assertEqual(len(accounts), 10)
        self.assertTrue(all(change["after"]["text"].isdigit() and len(change["after"]["text"]) == 4 for change in accounts))
        merchant = next(change for change in changes if change["label"] == "MERCHANT")
        self.assertEqual(merchant["after"]["text"], "COZMO سوبرماركت")
        self.assertFalse(self.artifact["metadata"]["humanReviewed"])
        self.assertFalse(self.artifact["metadata"]["independentEvaluationEligible"])

    def test_source_offsets_preserve_diacritics_digits_and_spacing(self):
        text = "🧾 أَسْوَاقِ  السَّلَامِ JOD١٢٫٥٠ رصيد ۸۰٫۰۰"
        tokens = preparation.source_tokens(text)
        self.assertTrue(all(text[token["start"]:token["end"]] == token["text"] for token in tokens))
        self.assertIn("١٢٫٥٠", [token["text"] for token in tokens])
        self.assertIn("۸۰٫۰۰", [token["text"] for token in tokens])
        name = "أَسْوَاقِ  السَّلَامِ"
        start = text.index(name)
        entity = {"start": start, "end": start + len(name), "label": "MERCHANT"}
        tags = preparation.tag_tokens(tokens, [entity])
        row = {"text": text, "tokenOffsets": tokens}
        spans, invalid = decode_spans(row, [TAGS.index(tag) for tag in tags])
        self.assertEqual(spans, [("MERCHANT", start, start + len(name))])
        self.assertEqual(invalid, 0)
        with self.assertRaises(ValueError):
            preparation.tag_tokens(tokens, [entity | {"start": start + 1}])
        with self.assertRaises(ValueError):
            preparation.tag_tokens(tokens, [entity, entity])

    def test_connected_groups_and_protected_identities_are_excluded(self):
        split = self.split
        self.assertEqual(tuple(len(split[key]) for key in ("trainIds", "validationIds", "quarantinedIds")), (63, 16, 4))
        self.assertEqual(set(split["quarantinedIds"]), {"TC_POS_ORA_005", "TC_EDG_DIA_002", "TC_POS_REF_001", "TC_POS_ZAI_003"})
        self.assertEqual(self.report["oldSplit"]["jointGroupsCrossingFolds"], 7)
        self.assertEqual(self.report["oldValidationTokenCoverage"]["B-AMT"], {"total": 25, "unseen": 25})
        preparation.validate_artifacts(self.artifact, split)
        group = next(group for group in split["groups"] if len(group["recordIds"]) > 1 and not group["quarantineReasons"])
        bad = copy.deepcopy(split)
        source = "trainIds" if group["recordIds"][0] in bad["trainIds"] else "validationIds"
        destination = "validationIds" if source == "trainIds" else "trainIds"
        bad[source].remove(group["recordIds"][0])
        bad[destination].append(group["recordIds"][0])
        with self.assertRaises(ValueError):
            preparation.validate_artifacts(self.artifact, bad)

    def test_malformed_or_incomplete_evaluations_fail_closed(self):
        row = self.artifact["examples"][0]
        for predictions in ([], [[0]], [[999] * len(row["tokens"])], [[True] * len(row["tokens"])]):
            with self.subTest(predictions=str(predictions)[:30]), self.assertRaises(ValueError):
                metrics([row], predictions)
        empty = metrics([], [])
        self.assertIsNone(empty["exactSequenceAgreement"]["rate"])
        self.assertIsNone(empty["perEntityCharacterSpan"]["AMT"]["recall"])

    def test_character_spans_and_unique_field_values_are_separate(self):
        text = "12 12"
        row = {"id": "span-control", "text": text, "tokens": ["12", "12"],
               "tokenOffsets": [{"start": 0, "end": 2}, {"start": 3, "end": 5}],
               "tags": ["B-AMT", "O"], "entities": [{"label": "AMT", "start": 0, "end": 2}]}
        result = metrics([row], [[0, TAGS.index("I-AMT")]])
        self.assertEqual(result["invalidIobTransitions"], 1)
        self.assertEqual(result["perEntityCharacterSpan"]["AMT"]["truePositives"], 0)
        self.assertEqual(result["exactPrimaryFields"]["count"], 1)
        two = slots(row, [("AMT", 0, 2), ("AMT", 3, 5)])
        self.assertFalse(same_slot("AMT", {"count": 1, "value": 12}, two["AMT"]))
        self.assertEqual(slots({"text": "دينارًا"}, [("CURR", 0, 7)])["CURR"]["value"], "JOD")

    def test_python_typescript_float32_ties_and_normalization_agree(self):
        model = blank_model()
        words = ["أَسْوَاق", "مدرسة", "فتى", "ـإيداع", "١٢٫٥٠", "۱۲٫۵۰", "constructor", "__proto__"]
        model["featureIndex"] = {normalize_token(word): index for index, word in enumerate(words)}
        model["emissionWeights"] = [0.] * (len(words) * len(TAGS))
        for index in range(len(words)):
            # Different doubles round to the same float32; earliest tag wins.
            model["emissionWeights"][index * len(TAGS)] = 16777216.
            model["emissionWeights"][index * len(TAGS) + 1] = 16777217.
        examples = [words, ["unseen", "آخر"], []]
        expected = [FlatBioModel(model).predict(tokens) for tokens in examples]
        self.assertEqual(expected[0], [0] * len(words))
        process = subprocess.run([node_executable(), str(ROOT / "tools/evaluation/probe_bio_model.ts")],
                                 input=json.dumps({"model": model, "examples": examples}), capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertEqual(json.loads(process.stdout), expected)
        # Give distinct positive weights to test feature normalization too.
        model["emissionWeights"] = [float(tag == index % len(TAGS)) for index in range(len(words)) for tag in range(len(TAGS))]
        process = subprocess.run([node_executable(), str(ROOT / "tools/evaluation/probe_bio_model.ts")],
                                 input=json.dumps({"model": model, "examples": [words]}), capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertEqual(json.loads(process.stdout), [FlatBioModel(model).predict(words)])

    def test_corrupt_exports_are_rejected(self):
        for bad in (blank_model() | {"version": "future"}, blank_model() | {"featureIndex": {"word": 2}},
                    blank_model() | {"bias": []}, blank_model() | {"bias": [float("nan")] * len(TAGS)},
                    blank_model() | {"bias": [1e100] * len(TAGS)}):
            with self.subTest(bad=str(bad)[:40]), self.assertRaises(ValueError):
                FlatBioModel(bad)


if __name__ == "__main__":
    unittest.main()
