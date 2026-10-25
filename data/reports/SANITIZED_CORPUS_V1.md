# Sanitized corpus v1 preparation

Prepared synthetic replacement; no active-gate migration, fitting, or Git publication.

- Synthetic transaction rows: 2120; transformed regression cases: 226.
- Verified generator template expressions: 102; global groups: 102.
- Development split: 1702 train / 418 validation; every existing class is represented in both.
- Zero cross-fold source-expression, normalized-text, numeric-proxy, and slot-proxy overlaps, on both historical and sanitized views.
- Known personal phrases removed; person identifiers vary, while financial values/dates/codes/account masks are synthetic and expected fields remapped.

## Legacy-model compatibility diagnostic

Run `py training/evaluate_sanitized_corpus.py` separately; preparation does not fit a model or run inference.
Results: `data/reports/sanitized_corpus_v1_legacy_v1_evaluation.json`. Retain expected labels when the model fails.


## Remaining work

- Synthetic transformation, not newly collected messages, approved real labels, or an independent test set.
- Known person strings are removed and values regenerated; this is not a certification of complete repository anonymization.
- Legacy tracked files and prior Git history still contain old data; migration/retirement and separately approved history cleanup remain.
- Source-expression and exact/slot proxies are grouped globally; arbitrary semantic paraphrase relationships remain unproven.
- No category dataset/split change or merchant final-test inference.

Fix measured compatibility failures before adopting this as the active regression gate. Preserve the historical baseline privately; review and retire unsafe legacy copies before publication. Remote-history changes require separate authorization.
