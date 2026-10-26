# Behavior evaluation

Development behavior/conformance diagnostics only; no independent benchmark accuracy

| Runtime | Include/exclude projection | Ordinary false inclusions | Eligible misses/reviews | P2P included |
| --- | --- | --- | --- | --- |
| python | 22/31 | 1/9 | 3/15 | 3/4 |
| typescript | 22/31 | 1/9 | 3/15 | 3/4 |
| browser | 22/31 | 1/9 | 3/15 | 3/4 |

The legacy boolean projection cannot emit review. Completion status, ownership, currency-resolution markers and category-status fields are unsupported; they are not guessed from rejection reasons.

Legacy category labels are not silently mapped onto the target 15-category taxonomy. Human category snapshots are component probes for the exact reviewed scenarios only, not new transaction labels.

## Complete result parity

- typescriptVsPython: 288/288 identical canonical outputs.
- browserVsPython: 288/288 identical canonical outputs.

Python duplicate aliases are validated then removed; every other field, including reasons, confidence, categories and FX values, is compared. Existing frozen compatibility gates are reported separately from stricter decimal/whole-value checks in the JSON.

Exact character spans and independent source/template-family slices are unmeasurable with current truth. Rates on authored/regression data do not establish deployment accuracy; sampling intervals are not claimed for correlated examples.

No fitting, promotion, reserved merchant-test inference or final release evaluation occurred.
