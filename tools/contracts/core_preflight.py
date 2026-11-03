"""Private core-evaluation intake checks; no engine imports or predictions."""
from collections import Counter
import argparse
import hashlib
import json
import math
from pathlib import Path
import re

from training.corpus.audit import canonical, number_masked
from tools.contracts.validate_transaction_behavior import finite_positive_number

ROOT = Path(__file__).resolve().parents[2]
POLICY_PATH = 'config/contracts/core_validation_preflight_v1.json'
INTAKE_PATH = 'data/private/core_evaluation_v1/intake.json'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def fingerprints(text):
    return dict(raw=sha(text.encode('utf-8')), normalized=sha(canonical(text).encode('utf-8')),
                numericProxy=sha(number_masked(text).encode('utf-8')))


def private_path(root, relative, policy):
    if not isinstance(relative, str):
        raise ValueError('private_path_missing')
    path = (root/relative).resolve()
    base = (root/policy['privateDirectory']).resolve()
    if not base.is_relative_to(root.resolve()) or not path.is_relative_to(base):
        raise ValueError('path_outside_private_intake')
    return path


def model_structure_errors(model):
    """The deployed additive-IDF feature triples and intercepts must be finite."""
    def finite(value):
        try:return type(value) in (int, float) and math.isfinite(value)
        except OverflowError:return False
    if not isinstance(model, dict):return ['model_not_an_object']
    metadata, features = model.get('metadata'), model.get('features')
    errors = []
    if not isinstance(metadata, dict) or not all(finite(metadata.get(k)) for k in ('intercept_tx', 'intercept_credit')):
        errors.append('invalid_intercepts')
    if not isinstance(features, dict) or not features:
        errors.append('missing_features')
    elif any(not isinstance(k, str) or not k or not isinstance(v, list) or len(v) != 3 or not all(finite(x) for x in v)
             for k,v in features.items()):
        errors.append('invalid_feature_triples')
    return errors


def runtime_preflight(root=ROOT):
    policy = json.loads((root/POLICY_PATH).read_text(encoding='utf-8'))
    p = root/policy['runtime']['modelPath']
    raw = p.read_bytes()
    errors = model_structure_errors(json.loads(raw))
    if sha(raw) != policy['runtime']['modelSha256']:errors.append('model_hash_mismatch')
    return dict(weightArtifactValid=not errors, errors=errors, modelSha256=sha(raw),
                initializationExecuted=False, engineBehaviorChanged=False, mobileSupportVerified=False,
                requirement=policy['runtime']['typescript'])


def reviewed(review, text_hash):
    return (isinstance(review, dict) and review.get('textSha256') == text_hash
            and all(isinstance(review.get(k), str) and review[k].strip() for k in ('reviewer', 'evidence')))


def truth_errors(labels, policy, behavior, text_hash):
    if not isinstance(labels, dict):return ['core_truth_incomplete']
    holds = []
    values = {}
    for field in policy['coreFields']:
        label = labels.get(field)
        if (not isinstance(label, dict) or label.get('state') != 'reviewed' or 'value' not in label
                or label.get('reviewerType') != 'human' or not isinstance(label.get('reviewer'), str)
                or not label['reviewer'].strip() or not isinstance(label.get('evidence'), str) or not label['evidence'].strip()
                or label.get('basis') not in ('source_text', 'owner_context', 'policy', 'not_stated')
                or label.get('textSha256') != text_hash):
            holds.append('core_truth_incomplete');continue
        values[field] = label['value']
    if holds:return sorted(set(holds))
    for field in ('transactionStatus', 'trackingDecision', 'currencyResolution', 'direction', 'transferRelationship'):
        if values[field] not in behavior['enums'][field]:holds.append('invalid_core_truth')
    if holds:return sorted(set(holds))
    amount = values['amount']
    if amount is not None and not finite_positive_number(amount):holds.append('uncontracted_or_invalid_amount')
    currency = values['currency']
    if currency is not None and (not isinstance(currency, str) or re.fullmatch('[A-Z]{3}', currency) is None):holds.append('invalid_currency')
    if values['transactionStatus'] == 'non_transaction':
        if (amount is not None or currency is not None or values['trackingDecision'] != 'exclude'
                or any(values[k] != 'not_applicable' for k in ('currencyResolution', 'direction', 'transferRelationship'))):
            holds.append('contradictory_core_truth')
    else:
        if currency is None or values['currencyResolution'] == 'not_applicable':holds.append('contradictory_core_truth')
        if values['currencyResolution'].startswith('default_') and currency != 'JOD':holds.append('contradictory_core_truth')
        relation = values['transferRelationship'];direction = values['direction']
        if relation == 'not_applicable' or ((relation == 'own_accounts') != (direction == 'not_applicable')):holds.append('contradictory_core_truth')
        decision = 'review' if values['transactionStatus'] == 'uncertain' else 'exclude' if relation == 'own_accounts' else (
            'include' if finite_positive_number(amount) and direction in ('incoming', 'outgoing') and relation in ('not_transfer', 'other_person') else 'review')
        if values['trackingDecision'] != decision:holds.append('contradictory_core_truth')
    return sorted(set(holds))


