"""Existing truth survives format changes; exact source and confirmation bindings do not change."""
from copy import deepcopy
import json
import subprocess
import unittest
from unittest.mock import patch

from src.python.engine import MasroofEngine
from src.python.entity_text import EntityText
from src.python.money_candidates import collect_candidates
from tools.evaluation.core_format_robustness import records, measure, transform
from tools.node_runtime import node_executable
from training.corpus_io import ROOT
from training.evaluation.ownership import ownership_controls


class CoreFormatRobustnessTests(unittest.TestCase):
    def test_historical_ownership_replay_uses_the_original_source_view(self):
        from training.evaluation.ownership import baseline_assessor
        old=baseline_assessor()
        frozen_view=old.__globals__['EntityText']
        self.assertEqual(frozen_view('\u200f17').text,'\u200f17')
        self.assertEqual(EntityText('\u200f17').text,'17')
        self.assertIs(old.baseline_engine.extract_entities.__func__.__globals__['EntityText'],frozen_view)

    def test_existing_core_expectations_and_full_three_runtime_parity(self):
        rows,base_count=records()
        self.assertEqual(base_count,582)
        self.assertEqual(len(rows),6984)
        for row in measure(rows):
            with self.subTest(cohort=row['cohort'],id=row['sourceId'],transform=row['transform']):
                self.assertFalse(any(row['mismatches'].values()),row['mismatches'])
                self.assertTrue(row['parity'])

    def test_display_controls_keep_exact_numeric_and_name_source_spans(self):
        fixture=json.loads((ROOT/'tests/fixtures/core_unmarked_amounts_v1.json').read_text(encoding='utf-8'))
        base=next(r['input']['text'] for r in fixture['cases'] if r['id']=='debit-ar')
        controls='\u061c\u200e\u200f\u202a\u202b\u202c\u202d\u202e\u2066\u2067\u2068\u2069\ufeff'
        texts=['🧾 '+mark+base.replace('17.250','١'+mark+'٧٫٢٥٠').replace(' ',mark+' ')+mark for mark in controls]
        run=subprocess.run([node_executable(),str(ROOT/'tools/evaluation/probe_money_candidates.ts')],input=json.dumps(texts),
                           cwd=ROOT,capture_output=True,text=True,encoding='utf-8',check=True)
        for raw,other in zip(texts,json.loads(run.stdout),strict=True):
            view=EntityText(raw)
            evidence=collect_candidates(view,MasroofEngine.parse_number)
            self.assertEqual(evidence,other)
            self.assertEqual(view.text,'🧾 '+EntityText(base.replace('17.250','١٧٫٢٥٠')).text)
            self.assertEqual(len(evidence['anchored']),1)
            c=evidence['anchored'][0];self.assertEqual(c['value'],17.25)
            self.assertEqual(raw[c['start']:c['end']],c['text'])
        names=json.loads((ROOT/'tests/fixtures/entity_text_cases.json').read_text(encoding='utf-8'))['cases']
        item=next(r for r in names if r['id']=='diacritics_and_spacing')
        raw_name=item['name'].replace(' ','\u200f ')
        raw='\ufeff🧾 '+item['text'].replace(item['name'],raw_name)
        view=EntityText(raw);logical_name=EntityText(raw_name).text;a=view.text.index(logical_name)
        self.assertEqual(view.exact(a,a+len(logical_name)),raw_name)

    def test_logically_empty_display_controls_do_not_reach_candidate_scoring(self):
        engine=MasroofEngine();texts=['\ufeff',' \u200f\u061c ','\u2067\u2069']
        with patch.object(engine,'_score_tokens',side_effect=AssertionError('Empty logical text is not a financial candidate')):
            actual=[engine.predict_detailed(dict(text=t)) for t in texts]
        run=subprocess.run([node_executable(),str(ROOT/'tools/evaluation/probe_detailed.ts')],
            input=json.dumps(dict(cases=[dict(id=str(i),input=dict(text=t)) for i,t in enumerate(texts)])),
            cwd=ROOT,capture_output=True,text=True,encoding='utf-8',check=True)
        for py,cross in zip(actual,json.loads(run.stdout)['rows'],strict=True):
            self.assertEqual(py['reasonCodes'],['empty_or_malformed'])
            self.assertEqual(py['trackingDecision'],'exclude')
            self.assertIsNone(py['amount'])
            self.assertEqual(py,cross['typescript']);self.assertEqual(py,cross['browser'])

    def test_format_equivalence_never_reuses_an_exact_raw_ownership_confirmation(self):
        original=next(r for r in ownership_controls() if r['contextStatus']=='applied'
                      and r['expect'].get('trackingDecision')=='include' and not r['sameAsBody'])
        engine=MasroofEngine();self.assertEqual(engine.predict_with_ownership(original['request'])['contextStatus'],'applied')
        rows=[]
        for kind in ('bom_prefix','directional_wrapper','rtl_word_boundaries'):
            request=deepcopy(original['request']);request['message']['text']=transform(request['message']['text'],kind)
            self.assertEqual(EntityText(request['message']['text']).text,EntityText(original['request']['message']['text']).text)
            py=engine.predict_with_ownership(request)
            self.assertEqual(py['contextStatus'],'invalid')
            self.assertEqual(py['assessment']['trackingDecision'],'review')
            rows.append(dict(id=kind,request=request))
        run=subprocess.run([node_executable(),str(ROOT/'tools/evaluation/probe_detailed.ts')],
            input=json.dumps(dict(cases=[],ownershipCases=rows)),cwd=ROOT,capture_output=True,text=True,encoding='utf-8',check=True)
        for row,cross in zip(rows,json.loads(run.stdout)['ownershipRows'],strict=True):
            py=engine.predict_with_ownership(row['request'])
            self.assertEqual(py,cross['typescript']);self.assertEqual(py,cross['browser'])
