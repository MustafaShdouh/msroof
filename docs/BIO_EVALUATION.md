# Entity-label repair and research evaluation

Updated 2026-10-26. The active extractor remains unchanged. This work repairs a
versioned development derivative, measures the existing word-based learner and
runs one owner-approved context/shape experiment. It does not establish
real-world accuracy or authorize model promotion.

## Data and labels

`config/contracts/bio_annotations.json` defines primary fields (amount, currency,
merchant/counterparty name, account identifier and balance), rather than every
entity mention in a receipt. Character coordinates are zero-based Unicode code
points with exclusive ends. Raw source names retain their descriptors,
diacritics, internal spacing, case and digit script. Introductory account wording
such as “ending in” is outside the identifier span.

`data/annotations/entities/bio_v2_review.json` records assistant corrections and
absence reviews against hashed frozen sources. The new derivative preserves all
83 source texts and IDs. Eleven spans change: ten account spans lose introductory
wording; one merchant expands from COZMO to its full adjacent source descriptor.
Currency symbols such as $/€ are aliases, not annotation defects. Original BIO
data and the frozen 226 regression cases remain intact. These labels are
assistant-reviewed synthetic development evidence, not human gold.

Tokenization runs independently of labels on a normalized matching view. Every
token projects back to its exact raw source text and code-point interval. Partial
token spans and overlaps fail validation. The model receives raw tokens; its
existing word normalization is separately shared by the Python/TypeScript
research probe. Whole-message preprocessing is not silently substituted.

## Split and reservation

Frozen derivative: `data/training/sanitized_v2/bio_training_data.json`.
Split: `data/training/splits/bio_sanitized_v2.json`.
Audit: `data/reports/bio/bio_annotation_v2.json`.

There are 63 training, 16 validation and four quarantined records. Connected
groups keep normalized slot/numeric template proxies, normalized parties, known
business aliases and known corporate families together. Seven such groups,
covering 27 records, crossed the old coarse folds. These proxies are bounded and
are not verified semantic template families or proof of independence. Broad
source topics are reported in a sensitivity audit; they do not equate every
purchase with one template. Split selection targets 20% by whole groups before
fitting; there was no score-based search or fold revision.

Two records are quarantined for unresolved actor roles: a named cash-in agent and
a phone-only transfer party. Two more touch protected merchant-category
validation/test identities. Their text/alias metadata are inspected only for data
preparation; the new tagger is neither fitted nor scored on these four records.
The reserved standalone category final test remains uninferred. This does not
erase legacy exposure through earlier development fixtures.

## Measured results

Research run `labels_v2_word_v1`, report
`data/reports/bio/labels_v2_word_v1_evaluation.json`, candidate
`data/models/bio_labels_v2_word_v1_candidate.json`:

Approved context run: `labels_v2_context_v1`, report
`data/reports/bio/context_labels_v2_context_v1_evaluation.json`, candidate
`data/models/bio_context_labels_v2_context_v1_candidate.json`.

| Measure | Word tagger | Context/shape tagger | Current regex |
| --- | ---: | ---: | ---: |
| All five primary fields correct, including absence | 0/16 | 13/16 | 16/16 |
| Exact BIO sequence | 0/16 | 13/16 | API returns values only |
| Token agreement | 329/397 (82.87%) | 388/397 (97.73%) | Not exposed |
| Arabic-script-present: all primary fields correct | 0/8 | 7/8 | Included in 16/16 |
| Invalid IOB2 transitions | 2 | 0 | Not exposed |

The word tagger has two invalid IOB2 transitions. Exact character-span F1 is 46.15%
for amounts, 69.77% currency, 47.62% names, 0% accounts and 0% balances. Orphan I
tags start physical spans for scoring and are separately counted as invalid;
they are not silently treated as valid IOB2. Multiple predicted primary fields
remain unresolved even if their values are equal. Value agreement and interval
agreement are distinct metrics. Zero denominators are null, not perfect scores.

Both trials have matching Python and TypeScript predictions on all16 validation
messages using float32 weight storage and float32 accumulation. Context feature
vectors match as well. Tests also exercise rounded-score ties, Arabic
word normalization, both Arabic digit scripts, prototype-like tokens and bad
exports. This is parity for provided tokens and model predictions; it does not
claim end-to-end TypeScript SMS tokenization/source-span parity.

The baseline's 16/16 result is development compatibility evidence: these records
come from exposed regression data. Both Arabic and other-script subsets have
eight records; script presence is not independently reviewed language truth.
There is no sampling interval or independent-accuracy claim. Older BIO 4% exact
sequence results use different labels/folds and cannot be compared as a direct
before/after percentage.

