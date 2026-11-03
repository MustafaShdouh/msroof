"""Source-bound R5a review and before/after safety contrasts; no fitting."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import subprocess

from src.python.engine import MasroofEngine
from tools.evaluation.assess_core_money_residuals import counts
from tools.evaluation.core_money import field_errors
from tools.evaluation.snapshot_core_money import legacy_result
from tools.node_runtime import node_executable
from training.corpus_io import ROOT, sha256, write_immutable
from training.evaluation.ownership import ownership_controls
from training.transactions.factorization_protocol import prepare_view

FIXTURE = ROOT / 'tests/fixtures/completion_frame_cases_v1.json'
REVIEW = ROOT / 'data/reports/behavior/core_money_r5a_priority1_review.json'
QUEUE = ROOT / 'data/reports/behavior/core_money_r5_repair_queue.json'
AREA = ROOT / '.local-backups/core_money_r5a'
REPORT = ROOT / 'data/reports/behavior/core_money_r5a_frame_repair.json'


def diagnostic_records():
    """Resolve only the already-scored exposed R5 cohort, checking every text."""
    _, _, cohorts, _ = prepare_view()
    text = {(name, r['recordId']): r['text'] for name, rows in cohorts.items() for r in rows}
    authored = ROOT / 'data/training/authored_sms_v1/messages.jsonl'
    text.update({('authored74', r['recordId']): r['text']
                 for r in map(json.loads, authored.read_text(encoding='utf-8').splitlines())})
    core = json.loads((ROOT / 'tests/fixtures/core_money_v1.json').read_text(encoding='utf-8'))
    text.update({('core52', r['id']): r['input']['text'] for r in core['cases']})
    metadata = json.loads((ROOT / 'data/reports/behavior/core_money_r5_cohort.json').read_text(encoding='utf-8'))
    records = []
    for row in metadata['records']:
        raw = text[row['cohort'], row['recordId']]
        if hashlib.sha256((raw or '').encode()).hexdigest() != row['textSha256']:
            raise ValueError('Stale diagnostic source: ' + row['recordId'])
        records.append(dict(row, input=dict(text=raw)))
    return records


def validate_review(records, review=None):
    review = review or json.loads(REVIEW.read_text(encoding='utf-8'))
    queue = json.loads(QUEUE.read_text(encoding='utf-8'))
    if review['sourceQueueSha256'] != sha256(QUEUE):
        raise ValueError('Review is not bound to the frozen queue')
    expected = {(r['cohort'], r['recordId']): r for r in queue['records'] if r['priority'] == 1}
    reviewed = {(r['cohort'], r['recordId']): r for r in review['records']}
    if len(reviewed) != len(review['records']) or set(reviewed) != set(expected):
        raise ValueError('Review must cover each priority-one entry exactly once')
    sources = {(r['cohort'], r['recordId']): r for r in records}
    for key, row in reviewed.items():
        original, source = expected[key], sources[key]
        raw = source['input']['text']
        if sha256_text(raw) != row['textSha256'] or row['textSha256'] != original['textSha256']:
            raise ValueError('Stale review source: ' + row['recordId'])
        if not row['expectedStatus'] == row['reviewedStatus'] == original['expected']['transactionStatus']:
            raise ValueError('Unexpected truth revision: ' + row['recordId'])
        evidence = row['evidence']
        if not 0 <= evidence['start'] < evidence['end'] <= len(raw):
            raise ValueError('Invalid evidence span')
        if sha256_text(raw[evidence['start']:evidence['end']]) != evidence['sha256']:
            raise ValueError('Stale evidence span')
        if (row['reviewState'] != 'assistant_reviewed_weak' or row['truthChanged'] is not False
                or row['trainingEligible'] is not False or row['independentEvaluationEligible'] is not False):
            raise ValueError('Review must retain weak, non-training status')
    return review


def sha256_text(text):
    return hashlib.sha256(text.encode()).hexdigest()


def evaluate(phase):
    records = diagnostic_records()
    review = validate_review(records)
    fixture = json.loads(FIXTURE.read_text(encoding='utf-8'))
    assert not any(fixture[k] for k in ('trainingEligible', 'independentEvaluationEligible', 'modelFittingAllowed'))
    for row in fixture['cases']:
        for script, digits in enumerate(('0123456789', '٠١٢٣٤٥٦٧٨٩', '۰۱۲۳۴۵۶۷۸۹')):
            for contact in (False, True):
                inp = dict(row['input'], text=row['input']['text'].translate(str.maketrans('0123456789', digits)),
                           sender='Saved contact' if contact else '', isContact=contact)
                records.append(dict(cohort='newFrameContrasts', recordId=f"{row['id']}:{script}:{contact}",
                                    language=row['language'], family=row['boundary'], input=inp,
                                    expected=row['expected']))
    cases = [dict(id=str(i), input=r['input']) for i, r in enumerate(records)]
    ownership = ownership_controls()
    run = subprocess.run([node_executable(), str(ROOT / 'tools/evaluation/probe_detailed.ts')],
                         input=json.dumps(dict(cases=cases, ownershipCases=ownership)), cwd=ROOT,
                         capture_output=True, text=True, encoding='utf-8', check=True)
    cross = json.loads(run.stdout)
    engine, results = MasroofEngine(), []
    for record, other in zip(records, cross['rows'], strict=True):
        actual = engine.predict_detailed(record['input'])
        assert actual == other['typescript'] == other['browser'], record['recordId']
        results.append(dict(record, actual=actual, mismatches=field_errors(actual, record['expected']),
                            legacyPython=legacy_result(engine, record['input']),
                            legacyTypescript=other['legacyTypescript'], legacyBrowser=other['legacyBrowser']))
    wrappers = []
    for row, other in zip(ownership, cross['ownershipRows'], strict=True):
        py = engine.predict_with_ownership(row['request'])
        assert py == other['typescript'] == other['browser'], row['id']
        wrappers.append(dict(id=row['id'], request=row['request'], output=py))
    state = dict(records=results, ownership=wrappers,
                 models={p.relative_to(ROOT).as_posix(): sha256(p) for p in sorted((ROOT / 'data/models').glob('*')) if p.is_file()},
                 fixtureSha256=sha256(FIXTURE), reviewSha256=sha256(REVIEW))
    AREA.mkdir(parents=True, exist_ok=True)
    if phase == 'after':
        before = json.loads((AREA / 'before.json').read_text(encoding='utf-8'))
        assert state['models'] == before['models'], 'Model artifacts changed'
        assert state['fixtureSha256'] == before['fixtureSha256'] and state['reviewSha256'] == before['reviewSha256']
        assert wrappers == before['ownership'], 'Ownership wrapper outputs changed'
        assert len(results) == len(before['records'])
        changes, regressions = [], []
        for row, old in zip(results, before['records'], strict=True):
            assert (row['cohort'], row['recordId'], row['input'], row['expected']) == (old['cohort'], old['recordId'], old['input'], old['expected'])
            for key in ('legacyPython', 'legacyTypescript', 'legacyBrowser'):
                assert row[key] == old[key], ('Legacy behavior changed', row['recordId'])
            lost_fields = set(row['mismatches']) - set(old['mismatches'])
            if lost_fields:
                regressions.append(dict(cohort=row['cohort'], recordId=row['recordId'], lostFields=sorted(lost_fields)))
            if row['actual'] != old['actual']:
                changes.append(dict(cohort=row['cohort'], recordId=row['recordId'],
                                    beforeStatus=old['actual']['transactionStatus'], afterStatus=row['actual']['transactionStatus'],
                                    beforeMismatches=old['mismatches'], afterMismatches=row['mismatches']))
        assert not regressions, regressions
        assert all(not r['mismatches'] for r in results if r['cohort'] in ('newFrameContrasts', 'core52'))
        summary = {}
        for name in sorted({r['cohort'] for r in results}):
            a = [r for r in results if r['cohort'] == name]
            b = [r for r in before['records'] if r['cohort'] == name]
            summary[name] = dict(before=counts(b), after=counts(a))
        report = dict(kind='Exposed weak development conformance, not independent accuracy',
                      cohorts=summary, changedDetailedResults=changes, expectedFieldRegressions=regressions,
                      inputEntries=len(results), reviewedPriorityOneEntries=len(review['records']),
                      newBaseCases=len(fixture['cases']), newScriptAndMetadataVariants=len(fixture['cases'])*6,
                      fullDetailedParity=True, legacyResultsUnchanged=True, ownershipRequestsUnchanged=len(wrappers),
                      modelsUnchanged=len(state['models']), training=False, reservedInferred=False,
                      newResearchModelInference=False,
                      artifacts={p.relative_to(ROOT).as_posix(): sha256(p) for p in
                                 (FIXTURE, REVIEW, Path(__file__), ROOT/'config/contracts/transaction_evidence.json',
                                  ROOT/'src/python/detailed_assessment.py', ROOT/'src/typescript/DetailedAssessment.ts',
                                  ROOT/'tools/browser/tester.html')},
                      privateSnapshots={name: sha256(AREA/(name+'.json')) for name in ('before',)},
                      limits=['Only noncash postings and explicit instructional headers repaired in this step.',
                              'Other reviewed priority-one failures remain pending; R5 exit not met.',
                              'No new learning, broad language-coverage, independent accuracy or mobile timing claim.'])
        write_immutable(REPORT, json.dumps(report, ensure_ascii=False, indent=2)+'\n')
    write_immutable(AREA/(phase+'.json'), json.dumps(state, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps(dict(phase=phase, entries=len(results), newContrastMatches=sum(not r['mismatches'] for r in results if r['cohort']=='newFrameContrasts'),
                          ownershipRequests=len(wrappers), models=len(state['models']))))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('phase', choices=('before', 'after'))
    evaluate(parser.parse_args().phase)
