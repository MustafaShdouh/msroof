"""Clause-scope contrasts for the R1 repairs in all three runtimes."""
import json
from pathlib import Path
import subprocess
import unittest
from src.python.engine import MasroofEngine
from tools.node_runtime import node_executable

ROOT=Path(__file__).resolve().parents[2]


class CoreMoneyR1Tests(unittest.TestCase):
    def test_requests_denials_unknowns_and_completed_contrasts(self):
        examples=[
            ("currency-code-request","Use code 934821 to authorize a JOD 32.500 purchase.","non_transaction"),
            ("plain-code-request","Enter your code 934821 to complete the payment.","non_transaction"),
            ("unrelated-login-code","JOD 32.500 was debited from your account. Your login OTP is 934821.","completed"),
            ("denied-debit","No funds were debited from your account.","non_transaction"),
            ("actual-debit","JOD 32.500 was debited from your account.","completed"),
            ("cashback-promotion","Use your card to earn up to JOD 12 cashback.","non_transaction"),
            ("cashback-posted","Your cashback of JOD 12 was credited to your account.","completed"),
            ("posted-plus-promotion","JOD 12 was credited to your account as cashback. Earn up to JOD 30 cashback next month.","completed"),
            ("unconfirmed","Whether funds were credited is not confirmed.","uncertain"),
            ("settled","JOD 12 was credited to your account and settlement completed.","completed"),
            ("bill-settled-ar","تم سداد فاتورة بقيمة ٢٢ دينار وخصم المبلغ من حسابك.","completed"),
            ("bill-request-ar","يرجى تسديد فاتورة بقيمة ٢٢ دينار.","non_transaction"),
            ("bill-rejected-ar","تم رفض سداد فاتورة بقيمة ٢٢ دينار ولم يتم الخصم.","non_transaction"),
            ("settled-no-pending-ar","تم خصم ٢٢ دينار من حسابك. لم يعد الطلب معلقا.","completed"),
        ]
        cases=[dict(id=id,input=dict(text=text)) for id,text,_ in examples]
        run=subprocess.run([node_executable(),str(ROOT/"tools/evaluation/probe_detailed.ts")],input=json.dumps(dict(cases=cases)),cwd=ROOT,capture_output=True,text=True,encoding="utf-8",check=True)
        cross={r["id"]:r for r in json.loads(run.stdout)["rows"]};engine=MasroofEngine()
        for id,text,status in examples:
            with self.subTest(id=id):
                actual=engine.predict_detailed(dict(text=text))
                self.assertEqual(actual["transactionStatus"],status)
                self.assertEqual(actual,cross[id]["typescript"])
                self.assertEqual(actual,cross[id]["browser"])