The word-only design memorizes numeric strings. In its old validation fold all
25 amount tokens and 24 balance tokens were unseen in training. This is an
observed coverage issue, not proof that a particular proposed replacement will
succeed. The trial stays a research artifact; no active model weights change.

The context model has exact span F1 of96.77% for amounts,100% currency,92.86%
names,100% accounts and100% balances. It recovers15/16 amount spans,16/16
currency spans,13/14 name spans,13/13 account spans and14/14 balance spans.
Field agreement includes correct absence; thus a16/16 account-field count is
not16 positive account spans. The predeclared research criterion is met: more
complete primary fields and better amount/balance recall than the word baseline.
It does not match the current regex field baseline and is not integrated.

Three remaining validation failures were inspected without changing the model,
features or split:

- `TC_POS_ARAB_005`: missed a whole-number cash-withdrawal amount; the branch,
  account, currency and balance were correct.
- `TC_POS_ETI_007`: incorrectly labeled “monthly card spending” as a merchant in
  a cashback notification with no named party.
- `TC_POS_ZAI_005`: missed the Arabic ATM/operator name; amount, currency and
  balance were correct.

Next data work should cover whole-number withdrawal contexts, cashback/purpose
phrases without names and Arabic ATM/operator boundaries. Use separately
collected and reviewed source families; do not simply copy these three
validation messages into training or tune against them. Keep label provenance
and admit new data only under the owner's data-control process. The two
unresolved role records still need explicit slot conventions before admission.

## Approved context/shape experiment

The owner's edited specification reserves meaningful model changes for approval.
The owner approved this specific experiment on2026-10-26. The following settings
were implemented once, without validation-based revisions.

Keep the averaged perceptron, 25 epochs and seed 20261024. Use the frozen 63/16
folds and four exclusions. Fit once with no validation-based epoch or feature
search. Compare with the saved word baseline and paired regex field values.

Replace numeric-string memorization with general features, and add context:

- A bias; the current normalized word for non-numeric tokens; numeric tokens
  use a shared `<NUMBER>` word feature instead of their literal value.
- Numeric shapes: integer/decimal, decimal places, digit count and masked-account
  shape. Arabic-Indic, Persian and ASCII equivalents share these feature keys.
- Normalized neighboring words at offsets -2, -1, +1 and +2; neighboring shapes
  at -1/+1; explicit beginning/end markers. For example, a number after
  “balance” can receive a different score from a number after “purchase”.
- Existing previous-tag transitions. Mask invalid IOB2 continuations so an
  `I-MERCHANT` cannot begin a sequence or follow a different entity type.

Use learned weights only, with no bank, sender or merchant lists. Preserve raw
text exclusively for returning exact spans/values; normalized feature keys must
not replace the name text. Do not generate thousands of repeated merchants or
introduce augmentation into this first controlled comparison.

Separate versioned multi-feature flat-array export and isolated Python/TypeScript
research scorers are in `src/python/research/bio_context.py` and
`src/typescript/research/BioContext.ts`; feature/score schema is
`config/contracts/bio_context_model.json`. They pin normalization, feature ordering,
transition legality, tie handling, dimensions and float32 operations with shared
vectors. Keep the deployed version-1 loader/API and browser tester unchanged.

Report exact spans, unique primary field values, token/sequence agreement,
invalid transitions and the same script slices. A useful research result must
improve primary-field completion and numeric span recall over the saved word
baseline. This is not a deployment threshold. The current extractor already
matches 16/16, so a new model cannot claim to exceed it on this metric. Promotion
would need a separate approved gate, preserved 226-case compatibility and fresh
independently reviewed messages. Do not tune or infer the reserved merchant final
test. More data may still be needed if this controlled experiment fails.

## Reproduction

From the authoritative `C:/Users/mustafa/Desktop/msroof` repository:

```powershell
py -X utf8 -m training.entities.prepare_labels --check
py -X utf8 -m training.entities.evaluate --run-id labels_v2_word_v1 --check
py -X utf8 -m training.entities.train_context --run-id labels_v2_context_v1 --check
py -X utf8 -m unittest tests.python.test_bio_labels -v
py -X utf8 -m unittest tests.python.test_bio_context -v
py -X utf8 run_all_tests.py
```

New fitting requires a fresh run ID. Frozen outputs reject changed contents;
do not overwrite the label derivative, split or earlier reports. Input/source
hashes are bound to each report and privately snapshotted with deduplicated
content blobs. Reproducing a historical version requires its bound inputs.
