"""Explicit unknown outcomes must survive early rejection without proving money moved."""
import json
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch

from src.python.engine import MasroofEngine
from tools.evaluation.core_boundary_check import fixture_variants
from tools.evaluation.core_money import field_errors
from tools.evaluation.evaluate_completion_frames import diagnostic_records, validate_review
from tools.node_runtime import node_executable
from training.corpus_io import ROOT

FIXTURE = ROOT/'tests/fixtures/completion_uncertainty_cases_v1.json'


class CompletionUncertaintyTests(unittest.TestCase):
    def test_uncertainty_and_denial_contrasts_across_runtimes(self):
        records = fixture_variants(FIXTURE)
        cases = [dict(id=str(i), input=r['input']) for i, r in enumerate(records)]
        run = subprocess.run([node_executable(), str(ROOT/'tools/evaluation/probe_detailed.ts')],
                             input=json.dumps(dict(cases=cases)), cwd=ROOT,
                             capture_output=True, text=True, encoding='utf-8', check=True)
        rows = json.loads(run.stdout)['rows']
        self.assertEqual(len(rows), len(records))
        engine = MasroofEngine()
        for record, row in zip(records, rows, strict=True):
            with self.subTest(id=record['recordId']):
                actual = engine.predict_detailed(record['input'])
                self.assertEqual(field_errors(actual, record['expected']), {})
                self.assertEqual(actual, row['typescript'])
                self.assertEqual(actual, row['browser'])

    def test_all_eight_reviewed_unknowns_bypass_candidate_fallback(self):
        records = diagnostic_records()
        review = validate_review(records)
        keys = {(r['cohort'], r['recordId']) for r in review['records'] if r['expectedStatus']=='uncertain'}
        self.assertEqual(len(keys), 8)
        engine = MasroofEngine()
        checked = 0
        with patch.object(engine, '_score_tokens', side_effect=AssertionError('Explicit unknown evidence must survive without fallback')):
            for row in records:
                if (row['cohort'], row['recordId']) in keys:
                    result = engine.predict_detailed(row['input'])
                    self.assertEqual(result['transactionStatus'], 'uncertain')
                    self.assertEqual(result['trackingDecision'], 'review')
                    self.assertIn('completion_unresolved', result['reasonCodes'])
                    checked += 1
        self.assertEqual(checked, 8)

    def test_quoted_questions_codes_and_points_do_not_become_unknown_cash(self):
        fixture = json.loads(FIXTURE.read_text(encoding='utf-8'))
        boundaries = {'instruction_contrast', 'question_contrast', 'authorization_contrast', 'noncash_contrast'}
        engine = MasroofEngine()
        with patch.object(engine, '_score_tokens', side_effect=AssertionError('Explicit nontransaction frame must not need fallback')):
            for row in fixture['cases']:
                if row['boundary'] in boundaries:
                    with self.subTest(id=row['id']):
                        result = engine.predict_detailed(row['input'])
                        self.assertEqual(result['transactionStatus'], 'non_transaction')
                        self.assertEqual(result['trackingDecision'], 'exclude')
                        self.assertIsNone(result['amount'])
