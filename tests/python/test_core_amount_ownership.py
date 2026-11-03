"""Amount-role ordering and transfer ownership preserve frozen source truth."""
from copy import deepcopy
import itertools
import json
import subprocess
import unittest

from src.python.engine import MasroofEngine
from tools.evaluation.core_boundary_check import fixture_variants, measure
from tools.evaluation.core_money import FIELDS
from tools.node_runtime import node_executable
from training.corpus_io import ROOT, sha256
from training.evaluation.ownership import ownership_controls

FIXTURE=ROOT/'tests/fixtures/core_amount_ownership_v1.json'


class CoreAmountOwnershipTests(unittest.TestCase):
    def test_contrasts_inherit_frozen_truth_and_only_permitted_source_edits(self):
        contract=json.loads(FIXTURE.read_text(encoding='utf-8'))
        source=ROOT/contract['sourceSnapshot']
        self.assertEqual(sha256(source),contract['sourceSnapshotSha256'])
        original=json.loads(source.read_text(encoding='utf-8'))['records']
        index={(r['cohort'],r['recordId']):r for r in original}
        balance=contract['balanceSource']
        base=index[(balance['cohort'],balance['recordId'])]
        self.assertEqual(balance['fragment'],base['input']['text'].split('. ',1)[0]+'.')
        self.assertEqual(len(contract['cases']),133)
        for row in contract['cases']:
            ref=row['source']; old=index[(ref['cohort'],ref['recordId'])]
            text=old['input']['text']; kind=ref['transform']
            self.assertEqual(row['expected'],{k:v for k,v in old['expected'].items() if k in FIELDS})
            self.assertEqual({k:v for k,v in row['input'].items() if k!='text'},
                             {k:v for k,v in old['input'].items() if k!='text'})
            if kind=='amount_clause_order':
                allowed={'; '.join(parts)+'.' for parts in itertools.permutations(text.rstrip('.').split('; '))}
            elif kind=='equal_competing_primaries':
                self.assertEqual(ref['recordId'],'two-primary-en:0:False')
                allowed={text.replace('19','17')}
            elif kind=='ownership_identity':allowed={text}
            elif kind=='balance_before_transfer':allowed={balance['fragment']+' '+text}
            elif kind=='balance_after_transfer':allowed={text+' '+balance['fragment']}
            else:self.fail('Unreviewed contrast transform: '+kind)
            self.assertIn(row['input']['text'],allowed)

    def test_frozen_amount_and_ownership_expectations_in_all_three_runtimes(self):
        rows=fixture_variants(FIXTURE)
        self.assertEqual(len(rows),798)
        for row in measure(rows)['records']:
            with self.subTest(id=row['recordId']):self.assertFalse(row['mismatches'])

    def test_balance_does_not_reuse_stale_confirmation_or_change_fresh_confirmed_core(self):
        engine=MasroofEngine(); requests=[]; expected=[]
        controls=[r for r in ownership_controls() if r['contextStatus']=='applied']
        self.assertTrue(controls)
        balance=json.loads(FIXTURE.read_text(encoding='utf-8'))['balanceSource']['fragment']
        for row in controls:
            old=engine.predict_with_ownership(row['request'])
            for before in (True,False):
                stale=deepcopy(row['request']);raw=stale['message']['text']
                stale['message']['text']=balance+' '+raw if before else raw+' '+balance
                result=engine.predict_with_ownership(stale)
                self.assertEqual(result['contextStatus'],'invalid')
                self.assertEqual(result['contextReason'],'message_mismatch')
                self.assertEqual(result['assessment']['trackingDecision'],'review')
                fresh=deepcopy(stale);fresh['ownershipContext']['text']=fresh['message']['text']
                confirmed=engine.predict_with_ownership(fresh)
                self.assertEqual(confirmed['contextStatus'],'applied')
                for field in FIELDS:self.assertEqual(confirmed['assessment'][field],old['assessment'][field],field)
                for kind,request,actual in [('stale',stale,result),('fresh',fresh,confirmed)]:
                    requests.append(dict(id=row['id']+str(before)+kind,request=request));expected.append(actual)
        run=subprocess.run([node_executable(),str(ROOT/'tools/evaluation/probe_detailed.ts')],
            input=json.dumps(dict(cases=[],ownershipCases=requests)),cwd=ROOT,capture_output=True,
            text=True,encoding='utf-8',check=True)
        for actual,other in zip(expected,json.loads(run.stdout)['ownershipRows'],strict=True):
            self.assertEqual(actual,other['typescript']);self.assertEqual(actual,other['browser'])
