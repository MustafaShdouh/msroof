"""Bare account amounts require cash roles, intact source spans and resolved outcomes."""
import json
import subprocess
import unittest
from unittest.mock import patch

from src.python.engine import MasroofEngine
from src.python.entity_text import EntityText
from src.python.money_candidates import collect_candidates
from tests.python.test_completion_settlement import probe
from tools.evaluation.core_boundary_check import fixture_variants
from tools.evaluation.core_money import field_errors
from tools.node_runtime import node_executable
from training.corpus_io import ROOT

FIXTURE = ROOT/'tests/fixtures/core_unmarked_amounts_v1.json'


def candidates_across_runtimes(texts):
    run = subprocess.run([node_executable(),str(ROOT/'tools/evaluation/probe_money_candidates.ts')],
                         input=json.dumps(texts),cwd=ROOT,capture_output=True,text=True,encoding='utf-8',check=True)
    return json.loads(run.stdout)


class UnmarkedAccountAmountsTests(unittest.TestCase):
    def test_frozen_account_amount_contrasts_across_three_runtimes(self):
        rows=fixture_variants(FIXTURE)
        other=probe([dict(id=str(i),input=r['input']) for i,r in enumerate(rows)])['rows']
        engine=MasroofEngine()
        for row,cross in zip(rows,other,strict=True):
            with self.subTest(id=row['recordId']):
                actual=engine.predict_detailed(row['input'])
                self.assertEqual(field_errors(actual,row['expected']),{})
                self.assertEqual(actual,cross['typescript']);self.assertEqual(actual,cross['browser'])

    def test_unicode_spans_balance_and_identifier_exclusions_retain_amount_role(self):
        texts=['📩 خُصم ١٧٫٢٥٠ من حسابك *١٢٣٤. الرصيد ٨٨٫٤٠٠ USD.',
               '📩 استلم حسابك ۱۷٫۲۵۰ من شخص آخر. رقم المرجع ۷۸۱۲۳۴.',
               'Your account was charged 17.250 dollars. Reference 781234.',
               'Purchase USD 10; your account was charged 7.090.']
        for raw,other in zip(texts,candidates_across_runtimes(texts),strict=True):
            with self.subTest(text=raw):
                actual=collect_candidates(EntityText(raw),MasroofEngine.parse_number)
                self.assertEqual(actual,other)
                bare=[c for key in ('anchored','primary') for c in actual[key] if c['currency'] is None]
                self.assertEqual({c['text'] for c in bare},{'١٧٫٢٥٠'} if raw==texts[0] else {'۱۷٫۲۵۰'} if raw==texts[1] else {'17.250'} if raw==texts[2] else {'7.090'})
                for c in bare:self.assertEqual(raw[c['start']:c['end']],c['text'])
                if raw==texts[0]:self.assertEqual({x['role'] for x in actual['exclusions']},{'balance','identifier'})

    def test_counts_masks_partial_references_and_unscored_values_do_not_gain_bare_candidates(self):
        texts=['Reference 17.250 was debited from your account.',
               'Ref 17.250 was credited to your account.',
               'Your account 1234 was debited from your account.',
               'حسابك 1234 أضيف إلى حسابك.',
               'Your account received 17 points.','استلم حسابك 17 حوالة.',
               'Your account received 17 kg.','Your account received 17%.',
               '17:25 was debited from your account.','*1234 was debited from your account.',
               '-17 was debited from your account.','Your account was debited +17.',
               'Your account received 0.000.']
        # Zero/signed are feature-eligibility checks, not new product truths.
        for raw,other in zip(texts,candidates_across_runtimes(texts),strict=True):
            with self.subTest(text=raw):
                actual=collect_candidates(EntityText(raw),MasroofEngine.parse_number)
                self.assertEqual(actual,other)
                self.assertFalse([c for key in ('anchored','primary') for c in actual[key]])

    def test_distinct_mentions_compete_and_primary_currency_stays_local(self):
        cases=[('Your account received 17 and your account received 17.',None,'default_missing'),
               ('Your account received 17; fee USD 0.500.',None,'default_missing'),
               ('Your account was charged 17; total debited 19.',None,'default_missing'),
               ('Purchase USD 10; your account was charged 7.090.',7.09,'default_missing'),
               ('Your account was charged 17 dollars.',17,'default_ambiguous'),
               ('Your account received 17 on 2026-11-01. Available balance USD 88.',17,'default_missing')]
        engine=MasroofEngine()
        other=probe([dict(id=str(i),input=dict(text=t)) for i,(t,_,_) in enumerate(cases)])['rows']
        for (text,amount,resolution),cross in zip(cases,other,strict=True):
            with self.subTest(text=text):
                actual=engine.predict_detailed(dict(text=text))
                self.assertEqual(actual,cross['typescript']);self.assertEqual(actual,cross['browser'])
                self.assertEqual(actual['amount'],amount);self.assertEqual(actual['currency'],'JOD')
                self.assertEqual(actual['currencyResolution'],resolution)
                if amount is None:self.assertEqual(actual['trackingDecision'],'review')
        c=collect_candidates(EntityText(cases[0][0]),engine.parse_number)
        self.assertEqual(len(c['anchored']),2)
        self.assertNotEqual(c['anchored'][0]['start'],c['anchored'][1]['start'])

    def test_explicit_account_roles_and_context_do_not_need_candidate_head(self):
        engine=MasroofEngine()
        with patch.object(engine,'_score_tokens',side_effect=AssertionError('Cash roles/context must resolve structurally')):
            for row in json.loads(FIXTURE.read_text(encoding='utf-8'))['cases']:
                if row['id']=='quantity-count-ar':continue
                with self.subTest(id=row['id']):
                    self.assertEqual(field_errors(engine.predict_detailed(row['input']),row['expected']),{})
