"""Reusable before/after core-boundary checks on exposed data, never fitting."""
import argparse
import json
from pathlib import Path
import re
import subprocess

from src.python.engine import MasroofEngine
from tools.evaluation.assess_core_money_residuals import counts
from tools.evaluation.core_money import field_errors
from tools.evaluation.evaluate_completion_frames import diagnostic_records, validate_review
from tools.evaluation.snapshot_core_money import legacy_result
from tools.node_runtime import node_executable
from training.corpus_io import ROOT, sha256, write_immutable
from training.evaluation.ownership import ownership_controls


def fixture_variants(path):
    obj = json.loads(path.read_text(encoding='utf-8'))
    if any(obj[k] is not False for k in ('trainingEligible', 'independentEvaluationEligible', 'modelFittingAllowed')):
        raise ValueError('Boundary fixtures must remain exposed, non-training development data')
    if len({r['id'] for r in obj['cases']}) != len(obj['cases']):
        raise ValueError('Duplicate boundary case ID')
    rows = []
    for case in obj['cases']:
        for script, digits in enumerate(('0123456789', '٠١٢٣٤٥٦٧٨٩', '۰۱۲۳۴۵۶۷۸۹')):
            for contact in (False, True):
                inp = dict(case['input'], text=case['input']['text'].translate(str.maketrans('0123456789', digits)),
                           sender='Saved contact' if contact else '', isContact=contact)
                rows.append(dict(cohort=path.stem, recordId=f"{case['id']}:{script}:{contact}",
                                 language=case['language'], family=case['boundary'], input=inp,
                                 expected=case['expected']))
    return rows


def measure(records):
    ownership = ownership_controls()
    request = dict(cases=[dict(id=str(i), input=r['input']) for i, r in enumerate(records)], ownershipCases=ownership)
    run = subprocess.run([node_executable(), str(ROOT/'tools/evaluation/probe_detailed.ts')],
                         input=json.dumps(request), cwd=ROOT, capture_output=True,
                         text=True, encoding='utf-8', check=True)
    cross = json.loads(run.stdout)
    engine, results = MasroofEngine(), []
    for record, other in zip(records, cross['rows'], strict=True):
        py = engine.predict_detailed(record['input'])
        assert py == other['typescript'] == other['browser'], record['recordId']
        results.append(dict(record, actual=py, mismatches=field_errors(py, record['expected']),
                            legacyPython=legacy_result(engine, record['input']),
                            legacyTypescript=other['legacyTypescript'], legacyBrowser=other['legacyBrowser']))
    wrappers = []
    for row, other in zip(ownership, cross['ownershipRows'], strict=True):
        py = engine.predict_with_ownership(row['request'])
        assert py == other['typescript'] == other['browser'], row['id']
        wrappers.append(dict(id=row['id'], request=row['request'], output=py))
    return dict(records=results, ownership=wrappers,
                models={p.relative_to(ROOT).as_posix(): sha256(p) for p in sorted((ROOT/'data/models').glob('*')) if p.is_file()})