def intake_preflight(batch, catalog, root=ROOT):
    policy = json.loads((root/POLICY_PATH).read_text(encoding='utf-8'))
    behavior = json.loads((root/policy['behaviorContract']).read_text(encoding='utf-8'))
    if (not isinstance(batch, dict) or batch.get('schemaVersion') != policy['schemaVersion'] or batch.get('trainingEligible') is not False
            or batch.get('evaluationEligible') is not False or not isinstance(batch.get('records'), list)):
        raise ValueError('invalid_intake_envelope_or_eligibility')
    if not all(isinstance(r, dict) for r in batch['records']):raise ValueError('invalid_intake_record')
    if (not isinstance(catalog, dict) or catalog.get('schemaVersion') != '1.0.0'
            or not all(isinstance(catalog.get(k), list) for k in ('raw', 'normalized', 'numericProxy', 'verifiedFamilyIds'))
            or any(not isinstance(v, str) or re.fullmatch('[0-9a-f]{64}', v) is None for k in ('raw', 'normalized', 'numericProxy') for v in catalog[k])
            or any(not isinstance(v, str) or not v.strip() for v in catalog['verifiedFamilyIds'])):
        raise ValueError('invalid_exposure_catalog')
    reference = {k:set(catalog[k]) for k in ('raw', 'normalized', 'numericProxy')}
    groups = Counter(fingerprints(r['text'])['normalized'] for r in batch['records'] if isinstance(r.get('text'), str))
    ids = Counter(r.get('id') if isinstance(r.get('id'), str) else None for r in batch['records'])
    results = []
    for row in batch['records']:
        holds = []
        text = row.get('text')
        if not isinstance(row.get('id'), str) or not row['id'].strip() or ids[row['id']] != 1:holds.append('invalid_or_duplicate_id')
        if row.get('trainingEligible') is not False or row.get('evaluationEligible') is not False:holds.append('eligibility_not_false')
        if not isinstance(text, str) or not text.strip():
            results.append(dict(id=row.get('id'), holds=sorted(set(holds+['missing_text']))));continue
        hashes = fingerprints(text)
        if row.get('textSha256') != hashes['raw']:holds.append('text_hash_mismatch')
        try:
            source = private_path(root, row.get('sourcePath'), policy)
            raw = source.read_bytes();decoded = raw.decode('utf-8-sig')
            locator = row.get('sourceLocator') or {}
            if not isinstance(locator, dict):raise ValueError('invalid_source_locator')
            a,b = locator.get('startChar'),locator.get('endChar')
            if (sha(raw) != row.get('sourceSha256') or type(a) is not int or type(b) is not int
                    or not 0 <= a < b <= len(decoded) or decoded[a:b] != text):holds.append('source_binding_mismatch')
        except (ValueError, OSError, UnicodeError):holds.append('source_binding_invalid')
        if row.get('origin') not in policy['acceptedOrigins']:holds.append('generated_or_unresolved_origin')
        for key in ('originVerification', 'consentReview', 'exposureReview', 'familyIsolationReview'):
            if not reviewed(row.get(key), hashes['raw']):holds.append(key+'_missing_or_stale')
        if row.get('sanitizationReviewStatus') != 'reviewed_private_original':holds.append('privacy_review_incomplete')
        if row.get('exposure') != 'attested_unexposed':holds.append('exposed_or_unknown_history')
        if row.get('language') not in ('ar', 'en', 'mixed'):holds.append('language_unreviewed')
        family = row.get('verifiedTemplateFamilyId')
        if not isinstance(family, str) or not family.strip():holds.append('source_family_unreviewed')
        elif family in catalog['verifiedFamilyIds']:holds.append('known_family_overlap')
        for kind, value in hashes.items():
            if value in reference[kind]:holds.append('known_'+kind+'_overlap')
        if groups[hashes['normalized']] > 1:holds.append('duplicate_content_review')
        holds.extend(truth_errors(row.get('labels'), policy, behavior, hashes['raw']))
        results.append(dict(id=row.get('id'), holds=sorted(set(holds))))
    blockers = []
    if not results:blockers.append('no_records')
    if catalog.get('coverageStatus') != 'reviewed_complete':blockers.append('exposure_catalog_partial')
    elif (not isinstance(catalog.get('referenceSources'), dict) or not catalog['referenceSources']
            or not reviewed(catalog.get('coverageReview'), sha(json.dumps(catalog['referenceSources'], sort_keys=True).encode('utf-8')))):
        blockers.append('exposure_catalog_coverage_unreviewed')
    if not all(reference.values()):blockers.append('exposure_catalog_empty')
    return dict(records=results, summary=dict(records=len(results), held=sum(bool(r['holds']) for r in results),
                locallyComplete=sum(not r['holds'] for r in results), verifiedFamilies=len({r.get('verifiedTemplateFamilyId') for r in batch['records'] if isinstance(r.get('verifiedTemplateFamilyId'), str) and r['verifiedTemplateFamilyId'].strip()}),
                holdReasons=dict(sorted(Counter(h for r in results for h in r['holds']).items())), batchBlockers=blockers),
                independentEvaluationEligible=False, trainingEligible=False, scoringAuthorized=False,
                limits=['Reviews are declarations, not bank authentication.', 'Local completeness never grants data admission.',
                        'Proxy overlap is a review hold, not proof of ancestry.', 'Private originals are not certified anonymized.'])


def load_private_intake(root=ROOT):
    policy = json.loads((root/POLICY_PATH).read_text(encoding='utf-8'))
    batch = json.loads(private_path(root, INTAKE_PATH, policy).read_text(encoding='utf-8'))
    catalog_path = private_path(root, batch.get('exposureCatalogPath'), policy)
    raw = catalog_path.read_bytes()
    if sha(raw) != batch.get('exposureCatalogSha256'):raise ValueError('exposure_catalog_hash_mismatch')
    return intake_preflight(batch, json.loads(raw), root)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('intake', 'runtime'))
    args = parser.parse_args()
    result = load_private_intake() if args.mode == 'intake' else runtime_preflight()
    print(json.dumps(result['summary'] | dict(scoringAuthorized=False) if args.mode == 'intake' else result))
