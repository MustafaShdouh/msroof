"""Audit safeguards: frozen truth is traceable and missing truth is not correctness."""
from copy import deepcopy
import json
import unittest
from tools.evaluation.review_plain_conjunctions import load_cases,summarize,TAG
from training.corpus_io import ROOT


class PlainConjunctionReviewTests(unittest.TestCase):
    def test_saved_review_reconstructs_scored_and_unscored_counts(self):
        cases=load_cases()
        self.assertEqual(len(cases),59)
        saved=json.loads((ROOT/'.local-backups'/TAG/'results.json').read_text(encoding='utf-8'))
        report=json.loads((ROOT/'data/reports/behavior'/(TAG+'.json')).read_text(encoding='utf-8'))
        self.assertEqual(summarize(saved['records']),report['summary'])
        self.assertEqual(report['summary']['scoredEntries'],282)
        self.assertEqual(report['summary']['unscoredEntries'],72)
        self.assertFalse(report['summary']['groups']['observation_only']['scored'])
        self.assertNotIn('allAssertedFieldsCorrect',report['summary']['groups']['observation_only'])
        self.assertTrue(all(not r['expected'] for r in saved['records'] if r['adjudication']=='observation_only'))

    def test_missing_truth_cannot_silently_become_a_passed_label(self):
        saved=json.loads((ROOT/'.local-backups'/TAG/'results.json').read_text(encoding='utf-8'))['records']
        corrupted=deepcopy(saved)
        row=next(r for r in corrupted if r['adjudication']=='observation_only')
        row['expected']={'trackingDecision':row['actual']['trackingDecision']}
        with self.assertRaisesRegex(ValueError,'no correctness labels'):summarize(corrupted)
        corrupted=deepcopy(saved)
        next(r for r in corrupted if r['adjudication']=='required_review')['expected']={}
        with self.assertRaisesRegex(ValueError,'explicit contract truth'):summarize(corrupted)
