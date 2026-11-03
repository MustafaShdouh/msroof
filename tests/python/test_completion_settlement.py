"""Settlement, collection and purpose roles must retain pending/ownership boundaries."""
import json
import subprocess
import unittest
from unittest.mock import patch

from src.python.engine import MasroofEngine
from src.python.entity_text import EntityText
from src.python.money_candidates import collect_candidates
from tools.evaluation.core_boundary_check import fixture_variants
from tools.evaluation.core_money import field_errors
from tools.node_runtime import node_executable
from training.corpus_io import ROOT

FIXTURE = ROOT/'tests/fixtures/completion_settlement_v1.json'


def probe(cases, ownership=()):
    run = subprocess.run([node_executable(),str(ROOT/'tools/evaluation/probe_detailed.ts')],
                         input=json.dumps(dict(cases=cases,ownershipCases=list(ownership))),cwd=ROOT,
                         capture_output=True,text=True,encoding='utf-8',check=True)
    return json.loads(run.stdout)


class CompletionSettlementTests(unittest.TestCase):
    def test_settlement_collection_and_purpose_contrasts_across_runtimes(self):
        rows = fixture_variants(FIXTURE)
        cases = [dict(id=str(i),input=r['input']) for i,r in enumerate(rows)]
        other = probe(cases)['rows']
        self.assertEqual(len(rows),len(other))
        engine = MasroofEngine()
        for row,cross in zip(rows,other,strict=True):
            with self.subTest(id=row['recordId']):
                actual = engine.predict_detailed(row['input'])
                self.assertEqual(field_errors(actual,row['expected']),{})
                self.assertEqual(actual,cross['typescript'])
                self.assertEqual(actual,cross['browser'])

    def test_after_movement_balances_preserve_currency_amount_and_raw_spans(self):
        texts = ['📩 صرف الصراف ١٧٫٢٥٠ USD وسجل المبلغ خصما على حسابك. الرصيد بعد الحركة ٨٨٫٤٠٠ JOD.',
                 'JOD 17.250 was debited. Balance after the movement: JOD 88.400.',
                 'Balance after the transaction: JOD 88.400. JOD 17.250 was debited.']
        run = subprocess.run([node_executable(),str(ROOT/'tools/evaluation/probe_money_candidates.ts')],
                             input=json.dumps(texts),cwd=ROOT,capture_output=True,text=True,encoding='utf-8',check=True)
        for raw,other in zip(texts,json.loads(run.stdout),strict=True):
            actual = collect_candidates(EntityText(raw),MasroofEngine.parse_number)
            self.assertEqual(actual,other)
            self.assertEqual([x['value'] for x in actual['monetary']],[17.25])
            self.assertEqual(actual['monetary'][0]['currency'],'USD' if raw==texts[0] else 'JOD')
            self.assertEqual({x['role'] for x in actual['exclusions']},{'balance'})
            for value in actual['monetary']:
                self.assertEqual(raw[value['start']:value['end']],value['text'])

    def test_outgoing_salary_stays_transfer_and_fee_confirmation_cannot_retype_it(self):
        text='حوالة الراتب: تم خصم 17 JOD من حسابك.'
        rows=[dict(id='outgoing-salary',input=dict(text=text))]
        engine=MasroofEngine();actual=engine.predict_detailed(rows[0]['input'])
        other=probe(rows)['rows'][0]
        self.assertEqual(actual['transferRelationship'],'unknown')
        self.assertEqual(actual['trackingDecision'],'review')
        self.assertEqual(actual,other['typescript']);self.assertEqual(actual,other['browser'])
        fee='Transfer commission collected: a JOD 17 debit has settled on your wallet.'
        request=dict(ownerScopeId='dev-owner',messageId='fee',message=dict(text=fee),
                     ownershipContext=dict(schemaVersion='1.0.0',ownerScopeId='dev-owner',messageId='fee',
                                           text=fee,evidence='user_confirmed',relationship='own_accounts'))
        py=engine.predict_with_ownership(request);cross=probe([], [dict(id='fee',request=request)])['ownershipRows'][0]
        self.assertEqual(py['contextStatus'],'not_applicable')
        self.assertEqual(py['contextReason'],'not_a_transfer')
        self.assertEqual(py['assessment']['trackingDecision'],'include')
        self.assertEqual(py,cross['typescript']);self.assertEqual(py,cross['browser'])

    def test_explicit_settlement_and_rejections_do_not_need_candidate_scores(self):
        engine=MasroofEngine()
        with patch.object(engine,'_score_tokens',side_effect=AssertionError('Explicit settlement/context must not require the candidate head')):
            for row in json.loads(FIXTURE.read_text(encoding='utf-8'))['cases']:
                with self.subTest(id=row['id']):
                    self.assertEqual(field_errors(engine.predict_detailed(row['input']),row['expected']),{})
