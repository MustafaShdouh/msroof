"""Summarize frozen development outputs; never import an engine or run inference."""
from collections import Counter
import argparse
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
COMPARISON = 'data/reports/behavior/core_money_r5a_unmarked_comparison.json'
SNAPSHOT = '.local-backups/core_money_r5a_unmarked/after.json'
REPORT = 'data/reports/behavior/core_money_r6_inventory_v1.json'
CORE_FIELDS = ('transactionStatus', 'trackingDecision', 'amount', 'currency',
               'currencyResolution', 'direction', 'transferRelationship')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fraction(correct, eligible):
    return dict(correct=correct, eligible=eligible, rate=correct/eligible if eligible else None)


def positive(value):
    return isinstance(value, (float, int)) and not isinstance(value, bool) and value > 0


def exact(row, fields):
    return all(row['actual'].get(key) == row['expected'][key] for key in fields if key in row['expected'])


def summarize(rows):
    """Partial/null labels do not become supported positive extraction truth."""
    def metric(eligible, correct):
        subset = [r for r in rows if eligible(r['expected'])]
        return fraction(sum(correct(r) for r in subset), len(subset))
    def event(e):
        return (e.get('transactionStatus') == 'completed' and e.get('trackingDecision') == 'include'
                and positive(e.get('amount')) and isinstance(e.get('currency'), str)
                and e.get('direction') in ('incoming', 'outgoing'))
    fields = {}
    for field in CORE_FIELDS:
        labeled = [r for r in rows if field in r['expected']]
        nonnull = [r for r in labeled if r['expected'][field] is not None]
        fields[field] = dict(allLabeled=fraction(sum(exact(r, [field]) for r in labeled), len(labeled)),
                             nonNullTruth=fraction(sum(exact(r, [field]) for r in nonnull), len(nonnull)),
                             nullTruthCases=len(labeled)-len(nonnull))
    amount_eligible = lambda e: e.get('transactionStatus') == 'completed' and positive(e.get('amount')) and isinstance(e.get('currency'), str)
    direction_eligible = lambda e: e.get('transactionStatus') == 'completed' and e.get('direction') in ('incoming', 'outgoing')
    def accepted_only(subset, fields):
        eligible = [r for r in rows if subset(r['expected']) and r['actual']['trackingDecision'] == 'include']
        return fraction(sum(exact(r, fields) for r in eligible), len(eligible))
    unsafe = [r for r in rows if r['expected'].get('trackingDecision') in ('exclude', 'review')]
    ordinary = [r for r in rows if r['expected'].get('transactionStatus') == 'non_transaction']
    own = [r for r in rows if r['expected'].get('transferRelationship') == 'own_accounts']
    included = [r for r in rows if r['expected'].get('trackingDecision') == 'include']
    uncertain = [r for r in rows if r['expected'].get('transactionStatus') == 'uncertain']
    missing_status = sum('transactionStatus' not in r['expected'] for r in rows)
    return dict(entries=len(rows),
                allAssertedCoreFields=fraction(sum(exact(r, CORE_FIELDS) for r in rows), len(rows)),
                statusTruthMissing=missing_status, fields=fields,
                acceptedEventAssertions=metric(event, lambda r: exact(r, CORE_FIELDS)),
                fullCoreAcceptedEvents=metric(lambda e: event(e) and all(k in e for k in CORE_FIELDS)
                                             and e['transferRelationship'] in ('not_transfer', 'other_person'),
                                             lambda r: exact(r, CORE_FIELDS)),
                amountCurrencyAllKnown=metric(amount_eligible, lambda r: exact(r, ['amount', 'currency'])),
                amountCurrencyExpectedInclude=metric(lambda e: amount_eligible(e) and e.get('trackingDecision') == 'include',
                                                    lambda r: exact(r, ['amount', 'currency'])),
                amountCurrencyAcceptedOnly=accepted_only(amount_eligible, ['amount', 'currency']),
                directionAllKnown=metric(direction_eligible, lambda r: exact(r, ['direction'])),
                directionExpectedInclude=metric(lambda e: direction_eligible(e) and e.get('trackingDecision') == 'include',
                                               lambda r: exact(r, ['direction'])),
                directionAcceptedOnly=accepted_only(direction_eligible, ['direction']),
                actualIncludesWithoutAmountCurrencyTruth=sum(r['actual']['trackingDecision'] == 'include' and not amount_eligible(r['expected']) for r in rows),
                actualIncludesWithoutDirectionTruth=sum(r['actual']['trackingDecision'] == 'include' and not direction_eligible(r['expected']) for r in rows),
                falseIncludes=dict(count=sum(r['actual']['trackingDecision'] == 'include' for r in unsafe), eligible=len(unsafe)),
                ordinaryFalseIncludes=dict(count=sum(r['actual']['trackingDecision'] == 'include' for r in ordinary), eligible=len(ordinary)),
                ownAccountFalseIncludes=dict(count=sum(r['actual']['trackingDecision'] == 'include' for r in own), eligible=len(own)),
                includeMissOrReview=dict(count=sum(r['actual']['trackingDecision'] != 'include' for r in included), eligible=len(included)),
                wrongCertainty=dict(count=sum(r['actual']['transactionStatus'] != 'uncertain' for r in uncertain), eligible=len(uncertain)),
                actualTrackingDecisions=dict(sorted(Counter(r['actual']['trackingDecision'] for r in rows).items())),
                labeledRelationships=dict(sorted(Counter(r['expected']['transferRelationship'] for r in rows if 'transferRelationship' in r['expected']).items())),
                fieldMasks=dict(sorted(Counter(','.join(k for k in CORE_FIELDS if k in r['expected']) for r in rows).items())))


