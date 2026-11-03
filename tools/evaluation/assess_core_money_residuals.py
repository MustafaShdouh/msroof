"""Current detailed-engine diagnostics versus saved research scores; no fitting."""
from collections import Counter,defaultdict
import hashlib
import json
from pathlib import Path
import subprocess
from src.python.engine import MasroofEngine
from training.corpus_io import ROOT,sha256,write_immutable
from training.transactions.factorization_protocol import prepare_view
from tools.node_runtime import node_executable
from tools.evaluation.core_money import field_errors,FIELDS

PREFIX=ROOT/'data/reports/behavior/core_money_r5'


def counts(rows):
    outcome=Counter();fields=defaultdict(Counter)
    for row in rows:
        expected,actual=row['expected'],row['actual']
        errors=field_errors(actual,expected)
        outcome['cases']+=1;outcome['allAssertedFieldsCorrect']+=not errors
        truth=expected.get('transactionStatus')
        outcome['statusCheckedCases']+=truth is not None
        outcome['statusCorrect']+=truth==actual['transactionStatus']
        outcome['nonTransactionCases']+=truth=='non_transaction'
        outcome['falseIncludes']+=truth=='non_transaction' and actual['trackingDecision']=='include'
        outcome['falseCompleted']+=truth=='non_transaction' and actual['transactionStatus']=='completed'
        outcome['unnecessaryReview']+=truth=='non_transaction' and actual['trackingDecision']=='review'
        outcome['completedCases']+=truth=='completed'
        outcome['missedCompletion']+=truth=='completed' and actual['transactionStatus']!='completed'
        outcome['uncertainCases']+=truth=='uncertain'
        outcome['wrongCertainty']+=truth=='uncertain' and actual['transactionStatus']!='uncertain'
        eligible=(truth=='completed' and expected.get('trackingDecision')=='include' and expected.get('amount') is not None and expected.get('currency') is not None and expected.get('direction') in ('incoming','outgoing'))
        outcome['endToEndEligible']+=eligible
        outcome['endToEndCorrect']+=eligible and not errors
        for field in expected:
            fields[field]['checked']+=1;fields[field]['correct']+=field not in errors
    return dict(**dict(outcome),fields={k:dict(v) for k,v in fields.items()})


