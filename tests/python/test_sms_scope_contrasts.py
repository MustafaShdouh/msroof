"""Safeguards for the authored corpus, admission boundary and Unicode spans."""
import json
import unittest
from collections import defaultdict
from unittest.mock import patch
from training.corpus_io import ROOT, recorded_source
from training.corpus.scope_contrasts import contained

from training.corpus.scope_contrasts import SOURCE, MANIFEST, build, parse, unmark


class ScopeContrastTests(unittest.TestCase):
    def test_frozen_corpus_and_whole_family_split(self):
        # Historical corpus reproduction uses its recorded comparison inventory.
        # New fixtures belong to new evaluations, not this immutable source report.
        checked=json.loads((ROOT/"data/reports/transactions/sms_scope_v1_preparation.json").read_text(encoding="utf-8"))["checkedPaths"]
        paths=[];texts=[]
        for relative,expected in sorted(checked.items()):
            path=ROOT/relative;raw=recorded_source(relative,expected).decode("utf-8-sig")
            obj=[json.loads(line) for line in raw.splitlines() if line.strip()] if path.suffix==".jsonl" else json.loads(raw)
            paths.append(path);texts.extend(contained(obj))
        with patch("training.corpus.scope_contrasts.comparison_inputs",return_value=(paths,texts)):
            rows, outputs = build()
        for path, expected in outputs.items():
            self.assertEqual(path.read_bytes(), expected.encode("utf-8"))
        manifest = json.loads(outputs[MANIFEST])
        folds = defaultdict(set)
        for row in rows:
            folds[row["authoringGroupId"]].add(row["fold"])
            self.assertEqual(row["labelState"], "weak")
            for flag in ("trainingEligible", "independentEvaluationEligible", "modelFittingAllowed", "ownershipInferred"):
                self.assertIs(row[flag], False)
            self.assertEqual(row["binaryScoringAllowed"], row["target"] != "uncertain")
            for span in row["evidence"]:
                self.assertEqual(row["text"][span["start"]:span["end"]], span["text"])
        self.assertEqual(len(rows), 192)
        self.assertEqual(len(folds), 24)
        self.assertTrue(all(len(v) == 1 for v in folds.values()))
        self.assertFalse(manifest["evaluationPlan"]["modelFittingAllowed"])

    def test_code_point_offsets_preserve_diacritics_and_supplementary_chars(self):
        text, spans = unmark("📩 {{context:إشعار:}} {{event:قُيِّدَ المبلغ.}}")
        self.assertEqual(text, "📩 إشعار: قُيِّدَ المبلغ.")
        self.assertEqual(spans[0]["start"], 2)
        self.assertEqual(text[spans[1]["start"]:spans[1]["end"]], "قُيِّدَ المبلغ.")

    def test_bad_markup_and_translation_label_conflict_rejected(self):
        with self.assertRaises(ValueError):
            unmark("{{context:broken}")
        source = SOURCE.read_text(encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "pair mismatch"):
            parse(source.replace("C ar ", "N ar ", 1))


if __name__ == "__main__":
    unittest.main()
