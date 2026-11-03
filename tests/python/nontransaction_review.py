"""Explicit source-bound live revisions; original controls and before results stay intact."""
from copy import deepcopy
import hashlib
import json
from unittest.mock import patch

from training.corpus_io import ROOT, sha256
from training.evaluation import paired
from training.evaluation.ownership import baseline_assessor


def reviewed_nontransaction(text, expected):
    review = json.loads((ROOT/'tests/fixtures/nontransaction_context_reviews_v1.json').read_text(encoding='utf-8'))
    matches = [r for r in review['reviews'] if r['textSha256']==hashlib.sha256(text.encode()).hexdigest()]
    if not matches:
        return expected
    if len(matches)!=1 or sha256(ROOT/review['sourceFixture'])!=review['sourceFixtureSha256']:
        raise ValueError('Nontransaction review source changed')
    row = matches[0]
    if expected!=row['previous'] or review['trainingEligible'] is not False or review['independentEvaluationEligible'] is not False:
        raise ValueError('Nontransaction review baseline changed')
    if row['current']['transactionStatus']!='non_transaction' or row['current']['trackingDecision']!='exclude':
        raise ValueError('Reviewed question/request must explicitly exclude')
    return deepcopy(row['current'])


def evaluate_pairs_with_review():
    review = json.loads((ROOT/'tests/fixtures/nontransaction_paired_review_v1.json').read_text(encoding='utf-8'))
    if sha256(ROOT/review['sourceFixture']) != review['sourceFixtureSha256']:
        raise ValueError('Paired review source fixture changed')
    load = paired.load
    row = next(r for r in load(review['sourceFixture'])['cases'] if r['id']==review['caseId'])
    if (row['recognized'] or row['expect'] or hashlib.sha256(row['text'].encode()).hexdigest()!=review['textSha256']
            or review['trainingEligible'] is not False or review['independentEvaluationEligible'] is not False):
        raise ValueError('Paired review no longer matches its original negative control')
    expected = dict(review['previous'], **review['changes'])
    if expected != review['current'] or expected['transactionStatus']!='non_transaction' or expected['trackingDecision']!='exclude':
        raise ValueError('Paired chat review must explicitly exclude without completion')
    old = baseline_assessor()
    engine = old.baseline_engine
    for digits in ('0123456789', '٠١٢٣٤٥٦٧٨٩', '۰۱۲۳۴۵۶۷۸۹'):
        text = row['text'].translate(str.maketrans('0123456789', digits))
        before = old(dict(text=text), lambda b,d:engine.extract_entities(b,d,categorize=False),
                     engine.parse_number, lambda t:engine._score_tokens(engine.tokenize(engine.preprocess(t)))[0]>=.70, None)
        if before != review['previous']:
            raise ValueError('Frozen paired before result changed')

    def reviewed_load(path):
        data = load(path)
        if path == paired.ARABIC_CONTROLS:
            data = deepcopy(data)
            if review['caseId'] in data['pairedControlRevisions']:
                raise ValueError('Paired review would overwrite an existing revision')
            data['pairedControlRevisions'][review['caseId']] = review['changes']
        return data

    # The original evaluator still checks every field, runtime and confirmation.
    # Only its existing explicit-revision layer gains this reviewed source case.
    with patch('training.evaluation.paired.load', side_effect=reviewed_load):
        return paired.evaluate_pairs()