def build():
    _,_,old,_=prepare_view()
    core=json.loads((ROOT/'tests/fixtures/core_money_v1.json').read_text(encoding='utf-8'))
    authored=[json.loads(l) for l in (ROOT/'data/training/authored_sms_v1/messages.jsonl').read_text(encoding='utf-8').splitlines()]
    contract=json.loads((ROOT/'config/contracts/sms_diagnostic_evaluation_v1.json').read_text())
    saved=json.loads((ROOT/'data/reports/transactions/sms_factorization_comparison_v2.json').read_text())
    records=[]
    for name,rows in old.items():
        labels={r['recordId']:r['language'] for r in saved['evaluations'][name]['rows']}
        for r in rows:records.append(dict(cohort=name,recordId=r['recordId'],text=r['text'],language=r.get('language',labels[r['recordId']]),family=r.get('theme',r.get('group','unspecified_prior_diagnostic')),expected=dict(transactionStatus=r['target'])))
    for r in core['cases']:
        records.append(dict(cohort='core52',recordId=r['id'],text=r['input']['text'],language=r['language'],family=r['family'],expected=r['expected']))
    for r in authored:
        records.append(dict(cohort='authored74',recordId=r['recordId'],text=r['text'],language=r['language'],family=r['eventType'],expected={k:v['value'] for k,v in r['annotations'].items() if k in FIELDS and v['state']=='weak'}))
    metadata=[]
    for r in records:
        key=r['cohort']+'/'+r['recordId']
        metadata.append({k:v for k,v in r.items() if k!='text'}|dict(textSha256=hashlib.sha256((r['text'] or '').encode()).hexdigest(),
            nullInput=r['text'] is None,uncertaintyReason=contract['uncertaintyReasons'].get(key),inSampleControl=key in contract['inSampleControls']))
    write_immutable(Path(str(PREFIX)+'_cohort.json'),json.dumps(dict(records=metadata,trainingEligible=False,independentEvaluationEligible=False),ensure_ascii=False,indent=2)+'\n')
    cases=[dict(id=str(i),input=dict(text=r['text'])) for i,r in enumerate(records)]
    process=subprocess.run([node_executable(),str(ROOT/'tools/evaluation/probe_detailed.ts')],input=json.dumps(dict(cases=cases)),capture_output=True,text=True,encoding='utf-8',cwd=ROOT,check=True)
    other=json.loads(process.stdout)['rows'];engine=MasroofEngine();results=[]
    original=engine._score_tokens;calls=[]
    def scoring(tokens):
        calls.append(1);return original(tokens)
    engine._score_tokens=scoring
    for r,meta,ts in zip(records,metadata,other,strict=True):
        calls.clear();actual=engine.predict_detailed(dict(text=r['text']))
        assert actual==ts['typescript']==ts['browser'],r['recordId']
        view={k:actual[k] for k in FIELDS}
        results.append(dict(meta,actual=view,reasonCodes=actual['reasonCodes'],mismatches=field_errors(view,r['expected']),legacyScorerCalls=len(calls)))
    references={}
    for name,rows in old.items():
        previous=saved['evaluations'][name]['rows']
        assert [r['recordId'] for r in rows]==[r['recordId'] for r in previous]
        for raw,past in zip(rows,previous,strict=True):assert hashlib.sha256(raw['text'].encode()).hexdigest()==past['textSha256'] and raw['target']==past['target']
        references[name]={m:dict(correct=sum(x['outputs'][m]['status']==x['target'] for x in previous),total=len(previous),uncertaintySupported=m in ('direct_status','factorized')) for m in ('direct_status','factorized','word','word_sequences','frozen_encoder','binary_adapted')}
    summary={}
    for name in sorted({r['cohort'] for r in results}):
        rows=[r for r in results if r['cohort']==name]
        summary[name]=dict(all=counts(rows),byLanguage={lang:counts([r for r in rows if r['language']==lang]) for lang in sorted({r['language'] for r in rows})},byFamily={f:counts([r for r in rows if r['family']==f]) for f in sorted({r['family'] for r in rows})})
    reason_slices={value:counts([r for r in results if r['uncertaintyReason']==value]) for value in contract['reasonDefinitions']}
    paths=['tests/fixtures/core_money_v1.json','data/training/authored_sms_v1/messages.jsonl','data/reports/transactions/sms_factorization_comparison_v2.json','config/contracts/sms_diagnostic_evaluation_v1.json',
        'src/python/engine.py','src/python/detailed_assessment.py','src/python/direction_policy.py','src/python/money_candidates.py','src/typescript/DetailedAssessment.ts','src/typescript/DirectionPolicy.ts','src/typescript/MoneyCandidates.ts','config/contracts/transaction_evidence.json','config/contracts/authorization_request.json','data/models/masroof_model.json','tools/browser/tester.html']
    result=dict(kind='Exposed assistant-weak diagnostic agreement, not independent accuracy',records=results,cohorts=summary,uncertaintyReasons=reason_slices,savedLearnedStatusReferences=references,
        inputEntries=len(results),distinctTextInputs=len({(r['textSha256'],r['nullInput']) for r in results}),legacyFallbackCalls=sum(r['legacyScorerCalls'] for r in results),
        training=False,reservedInferred=False,newResearchModelInference=False,currentDetailedInference=True,
        attribution='Detailed completion uses structural evidence; legacy scoring is only the existing financial-candidate fallback, not the failed direct/factorized research candidates. Logged scorer use is not causal feature attribution.',
        inputs={p:sha256(ROOT/p) for p in paths}|{Path(__file__).relative_to(ROOT).as_posix():sha256(Path(__file__))},
        limits=['Cohorts overlap in ancestry and sometimes text; no pooled accuracy.','Saved research scores measure status only; no amount/direction predictions fabricated for them.','Field comparisons score only explicitly weak-reviewed expected fields; missing annotations are unscored.','Passing finite authored tests does not establish independent accuracy or release readiness.'])
    write_immutable(Path(str(PREFIX)+'_residuals.json'),json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    return result


if __name__=='__main__':
    r=build();print(json.dumps(dict(cohorts={k:{f:v['all'][f] for f in ('cases','statusCorrect','allAssertedFieldsCorrect','falseIncludes','missedCompletion','wrongCertainty')} for k,v in r['cohorts'].items()},legacyFallbackCalls=r['legacyFallbackCalls'])))