def digit_script(row):
    text = row['input'].get('text') or ''
    scripts = [label for label, pattern in [('ascii', '[0-9]'), ('arabic_indic', '[٠-٩]'),
                                           ('eastern_arabic', '[۰-۹]')] if re.search(pattern, text)]
    return scripts[0] if len(scripts) == 1 else 'mixed_digits' if scripts else 'no_digits'


def separators(row):
    text = row['input'].get('text') or ''
    found = [label for label, char in [('dot', '.'), ('comma', ','), ('arabic_decimal', '٫'),
                                      ('arabic_grouping', '٬'), ('apostrophe', "'"), ('curly_apostrophe', '’')]
             if re.search(r'\d' + re.escape(char) + r'\d', text)]
    return '+'.join(found) if found else 'no_digit_separator'


def slices(rows, key):
    groups = {}
    for row in rows:
        groups.setdefault(key(row), []).append(row)
    return {name:summarize(group) for name,group in sorted(groups.items())}


def load_checked(root, relative, expected):
    path = (root/relative).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError('Evidence path escapes the repository')
    if digest(path) != expected:
        raise ValueError('Changed evidence: ' + relative)
    return path


def build(root=ROOT):
    comparison = json.loads((root/COMPARISON).read_text(encoding='utf-8'))
    load_checked(root, SNAPSHOT, comparison['privateSnapshotSha256']['after'])
    for relative, sha in comparison['artifacts'].items():
        load_checked(root, relative, sha)
    snapshot = json.loads((root/SNAPSHOT).read_text(encoding='utf-8'))
    for relative, sha in snapshot['models'].items():
        load_checked(root, relative, sha)
    rows = snapshot['records']
    if (len(rows) != comparison['inputEntries'] or comparison['expectedFieldRegressions']
            or not comparison['fullDetailedParity'] or not comparison['legacyResultsUnchanged']):
        raise ValueError('The inventory requires the verified unchanged/parity snapshot')
    if any(r['mismatches'] or not exact(r, CORE_FIELDS) for r in rows):
        raise ValueError('A saved mismatch needs review before the readiness inventory')
    # Decode only the manifest object; the rest of the HTML/JavaScript is never executed.
    html = (root/'tools/browser/tester.html').read_text(encoding='utf-8')
    markers = list(re.finditer(r'serviceNotice: __modules\[[0-9]+\], sourceSha256: ', html))
    if len(markers) != 1:
        raise ValueError('Expected one browser source manifest')
    graph, _ = json.JSONDecoder().raw_decode(html[markers[0].end():])
    for relative, sha in graph.items():
        load_checked(root, relative, sha)
    contract = json.loads((root/'config/contracts/transaction_behavior.json').read_text(encoding='utf-8'))
    comparison_inputs = {COMPARISON:digest(root/COMPARISON), SNAPSHOT:digest(root/SNAPSHOT)}
    references = ['config/contracts/transaction_behavior.json', 'docs/CORE_MONEY_DATA_AUDIT.md',
                  'docs/CORE_MONEY_UNMARKED_AMOUNTS.md', 'tools/browser/build_tester_ui.py',
                  'tools/browser/sms_research.py', 'tools/browser/merchant_lab.py',
                  'src/python/engine.py', 'tools/browser/bundle_engine.mjs',
                  'tools/evaluation/core_readiness_inventory.py']
    cohorts = {}
    for name in sorted({r['cohort'] for r in rows}):
        group = [r for r in rows if r['cohort'] == name]
        cohorts[name] = dict(summary=summarize(group), byLanguage=slices(group, lambda r:r['language']),
                             byDeclaredFamily=slices(group, lambda r:r['family']),
                             byInputDigitScript=slices(group, digit_script),
                             byInputSeparator=slices(group, separators))
    legacy_disagreements = {}
    for name in cohorts:
        group = [r for r in rows if r['cohort'] == name]
        legacy_disagreements[name] = {}
        for runtime,key in [('python','legacyPython'), ('typescript','legacyTypescript'), ('browser','legacyBrowser')]:
            comparable = [r for r in group if isinstance(r[key], dict) and isinstance(r[key].get('isValidTransaction'), bool)]
            legacy_disagreements[name][runtime] = dict(
                count=sum(r[key]['isValidTransaction'] != (r['actual']['trackingDecision'] == 'include') for r in comparable),
                comparable=len(comparable), uncomparable=len(group)-len(comparable))
    return dict(schemaVersion='1.0.0', kind='Frozen exposed development readiness inventory; not independent accuracy',
                inferenceExecuted=False, trainingExecuted=False, reservedInferred=False,
                independentEvaluationEligible=False, inputEntries=len(rows),
                distinctRawTextsIncludingNull=len({r['input'].get('text') for r in rows}),
                distinctNonNullTexts=len({r['input'].get('text') for r in rows if r['input'].get('text') is not None}),
                nullInputEntries=sum(r['input'].get('text') is None for r in rows),
                independentEligibleCases=0, pooledAccuracy=None, cohorts=cohorts,
                ownershipWrapperRequests=len(snapshot['ownership']),
                ownershipWrapperEvidence='Historical unchanged/parity checks and binding tests; no new human ownership truth inferred here.',
                legacyVsDetailedRecordingDisagreements=legacy_disagreements,
                legacyComparisonLimit='API recording disagreement only, not a new accuracy claim or proof that legacy can be deleted.',
                runtime=dict(browserGraphFiles=len(graph), browserGraphSourceBytes=sum((root/p).stat().st_size for p in graph),
                             graphArtifacts={p:dict(sha256=sha,bytes=(root/p).stat().st_size) for p,sha in graph.items()},
                             legacyWeightsBytes=(root/'data/models/masroof_model.json').stat().st_size,
                             standaloneTesterBytes=(root/'tools/browser/tester.html').stat().st_size,
                             researchImportsInCoreGraph=[p for p in graph if '/research/' in p],
                             mobileRuntimeMeasured=False, mobilePackageBytes=None, latencyMs=None,
                             limitation='Source/JSON/HTML disk bytes only; not compressed app size, loaded memory or Hermes performance.'),
                release=dict(independentEvidenceAvailable=contract['evaluation']['independentFinalEvaluationAvailable'],
                             thresholds=contract['evaluation']['releaseThresholds'], finalTestRequires=contract['evaluation']['finalTestRequires'],
                             decision='Not ready for independent accuracy or release claims'),
                sourceSha256=comparison_inputs | comparison['artifacts'] | snapshot['models']
                             | {p:digest(root/p) for p in references},
                limits=['Never pool these overlapping/augmented cohorts into independent accuracy.',
                        'Zero eligible labels gives a null rate; null amount truths are not positive extraction tests.',
                        'Full-core accepted-event truth requires all seven core fields; partial assertions are separate.',
                        'Digit/separator profiles describe the whole input, including dates/IDs, not the gold amount alone.',
                        'Declared family is development metadata, not proof of independent source/template coverage.',
                        'Variants retain the same base scenario; uncertainty intervals assuming independent samples are not justified.',
                        'Private snapshot text is read only; this report emits aggregate metrics without SMS text.'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='Reproduce the existing immutable report without rewriting it')
    args = parser.parse_args()
    payload = json.dumps(build(), ensure_ascii=False, indent=2) + '\n'
    target = ROOT/REPORT
    if args.check:
        if target.read_text(encoding='utf-8') != payload:
            raise ValueError('Readiness inventory did not reproduce')
    else:
        if target.exists():
            raise FileExistsError('Use --check; existing readiness reports are immutable')
        target.write_text(payload, encoding='utf-8')
    print(json.dumps(dict(report=REPORT, mode='check' if args.check else 'created', inferenceExecuted=False)))


if __name__ == '__main__':
    main()
