"""Raw source evidence and exclusion roles must survive multilingual normalization."""
import json
import subprocess
import unittest
from pathlib import Path
from src.python.entity_text import EntityText
from src.python.engine import MasroofEngine
from src.python.money_candidates import collect_candidates,amounts
from tools.node_runtime import node_executable

ROOT=Path(__file__).resolve().parents[2]


class MoneyCandidateTests(unittest.TestCase):
    def test_exact_source_spans_and_cross_runtime_roles(self):
        texts=[
            '📩  تم خَصم ١٢٫٧٥٠ دينار. الرصيد المتاح ٥٠ دينار.',
            'Balance JOD 50. JOD 12.750 debited from account *7812. Ref 981122; date 2026-10-29.',
            'تم خصم ۱۲٫۷۵۰ دينار من حسابك.',
            'JOD 1,250.375 was debited. Available balance JOD 2,000.000.',
            'Amount 18.250 was debited.',
            'A purchase of 20 JOD الرصيد 100 JOD',
            '📩 JOD 12.750 debited from account *7812.',
            'USD 10 was debited; equivalent JOD 7.090. Fee JOD 0.500.',
            '📩 Purchase USD 10; your account was charged 7.090 JOD.',
        ]
        p=subprocess.run([node_executable(),str(ROOT/'tools/evaluation/probe_money_candidates.ts')],input=json.dumps(texts),capture_output=True,text=True,encoding='utf-8',cwd=ROOT,check=True)
        other=json.loads(p.stdout)
        for raw,ts in zip(texts,other,strict=True):
            with self.subTest(text=raw):
                evidence=collect_candidates(EntityText(raw),MasroofEngine.parse_number)
                self.assertEqual(evidence,ts)
                for candidate in evidence['monetary']+evidence['anchored']+evidence['primary']:
                    self.assertEqual(raw[candidate['start']:candidate['end']],candidate['text'])
                for excluded in evidence['exclusions']:
                    self.assertGreater(excluded['end'],excluded['start'])
                    self.assertNotIn(excluded['role'],['transaction','fee','primary_fx'])
        self.assertEqual(other[0]['monetary'][0]['text'],'١٢٫٧٥٠')
        self.assertEqual(other[0]['monetary'][0]['value'],12.75)
        self.assertEqual({r['role'] for r in other[1]['exclusions']},{'balance','identifier','date'})
        self.assertEqual([c['value'] for c in other[5]['monetary']],[20])

    def test_balance_preserves_the_currency_of_a_debit_on_the_next_line(self):
        debit = 'USD 8.250 was debited from your account.'
        cases = [
            ('Available balance 630.500\n' + debit, 'USD', 'explicit'),
            ('Available balance JOD 630.500\r\n' + debit, 'USD', 'explicit'),
            ('Available balance 630.500\\r\\n' + debit, 'USD', 'explicit'),
            ('📩 الرصيد المتاح ٦٣٠٫٥٠٠\nUSD ٨٫٢٥٠ was debited from your account.', 'USD', 'explicit'),
            ('Available balance 630.500 JOD\n' + debit, 'USD', 'explicit'),
            ('Available balance 630.500\nUSD\nYour account was debited 8.250.', 'JOD', 'default_missing'),
        ]
        inputs = [dict(id=str(i), input=dict(text=text)) for i, (text, _, _) in enumerate(cases)]
        detailed = subprocess.run(
            [node_executable(), str(ROOT/'tools/evaluation/probe_detailed.ts')],
            input=json.dumps(dict(cases=inputs)), capture_output=True, text=True,
            encoding='utf-8', cwd=ROOT, check=True,
        )
        candidates = subprocess.run(
            [node_executable(), str(ROOT/'tools/evaluation/probe_money_candidates.ts')],
            input=json.dumps([text for text, _, _ in cases]), capture_output=True, text=True,
            encoding='utf-8', cwd=ROOT, check=True,
        )
        engine = MasroofEngine()
        for (text, currency, resolution), row, js_candidates in zip(
            cases, json.loads(detailed.stdout)['rows'], json.loads(candidates.stdout), strict=True
        ):
            with self.subTest(text=text):
                actual = engine.predict_detailed(dict(text=text))
                self.assertEqual(actual, row['typescript'])
                self.assertEqual(actual, row['browser'])
                self.assertEqual(actual['trackingDecision'], 'include')
                self.assertEqual(actual['amount'], 8.25)
                self.assertEqual(actual['currency'], currency)
                self.assertEqual(actual['currencyResolution'], resolution)
                evidence = collect_candidates(EntityText(text), engine.parse_number)
                self.assertEqual(evidence, js_candidates)
                balance, = [item for item in evidence['exclusions'] if item['role'] == 'balance']
                self.assertEqual('USD' in text[balance['start']:balance['end']], resolution == 'default_missing')

    def test_owner_selected_posted_total_and_account_charge(self):
        examples=[
            ('Purchase JOD 10; fee JOD 0.500; total debited JOD 10.500.',10.5,'JOD'),
            ('Purchase USD 10; your account was charged JOD 7.090.',7.09,'JOD'),
            ('قيمة الشراء ١٠ دولار. تم خصم من حسابك ٧٫٠٩٠ دينار.',7.09,'JOD'),
            ('📩 Purchase USD 10; your account was charged 7.090 JOD.',7.09,'JOD'),
        ]
        inputs=[dict(id=str(i),input=dict(text=text)) for i,(text,_,_) in enumerate(examples)]
        p=subprocess.run([node_executable(),str(ROOT/'tools/evaluation/probe_detailed.ts')],input=json.dumps(dict(cases=inputs)),capture_output=True,text=True,encoding='utf-8',cwd=ROOT,check=True)
        other=json.loads(p.stdout)['rows'];engine=MasroofEngine()
        for (text,value,unit),row in zip(examples,other,strict=True):
            result=engine.predict_detailed(dict(text=text))
            self.assertEqual(result,row['typescript']);self.assertEqual(result,row['browser'])
            self.assertEqual(result['amount'],value);self.assertEqual(result['currency'],unit)
            self.assertEqual(result['trackingDecision'],'include')
        self.assertIsNone(amounts('Purchase JOD 10; fee JOD 0.500.',{},MasroofEngine.parse_number)[0])
        self.assertIsNone(amounts('Account was charged JOD 10; account was charged JOD 12.',{},MasroofEngine.parse_number)[0])

    def test_ambiguous_multiple_amounts_and_nonfinite_values_stay_unselected(self):
        self.assertIsNone(amounts('JOD 10 or JOD 12',{},MasroofEngine.parse_number)[0])
        self.assertIsNone(amounts('JOD 10 and JOD 12',{},MasroofEngine.parse_number)[0])
        for value in (float('nan'),float('inf'),0,-1):
            e=collect_candidates(EntityText('JOD 10'),lambda _:value)
            self.assertEqual(e['monetary'],[])
