"""Noncash/instructional boundary contrasts and source-bound weak review."""
from copy import deepcopy
import json
import subprocess
import unittest
from unittest.mock import patch

from src.python.engine import MasroofEngine
from tools.evaluation.core_money import field_errors
from tools.evaluation.evaluate_completion_frames import FIXTURE, ROOT, diagnostic_records, validate_review
from tools.node_runtime import node_executable


class CompletionFrameTests(unittest.TestCase):
    def test_bilingual_boundaries_across_digits_metadata_and_runtimes(self):
        fixture = json.loads(FIXTURE.read_text(encoding='utf-8'))
        cases, expected = [], {}
        for case in fixture['cases']:
            for digits in ('0123456789', '٠١٢٣٤٥٦٧٨٩', '۰۱۲۳۴۵۶۷۸۹'):
                for contact in (False, True):
                    key = str(len(cases))
                    inp = dict(case['input'], text=case['input']['text'].translate(str.maketrans('0123456789', digits)),
                               sender='Saved contact' if contact else '', isContact=contact)
                    cases.append(dict(id=key, input=inp))
                    expected[key] = case
        run = subprocess.run([node_executable(), str(ROOT/'tools/evaluation/probe_detailed.ts')],
                             input=json.dumps(dict(cases=cases)), cwd=ROOT,
                             capture_output=True, text=True, encoding='utf-8', check=True)
        rows = json.loads(run.stdout)['rows']
        engine = MasroofEngine()
        self.assertEqual(len(rows), len(cases))
        for case, row in zip(cases, rows, strict=True):
            with self.subTest(id=expected[case['id']]['id'], input=case['input']):
                actual = engine.predict_detailed(case['input'])
                self.assertEqual(field_errors(actual, expected[case['id']]['expected']), {})
                self.assertEqual(actual, row['typescript'])
                self.assertEqual(actual, row['browser'])

    def test_clear_points_and_exercises_do_not_need_a_learned_score(self):
        fixture = json.loads(FIXTURE.read_text(encoding='utf-8'))
        engine = MasroofEngine()
        with patch.object(engine, '_score_tokens', side_effect=AssertionError('Explicit boundary must not use learned fallback')):
            for row in fixture['cases']:
                if row['expected']['transactionStatus'] == 'non_transaction':
                    actual = engine.predict_detailed(row['input'])
                    self.assertEqual(actual['trackingDecision'], 'exclude')
                    self.assertIsNone(actual['amount'])

    def test_review_retains_original_truth_and_rejects_changed_sources(self):
        records = diagnostic_records()
        review = validate_review(records)
        self.assertEqual(len(review['records']), 37)
        altered = deepcopy(records)
        first = review['records'][0]
        row = next(r for r in altered if (r['cohort'], r['recordId']) == (first['cohort'], first['recordId']))
        row['input']['text'] += ' Changed.'
        with self.assertRaisesRegex(ValueError, 'Stale review source'):
            validate_review(altered)
        altered_review = deepcopy(review)
        altered_review['records'][0]['reviewedStatus'] = 'completed'
        with self.assertRaisesRegex(ValueError, 'Unexpected truth revision'):
            validate_review(records, altered_review)
        altered_review = deepcopy(review)
        altered_review['records'][0]['evidence']['end'] -= 1
        with self.assertRaisesRegex(ValueError, 'Stale evidence span'):
            validate_review(records, altered_review)
