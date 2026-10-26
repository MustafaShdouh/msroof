"""Deployed additive-IDF scoring; preserve legacy feature order and arithmetic."""


def _sigmoid(value):
    try:
        return 1.0 / (1.0 + pow(2.718281828459045, -value))
    except OverflowError:
        # JavaScript Math.exp returns Infinity here, producing a score of zero.
        return 0.0


def score_legacy_transaction_model(features, tokens, intercept_tx, intercept_credit):
    transaction, incoming = intercept_tx, intercept_credit
    for token in tokens:
        if token in features:
            idf, weight_tx, weight_type = features[token]
            transaction += weight_tx * idf
            incoming += weight_type * idf
    return _sigmoid(transaction), _sigmoid(incoming)
