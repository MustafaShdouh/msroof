"""Readiness summaries must expose missing labels and avoid independence claims."""
import json
from pathlib import Path
import tempfile
import unittest

from tools.evaluation.core_readiness_inventory import CORE_FIELDS, ROOT, REPORT, build, digest, digit_script, load_checked, separators, summarize
from training.corpus_io import recorded_source


def row(expected, **changes):
    actual=dict(transactionStatus='completed', trackingDecision='include', amount=17,
                currency='JOD', currencyResolution='explicit', direction='outgoing', transferRelationship='not_transfer')
    actual.update(changes)
    return dict(input=dict(text='JOD 17'), expected=expected, actual=actual)


class CoreReadinessInventoryTests(unittest.TestCase):
    def test_empty_denominators_and_null_truth_are_not_positive_extraction_success(self):
        empty=summarize([])
        self.assertIsNone(empty['amountCurrencyAcceptedOnly']['rate'])
        self.assertEqual(empty['fullCoreAcceptedEvents']['eligible'],0)
        s=summarize([row(dict(transactionStatus='non_transaction',amount=None),amount=None,
                         transactionStatus='non_transaction',trackingDecision='exclude')])
        self.assertEqual(s['fields']['amount']['nullTruthCases'],1)
        self.assertEqual(s['fields']['amount']['allLabeled']['correct'],1)
        self.assertIsNone(s['fields']['amount']['nonNullTruth']['rate'])
        self.assertEqual(s['amountCurrencyAllKnown']['eligible'],0)

    def test_partial_event_truth_does_not_become_complete_contract_truth(self):
        e=dict(transactionStatus='completed',trackingDecision='include',amount=17,currency='JOD',direction='outgoing')
        partial=row(e)
        s=summarize([partial,row(dict(partial['actual']))])
        self.assertEqual(s['acceptedEventAssertions']['eligible'],2)
        self.assertEqual(s['fullCoreAcceptedEvents']['eligible'],1)
        self.assertEqual(s['fields']['transferRelationship']['allLabeled']['eligible'],1)
        status_only=summarize([row(dict(transactionStatus='completed'))])
        self.assertEqual(status_only['acceptedEventAssertions']['eligible'],0)
        self.assertEqual(status_only['actualIncludesWithoutAmountCurrencyTruth'],1)

    def test_abstention_and_wrong_amount_count_in_all_eligible_and_accepted_views(self):
        e=dict(transactionStatus='completed',trackingDecision='include',amount=17,currency='JOD',direction='outgoing')
        s=summarize([row(e,amount=None,trackingDecision='review'),row(e,amount=19),row(e)])
        self.assertEqual(s['amountCurrencyExpectedInclude'],dict(correct=1,eligible=3,rate=1/3))
        self.assertEqual(s['amountCurrencyAcceptedOnly'],dict(correct=1,eligible=2,rate=1/2))
        self.assertEqual(s['includeMissOrReview'],dict(count=1,eligible=3))
        self.assertEqual(s['acceptedEventAssertions']['correct'],1)

    def test_false_includes_cover_own_accounts_and_reviews_as_well_as_ordinary_noise(self):
        rows=[row(dict(transactionStatus='non_transaction',trackingDecision='exclude')),
              row(dict(transactionStatus='completed',trackingDecision='exclude',transferRelationship='own_accounts')),
              row(dict(transactionStatus='uncertain',trackingDecision='review'))]
        s=summarize(rows)
        self.assertEqual(s['falseIncludes'],dict(count=3,eligible=3))
        self.assertEqual(s['ordinaryFalseIncludes'],dict(count=1,eligible=1))
        self.assertEqual(s['ownAccountFalseIncludes'],dict(count=1,eligible=1))
        self.assertEqual(s['wrongCertainty'],dict(count=1,eligible=1))

    def test_digit_profiles_are_whole_input_metadata_with_distinct_scripts(self):
        for text,want in [('17','ascii'),('١٧','arabic_indic'),('۱۷','eastern_arabic'),('17 ١٧','mixed_digits'),('x','no_digits')]:
            self.assertEqual(digit_script(dict(input=dict(text=text))),want)
        self.assertEqual(separators(dict(input=dict(text='17.250 ١٧٫٢٥٠'))),'dot+arabic_decimal')
        self.assertEqual(separators(dict(input=dict(text='Sentence. Ref 1234'))),'no_digit_separator')

    def test_changed_or_escaped_evidence_is_rejected(self):
        with tempfile.TemporaryDirectory() as area:
            root=Path(area);p=root/'evidence.json';p.write_text('{}',encoding='utf-8')
            sha=digest(p);self.assertEqual(load_checked(root,p.name,sha),p.resolve())
            p.write_text('[]',encoding='utf-8')
            with self.assertRaisesRegex(ValueError,'Changed evidence'):load_checked(root,p.name,sha)
            with self.assertRaisesRegex(ValueError,'escapes'):load_checked(root,'../elsewhere',sha)

    def test_bound_inventory_reproduces_without_importing_engines_or_scoring(self):
        expected=json.loads((ROOT/REPORT).read_text(encoding='utf-8'))
        hashes=json.loads((ROOT/'data/private/report_inputs/manifests/core_money_r6_inventory_v1.json').read_text(encoding='utf-8'))
        # A later tester/runtime edit must not rewrite or invalidate historical truth.
        with tempfile.TemporaryDirectory(prefix='masroof-readiness-') as directory:
            root=Path(directory).resolve()
            for relative,sha in hashes.items():
                target=(root/relative).resolve()
                if not target.is_relative_to(root):raise ValueError('Escaped readiness snapshot')
                target.parent.mkdir(parents=True,exist_ok=True)
                target.write_bytes(recorded_source(relative,sha))
            self.assertEqual(build(root),expected)
            evidence=root/'config/contracts/transaction_evidence.json'
            evidence.write_text('{}',encoding='utf-8')
            with self.assertRaisesRegex(ValueError,'Changed evidence'):build(root)
        self.assertFalse(expected['inferenceExecuted']);self.assertFalse(expected['trainingExecuted'])
        self.assertFalse(expected['reservedInferred']);self.assertIsNone(expected['pooledAccuracy'])
        self.assertEqual(expected['independentEligibleCases'],0)
        self.assertEqual(expected['inputEntries'],2302)
        self.assertIsNone(expected['release']['thresholds'])
        self.assertEqual(expected['runtime']['researchImportsInCoreGraph'],[])
        self.assertEqual(expected['cohorts']['core_unmarked_amounts_v1']['summary']['fullCoreAcceptedEvents']['eligible'],0)
        self.assertEqual(set(CORE_FIELDS),set(expected['cohorts']['authored74']['summary']['fields']))
