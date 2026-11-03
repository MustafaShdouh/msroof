"""Review ordinary conjunctions without treating unlabelled ambiguity as correctness."""
from collections import Counter
import json

from tools.evaluation.core_boundary_check import measure
from training.corpus_io import ROOT,sha256,snapshot_report_inputs,write_immutable

FIXTURE=ROOT/'tests/fixtures/core_plain_conjunction_review_v1.json'
TAG='core_plain_conjunction_review_v1'


def load_cases():
    obj=json.loads(FIXTURE.read_text(encoding='utf-8'))
    for flag in ('trainingEligible','independentEvaluationEligible','modelFittingAllowed'):
        if obj[flag] is not False:raise ValueError('Review data must remain exposed and ineligible')
    for key in ('sourceSnapshot','priorFixture','pairedFixture'):
        if sha256(ROOT/obj[key])!=obj[key+'Sha256']:raise ValueError('Frozen source changed: '+key)
    idx={(r['cohort'],r['recordId']):r for r in json.loads((ROOT/obj['sourceSnapshot']).read_text(encoding='utf-8'))['records']}
    prior={r['id']:r for r in json.loads((ROOT/obj['priorFixture']).read_text(encoding='utf-8'))['cases']}
    paired={r['id']:r for r in json.loads((ROOT/obj['pairedFixture']).read_text(encoding='utf-8'))['cases']}
    if len({r['id'] for r in obj['cases']})!=len(obj['cases']):raise ValueError('Duplicate review ID')
    for row in obj['cases']:
        if row['boundary']=='unadorned_conjunction':
            a,b=[idx[(r['cohort'],r['recordId'])] for r in row['sources']]
            if row['input']['text']!=a['input']['text'].rstrip('.')+row['joiner']+b['input']['text']:raise ValueError('Source composition changed')
            ambiguous=a['expected'].get('amount')==b['expected'].get('amount') and a['expected'].get('direction')==b['expected'].get('direction')
            if ambiguous:
                if row['adjudication']!='observation_only' or 'expected' in row:raise ValueError('Unadjudicated restatement must remain unscored')
            elif row['adjudication']!='required_review' or row.get('expected')!=dict(trackingDecision='review',amount=None):raise ValueError('Conflicting-amount review contract changed')
        elif row['adjudication']=='inherited_control':
            if 'priorCaseId' in row:old=prior[row['priorCaseId']];expected=old['expected'];inp=old['input']
            elif 'pairedCaseId' in row:
                old=paired[row['pairedCaseId']]
                if not old['recognized']:raise ValueError('Only frozen recognized controls admitted here')
                expected=dict(transactionStatus='completed',trackingDecision='review',direction='uncertain',transferRelationship='unknown',amount=7.333,currency='JOD',currencyResolution='explicit');expected.update(old['expect']);inp=dict(text=old['text'])
            else:
                ref=row['sources'][0];old=idx[(ref['cohort'],ref['recordId'])];expected=old['expected'];inp=old['input']
            if row['input']!=inp or row['expected']!=expected:raise ValueError('Existing control truth changed')
        else:raise ValueError('Unknown adjudication')
    return obj['cases']


def records():
    rows=[]
    for case in load_cases():
        for script,digits in enumerate(('0123456789','٠١٢٣٤٥٦٧٨٩','۰۱۲۳۴۵۶۷۸۹')):
            for contact in (False,True):
                inp=dict(case['input'],text=case['input']['text'].translate(str.maketrans('0123456789',digits)),sender='Saved contact' if contact else '',isContact=contact)
                rows.append(dict(cohort=TAG,recordId=case['id']+':'+str(script)+':'+str(contact),language=case['language'],family=case['boundary'],adjudication=case['adjudication'],input=inp,expected=case.get('expected',{})))
    return rows


def summarize(rows):
    groups={}
    for kind in ('required_review','inherited_control','observation_only'):
        subset=[r for r in rows if r['adjudication']==kind]
        if kind=='observation_only':
            if any(r['expected'] for r in subset):raise ValueError('Observation-only rows must have no correctness labels')
            groups[kind]=dict(entries=len(subset),scored=False,observedDecisions=dict(sorted(Counter(r['actual']['trackingDecision'] for r in subset).items())))
        else:
            if any(not r['expected'] for r in subset):raise ValueError('Scored rows need explicit contract truth')
            groups[kind]=dict(entries=len(subset),scored=True,allAssertedFieldsCorrect=sum(not r['mismatches'] for r in subset),observedDecisions=dict(sorted(Counter(r['actual']['trackingDecision'] for r in subset).items())),fieldErrors=dict(sorted(Counter(k for r in subset for k in r['mismatches']).items())))
    return dict(entries=len(rows),scoredEntries=sum(v['entries'] for v in groups.values() if v['scored']),unscoredEntries=groups['observation_only']['entries'],groups=groups)


def evaluate():
    state=measure(records());summary=summarize(state['records'])
    state['fixtureSha256']=sha256(FIXTURE)
    area=ROOT/'.local-backups'/TAG;area.mkdir(parents=True,exist_ok=True)
    write_immutable(area/'results.json',json.dumps(state,ensure_ascii=False,indent=2)+'\n')
    sources=[FIXTURE,ROOT/'tools/evaluation/review_plain_conjunctions.py',ROOT/'tools/evaluation/core_boundary_check.py',ROOT/'config/contracts/transaction_evidence.json',ROOT/'tools/browser/tester.html']
    sources.extend(sorted((ROOT/'src/python').glob('*.py')));sources.extend(sorted((ROOT/'src/typescript').glob('*.ts')))
    bindings={p.relative_to(ROOT).as_posix():sha256(p) for p in sources}|state['models']
    snapshot_report_inputs(TAG,bindings)
    report=dict(kind='Exposed ordinary-conjunction review, NOT independent accuracy',summary=summary,fullDetailedParity=True,ownershipRequests=len(state['ownership']),modelArtifacts=len(state['models']),sourceSha256=bindings,privateSnapshotSha256=sha256(area/'results.json'),failures=[dict(id=r['recordId'],adjudication=r['adjudication'],mismatches=r['mismatches']) for r in state['records'] if r['adjudication']!='observation_only' and r['mismatches']],runtimeEdited=False,training=False,reservedInferred=False,independentEvaluationEligible=False,limits=['Unadjudicated equal-amount/same-flow restatements are observations, never correct/incorrect counts.','Related authored compositions and digit/contact variants are not independent SMS.','Source currency defaults do not prove distinct units inside a composed message.'])
    write_immutable(ROOT/'data/reports/behavior'/(TAG+'.json'),json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(summary))


if __name__=='__main__':evaluate()
