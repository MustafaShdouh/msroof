# SMS semantics annotation preparation1.0.0

This is a reference-only view of the existing synthetic **training** fold.
It does not duplicate SMS bodies, invent new messages, admit data to training,
or provide human-gold/independent evaluation labels.

| Artifact | Meaning |
| --- | --- |
| `manifest.json` | Source/split/contract hashes and exact output checksums |
| `drafts.jsonl` | 1,702 original training record references, weak legacy claims, currently empty canonical annotations |
| `review_queue.jsonl` | One existing hash-minimum record per80 training source expressions |
| `../../reports/sms_semantics_preparation_v1.json` | Coverage and reservation audit |

The418 original validation records are not exported into this view. Every draft
has `trainingEligible=false` and `independentEvaluationEligible=false`.
The base preparation remains immutable. Its80 representatives have subsequently
been reviewed in the separate weak layer below; the base drafts are still
unannotated and all admission flags remain false.

## Completed weak text review1.0.0

| Artifact | Meaning |
| --- | --- |
| `text_review_decisions_v1.json` | Explicit assistant decisions bound to each queue index, record ID, text hash and original manifest |
| `text_reviews_v1.jsonl` | 80 reviewed copies of queue drafts with791 weak source-evidenced field annotations |
| `text_review_manifest_v2.json` | Current review provenance, input hashes and exact-byte output checksum |
| `../../reports/sms_semantics_text_review_v2.json` | Current coverage, partial roles, unresolved ownership and recording outcomes |

```powershell
py -X utf8 -m training.corpus.review_semantics --check
```

The review finds24 completed notifications,55 non-transactions and1 uncertain
fragment. Canonical policy produces11 include/55 exclude/14 review. All13 transfer
relationships remain unknown. Missing owner roles also leave direction uncertain
where needed. No merchant-category model or student runtime predicted these labels;
the assistant's interpretations are explicitly weak, not human gold.
The original manifest/reportv1 remain historical. V2 hardens exact-byte source
checks, including newline changes, without changing the80 reviewed records.

Queue7 has an unresolved named-source-account role, so its party slot remains
unannotated. Queue44 has a truncated prefix/date/balance, so only completion
uncertainty and the resulting review decision are annotated. Non-transaction
quoted amounts are inapplicable rather than posted amounts. An exact ATM
withdrawal is the only expense-purpose assignment; name-only merchants/billers
do not supply a unique spending purpose. Source party phrases retain their raw
descriptors/diacritics/formatting.

The13 admission blocks are retained. Among67 unblocked reviews there are17
completed,49 non-transactions and1 uncertain; completed directions are6 outgoing,
7 incoming and4 uncertain. That supplies only66 potential binary-status targets
and13 resolved-direction targets before any admission decision. It does not label
the other1,622 training records or the418 validation records, and does not train
a model. Do not propagate a representative's interpretation without checking
descendant slots and source grouping. All outputs remain ineligible for fitting
and independent evaluation.

## Guarded expansion proposal1.0.0

`training.corpus.propagation` audits all1,702 training references against the
80 weak reviews. Its rules live in
`config/contracts/sms_semantics_propagation.json`. These are **proposals**, not
new canonical annotations or permission to fit a model.

| Artifact | Meaning |
| --- | --- |
| `propagation_proposal_v1.jsonl` | Every training reference, outcome, source review and proposed targets |
| `validation_review_queue_v1.jsonl` | 22 separate, unannotated validation-expression references; four blocked |
| `propagation_manifest_v1.json` | Exact input/output hashes and false admission/training flags |
| `../../reports/sms_semantics_propagation_v1.json` | Aggregate coverage and limitations; read this first |

```powershell
py -X utf8 -m training.corpus.propagation --check
```

Of1,133 initial guard matches,189 normalized-text duplicates are removed, leaving
944 candidates:66 direct reviews plus878 proposed descendants across66 source
expressions. Status support is495 completed/449 non-transaction;321 also have
resolved direction (198 incoming/123 outgoing). These are synthetic variations,
not944 independent observations. Proposed weights sum to one per expression and
head; they are sampling weights, never confidence percentages.

410 records retain their existing blocks.159 are held:149 changed literal
skeletons, nine uncertain-completion descendants, and one changed name slot
matching a conservative risk veto. A veto can be a false alarm; it never grants
an annotation. Only numeric/mask slots and uniquely located untrusted legacy
name claims can vary. Other normalized wording must match; changed name slots
are checked for financial, ownership, negation and conditional language. Only
the explicit `JO` newline routing prefix is removed, preserving words such as
`IF` and `NO`. Completed candidates require a positive primary amount in the
reviewed slot, without propagating an amount label.

