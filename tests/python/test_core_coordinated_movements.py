"""Explicit same-clause separation cannot hide a second completed movement."""
import json
import unittest
from tools.evaluation.core_boundary_check import fixture_variants, measure
from training.corpus_io import ROOT,sha256

FIXTURE=ROOT/'tests/fixtures/core_coordinated_movements_v1.json'


class CoordinatedMovementTests(unittest.TestCase):
    def test_frozen_source_edits_and_evidence_are_traceable(self):
        obj=json.loads(FIXTURE.read_text(encoding='utf-8'))
        source=ROOT/obj['sourceSnapshot'];prior=ROOT/obj['priorFixture']
        self.assertEqual(sha256(source),obj['sourceSnapshotSha256'])
        self.assertEqual(sha256(prior),obj['priorFixtureSha256'])
        idx={(r['cohort'],r['recordId']):r for r in json.loads(source.read_text(encoding='utf-8'))['records']}
        old={r['id']:r for r in json.loads(prior.read_text(encoding='utf-8'))['cases']}
        balance=obj['balanceSource'];self.assertEqual(balance['fragment'],idx[(balance['cohort'],balance['recordId'])]['input']['text'].split('. ',1)[0]+'.')
        self.assertEqual(len(obj['cases']),90)
        for row in obj['cases']:
            refs=[idx[(r['cohort'],r['recordId'])] for r in row['sources']]
            with self.subTest(id=row['id']):
                if row['boundary']=='explicit_separate_operation':
                    self.assertEqual(len(refs),2)
                    self.assertTrue(all(r['expected']['transactionStatus']=='completed' and r['expected']['amount']>0 for r in refs))
                    self.assertEqual(row['input']['text'],refs[0]['input']['text'].rstrip('.')+row['joiner']+refs[1]['input']['text'])
                    self.assertEqual(row['expected'],dict(transactionStatus='uncertain',trackingDecision='review',amount=None))
                elif row['boundary']=='single_event_control':
                    original=old[row['id'].removeprefix('single-')]
                    self.assertEqual(row['input'],original['input']);self.assertEqual(row['expected'],original['expected'])
                elif row['boundary']=='single_event_supporting_amounts':
                    self.assertEqual(row['input']['text'],refs[0]['input']['text'].replace('; ',' and '))
                    self.assertEqual(row['expected'],refs[0]['expected'])
                else:
                    self.assertEqual(row['boundary'],'separate_balance_not_movement')
                    a,b=(balance['fragment'],refs[0]['input']['text']) if row['balanceBefore'] else (refs[0]['input']['text'],balance['fragment'])
                    self.assertEqual(row['input']['text'],a.rstrip('.')+row['joiner']+b)
                    self.assertEqual(row['expected'],refs[0]['expected'])

    def test_all_frozen_variants_match_in_python_typescript_and_tester(self):
        rows=fixture_variants(FIXTURE);self.assertEqual(len(rows),540)
        for row in measure(rows)['records']:
            with self.subTest(id=row['recordId']):self.assertFalse(row['mismatches'])

    def test_separate_operation_wording_cannot_escape_a_nonreceipt_frame(self):
        cases=json.loads(FIXTURE.read_text(encoding='utf-8'))['cases'];rows=[]
        frames={'en':['This is an example, not a financial notification: "{}"','Teaching example, not a financial notification: {}'],
                'ar':['هذا مثال توضيحي وليس إشعاراً مالياً: «{}»','هذا نموذج تعليمي: «{}»']}
        for language in ('en','ar'):
            source=next(r for r in cases if r['boundary']=='explicit_separate_operation' and r['language']==language and ';' not in r['input']['text'])
            for frame in frames[language]:
                for digits in ('0123456789','٠١٢٣٤٥٦٧٨٩','۰۱۲۳۴۵۶۷۸۹'):
                    for contact in (False,True):
                        raw=frame.format(source['input']['text']).translate(str.maketrans('0123456789',digits))
                        rows.append(dict(cohort='authored_scope_controls',recordId=str(len(rows)),language=language,family='explicit_nonreceipt_frame',input=dict(text=raw,sender='Saved contact' if contact else '',isContact=contact),expected=dict(transactionStatus='non_transaction',trackingDecision='exclude',amount=None)))
        self.assertEqual(len(rows),24)
        for row in measure(rows)['records']:
            with self.subTest(id=row['recordId']):self.assertFalse(row['mismatches'])
