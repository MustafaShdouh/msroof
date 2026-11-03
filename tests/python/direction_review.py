"""Apply source-bound reviewed expectations without changing historical fixtures."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]


def reviewed_direction(text,expected):
    rows=json.loads((ROOT/'tests/fixtures/direction_policy_reviews_v1.json').read_text())['reviews']
    matches=[r for r in rows if r['textSha256']==hashlib.sha256(text.encode()).hexdigest()]
    if not matches:return expected
    assert len(matches)==1
    review=matches[0]
    assert expected['direction']==review['previousDirection']
    assert expected['trackingDecision']==review['trackingDecision']=='review'
    result=deepcopy(expected);result['direction']=review['reviewedDirection']
    result['reasonCodes']=sorted(set(result['reasonCodes'])|{'direction_unresolved'})
    return result
