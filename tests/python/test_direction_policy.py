"""Perspective and ownership contrasts around the extracted policy boundary."""
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import unittest
from src.python.engine import MasroofEngine
from src.python.direction_policy import recording_decision
from tools.node_runtime import node_executable

ROOT=Path(__file__).resolve().parents[2]


def probe(cases=(),ownership=()):
    result=subprocess.run([node_executable(),str(ROOT/'tools/evaluation/probe_detailed.ts')],
        input=json.dumps(dict(cases=list(cases),ownershipCases=list(ownership))),capture_output=True,text=True,encoding='utf-8',cwd=ROOT,check=True)
    return json.loads(result.stdout)


class DirectionPolicyTests(unittest.TestCase):
    def test_owner_perspective_and_relationship_traps_in_three_runtimes(self):
        examples=[
            ('external-out','Transfer of JOD 20 from your account to another person completed.','outgoing','other_person','include'),
            ('external-in','Transfer of JOD 20 from another person to your account completed.','incoming','other_person','include'),
            ('ar-out','تم تحويل ٢٠ دينار من حسابك إلى شخص آخر بنجاح.','outgoing','other_person','include'),
            ('ar-in','تم تحويل ٢٠ دينار من شخص آخر إلى حسابك بنجاح.','incoming','other_person','include'),
            ('named-out','JOD 20 was debited. Transfer to SAMER completed.','outgoing','unknown','review'),
            ('named-in','JOD 20 was credited. Transfer from SAMER completed.','incoming','unknown','review'),
            ('own','Transfer of JOD 20 between your own accounts completed.','not_applicable','own_accounts','exclude'),
            ('two-masks','Transfer of JOD 20 from account *1234 to account *5678 completed.','uncertain','unknown','review'),
            ('owned-source','Transfer of JOD 20 from your account *1234 to account *5678 completed.','outgoing','unknown','review'),
            ('explicit-own-endpoints','Transfer of JOD 20 from your account *1234 to your account *5678 completed.','not_applicable','own_accounts','exclude'),
            ('cash-out','JOD 20 was debited from your account for a cash withdrawal.','outgoing','not_transfer','include'),
            ('cash-in','A cash deposit of JOD 20 was credited to your account.','incoming','not_transfer','include'),
            ('refund','A refund of JOD 20 was credited to your account.','incoming','not_transfer','include'),
            ('pending','Transfer of JOD 20 requested; no money has moved.','not_applicable','not_applicable','exclude'),
            ('declined','Transfer of JOD 20 declined; no funds were debited.','not_applicable','not_applicable','exclude'),
        ]
        cases=[dict(id=id,input=dict(text=text)) for id,text,*_ in examples]
        output=probe(cases)['rows'];engine=MasroofEngine()
        for (id,text,direction,relation,decision),other in zip(examples,output,strict=True):
            with self.subTest(id=id):
                result=engine.predict_detailed(dict(text=text))
                self.assertEqual(result,other['typescript']);self.assertEqual(result,other['browser'])
                self.assertEqual((result['direction'],result['transferRelationship'],result['trackingDecision']),(direction,relation,decision))

    def test_confirmation_remains_bound_and_cannot_supply_missing_amount(self):
        text='Your account was debited. Transfer to SAMER completed.'
        base=dict(ownerScopeId='owner',messageId='one',message=dict(text=text),ownershipContext=dict(schemaVersion='1.0.0',ownerScopeId='owner',messageId='one',text=text,evidence='user_confirmed',relationship='other_person'))
        rows=[dict(id='missing-amount',request=base)]
        for field,value in (('ownerScopeId','different-owner'),('messageId','two')):
            request=deepcopy(base);request[field]=value;rows.append(dict(id=field,request=request))
        request=deepcopy(base);request['message']['text']+=' JOD 20.';rows.append(dict(id='changed-text',request=request))
        request=deepcopy(base);request.pop('ownershipContext');rows.append(dict(id='revoked',request=request))
        output=probe(ownership=rows)['ownershipRows'];engine=MasroofEngine()
        for row,other in zip(rows,output,strict=True):
            result=engine.predict_with_ownership(row['request'])
            self.assertEqual(result,other['typescript']);self.assertEqual(result,other['browser'])
            self.assertEqual(result['assessment']['trackingDecision'],'review')
            if row['id']=='missing-amount':
                self.assertIsNone(result['assessment']['amount'])
                self.assertEqual(result['contextStatus'],'applied')
            elif row['id']=='revoked':self.assertEqual(result['contextStatus'],'absent')
            else:self.assertEqual(result['contextStatus'],'invalid')

    def test_recording_requires_completion_and_does_not_invent_fields(self):
        self.assertEqual(recording_decision('uncertain',20,'outgoing','other_person'),'review')
        self.assertEqual(recording_decision('completed',None,'incoming','other_person'),'review')
        self.assertEqual(recording_decision('completed',20,'uncertain','other_person'),'review')
        self.assertEqual(recording_decision('completed',20,'incoming','unknown'),'review')
        self.assertEqual(recording_decision('completed',None,'not_applicable','own_accounts'),'exclude')
