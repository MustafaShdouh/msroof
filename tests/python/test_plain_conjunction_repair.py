"""Safety repair preserves source truth, undecided observations and ownership scope."""
import json
import subprocess
import unittest
from src.python.engine import MasroofEngine
from src.python.entity_text import EntityText
from src.python.money_candidates import movement_values
from tools.contracts.validate_transaction_behavior import validate_result
from tools.contracts.validate_ownership_context import validate_response
from tools.evaluation.core_boundary_check import measure
from tools.evaluation.review_plain_conjunctions import records
from tools.node_runtime import node_executable
from training.corpus_io import ROOT


class PlainConjunctionRepairTests(unittest.TestCase):
    def test_frozen_scored_truth_and_full_three_runtime_parity(self):
        before=json.loads((ROOT/'.local-backups/core_plain_conjunction_review_v1/results.json').read_text(encoding='utf-8'))['records']
        now=measure(records())['records']
        self.assertEqual(len(now),354)
        for row,old in zip(now,before,strict=True):
            with self.subTest(id=row['recordId']):
                validate_result(row['actual'])
                if row['adjudication']=='observation_only':
                    self.assertFalse(row['expected'])
                    self.assertEqual(row['actual'],old['actual'],'Preservation check, not a correctness label')
                else:self.assertFalse(row['mismatches'])
                for key in ('legacyPython','legacyTypescript','legacyBrowser'):self.assertEqual(row[key],old[key])

    def test_ownership_confirmations_cannot_resolve_competing_event_selection(self):
        engine=MasroofEngine();requests=[];expected=[]
        base=[r for r in records() if r['adjudication']=='required_review' and r['recordId'].endswith(':0:False')]
        self.assertEqual(len(base),30)
        for row in base:
            body=engine.predict_detailed(row['input'])
            for relation in (None,'own_accounts','other_person','unknown','invalid'):
                request=dict(ownerScopeId='conjunction-development',messageId=row['recordId'],message=row['input'])
                if relation is not None:
                    request['ownershipContext']=dict(schemaVersion='1.0.0',ownerScopeId=request['ownerScopeId'],messageId=request['messageId'],text=request['message']['text'],evidence='user_confirmed',relationship='own_accounts' if relation=='invalid' else relation)
                    if relation=='invalid':request['ownershipContext']['messageId']='another-message'
                py=engine.predict_with_ownership(request)
                validate_response(py)
                self.assertEqual(py['assessment']['transactionStatus'],body['transactionStatus'])
                self.assertEqual(py['assessment']['trackingDecision'],'review')
                self.assertIsNone(py['assessment']['amount'])
                requests.append(dict(id=row['recordId']+str(relation),request=request));expected.append(py)
        self.assertEqual(len(requests),150)
        run=subprocess.run([node_executable(),str(ROOT/'tools/evaluation/probe_detailed.ts')],input=json.dumps(dict(cases=[],ownershipCases=requests)),cwd=ROOT,capture_output=True,text=True,encoding='utf-8',check=True)
        for py,other in zip(expected,json.loads(run.stdout)['ownershipRows'],strict=True):
            self.assertEqual(py,other['typescript']);self.assertEqual(py,other['browser'])

    def test_conjunction_safety_does_not_create_completion_from_examples(self):
        fixture=json.loads((ROOT/'tests/fixtures/core_plain_conjunction_review_v1.json').read_text(encoding='utf-8'))['cases']
        frames={'en':['This is an example, not a financial notification: {}','Teaching example, not a financial notification: {}'],
                'ar':['هذا مثال توضيحي وليس إشعاراً مالياً: {}','هذا نموذج تعليمي: {}']}
        rows=[]
        for language in ('en','ar'):
            source=next(r for r in fixture if r['adjudication']=='required_review' and r['language']==language and ';' not in r['input']['text'])
            for frame in frames[language]:
                for digits in ('0123456789','٠١٢٣٤٥٦٧٨٩','۰۱۲۳۴۵۶۷۸۹'):
                    for contact in (False,True):
                        text=frame.format(source['input']['text']).translate(str.maketrans('0123456789',digits))
                        rows.append(dict(cohort='authored_conjunction_scope',recordId=str(len(rows)),language=language,family='illustrative_frame',input=dict(text=text,isContact=contact,sender='Saved contact' if contact else ''),expected=dict(transactionStatus='non_transaction',trackingDecision='exclude',amount=None)))
        self.assertEqual(len(rows),24)
        for row in measure(rows)['records']:self.assertFalse(row['mismatches'])

    def test_posted_value_evidence_uses_masks_and_local_primary_roles(self):
        parse=MasroofEngine.parse_number
        for text in ('Available balance JOD 17.250.','Account *7812 was debited.','Your account was debited. Reference 17.250.','Total debited JOD 17.500.'):
            with self.subTest(text=text):self.assertFalse(movement_values(EntityText(text).text,parse))
        for text in ('Your account was charged 17.250.','خُصم ١٧٫٢٥٠ من حسابك.'):
            with self.subTest(text=text):self.assertEqual(movement_values(EntityText(text).text,parse),{17.25})
        self.assertEqual(movement_values(EntityText('Purchase USD 10 your account was charged JOD 7.090.').text,parse),{7.09})
