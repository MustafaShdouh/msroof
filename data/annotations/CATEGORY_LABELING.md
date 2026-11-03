# Category Annotation Guide

Policy revision1.1,2026-10-27: align `Other` with the approved transaction contract.
This corrects guidance only; existing labels, models and splits are unchanged.
The previous guide bytes are preserved in the private report-input archive.

Use this folder for category-data preparation. `category_labels.jsonl` holds manually reviewed, completed bank or wallet transactions. `merchant_candidates.jsonl` holds a separate merchant-name research collection assembled from the existing synthetic source list and public Amman/Irbid listings. Merchant-name learning can bootstrap category suggestions, but must be evaluated separately from real transaction SMS.

Regenerate merchant candidates with `py -m training.categories.candidates`. Public evidence and proposed categories are recorded in `local_merchant_sources.json`; proposals have not been human reviewed. Confidence is intentionally null until a model is fitted and evaluated. Review approvals must be saved separately from generated candidates so regeneration cannot overwrite them. Keep aliases and branches of one brand together when splitting training and evaluation. Fees, installments, cash withdrawals, and ambiguous merchants need transaction context. Public listings do not by themselves establish a redistribution or model-training license.

## Allowed categories

- `Telecom`
- `Water and Electricity`
- `Food`
- `Groceries`
- `Transportation`
- `Subscriptions`
- `Shopping`
- `Health`
- `Entertainment`
- `Education`
- `Travel`
- `Cash Withdrawals`
- `Installments`
- `Fees`
- `Other`

## Annotation record

Add one JSON object per line to `category_labels.jsonl` using this shape. The file is already created; `category_labels.example.jsonl` contains a copyable example:

```json
{"id":"cat-0001","text":"Purchase at example merchant for JOD 12.50","category":"Food","labeler":"human","reviewed":true}
```

Rules:

1. Label only a completed transaction. Do not include OTPs, promotions, declined attempts, balance alerts, or chat messages.
2. Preserve the useful transaction wording. Replace personal names, account numbers, phone numbers, and reference IDs with neutral placeholders if needed.
3. Use `Other` only for an understood expense outside the other14 categories. Unknown purpose stays null/uncertain in the SMS annotation view; do not admit it to this completed-category file as an `Other` placeholder. An unreviewed field remains unannotated, which differs from reviewed semantic uncertainty.
4. Set `reviewed` to `true` only after a human has checked the label.
5. Keep records independent of the frozen regression fixtures and synthetic training dataset.

The future trainer must reject missing fields, unreviewed records, duplicate IDs, unsupported categories, and non-transaction records. It must split evaluation by merchant/template family and report that the labels were human reviewed.

The synthetic field-level draft view is under `sms_semantics_v1/`; its legacy
claims and later assistant text reviews are weak supervision, never entries in
this human-reviewed category file or automatic training/evaluation admission.
