"""Posted entries need source-linked direction and must retain uncertainty guards."""
import json
import hashlib
import subprocess
import unittest
from unittest.mock import patch

from src.python.engine import MasroofEngine
from tools.evaluation.core_boundary_check import fixture_variants
from tools.evaluation.core_money import field_errors
from tools.evaluation.evaluate_completion_frames import diagnostic_records
from tools.node_runtime import node_executable
from training.corpus_io import ROOT

FIXTURE = ROOT/'tests/fixtures/completion_posted_cases_v1.json'


def cross_results(cases):
    run = subprocess.run([node_executable(), str(ROOT/'tools/evaluation/probe_detailed.ts')],
                         input=json.dumps(dict(cases=cases)), cwd=ROOT,
                         capture_output=True, text=True, encoding='utf-8', check=True)
    return json.loads(run.stdout)['rows']


class CompletionPostedTests(unittest.TestCase):
    def test_posting_roles_and_negative_contrasts_in_three_runtimes(self):
        records = fixture_variants(FIXTURE)
        cases = [dict(id=str(i), input=r['input']) for i,r in enumerate(records)]
        other = cross_results(cases)
        self.assertEqual(len(other), len(records))
        engine = MasroofEngine()
        for row, cross in zip(records, other, strict=True):
            with self.subTest(id=row['recordId']):
                actual = engine.predict_detailed(row['input'])
                self.assertEqual(field_errors(actual, row['expected']), {})
                self.assertEqual(actual, cross['typescript'])
                self.assertEqual(actual, cross['browser'])

    def test_final_outcome_uncertainty_is_not_overridden_by_posting(self):
        # Fresh exposed contrasts for the unknown-outcome regression found during review.
        texts = [
            'ورد قيد خصم بقيمة 17 JOD والنتيجة النهائية غير محسومة.',
            'قيد خصم وقيد إلغاء لنفس العملية؛ النتيجة النهائية غير مؤكدة.',
            'A debit of JOD 17 is posted to your account; its final outcome is unresolved.',
        ]
        cases = [dict(id=str(i), input=dict(text=t)) for i,t in enumerate(texts)]
        engine = MasroofEngine()
        for row, other in zip(cases, cross_results(cases), strict=True):
            actual = engine.predict_detailed(row['input'])
            self.assertEqual(actual['transactionStatus'], 'uncertain')
            self.assertEqual(actual['trackingDecision'], 'review')
            self.assertEqual(actual, other['typescript'])
            self.assertEqual(actual, other['browser'])

    def test_review_retains_all_original_completed_expectations(self):
        doc = json.loads((ROOT/'data/reports/behavior/core_money_r5a_completed_review.json').read_text(encoding='utf-8'))
        sources = {(r['cohort'], r['recordId']):r for r in diagnostic_records()}
        queue = json.loads((ROOT/'data/reports/behavior/core_money_r5_repair_queue.json').read_text(encoding='utf-8'))
        expected = {(r['cohort'], r['recordId']) for r in queue['records'] if r['priority']==2}
        self.assertEqual(len(doc['records']),68)
        self.assertEqual({(r['cohort'],r['recordId']) for r in doc['records']}, expected)
        self.assertEqual(doc['sourceCohortSha256'],hashlib.sha256((ROOT/'data/reports/behavior/core_money_r5_cohort.json').read_bytes()).hexdigest())
        for row in doc['records']:
            original = sources[row['cohort'],row['recordId']]
            self.assertEqual(row['textSha256'],original['textSha256'])
            self.assertEqual(original['expected']['transactionStatus'],row['reviewedStatus'])
            for flag in ('truthChanged','trainingEligible','independentEvaluationEligible'):
                self.assertIs(row[flag],False)

    def test_asserted_postings_and_their_guards_do_not_need_candidate_scores(self):
        engine = MasroofEngine()
        with patch.object(engine,'_score_tokens',side_effect=AssertionError('Posting evidence must be structural, not a candidate score')):
            for row in json.loads(FIXTURE.read_text(encoding='utf-8'))['cases']:
                with self.subTest(id=row['id']):
                    actual = engine.predict_detailed(row['input'])
                    self.assertEqual(field_errors(actual,row['expected']),{})
