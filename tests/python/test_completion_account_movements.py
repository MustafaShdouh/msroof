"""Explicit owned-account cash effects must share amount syntax and retain context."""
import json
import subprocess
import unittest
from unittest.mock import patch

from src.python.engine import MasroofEngine
from tools.evaluation.core_boundary_check import fixture_variants
from tools.evaluation.core_money import field_errors
from tools.node_runtime import node_executable
from training.corpus_io import ROOT

FIXTURE = ROOT/'tests/fixtures/completion_account_movements_v1.json'


class CompletionAccountMovementTests(unittest.TestCase):
    def test_account_movements_and_guards_across_runtimes(self):
        records = fixture_variants(FIXTURE)
        cases = [dict(id=str(i), input=r['input']) for i,r in enumerate(records)]
        run = subprocess.run([node_executable(),str(ROOT/'tools/evaluation/probe_detailed.ts')],
                             input=json.dumps(dict(cases=cases)),cwd=ROOT,capture_output=True,
                             text=True,encoding='utf-8',check=True)
        other = json.loads(run.stdout)['rows']
        self.assertEqual(len(records),len(other))
        engine = MasroofEngine()
        for row,cross in zip(records,other,strict=True):
            with self.subTest(id=row['recordId']):
                actual = engine.predict_detailed(row['input'])
                self.assertEqual(field_errors(actual,row['expected']),{})
                self.assertEqual(actual,cross['typescript'])
                self.assertEqual(actual,cross['browser'])

    def test_movement_and_context_evidence_do_not_need_candidate_scores(self):
        engine = MasroofEngine()
        with patch.object(engine,'_score_tokens',side_effect=AssertionError('Explicit account effects must not rely on the candidate head')):
            for row in json.loads(FIXTURE.read_text(encoding='utf-8'))['cases']:
                # Ordinary profile metadata still uses the pre-existing fallback.
                if row['boundary']=='administration':
                    continue
                with self.subTest(id=row['id']):
                    actual = engine.predict_detailed(row['input'])
                    self.assertEqual(field_errors(actual,row['expected']),{})

    def test_balance_question_reason_does_not_hide_movement_questions(self):
        examples = [('كم رصيدك المتاح في المحفظة؟','balance_only'),
                    ('هل أضيف 17 JOD إلى رصيد حسابك؟','personal_conversation'),
                    ('Hi, I sent you JOD 17. Check whether you see it in your balance.','personal_conversation')]
        cases = [dict(id=str(i),input=dict(text=text)) for i,(text,_) in enumerate(examples)]
        run = subprocess.run([node_executable(),str(ROOT/'tools/evaluation/probe_detailed.ts')],
                             input=json.dumps(dict(cases=cases)),cwd=ROOT,capture_output=True,
                             text=True,encoding='utf-8',check=True)
        engine = MasroofEngine()
        for row,(_,reason),other in zip(cases,examples,json.loads(run.stdout)['rows'],strict=True):
            actual = engine.predict_detailed(row['input'])
            self.assertEqual(actual['trackingDecision'],'exclude')
            self.assertEqual(actual['reasonCodes'],[reason])
            self.assertEqual(actual,other['typescript'])
            self.assertEqual(actual,other['browser'])
