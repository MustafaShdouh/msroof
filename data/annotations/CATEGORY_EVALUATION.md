# Jordanian Arabic category evaluation

The prospective business reservation is `data/training/splits/category_brand_split.json`.
The current evidence and gaps are in `data/reports/category_evaluation_readiness.json`.
Rebuild both with `py -X utf8 -m training.categories.split`.

This is a preparation contract, not an accuracy result or a newly collected SMS dataset.
The 200 sourced businesses produce 199 leakage groups: ZARA and ZARA Home share a
conservative whole-name-token prefix bucket. This bucket does not assert corporate
ownership. Other related families still need an identity audit before fitting.

The fixed allocation is 142 training businesses, 29 validation businesses and 29 test
businesses. Arabic names or aliases occur in 17, 3 and 3 businesses respectively.
Allocation used identity hashes and Arabic-name availability, never category labels.
Updates preserve assignments. A new alias joining different folds, or changed business
membership, fails rather than silently reshuffling. Review conflicts explicitly before
any training. Do not regenerate or tune the reservation in response to model scores.

## What can be measured

- Merchant-name generalization: train only on reviewed defaults in the training fold.
  Keep every Arabic/English spelling and future variant of a held-out identity in its
  assigned fold. Aggregate performance per business so multiple aliases do not inflate
  sample counts; separately report Arabic and English coverage and missing labels.
- Transaction understanding: requires independently sourced Jordanian bank/wallet SMS
  with sanitized text, source provenance, sender type, true transaction status, exact
  amount/currency, direction and human-reviewed category or an explicit context-needed
  outcome. Merchant defaults alone cannot label a transaction reliably in every case.
- Training and development must exclude held-out names from fitting, augmentation,
  vocabulary construction, feature selection and calibration. Tune on validation only;
  use the test fold once for final comparison. Any pretrained model or external corpus
  may already know these businesses; disclose that exposure instead of claiming total
  novelty. The reservation does not erase prior research exposure.

Current counts by reviewer type and split are maintained in the generated readiness
report; avoid copying mutable counts into this protocol. Category coverage is incomplete.
Fees, Installments and Cash Withdrawals need transaction context. No 15-category model
is ready and no accuracy is currently reported.

Reviewer delegation update (2026-10-24): the user now authorizes Codex to categorize
businesses directly. Assistant decisions carry explicit provenance and are separate
research labels. These do not increase the human counts in the readiness report.
They may support disclosed weak-supervision research,
but are not independent human gold and cannot establish accuracy of a model trained
or evaluated against the same assistant judgments. Human decisions retain priority.

## Admission rules for an independent SMS set

1. Establish permitted access and provenance for actual Jordanian messages; do not
   substitute authored examples, translations, digit variants or repeated merchants.
2. Remove personal identifiers while preserving amount/entity offsets consistently.
   Keep sanitized provenance records; do not publish raw personal messages.
3. Human-review the labels and retain uncertainty/context-needed cases explicitly.
4. Audit normalized duplicates, near-duplicate bank templates, source overlap and all
   merchant aliases against training and the frozen regression fixtures. Group shared
   templates/sources appropriately; brand separation alone cannot prevent SMS leakage.
5. Freeze the accepted records and hashes before training. If the current model or
   extraction rules were tuned on a message, keep it as a regression example instead.

Current fixtures and reviewed illustrative boundary scenarios have already been used
in development. They remain useful regression/diagnostic checks, not independent SMS
evidence. No independent SMS set was acquired or validated in this step. The user wants
real-world data and small ambiguity reviews, not hundreds of manually typed messages.

## Coverage audit and augmentation

Run `py -X utf8 -m training.categories.audit` for the current coverage table,
known-family checks, exact alias/preprocessing collisions and lexical held-out-name
mentions in historical SMS files. Outputs are `data/reports/category_corpus_audit.json`
and `data/reports/CATEGORY_CORPUS_AUDIT.md`. This audit never moves reserved assignments.
Verified family evidence lives in `data/sources/businesses/brand_families.json`; its
coverage is bounded, not an exhaustive ownership/franchise registry. Historical name
mentions are lexical candidates, not proof of merchant identity or a template audit.

Augmentation can be tested after splitting: start with observed Arabic/English aliases
of training businesses, then at most one feature-changing synthetic form per eligible
training business. Keep each business's total weight constant and retain provenance.
Keep validation/test unchanged and exclude unresolved identities. Remove collisions
with held-out names/aliases and duplicates under the actual model feature contract.
Variants normalized to identical input add no model evidence. Do not insert a category
word into an opaque name merely because it is the expected answer. Invented merchant
names or transliterations are not verified aliases.

For future SMS augmentation, protect negation, declined/completed/OTP cues, direction,
amount/currency and entity spans. Merchant default categories are not universal
transaction labels. Random word deletion, swapping, or unrestricted paraphrasing can
change financial meaning. Compare augmentation versus the unchanged training baseline
on unchanged validation businesses before touching the final test. Generic text
augmentation literature is a reason to test, not evidence of benefit on this corpus.

The bounded experiment is now implemented by `training/categories/train.py`.
It fits three separate flat exports: canonical names, observed aliases, then aliases
plus one synthetic spelling/spacing form per eligible business. All use the same seed,
optimization settings and fixed abstention thresholds. Each business has total weight
one per epoch regardless of name count. The trainer records generated forms with base
identity and inherited label provenance in the research JSON report; it does not create
a padded SMS dataset. Generation is capped at one extra synthetic form per business.

Candidate normalization is versioned separately as `merchant-name-category-1.0.0`:
it uses the shared financial-number helper, preserves LC-like merchant prefixes, keeps
Latin/Arabic letters, and emits binary words plus boundary character 3/4/5-grams. It
does not apply SMS routing removal or long-account-number masking to merchant names.
Python and standalone TypeScript validate/score the actual exported flat weights;
this scorer is disconnected from the active engine and browser playground.

Model selection uses human validation answers only; ties retain the unaugmented
baseline. No tuning or selection uses assistant validation labels or test inference.
The five human validation records are too few to calibrate correctness probabilities.
Softmax values are explicitly uncalibrated scores. A score below 0.6, top-two margin
below 0.15, known-feature fraction below 0.15, or a winning class with fewer than three
training businesses causes abstention. These are fixed pilot settings, not proven
confidence guarantees. Empty/unknown-feature inputs also abstain. The final test
evaluation function deliberately raises during this research phase.

Current experiment outcome: baseline retained; neither alias nor synthetic treatment
improved the human-validation selection result. Baseline answers one of five human
records correctly and abstains on four. On all 28 labeled validation businesses it
answers 12, with nine correct and three wrong; 23 labels in that group are assistant
judgments. All three Arabic-name validation businesses abstain. This does not establish
usable Arabic category generalization or a deployable model. The test set remains
unevaluated. Exact outputs, input hashes and limitations are in the research report.

Augmentation cannot supply missing category labels, independent human truth, or new
businesses by repeating existing ones. Next: expand genuinely sourced Arabic names
and underrepresented categories, plus independent evaluation evidence; preserve the
current baseline and test reservation while gathering data. A full SMS model still
needs transaction-context truth beyond merchant defaults.
