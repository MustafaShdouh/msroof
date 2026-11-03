"""One-event safety distinguishes separate cash movements from inclusive totals."""
import json
import unittest

from src.python.engine import MasroofEngine
from src.python.entity_text import EntityText
from src.python.money_candidates import has_movement_amount
from tools.evaluation.core_boundary_check import fixture_variants, measure
from training.corpus_io import ROOT, sha256

FIXTURE=ROOT/'tests/fixtures/core_multiple_movements_v1.json'


class CoreMultipleMovementTests(unittest.TestCase):
    def test_source_parts_and_policy_expectations_were_frozen_before_repair(self):
        obj=json.loads(FIXTURE.read_text(encoding='utf-8'))
        source=ROOT/obj['sourceSnapshot']
        self.assertEqual(sha256(source),obj['sourceSnapshotSha256'])
        original=json.loads(source.read_text(encoding='utf-8'))['records']
        index={(r['cohort'],r['recordId']):r for r in original}
        self.assertEqual(len(obj['cases']),71)
        for row in obj['cases']:
            refs=[index[(r['cohort'],r['recordId'])] for r in row['sources']]
            if row['boundary']=='separate_completed_movements':
                self.assertEqual(len(refs),2)
                self.assertTrue(all(r['expected']['transactionStatus']=='completed' for r in refs))
                self.assertTrue(all(r['expected']['amount']>0 for r in refs))
                self.assertEqual(row['input']['text'],refs[0]['input']['text'].rstrip('.')+row['separator']+refs[1]['input']['text'])
                self.assertEqual(row['expected'],dict(transactionStatus='uncertain',trackingDecision='review',amount=None))
            else:
                self.assertEqual(len(refs),1)
                text=refs[0]['input']['text']
                if row['transform']=='explicit_same_currency_principal':text=text.replace('17 was','JOD 17 was')
                else:self.assertEqual(row['transform'],'identity')
                self.assertEqual(row['input']['text'],text)
                self.assertEqual(row['expected'],refs[0]['expected'])

    def test_all_three_runtimes_reject_multi_event_selection_and_keep_single_event_totals(self):
        rows=fixture_variants(FIXTURE)
        self.assertEqual(len(rows),426)
        for row in measure(rows)['records']:
            with self.subTest(id=row['recordId']):self.assertFalse(row['mismatches'])

    def test_only_standalone_totals_are_supporting_amount_clauses(self):
        parse=MasroofEngine.parse_number
        for text in ('total debited 17.500.','Total amount charged JOD 17.500.','إجمالي المبلغ المخصوم ١٧٫٥٠٠ دينار.'):
            with self.subTest(text=text):self.assertFalse(has_movement_amount(EntityText(text).text,parse))
        for text in ('Your account was charged 17.500.','17.500 was debited from your account.',
                     'أُضيف ١٧٫٥٠٠ إلى حسابك.','total debited 17.500; 5 was credited to your account.',
                     'total debited JOD 17.500 and another JOD 5 was credited.'):
            with self.subTest(text=text):self.assertTrue(has_movement_amount(EntityText(text).text,parse))
        for text in ('Account *7812 was debited.','Your account was debited. Reference 17.250.',
                     'Your available balance is JOD 17.250.'):
            with self.subTest(text=text):self.assertFalse(has_movement_amount(EntityText(text).text,parse))