def evaluate(phase, tag, fixtures):
    if not re.fullmatch('[a-z0-9_]+', tag):
        raise ValueError('Use a simple versioned report tag')
    if len({p.stem for p in fixtures}) != len(fixtures):
        raise ValueError('Fixture cohort names must be distinct')
    records = diagnostic_records()
    validate_review(records)
    for path in fixtures:
        records.extend(fixture_variants(path))
    state = measure(records)
    state['fixtures'] = {p.relative_to(ROOT).as_posix(): sha256(p) for p in fixtures}
    state['reviewSha256'] = sha256(ROOT/'data/reports/behavior/core_money_r5a_priority1_review.json')
    area = ROOT/'.local-backups'/tag
    area.mkdir(parents=True, exist_ok=True)
    report = None
    if phase == 'after':
        before = json.loads((area/'before.json').read_text(encoding='utf-8'))
        for key in ('models', 'fixtures', 'reviewSha256', 'ownership'):
            assert state[key] == before[key], key + ' changed'
        regressions, changes = [], []
        for row, old in zip(state['records'], before['records'], strict=True):
            for key in ('cohort', 'recordId', 'input', 'expected', 'legacyPython', 'legacyTypescript', 'legacyBrowser'):
                assert row[key] == old[key], (key, row['recordId'])
            lost = set(row['mismatches']) - set(old['mismatches'])
            if lost:
                regressions.append(dict(cohort=row['cohort'], recordId=row['recordId'], fields=sorted(lost)))
            if row['actual'] != old['actual']:
                changes.append(dict(cohort=row['cohort'], recordId=row['recordId'], before=old['actual'], after=row['actual'],
                                    beforeMismatches=old['mismatches'], afterMismatches=row['mismatches']))
        assert not regressions, regressions
        required = {'core52'} | {p.stem for p in fixtures}
        assert all(not r['mismatches'] for r in state['records'] if r['cohort'] in required), 'A required boundary/core case failed'
        cohorts = {}
        for name in sorted({r['cohort'] for r in state['records']}):
            a = [r for r in state['records'] if r['cohort'] == name]
            b = [r for r in before['records'] if r['cohort'] == name]
            cohorts[name] = dict(before=counts(b), after=counts(a),
                                 byLanguage={lang:dict(before=counts([r for r in b if r['language']==lang]),
                                                      after=counts([r for r in a if r['language']==lang])) for lang in sorted({r['language'] for r in a})})
        sources = [Path(__file__), ROOT/'src/python/money_syntax.py', ROOT/'src/typescript/MoneySyntax.ts',
                   ROOT/'src/python/account_movement.py', ROOT/'src/typescript/AccountMovement.ts',
                   ROOT/'src/python/direction_policy.py', ROOT/'src/typescript/DirectionPolicy.ts',
                   ROOT/'src/python/money_candidates.py', ROOT/'src/typescript/MoneyCandidates.ts',
                   ROOT/'src/python/detailed_assessment.py', ROOT/'src/typescript/DetailedAssessment.ts',
                   ROOT/'config/contracts/transaction_evidence.json', ROOT/'tools/browser/tester.html']
        report = dict(kind='Exposed weak development conformance, not independent accuracy', tag=tag,
                      cohorts=cohorts, changedDetailedResults=changes, expectedFieldRegressions=regressions,
                      inputEntries=len(state['records']), fullDetailedParity=True, legacyResultsUnchanged=True,
                      unchangedOwnershipRequests=len(state['ownership']), unchangedModelArtifacts=len(state['models']),
                      training=False, reservedInferred=False, newResearchModelInference=False,
                      artifacts={p.relative_to(ROOT).as_posix():sha256(p) for p in sources}|state['fixtures'],
                      limits=['Variant counts are not independent examples.', 'No mobile performance or release-readiness claim.'])
    write_immutable(area/(phase+'.json'), json.dumps(state, ensure_ascii=False, indent=2)+'\n')
    if report is not None:
        report['privateSnapshotSha256'] = {p:sha256(area/(p+'.json')) for p in ('before', 'after')}
        write_immutable(ROOT/'data/reports/behavior'/(tag+'_comparison.json'), json.dumps(report, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps(dict(phase=phase, entries=len(state['records']), ownershipRequests=len(state['ownership']),
                          cohorts={name:counts([r for r in state['records'] if r['cohort']==name])['allAssertedFieldsCorrect']
                                   for name in sorted({r['cohort'] for r in state['records']})})))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('phase', choices=('before', 'after'))
    parser.add_argument('--tag', required=True)
    parser.add_argument('--fixture', type=Path, action='append', required=True)
    args = parser.parse_args()
    evaluate(args.phase, args.tag, [(ROOT/p).resolve() for p in args.fixture])
