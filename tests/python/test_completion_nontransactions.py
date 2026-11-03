"""Reviewed denial/request boundaries must exclude without erasing real cash."""
import json
import subprocess
import unittest
from unittest.mock import patch

from src.python.engine import MasroofEngine
from tools.evaluation.core_boundary_check import fixture_variants
from tools.evaluation.core_money import field_errors
from tools.evaluation.evaluate_completion_frames import diagnostic_records, validate_review
from tools.node_runtime import node_executable
from training.corpus_io import ROOT
from tests.python.nontransaction_review import reviewed_nontransaction

FIXTURE = ROOT/'tests/fixtures/completion_nontransaction_cases_v1.json'


class CompletionNontransactionTests(unittest.TestCase):
    def test_denials_requests_admin_and_cash_across_runtimes(self):
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

    def test_all_reviewed_statuses_follow_evidence_without_model_fallback(self):
        records = diagnostic_records()
        review = validate_review(records)
        expected = {(r['cohort'], r['recordId']):r['reviewedStatus'] for r in review['records']}
        engine, checked = MasroofEngine(), 0
        with patch.object(engine, '_score_tokens', side_effect=AssertionError('Reviewed boundaries must not require a financial-candidate score')):
            for row in records:
                key = row['cohort'], row['recordId']
                if key in expected:
                    with self.subTest(cohort=key[0], id=key[1]):
                        actual = engine.predict_detailed(row['input'])
                        self.assertEqual(actual['transactionStatus'], expected[key])
                        self.assertEqual(actual['trackingDecision'], 'review' if expected[key]=='uncertain' else 'exclude')
                    checked += 1
        self.assertEqual(checked, 37)

    def test_historical_review_does_not_accept_a_different_baseline(self):
        from training.evaluation.ownership import no_context_cases
        doc = json.loads((ROOT/'tests/fixtures/nontransaction_context_reviews_v1.json').read_text(encoding='utf-8'))
        sources = {r['id']:r['input']['text'] for r in no_context_cases()}
        for row in doc['reviews']:
            text = sources[row['caseId']]
            self.assertEqual(reviewed_nontransaction(text, row['previous']), row['current'])
            changed = dict(row['previous'], trackingDecision='include')
            with self.assertRaisesRegex(ValueError, 'baseline changed'):
                reviewed_nontransaction(text, changed)
