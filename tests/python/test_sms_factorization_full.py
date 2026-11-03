"""Complete source coverage, lossless source display and frozen review safeguards."""
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from training.corpus import factorization_full as full


class FullFactorizationTests(unittest.TestCase):
    def test_complete_source_bound_coverage_and_holds(self):
        rows, report, outputs = full.build()
        for path, content in outputs.items():
            self.assertEqual(path.read_bytes(), content.encode("utf-8"))
        self.assertEqual(len(rows), 1158)
        self.assertEqual(len({r["recordId"] for r in rows}), 1158)
        self.assertEqual(report["unreviewedRecords"], 0)
        self.assertEqual(report["reviewedWeakRecords"], 1143)
        self.assertEqual(report["heldRecords"], 15)
        self.assertEqual(report["groupsAllNonheld"], 128)
        self.assertEqual(report["nonheldGroupWeight"], 128.0)
        self.assertEqual(report["absentNonheldContextClasses"], ["unknown"])
        self.assertFalse(report["unknownContextClassTrainable"])
        self.assertFalse(report["trainingReady"])
        original = [json.loads(line) for path in (full.pilot.ANNOTATIONS,full.supplement.ANNOTATIONS)
                    for line in path.read_text(encoding="utf-8").splitlines()]
        by_id = {r["recordId"]:r for r in rows}
        self.assertTrue(all(by_id[r["recordId"]]==r for r in original))

    def test_display_reconstructs_every_changed_character(self):
        packet=dict(packetId="test",group="test",rows=[
            dict(recordId="one",text="JO\nDebit posted for متجر ألف.\nBalance 1.00"),
            dict(recordId="two",text="JO\nDebit NOT posted for متجر باء.\nBalance 2.50")])
        captured=io.StringIO()
        with redirect_stdout(captured): full.display(packet)
        view=[json.loads(line) for line in captured.getvalue().splitlines()]
        tokens=[value for _,value in view[0]["baseTokens"]]
        decoded={}
        for block in view[1:]:
            for record in block["records"]:
                rebuilt=tokens[:]
                for (start,end),replacement in reversed(list(zip(block["replaceTokenRanges"],record[1:]))):
                    rebuilt[start:end]=[replacement]
                decoded[record[0]]="".join(rebuilt)
        self.assertEqual(decoded,{r["recordId"]:r["text"] for r in packet["rows"]})
        self.assertIn("NOT",captured.getvalue())

    def test_incomplete_ledger_has_no_default_labels(self):
        entries=full.LOG.read_text(encoding="utf-8").splitlines()
        with tempfile.TemporaryDirectory() as directory:
            missing=Path(directory)/"partial.jsonl"
            missing.write_text("\n".join(entries[:-1])+"\n",encoding="utf-8")
            with patch.object(full,"LOG",missing):
                with self.assertRaisesRegex(ValueError,"exactly one explicit review"):
                    full.build()

    def test_finalized_review_refuses_more_assignments(self):
        before=full.pilot.digest(full.LOG)
        with self.assertRaisesRegex(ValueError,"frozen"):
            full.record_review("source-001","financial_notice","completed","x","y","not applied")
        self.assertEqual(full.pilot.digest(full.LOG),before)


if __name__=="__main__": unittest.main()