Only completion and resolved physical direction are proposed. Ownership,
recording decisions, purpose, amounts/currencies and party labels are excluded.
No student predictions, new messages, model fitting or admission occurs. All
training/evaluation eligibility flags remain false. Validation references carry
no proposed targets; known control and protected-merchant overlaps remain
blocked. They still need separate source-text review before a research admission
decision. Neither this queue nor existing synthetic data establish independence.

## Separate validation review1.0.0

`training.corpus.validation_semantics` materializes22 explicit source-text
judgments from `validation_review_decisions_v1.json`. Read the aggregate
`../../reports/sms_semantics_validation_review_v1.json` first. Reviewed copies
are `validation_text_reviews_v1.jsonl`; `validation_review_manifest_v1.json`
binds their exact bytes, decisions and source queue. Original queue references
remain unannotated and unchanged.

```powershell
py -X utf8 -m training.corpus.validation_semantics --check
```

These212 weak field annotations describe16 non-transactions, five completed
movements and one uncertain purchase notice. Recording outcomes are16 exclude,
three include and three review. Both named CliQ transfers retain unknown
ownership despite resolved physical direction. The unconfirmed purchase notice
has only completion uncertainty and a derived review decision; its other fields
are deliberately unannotated. Loyalty points are not a posted money amount;
declined charges and conversational transfer claims are not completed receipts.
Only explicit cash withdrawal receives a purpose label. Named merchant/operator
text does not establish a unique spending purpose.

Four blocked representatives stay blocked. The18 unblocked references contain
14 non-transactions and four completed movements, with two incoming/two outgoing
directions. Two completed events still need ownership facts before recording.
The396 other validation records remain unannotated: no inheritance, expansion
or training admission follows. No model predictions were used for the decisions.
Assistant labels on this exposed synthetic development fold are not human gold
or independent accuracy evidence. The research-only proposal and exact cohort
bindings are in `docs/REFACTOR_REVIEW.md`. The owner subsequently approved one
isolated research A/B, recorded in `data/reports/transactions/sms_semantics_ab_v1.json`;
its selection leaves these original eligibility flags unchanged. Neither candidate
was promoted, and validation descendants remain unannotated.

## Resolve a queue item

From the repository root:

```powershell
py -X utf8 -m training.corpus.semantics --check
py -X utf8 -m training.corpus.semantics --queue-index 0
```

The second command resolves index0 through79 against the hash-bound original
corpus and shows its existing SMS, draft and admission blockers. It does not score
a model or label that text. All record IDs, source indices, source-expression IDs
and unioned leakage groups come from the original frozen corpus/split.

`legacyClaims` are source-column assertions with origin
`legacy_generator_not_human_gold`, not reviewed canonical field values. Their
source columns are specified in `config/contracts/sms_semantics_annotations.json`.
A null legacy amount/party does not establish absence. An omitted annotation is
**unannotated**; it does not mean semantic uncertainty, unknown ownership or
not_applicable. A real text review may later assert one of those meanings as an
explicitly weak interpretation with evidence.

## Review without overwriting the prepared view

Keep these generated artifacts immutable. Store subsequent review decisions in
a separate versioned review file. Bind each decision to `recordId` and
`textSha256`, and validate its annotations on a copy of the matching draft using
`tools/contracts/validate_sms_semantics.py`. Only text-supported fields are
annotated; a reviewer must not invent ownership/purpose or copy a model's output
as truth. No representative decision automatically labels its descendants.

For each weak field record `state`, `value`, `origin`, `reviewer`, `evidence` and
`note` as specified by the contract. State is `weak`, reviewer is `assistant`, and
origin is `assistant_reviewed_text`. Evidence uses exact original Unicode
code-point offsets and text, including diacritics/digit script. Null values need
an explained text review; they do not inherit meaning from a missing annotation.
`trackingDecision` instead uses `derived_policy` and references annotated facts;
the validator rejects include/exclude decisions based only on a legacy class.

13 queue entries/410 draft records have admission blockers:399 records touch a
protected merchant lexical candidate and11 touch known frozen/control text.
Blockers propagate to the entire existing SMS group. Related-brand metadata is
checked too. These are conservative, bounded matches, not certified identities
or exhaustive semantic-overlap detection. Keep all blockers and frozen folds;
67 unblocked queue entries are still **not** automatically training-eligible.
Do not infer the reserved merchant final fold or import its category labels.

Unknown purpose stays unannotated until review, then null/uncertain when the
message cannot establish it. `Other` requires an understood out-of-taxonomy
expense; it is never a replacement for missing knowledge. These weak drafts do
not populate the separate human-reviewed `category_labels.jsonl` file.

The original experiment design, its completed single trial and next data needs are in
`docs/REFACTOR_REVIEW.md`. No fitting, augmentation, active-model/default-caller
change or final-test run is part of this preparation.
