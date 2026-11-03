"""Confirmed arrivals/execution must preserve unknown ownership and monetary roles."""
import json
import subprocess
import unittest
from unittest.mock import patch

from src.python.engine import MasroofEngine
from src.python.entity_text import EntityText
from src.python.money_candidates import amounts, collect_candidates
from tools.evaluation.core_boundary_check import fixture_variants
from tools.evaluation.core_money import field_errors
from tools.node_runtime import node_executable
from training.corpus_io import ROOT

FIXTURE = ROOT/'tests/fixtures/completion_income_transfers_v1.json'


def probe(cases):
    run = subprocess.run([node_executable(),str(ROOT/'tools/evaluation/probe_detailed.ts')],
                         input=json.dumps(dict(cases=cases)),cwd=ROOT,capture_output=True,
                         text=True,encoding='utf-8',check=True)
    return json.loads(run.stdout)['rows']


class CompletionIncomeTransferTests(unittest.TestCase):
    def test_arrival_execution_and_context_contrasts_across_runtimes(self):
        records = fixture_variants(FIXTURE)
        cases = [dict(id=str(i),input=r['input']) for i,r in enumerate(records)]
        other = probe(cases)
        self.assertEqual(len(records),len(other))
        engine = MasroofEngine()
        for row,cross in zip(records,other,strict=True):
            with self.subTest(id=row['recordId']):
                actual = engine.predict_detailed(row['input'])
                self.assertEqual(field_errors(actual,row['expected']),{})
                self.assertEqual(actual,cross['typescript'])
                self.assertEqual(actual,cross['browser'])

    def test_received_amount_is_not_an_identifier_or_a_primary_override(self):
        texts = ['📩 استلم حسابك ١٧٫٢٥٠ JOD من شخص آخر. الرصيد ٥٠ JOD.',
                 'استلم حسابك *1234 مبلغ 17 JOD من شخص آخر.',
                 'استلم حسابك 17 JOD؛ ورد 5 JOD.',
                 'رقم الحساب 1234؛ حوالة بقيمة 17 JOD.']
        run = subprocess.run([node_executable(),str(ROOT/'tools/evaluation/probe_money_candidates.ts')],
                             input=json.dumps(texts),cwd=ROOT,capture_output=True,text=True,encoding='utf-8',check=True)
        other = json.loads(run.stdout)
        for raw,cross,values in zip(texts,other,([17.25],[17],[17,5],[17]),strict=True):
            with self.subTest(text=raw):
                evidence = collect_candidates(EntityText(raw),MasroofEngine.parse_number)
                self.assertEqual(evidence,cross)
                self.assertEqual([x['value'] for x in evidence['monetary']],values)
                self.assertEqual(evidence['primary'],[])
                for value in evidence['monetary']:
                    self.assertEqual(raw[value['start']:value['end']],value['text'])
        self.assertEqual(other[0]['monetary'][0]['text'],'١٧٫٢٥٠')
        self.assertIn('identifier',{x['role'] for x in other[1]['exclusions']})
        self.assertIsNone(amounts(texts[2],{},MasroofEngine.parse_number)[0])

    def test_external_transfer_is_not_proof_of_another_person(self):
        examples = [
            ('Your account received JOD 17 by an external transfer.','unknown','review'),
            ('استلم حسابك 17 JOD من حوالة خارجية.','unknown','review'),
            ('Your account received JOD 17 by an external transfer from another person.','other_person','include'),
            ('An external transfer between your own accounts completed: JOD 17.','own_accounts','exclude'),
        ]
        cases = [dict(id=str(i),input=dict(text=text)) for i,(text,_,_) in enumerate(examples)]
        engine = MasroofEngine()
        for row,(_,relation,decision),other in zip(cases,examples,probe(cases),strict=True):
            actual = engine.predict_detailed(row['input'])
            self.assertEqual(actual['transactionStatus'],'completed')
            self.assertEqual(actual['transferRelationship'],relation)
            self.assertEqual(actual['trackingDecision'],decision)
            self.assertEqual(actual,other['typescript'])
            self.assertEqual(actual,other['browser'])

    def test_confirmed_and_rejected_frames_do_not_need_candidate_scores(self):
        engine = MasroofEngine()
        with patch.object(engine,'_score_tokens',side_effect=AssertionError('Explicit arrival/execution/context must not require candidate scores')):
            for row in json.loads(FIXTURE.read_text(encoding='utf-8'))['cases']:
                with self.subTest(id=row['id']):
                    self.assertEqual(field_errors(engine.predict_detailed(row['input']),row['expected']),{})
