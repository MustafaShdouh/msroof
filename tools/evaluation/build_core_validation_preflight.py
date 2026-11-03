"""Prepare an empty private intake and partial known-exposure catalog; never score."""
import argparse
import json
from pathlib import Path

from tools.contracts.core_preflight import POLICY_PATH, INTAKE_PATH, fingerprints, load_private_intake, runtime_preflight
from training.corpus_io import ROOT, historical_path, sha256, snapshot_report_inputs, write_immutable


def known_reference_catalog():
    paths = [ROOT/'.local-backups/core_money_r5a_unmarked/after.json',
             ROOT/'data/training/sanitized_v1/transactions.json',
             historical_path('tests/fixtures/test_suite_cases.json'),
             historical_path('tests/fixtures/qa_adversarial_cases.json')]
    sources = {p.relative_to(ROOT).as_posix():sha256(p) for p in paths}
    comparison = json.loads((ROOT/'data/reports/behavior/core_money_r5a_unmarked_comparison.json').read_text(encoding='utf-8'))
    if sha256(paths[0]) != comparison['privateSnapshotSha256']['after']:
        raise ValueError('Frozen R5 reference changed')
    saved = json.loads(paths[0].read_text(encoding='utf-8'))
    texts = [r['input'].get('text') for r in saved['records']]
    texts += [r['text'] for r in json.loads(paths[1].read_text(encoding='utf-8'))]
    texts += [r['body'] for r in json.loads(paths[2].read_text(encoding='utf-8'))['testCases']]
    texts += [r['body'] for r in json.loads(paths[3].read_text(encoding='utf-8'))]
    hashes = [fingerprints(t) for t in texts if isinstance(t, str) and t.strip()]
    return dict(schemaVersion='1.0.0',coverageStatus='partial',coverageReview=None,
                referenceSources=sources,referenceTextEntries=len(hashes),
                **{k:sorted({r[k] for r in hashes}) for k in ('raw','normalized','numericProxy')},
                verifiedFamilyIds=[],
                limits=['These known exposed references are sufficient to detect some contamination, not certify independence.',
                        'Development family labels are not verified source-template families.',
                        'Other authored/context/scope corpora, source originals, prompts, web examples and generated descendants still need a complete exposure audit.',
                        'No protected reserved data is read or repurposed.'])


def build(report):
    catalog = known_reference_catalog()
    area = ROOT/'data/private/core_evaluation_v1'
    area.mkdir(parents=True, exist_ok=True)
    catalog_path = area/'known_exposure_v1.json'
    write_immutable(catalog_path,json.dumps(catalog,ensure_ascii=False,indent=2)+'\n')
    intake_path = ROOT/INTAKE_PATH
    if not intake_path.exists():
        write_immutable(intake_path,json.dumps(dict(schemaVersion='1.0.0',trainingEligible=False,evaluationEligible=False,
            exposureCatalogPath=catalog_path.relative_to(ROOT).as_posix(),exposureCatalogSha256=sha256(catalog_path),records=[]),indent=2)+'\n')
    intake = load_private_intake()
    runtime = runtime_preflight()
    files = [POLICY_PATH,'config/contracts/sms_provenance_record.json','config/contracts/transaction_behavior.json',
             'tools/contracts/core_preflight.py','tools/evaluation/build_core_validation_preflight.py',
             'training/corpus/audit.py','src/python/preprocessing.py','tools/contracts/validate_transaction_behavior.py',
             'tests/python/test_core_preflight.py','tests/typescript/test_runtime_initialization.ts',
             'src/python/engine.py','src/typescript/MasroofEngine.ts','src/typescript/LegacyTransactionModel.ts',
             'data/models/masroof_model.json',INTAKE_PATH,catalog_path.relative_to(ROOT).as_posix()]
    sources = catalog['referenceSources'] | {p:sha256(ROOT/p) for p in files}
    snapshot_report_inputs(report.stem,sources)
    result = dict(schemaVersion='1.0.0',kind='Core validation preflight, not independent evaluation or automatic admission',
        date='2026-11-02',intake=intake['summary'],runtime=runtime,
        catalog=dict(referenceTextEntries=catalog['referenceTextEntries'],distinctRawHashes=len(catalog['raw']),
                     distinctNormalizedHashes=len(catalog['normalized']),distinctNumericProxies=len(catalog['numericProxy']),coverageStatus='partial'),
        independentEvaluationEligible=False,trainingEligible=False,scoringAuthorized=False,
        reservedRead=False,predictionsExecuted=False,engineBehaviorChanged=False,
        startupCharacterization='Existing no-init fallback and invalid-init behavior are tested separately with toy controls; not new bank-SMS truth.',
        sourceSha256=sources,
        limits=['Empty intake is preparation, not acquired real-world data.', 'Reviews and private source bindings do not authenticate bank origin.',
                'Partial reference coverage and text/proxy disjointness do not prove family independence.',
                'Pinned weight validity does not prove caller initialization, model accuracy or actual mobile support.',
                'No release thresholds, final evaluation approval or runtime failure policy was granted.'])
    write_immutable(report,json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report',type=Path,default=Path('data/reports/behavior/core_validation_preflight_v1.json'))
    args = parser.parse_args()
    target = (ROOT/args.report).resolve()
    if not target.is_relative_to((ROOT/'data/reports/behavior').resolve()):raise ValueError('Public aggregate report must stay in behavior reports')
    r=build(target)
    print(json.dumps(dict(intake=r['intake'],catalog=r['catalog'],weightArtifactValid=r['runtime']['weightArtifactValid'],scoringAuthorized=False)))
