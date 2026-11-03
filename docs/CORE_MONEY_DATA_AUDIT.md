# R2 money/direction data audit — 2026-10-31

R2 is complete as a data inventory and review-selection step. No labels, weights,
folds, admission flags, models or runtime behavior changed. No model was loaded,
trained or used to predict; no reserved set was scored.

Reproduce with the existing isolated Python environment:

```text
.local-backups/sms_completion_encoder_v1/env/Scripts/python.exe -X utf8 -m tools.evaluation.audit_core_money_data
.local-backups/sms_completion_encoder_v1/env/Scripts/python.exe -X utf8 -m unittest tests.python.test_core_money_data_audit
```

Outputs are immutable:

- `data/reports/behavior/core_money_r2_audit.json`: input hashes, duplicate groups,
  conflicts, fold checks and record-level provenance/span inventory.
- `data/reports/behavior/core_money_r2_review_manifest.json`: review candidates,
  held records, excluded development cases and future admission requirements.

Three safeguards pass: numeric variants versus real label conflicts, exact
Unicode code-point spans, and integration checks for review/fold boundaries.
The report reproduces byte for byte. The full runtime suite was last run at R1
(279 Python tests, 11 TypeScript suites, 226 compatibility cases); it was not
repeated for this offline-only inventory.

## Results and interpretation

The unchanged 1,177-row / 129-family research view has the expected SHA256
`e169213308c680ba7e5210ad6922ec6f8dee77f0f14c11d3539f2d22697919a3`.
There are no raw duplicates and no conflicting status/context/event labels
under raw-text or existing research-normalized equality.

Research normalization produces **754 distinct inputs**, with 61 repeated-input
groups covering 484 rows. Those repetitions stay inside their existing source
families; none connects two authoring groups. Numeric replacement intentionally
makes some different amounts look identical to the classifier. Such variants
are not label corruption, and this does not establish semantic consistency of
all labels. Conflicts among paraphrases or incorrect but consistently assigned
labels remain possible.

These findings do **not** support blaming the failed experiments on contradictory
duplicate labels. They also do not show that deleting duplicate rows would
improve the model: existing group weights already total one per source family,
and deduplication can alter effective supervision. Do not change the historical
data or fit another model based on this audit alone.

The known quote control `qualified-en` still overlaps training record
`instruction-quote-non_transaction-en`. Its exposure is already bound in the
diagnostic contract; do not use it as an unseen-text success. The audit finds
no other normalized matches among the scored diagnostic cohorts. This is not
a claim of absent paraphrase/family exposure or independent evaluation.

## Amount and direction evidence

| Pool | Inventory | What the labels support |
| --- | --- | --- |
| Legacy synthetic transactions | 2,120 rows; 1,130 amount claims; 755 DEBIT, 375 CREDIT, 990 NONE claims | Generator labels, zero reviewed amount/direction spans. Do not treat them as human receipt truth. |
| Corrected synthetic BIO v2 | 83 exact AMT spans; 63 train, 16 validation, four quarantined records | Assistant policy-corrected primary entity spans; inherited fixture direction claims lack reviewed direction spans. |
| Authored SMS v1 | 74 proposed-training records; 52 positive amount and 50 incoming/outgoing direction review candidates | Assistant-weak annotations with source spans; contextual review is still needed before any task-specific admission. |
| Weak propagation proposals | 1,702 records; 321 direction proposals; zero amount targets | Guarded proposals from prior weak reviews, not new independent adjudication. |
| Authored context/scope corpora | Existing context groups and 192 scope rows | Status/context/event annotations do not create amount/direction gold. Do not parse numbers into missing labels. |
| User-attested originals | 26 source blocks; zero admitted or independently eligible in the existing provenance audit | Already exposed through project/Gemini history; authentic packet boundaries and exact generation parents remain unresolved. |
| Core-money development fixture | 52 scored cases and four pending policy cases | Exposed authored conformance; excluded from training review candidates. |

These pools overlap in ancestry. Counts must not be added to obtain a number of
independent receipts. Existing public-source examples discussed in the handoff
remain exposed diagnostics; this audit did not newly collect or authenticate
them. There is still no independent Jordan SMS amount/direction release set.

All inspected corrected BIO entities and authored evidence spans match their
exact source slices; no invalid spans were found. That checks offsets/text,
**not** whether an annotation selects the correct financial event. Zero/missing
values and nontransaction annotations are not positive amount targets. Of 74
authored rows, four have no amount/direction annotation; 70 carry weak fields,
but only 52/50 meet the specific positive-amount/resolved-direction review filters.

The existing 2,120-row split passes its source/hash/group checks and has zero
research-normalized cross-fold groups. BIO folds are hash-checked, disjoint and
exhaustive, and their quarantines remain intact. This does not erase the older
historical split leakage already documented in the provenance audit.

## Review manifest and remaining gaps

The manifest is **not an admitted training set**. All new fitting/admission and
independent-evaluation flags are false. It preserves the 17 interpretation holds,
all BIO validation/quarantine memberships, and the 52 core development exclusions.
It lists 1,177 existing status review candidates, 63 BIO train-fold review
candidates, and the authored task-specific review IDs. No row is moved or relabeled.

Before any future learning protocol:

1. Review primary amount, explicit/default currency, and owner-relative direction
   together, including evidence roles. Completion alone supplies none of these.
2. Keep originals/descendants, translations, numeric variants and connected source
   families in one assigned partition. Run the content guard and protected-identity
   checks; reject unacknowledged overlaps and conflicts. No automatic propagation.
3. Resolve the pending fee-total, FX-primary-pair, zero/signed and ingestion-dedup
   product decisions before giving those branches scored truth.
4. Keep uncertain fields, unresolved roles and unsupported annotations out of
   positive supervised targets. Null/unreviewed is not confirmed absence.
5. Preserve provenance classes: synthetic, assistant-authored, user-attested
   source and independently collected future data. Realistic wording, bank names
   and model scores cannot establish authentication or independence.

Immediate next work is **R3 amount-candidate/role isolation**, using the passing
R1 core baseline and existing EntityText/numeric contracts. Start with a complete
before snapshot and a structural extraction that preserves outputs, then add
role-specific contrasts. Pending fee/FX branches remain unscored. No new model
training is justified or authorized by this inventory.
