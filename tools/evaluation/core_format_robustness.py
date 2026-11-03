"""Frozen-message format contrasts across Python, TypeScript and the tester."""
import argparse
from collections import Counter
import json
import subprocess

from src.python.engine import MasroofEngine
from tools.evaluation.core_money import field_errors
from tools.node_runtime import node_executable
from training.corpus_io import ROOT, sha256, snapshot_report_inputs, write_immutable

FIXTURE = ROOT/'tests/fixtures/core_format_robustness_v1.json'


def transform(text, kind):
    if not isinstance(text, str):return text
    if kind == 'identity':return text
    if kind == 'bom_prefix':return '\ufeff'+text
    if kind == 'directional_wrapper':return '\u2067'+text+'\u2069'
    if kind == 'lowercase':return text.lower()
    if kind == 'uppercase':return text.upper()
    joiners = dict(space_runs='   ', tabs='\t', nbsp='\u00a0', narrow_nbsp='\u202f',
                   crlf_wrap='\r\n', escaped_crlf_wrap='\\r\\n', rtl_word_boundaries=' \u200f')
    if kind not in joiners:raise ValueError('Unknown format transform')
    return text.replace(' ', joiners[kind])


def records():
    contract = json.loads(FIXTURE.read_text(encoding='utf-8'))
    if any(contract[k] is not False for k in ('trainingEligible','independentEvaluationEligible','modelFittingAllowed')):
        raise ValueError('Formatting checks cannot be admitted as training or independent evidence')
    path = ROOT/contract['baselineSnapshot']
    binding = json.loads((ROOT/contract['baselineBindingReport']).read_text(encoding='utf-8'))
    if sha256(path) != binding['privateSnapshotSha256']['after']:raise ValueError('Frozen source snapshot changed')
    original = json.loads(path.read_text(encoding='utf-8'))['records']
    # One canonical numeric/contact variant per existing repair case; keep all original diagnostic rows.
    base = [r for r in original if not r['cohort'].startswith(('completion_','core_unmarked_')) or r['recordId'].endswith(':0:False')]
    rows = []
    for r in base:
        for kind in contract['transforms']:
            rows.append(dict(cohort=r['cohort'],sourceId=r['recordId'],language=r['language'],transform=kind,
                input=dict(r['input'],text=transform(r['input'].get('text'),kind)),
                expected={k:v for k,v in r['expected'].items() if k in contract['expectedFields']}))
    return rows,len(base)


def measure(rows):
    engine = MasroofEngine()
    run = subprocess.run([node_executable(),str(ROOT/'tools/evaluation/probe_detailed.ts')],
        input=json.dumps(dict(cases=[dict(id=str(i),input=r['input']) for i,r in enumerate(rows)])),
        cwd=ROOT,capture_output=True,text=True,encoding='utf-8',check=True)
    other = json.loads(run.stdout)['rows']
    results = []
    for row,cross in zip(rows,other,strict=True):
        actual = engine.predict_detailed(row['input'])
        parity = actual == cross['typescript'] == cross['browser']
        results.append(dict(row,actual=actual,parity=parity,
            mismatches={name:field_errors(value,row['expected']) for name,value in
                        [('python',actual),('typescript',cross['typescript']),('browser',cross['browser'])]}))
    return results


def summarize(rows):
    return dict(entries=len(rows), allAssertedFieldsCorrect=sum(not any(r['mismatches'].values()) for r in rows),
                fullResultParityFailures=sum(not r['parity'] for r in rows),
                nonTransactionCases=sum(r['expected'].get('transactionStatus')=='non_transaction' for r in rows),
                pythonFalseIncludes=sum(r['expected'].get('transactionStatus')=='non_transaction' and r['actual']['trackingDecision']=='include' for r in rows),
                pythonFalseCompleted=sum(r['expected'].get('transactionStatus')=='non_transaction' and r['actual']['transactionStatus']=='completed' for r in rows),
                pythonFieldErrors=dict(sorted(Counter(k for r in rows for k in r['mismatches']['python']).items())))


def evaluate(phase):
    rows,base_count = records()
    results = measure(rows)
    area = ROOT/'.local-backups/core_format_robustness_v1';area.mkdir(parents=True,exist_ok=True)
    model_hashes = {p.relative_to(ROOT).as_posix():sha256(p) for p in sorted((ROOT/'data/models').iterdir()) if p.is_file()}
    state = dict(records=results,models=model_hashes,fixtureSha256=sha256(FIXTURE))
    if phase == 'after':
        before = json.loads((area/'before.json').read_text(encoding='utf-8'))
        if state['models'] != before['models'] or state['fixtureSha256'] != before['fixtureSha256']:raise ValueError('Frozen model/fixture changed')
        for now,old in zip(results,before['records'],strict=True):
            for key in ('cohort','sourceId','language','transform','input','expected'):
                if now[key] != old[key]:raise ValueError('Frozen format inputs changed')
        if any(any(r['mismatches'].values()) or not r['parity'] for r in results):raise ValueError('Remaining format mismatches; preserve the frozen baseline and repair/review before final after report')
    write_immutable(area/(phase+'.json'),json.dumps(state,ensure_ascii=False,indent=2)+'\n')
    sources = [FIXTURE,ROOT/'tools/evaluation/core_format_robustness.py',ROOT/'src/python/entity_text.py',
               ROOT/'src/typescript/EntityText.ts',ROOT/'src/python/detailed_assessment.py',
               ROOT/'src/typescript/DetailedAssessment.ts',ROOT/'tools/browser/tester.html']
    sources.append(ROOT/'training/evaluation/ownership.py')
    view_contract = ROOT/'config/contracts/source_text_view.json'
    if view_contract.exists():sources.append(view_contract)
    bindings = {p.relative_to(ROOT).as_posix():sha256(p) for p in sources} | model_hashes
    snapshot_report_inputs('core_format_robustness_'+phase+'_v1',bindings)
    report = dict(kind='Existing-message format conformance; NOT independent accuracy',baseEntries=base_count,
        phase=phase,summary=summarize(results),byTransform={k:summarize([r for r in results if r['transform']==k]) for k in sorted({r['transform'] for r in results})},
        byLanguage={k:summarize([r for r in results if r['language']==k]) for k in sorted({r['language'] for r in results})},
        failures=[dict(cohort=r['cohort'],sourceId=r['sourceId'],transform=r['transform'],parity=r['parity'],mismatches=r['mismatches'])
                  for r in results if any(r['mismatches'].values()) or not r['parity']],
        sourceSha256=bindings,privateSnapshotSha256=sha256(area/(phase+'.json')),
        training=False,reservedInferred=False,independentEvaluationEligible=False)
    if phase == 'after':report['beforeSummary']=summarize(before['records'])
    write_immutable(ROOT/'data/reports/behavior'/('core_format_robustness_'+phase+'_v1.json'),json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(dict(baseEntries=base_count,phase=phase,summary=report['summary'],byTransform=report['byTransform'])))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__);parser.add_argument('phase',choices=('before','after'))
    evaluate(parser.parse_args().phase)
