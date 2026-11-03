"""Intake holds are not admission; reviews/source truth must bind exact content."""
import copy
import json
from pathlib import Path
import tempfile
import unittest

from tools.contracts.core_preflight import ROOT, POLICY_PATH, fingerprints, intake_preflight, load_private_intake, model_structure_errors, private_path, runtime_preflight, sha


class CorePreflightTests(unittest.TestCase):
    def setUp(self):
        self.area=tempfile.TemporaryDirectory(prefix='masroof-intake-')
        self.addCleanup(self.area.cleanup)
        self.root=Path(self.area.name)
        for name in (POLICY_PATH,'config/contracts/transaction_behavior.json'):
            p=self.root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((ROOT/name).read_bytes())
        self.policy=json.loads((ROOT/POLICY_PATH).read_text(encoding='utf-8'))
        text='A synthetic unit-test receipt only: 17 was debited from your account.'
        source=self.root/'data/private/core_evaluation_v1/sources/unit.txt';source.parent.mkdir(parents=True);source.write_text(text,encoding='utf-8')
        h=fingerprints(text)['raw']
        review=dict(reviewer='unit-test-reviewer',evidence='Synthetic test declaration, not real human gold',textSha256=h)
        expected=dict(transactionStatus='completed',trackingDecision='include',amount=17,currency='JOD',currencyResolution='default_missing',direction='outgoing',transferRelationship='not_transfer')
        self.row=dict(id='unit',sourcePath=source.relative_to(self.root).as_posix(),sourceSha256=sha(source.read_bytes()),
            sourceLocator=dict(startChar=0,endChar=len(text)),text=text,textSha256=h,origin='user_attested_real_seed',
            originVerification=review,consentReview=review,exposureReview=review,familyIsolationReview=review,
            exposure='attested_unexposed',sanitizationReviewStatus='reviewed_private_original',language='en',
            verifiedTemplateFamilyId='unit-family',trainingEligible=False,evaluationEligible=False,
            labels={k:dict(state='reviewed',reviewer='unit-test-reviewer',reviewerType='human',value=v,
                           basis='source_text',evidence='Synthetic test assertion only',textSha256=h) for k,v in expected.items()})
        self.catalog=dict(schemaVersion='1.0.0',coverageStatus='partial',verifiedFamilyIds=[],**fingerprints('Known exposed reference'))
        for key in ('raw','normalized','numericProxy'):self.catalog[key]=[self.catalog[key]]

    def run_rows(self,*rows,catalog=None):
        return intake_preflight(dict(schemaVersion='1.0.0',trainingEligible=False,evaluationEligible=False,records=list(rows)),
                                self.catalog if catalog is None else catalog,self.root)

    def holds(self,row):return self.run_rows(row)['records'][0]['holds']

    def test_local_completeness_never_authorizes_scoring_or_clears_partial_coverage(self):
        result=self.run_rows(self.row)
        self.assertEqual(result['records'][0]['holds'],[])
        self.assertEqual(result['summary']['locallyComplete'],1)
        self.assertIn('exposure_catalog_partial',result['summary']['batchBlockers'])
        for key in ('trainingEligible','independentEvaluationEligible','scoringAuthorized'):self.assertFalse(result[key])
        self.assertIn('no_records',self.run_rows()['summary']['batchBlockers'])

    def test_generated_exposed_unknown_and_weak_reviews_are_held(self):
        for key,value,reason in [('origin','generated','generated_or_unresolved_origin'),
                                 ('exposure','gemini_seed','exposed_or_unknown_history'),
                                 ('verifiedTemplateFamilyId',None,'source_family_unreviewed'),
                                 ('consentReview',None,'consentReview_missing_or_stale')]:
            row=copy.deepcopy(self.row);row[key]=value
            with self.subTest(key=key):self.assertIn(reason,self.holds(row))
        for kind in ('weak','unknown'):
            row=copy.deepcopy(self.row);row['labels']['amount']['state']=kind
            self.assertIn('core_truth_incomplete',self.holds(row))
        row=copy.deepcopy(self.row);row['labels']['amount']['reviewerType']='assistant'
        self.assertIn('core_truth_incomplete',self.holds(row))

    def test_changed_partial_source_or_stale_label_and_review_cannot_pass(self):
        row=copy.deepcopy(self.row);row['sourceLocator']['endChar']-=1
        self.assertIn('source_binding_mismatch',self.holds(row))
        for field in ('exposureReview','originVerification'):
            row=copy.deepcopy(self.row);row[field]['textSha256']='0'*64
            self.assertIn(field+'_missing_or_stale',self.holds(row))
        row=copy.deepcopy(self.row);row['labels']['amount']['textSha256']='0'*64
        self.assertIn('core_truth_incomplete',self.holds(row))

    def test_raw_normalized_numeric_proxy_and_known_family_matches_are_review_holds(self):
        for text in (self.row['text'], self.row['text'].upper(),self.row['text'].replace('17','19')):
            catalog=copy.deepcopy(self.catalog)
            for key,value in fingerprints(text).items():catalog[key]=[value]
            result=self.run_rows(self.row,catalog=catalog)
            self.assertTrue(any(h.startswith('known_') for h in result['records'][0]['holds']))
        catalog=copy.deepcopy(self.catalog);catalog['verifiedFamilyIds']=['unit-family']
        self.assertIn('known_family_overlap',self.run_rows(self.row,catalog=catalog)['records'][0]['holds'])

    def test_duplicates_remain_present_and_held_instead_of_being_silently_deleted(self):
        row=copy.deepcopy(self.row);row['id']='second'
        result=self.run_rows(self.row,row)
        self.assertEqual(result['summary']['records'],2)
        self.assertTrue(all('duplicate_content_review' in r['holds'] for r in result['records']))
        self.assertEqual(result['summary']['verifiedFamilies'],1)

    def test_reviewed_unknown_ownership_is_valid_and_must_remain_review(self):
        row=copy.deepcopy(self.row)
        row['labels']['transferRelationship']['value']='unknown';row['labels']['trackingDecision']['value']='review'
        self.assertEqual(self.holds(row),[])
        row['labels']['trackingDecision']['value']='include'
        self.assertIn('contradictory_core_truth',self.holds(row))

    def test_null_amount_is_different_from_missing_annotation_and_uncontracted_signs(self):
        row=copy.deepcopy(self.row);row['labels']['amount']['value']=None;row['labels']['trackingDecision']['value']='review'
        self.assertEqual(self.holds(row),[])
        del row['labels']['amount']
        self.assertIn('core_truth_incomplete',self.holds(row))
        for amount in (0,-17,float('nan'),float('inf'),True):
            row=copy.deepcopy(self.row);row['labels']['amount']['value']=amount
            self.assertIn('uncontracted_or_invalid_amount',self.holds(row))

    def test_private_path_boundaries_and_malformed_input_reject_without_reading_reservations(self):
        for path in ('../outside','data/private/sms_scope_reserved.json','data/annotations/sms_scope_v1/anything.json'):
            with self.assertRaises(ValueError):private_path(self.root,path,self.policy)
        row=copy.deepcopy(self.row);row['labels']['currencyResolution']['value']=[]
        self.assertIn('invalid_core_truth',self.holds(row))
        row=copy.deepcopy(self.row);row['sourceLocator']=[]
        self.assertIn('source_binding_mismatch',self.holds(row))

    def test_pinned_weights_and_finite_triples_are_checked_without_inference(self):
        self.assertTrue(runtime_preflight()['weightArtifactValid'])
        for model in ({},dict(metadata=dict(intercept_tx=True,intercept_credit=0),features={'x':[1,1,1]}),
                      dict(metadata=dict(intercept_tx=0,intercept_credit=0),features={'x':[1,float('nan'),1]})):
            self.assertTrue(model_structure_errors(model))
        p=self.root/'data/models/masroof_model.json';p.parent.mkdir(parents=True)
        p.write_text(json.dumps(dict(metadata=dict(intercept_tx=0,intercept_credit=0),features={'x':[1,1,1]})),encoding='utf-8')
        self.assertIn('model_hash_mismatch',runtime_preflight(self.root)['errors'])

    def test_catalog_hash_binding_and_eligibility_envelope_cannot_be_bypassed(self):
        area=self.root/self.policy['privateDirectory'];catalog=area/'catalog.json';catalog.write_text('{}',encoding='utf-8')
        (area/'intake.json').write_text(json.dumps(dict(exposureCatalogPath=catalog.relative_to(self.root).as_posix(),exposureCatalogSha256='0'*64)),encoding='utf-8')
        with self.assertRaisesRegex(ValueError,'catalog_hash_mismatch'):load_private_intake(self.root)
        with self.assertRaisesRegex(ValueError,'eligibility'):
            intake_preflight(dict(schemaVersion='1.0.0',trainingEligible=True,evaluationEligible=False,records=[]),self.catalog,self.root)
        catalog=copy.deepcopy(self.catalog);catalog['coverageStatus']='reviewed_complete'
        self.assertIn('exposure_catalog_coverage_unreviewed',self.run_rows(self.row,catalog=catalog)['summary']['batchBlockers'])
