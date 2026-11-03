# Masroof ML engine — readiness and refactor review

## Readiness review,2026-10-26; preparation update2026-10-27

The detailed engine has stronger, reproducible behavior checks, but the evidence
is insufficient to call the complete machine ready. The largest remaining work
is task-aligned annotation and independent evaluation. Recent completion,
direction and purpose improvements are structural rules, not a newly trained
language-understanding model. This review does not fit a candidate, change runtime
behavior, promote a loader or evaluate a reserved final fold.

Current aggregate evidence: `data/reports/behavior/ml_readiness_annotation_prep_v1.json`.
The original `ml_readiness_v1.json` remains a historical snapshot. Reproduce:

```powershell
py -X utf8 -m training.evaluation.readiness --run-id ml_readiness_annotation_prep_v1 --check
```

The audit verifies the source hashes of the current Arabic behavior report,
counts existing corpus/report metadata, and replays only the389 already exposed
public development controls. It does not infer reserved merchant names or inspect
additional private originals. Its counts are diagnostics, not independent accuracy.

| Area | Current evidence | Remaining gap |
| --- | --- | --- |
| Transaction/completion | Detailed inclusion and completion primarily follow shared structural evidence. The old learned score is a fallback that can send otherwise unrecognized text to review. | A new learned classifier has not demonstrated better source-family generalization or replaced these rules. |
| Direction | The saved candidate's raw head matches100/215 eligible synthetic validation labels before lexical overrides. | Learned direction remains weak; final guarded outputs must not be mistaken for model-only understanding. |
| Extraction | Approved context BIO trial13/16 complete primary fields; word trial0/16; retained regex16/16 on the same exposed validation records. | No learned entity replacement has passed the existing baseline; fresh withdrawal/cashback/Arabic ATM source families are still needed. |
| Expense purpose | The canonical transaction-purpose labeling file has0 records. On389 development controls,120 outputs are included/outgoing and15 receive a category. | No15-category SMS-purpose learner is trained or independently evaluated. The15/120 (12.5%) conditional assignment rate is not category accuracy or all-eligible coverage. |
| Merchant research | Selected V3 has166 training businesses; human validation answers2/5 correctly and abstains on3/5. All3 Arabic validation identities abstain. | Merchant defaults do not establish the purpose of an SMS transaction or Arabic generalization. Reserved final29 identities remain uninferred. |
| Real-world evaluation | Located originals and four web diagnostics are already exposed; no independent final SMS evaluation is available. Release thresholds remain null. | Passing153 Python/ten TypeScript suites and226 frozen cases establishes conformance, not real-world accuracy. |

### What the data actually supports

The2,120-row SMS corpus is entirely marked synthetic privacy-transformed generator
data with legacy-generator, non-human labels. It has seven old classes: transaction
debit/credit, OTP, declined, chat, promo and announcement. Existing expected amount,
currency, merchant and type fields remain useful **weak supervision**. The absence
of canonical field names is not proof that all supervision is absent.

However, those classes do not supply individually reviewed completion uncertainty,
tracking policy, own-versus-other ownership, or transaction purpose. Relabeling
TRANSACTION_DEBIT to include would incorrectly turn own/ambiguous transfers into
eligible expenses. Missing annotations are also different from a message whose
meaning is genuinely uncertain. The corpus keeps1,702 training records across80
source-expression IDs and418 validation records across22; these are generator
expressions, not102 independently collected real bank templates.

Both saved replacement classifiers have0 false positives and45 false negatives
on the418-row guarded synthetic validation comparison, and20 false negatives on
226 frozen cases. All45 validation misses are the same held-out source expression
`literal-L566-C15` (provider metadata HOUSING_BANK). This indicates a concentrated
unseen-expression problem, not45 independent novel failures. It does not justify
a bank registry, putting those validation rows into training, or repeatedly tuning
the same fold. Character/subword features are a reasonable future hypothesis,
not a demonstrated fix. The exposed legacy baseline's perfect fixture result is
not an unbiased generalization benchmark.

In the389-record diagnostic, decisions are138 include/129 exclude/122 review.
Overlapping review reasons include68 ownership,43 completion,33 direction and25
amount gaps;79 reviewed records retain completed status. These counts do not sum
to122 because each record can have several reasons. Ownership unavailable from the
text cannot be learned into existence; the opt-in confirmation API supplies a
caller fact, not a probability or new human-gold training label.

### Recommended next bounded task

Status: this preparation is complete as of2026-10-27; see the completion section
below. That weak review is also complete in the subsequent section; the next step is safe expansion/admission planning.

Build a **versioned field-level SMS annotation view and training-family review
queue**, before fitting another classifier:

1. Reuse the transaction contract's semantics/taxonomy and the existing provenance
   ledger's labels/evidence conventions. Specify per-field annotation state,
   origin/reviewer, evidence span and source hash. Distinguish unannotated from
   semantic uncertain and from not_applicable. Derive tracking policy from
   supported facts rather than importing the old boolean/class as canonical truth.
2. Import existing legacy labels as weak evidence with their original record IDs
   and frozen split membership. Begin the review queue with one representative
   for each of the80 **training** source expressions; preserve the unioned leakage
   groups. Do not copy validation/frozen/control examples into training. Do not
   manufacture ownership, certainty, new messages or independent evaluation flags.
3. Assistant-reviewed text-supported fields remain weak labels. Preserve unknown
   ownership/purpose when no fact is available; ask only for facts that the owner
   can actually supply. Do not ask the owner to hand-label2,120 variations. Carry
   a reviewed template interpretation to descendants only after checking whether
   changed slots alter the field's meaning.
4. Resolve the existing category-guide conflict before admitting new labels:
   CATEGORY_LABELING.md currently suggests Other when a category cannot be chosen;
   the approved transaction contract reserves Other for a known out-of-taxonomy
   expense. Unknown purpose must remain null/uncertain. Preserve historical
   artifact bytes or record a deliberate documentation version change.
5. Produce a field/support/provenance/fold audit and an explicit candidate
   experiment proposal. Acceptance for this preparation task is validated
   annotations, deterministic queue membership, no cross-fold admission, and
   unchanged runtime/model/fixture bytes. It does not include fitting, promotion,
   threshold changes, or a final-test run.

Independent Jordanian data acquisition remains a parallel prerequisite for a
credible final evaluation. The owner already has no additional fresh originals;
do not ask that question again. Current seeds/descendants and exposed web fixtures
cannot be rebranded as a fresh test. Future public sources still need documented
origin, permission, sanitization, reviewed truth and exposure/family checks.

The active model export's historical metadata still says accuracy100.00%. Its
bytes are preserved, but that string is not evidence of real-world accuracy.
Model scores are uncalibrated. Proposed release targets in the behavior contract
are still proposals; there is no basis here to approve automatic deployment or
claim the machine has reached them. The main tester output also remains the
legacy caller; corrected detailed results appear in the separate comparison.

## Annotation preparation completed,2026-10-27

The proposed preparation is implemented in training/corpus/semantics.py and the
versioned annotation contract/validator. Artifacts and review instructions:
`data/annotations/sms_semantics_v1/README.md`. The generated view references1,702
existing training records without copying their SMS text; its queue chooses one
hash-minimum representative per80 training expressions. The418 validation records
are not exported. Existing legacy claims remain explicitly weak. Canonical fields
remain **unannotated** until text review; this is not a claim that80 messages have
been reviewed or that new training labels are ready.

Coverage audit: `data/reports/sms_semantics_preparation_v1.json`.
13 queue entries/410 draft records are blocked for future admission by protected
merchant/family candidates or known test/control text (399 protected-merchant
records;11 fixture/control overlaps). Blocking propagates within the original
frozen SMS group, never by moving folds. All drafts, including the67 unblocked
queue entries, remain training/evaluation-ineligible. Conservative lexical
matching is not complete identity/semantic isolation. The builder performs no
model inference, final-fold inference, teacher labeling or message generation.

Ten new safeguards cover source hashes/folds, exact Unicode evidence, weak versus
unannotated states, no model calls, reservation/family propagation, legacy nulls,
non-invented decisions and admission flags.163 Python tests, ten TypeScript suites
and226 frozen cases pass; runtime/model/fixture bytes are unchanged. The category
guide has an explicit policy revision1.1 correcting Other to the approved
out-of-taxonomy meaning; old guide bytes were archived before editing. No category
records were added. Updated readiness snapshot:
`data/reports/behavior/ml_readiness_annotation_prep_v1.json`; older readiness
snapshots remain historical and their source hashes are preserved.

```powershell
py -X utf8 -m training.corpus.semantics --check
py -X utf8 -m training.corpus.semantics --queue-index 0
```

### Original candidate design — completed trial recorded below

Hypothesis: train-only word plus character3–5-gram evidence, with numeric runs
mapped to a fixed placeholder in a research-only feature view, may generalize
better to unseen notification expressions than word-only features. This is an
original hypothesis, tested once below; adding text variations does not create independent evidence.

Prerequisites: complete weak text reviews in the queue, verify slots before any
interpretation inheritance, resolve admission blockers and explicitly audit usable
field/class coverage. Preserve source hashes, families and folds. Unannotated
fields must not become training targets; genuine semantic uncertainty remains a
separate value. Assistant labels stay weak. Do not import the known45 validation
misses, BIO failures, frozen controls or final merchant identities into training.
There is currently no approved/admitted canonical training view.

If that preparation supports the experiment, freeze one A/B configuration:
word-only versus word+character features on the **same admitted records and
annotated targets**, fixed L2 logistic solver/C1, seed20261027, minimum training
feature frequency2, maximum2,000 iterations. No hyperparameter/threshold search.
Use completed versus non_transaction evidence only where status is annotated;
skip uncertain/unannotated status in that binary head. Direction uses annotated
incoming/outgoing on completed records; skip uncertain/not_applicable/unannotated
direction. Neither head learns account ownership, recording eligibility or
expense purpose from a legacy class. If a required class/family is absent, report
the experiment as unsupported rather than filling it with generated data.

Fit vocabulary/normalization only on training data; retain the original SMS for
exact entity extraction. Give each existing training expression equal total
sample weight in both arms so repeated slots do not dominate. Export one isolated
candidate through an explicitly versioned research feature contract and verify
complete Python/TypeScript/browser score parity. The character feature path must
not silently change active preprocessing or export math.

Freeze candidate/settings before evaluating the validation fold with separately
reviewed weak targets. Report raw heads and guarded outputs separately, including
false inclusions, eligible misses/reviews, direction, exact amount/currency,
source-expression and script slices, coverage and model size. Do not substitute
trackingDecision for completion truth. Keep the226 frozen compatibility check as
exposed regression evidence, not a final accuracy benchmark. Reserved merchant
final inference, another BIO trial, purpose-model training, deployment thresholds
and loader/default-caller migration are excluded. This proposal is not fitting
or promotion authorization; the current task only prepares drafts and controls.

## Weak text review completed,2026-10-27

All80 queued representatives are reviewed in a separate immutable layer:
`data/annotations/sms_semantics_v1/text_reviews_v1.jsonl`, with explicit source-bound
assistant decisions and a review manifest. `training.corpus.review_semantics`
materializes those specific reviews; it does not run a student classifier, look up
merchant categories, or annotate descendants. Reproduce with `--check`.

The791 weak field annotations yield24 completed notifications,55 non-transactions
and1 uncertain fragment; policy yields11 include/55 exclude/14 review. All13
transfer relationships stay unknown. Queue7's named source account does not resolve
its party role; queue44 is truncated/date/balance text with no established event.
Those fields remain unannotated instead of inheriting a missing legacy value.
Only the explicit ATM withdrawal receives an expense-purpose label. Other shop/
biller names are retained as source text without inventing a unique purpose.
These are assistant labels, not human gold or independent accuracy evidence.

All13 admission blocks/folds/source hashes remain intact; all records still have
trainingEligible=false and independentEvaluationEligible=false. The67 unblocked
reviews contain17 completed,49 non-transactions and1 uncertain; only13 completed
records have resolved incoming/outgoing direction. Thus66 binary completion
labels and13 direction labels could potentially support research after admission,
not a15-category purpose model or a credible independent final benchmark.
There is no automatic propagation to the other1622 training records or418 held-out
records.172 Python tests, ten TypeScript suites and226 frozen cases pass.
The current review manifest/report are text_review_manifest_v2.json and
sms_semantics_text_review_v2.json; exact-byte checks reject newline-only source
changes. The reviewed data file is unchanged; v1 evidence is retained. The full
suite now passes173 Python tests with this additional integrity safeguard.

### Guarded expansion audit completed,2026-10-27

`training.corpus.propagation` and its versioned contract audit all1,702 training
records. Saved evidence: `data/reports/sms_semantics_propagation_v1.json`; candidate
references and separate validation queue are documented in the annotation README.
The1,133 initial guard matches become944 candidates after189 normalized-text
duplicates are removed.410 existing blocks remain;159 holds comprise149 literal
changes, nine uncertain fragments and one conservative changed-name risk veto.

Candidates span66 source expressions:66 direct reviews and878 proposed
descendants. Completion support495 completed/449 non-transaction; direction
support198 incoming/123 outgoing. Each expression has proposed total weight one
per head, preventing repeated slots from masquerading as independent support.
These weights are not certainty. Only numeric/mask and untrusted exact name
locator slots may vary; other wording must match and changed names face risk
checks. This is a reproducible weak-label proposal, not semantic proof.

No ownership, tracking, purpose, amount/currency or party labels propagate. No
canonical annotations, frozen data, weights or runtime behavior changed in this
audit. All admission flags stay false. A separate22-reference validation queue
has no annotations and retains four control/protected-merchant blocks. Full
verification:183 Python tests, ten TypeScript suites and226 frozen cases pass;
preparation, weak review and proposal checks reproduce.

### Separate validation review completed,2026-10-27

All22 queued validation representatives now have explicit source-text assistant
judgments, with no student predictions or legacy-label import. The212 weak fields
are saved separately by `training.corpus.validation_semantics`; source references
remain unchanged. Aggregate report:
`data/reports/sms_semantics_validation_review_v1.json`. Outcomes:16 non-transactions,
five completed movements, one uncertain purchase notice; recording16 exclude,
three include, three review. Both named CliQ transfers have unknown ownership.
The generic purchase notice has no source-confirmed settlement, so only uncertain
completion and derived review are annotated. Names do not establish purpose.

Four existing blocks remain.18 unblocked representatives supply14 non-transaction
and four completed targets; direction is two incoming/two outgoing. Only two
completed events have enough ownership facts for inclusion.396 validation
descendants stay unannotated. All training/independent-evaluation eligibility flags
remain false. These are tiny, exposed synthetic-development cohorts with weak
assistant labels; neither independent final evidence nor precise accuracy claims
are possible.190 Python tests, ten TypeScript suites and226 frozen cases pass.
The validation review and prior layers reproduce with `--check`.

### Concrete research proposal — owner approved2026-10-27

The owner approved this exact comparison with “sure” on2026-10-27.
This proposal selects records for **one isolated research comparison**, without
changing canonical admission flags, source labels or runtime loaders. The trial
results are below. Its frozen cohorts bind to these immutable manifests:

- `data/annotations/sms_semantics_v1/propagation_manifest_v1.json`:
  `60e44bb3ca335c36c93660a7385607c8f1fdd0d2a0b0e3497e5d861127d82eac`.
- `data/annotations/sms_semantics_v1/validation_review_manifest_v1.json`:
  `a910150b95c0bbd2dddd99bed3d88338e57e04ca29de4e28d5afe7955ef223a7`.

| Head | Proposed training view | Separate weak validation view |
| --- | --- | --- |
| Completion | Exactly944 `candidate` rows:495 completed/449 non-transaction, across17/49 source expressions | Exactly18 unblocked reviewed representatives:4 completed/14 non-transaction |
| Physical direction | Exactly321 completion-positive candidates with resolved direction:198 incoming/123 outgoing, across7/6 expressions | Exactly4 unblocked completed representatives:2 incoming/2 outgoing |

Do not add the410 blocked,159 held or189 duplicate train rows, the four blocked
validation representatives, or396 unreviewed validation descendants. Review/unknown
ownership is not a negative completion label. The direction head describes physical
flow even when ownership prevents recording; it does not decide tracking eligibility.
Each training expression has total weight one per head in both arms; report raw
row counts alongside these much smaller expression counts. Validation counts one
reviewed representative per expression. Fit neither vocabulary nor thresholds on
validation. Preserve uncertainty and all source/fold/hash bindings.

Use the single fixed A/B design above: word-only versus the same words plus
character3–5-grams, L2 logistic/liblinear C1, seed20261027, training minimum feature
frequency2, maximum2000 iterations, no class reweighting or parameter search. Freeze
a separate feature/export contract before fitting; apply the same train-only
normalization/numeric-placeholder view in both arms. Binary prediction uses a
fixed zero decision-score boundary, with ties assigned to the negative class;
completed and incoming are the respective positive classes. Use binary feature
presence rather than term counts or TF-IDF, with identical word unigrams in both
arms and additional character features only in the second arm.
Never describe its probability as calibrated certainty. A convergence failure
invalidates the trial rather than authorizing extra search.

Export isolated candidates and check feature vectors, decision scores and full
head predictions across Python/TypeScript/browser before evaluation. Report raw
completion confusion and direction counts first; show unchanged-rule recording
outcomes separately, with source-expression and Arabic/English/mixed slices and
their denominators. Do not attribute a structural guard's result to the learned
head. Four completed validation representatives cannot estimate real-world recall
precisely; no release threshold or superiority claim follows from winning here.
If export parity or cohort checks fail, stop that experiment and report the cause.
The226 frozen cases remain a separate exposed compatibility check.

Owner approval was limited to implementing/fitting/evaluating this one
comparison on the specified weak research views. Ownership/purpose/BIO training,
new augmentation, deployment, promotion, active caller migration, reserved final
inference and publication remain outside its scope. The existing engine and tester
remain active until a separate evidence-based promotion decision.

### Approved A/B completed once,2026-10-27

Reproduce without fitting:

```powershell
py -X utf8 -m training.transactions.semantics_ab --check
```

Report: `data/reports/transactions/sms_semantics_ab_v1.json`. The matching cohort
and immutable start ledger sit beside it. The ledger prevents another fit;
`--check` loads saved exports and recomputes scores/metrics without a solver call.
Snapshots preserve all bound source versions. Exactly four fits completed, one
per arm/head, with no convergence failure, parameter search or extra trials.
Canonical data-admission flags were not changed.

| Isolated candidate | Completion on18 representatives | Direction on4 completed representatives | JSON export bytes |
| --- | --- | --- | --- |
| Word only | 4/4 completed,14/14 non-transactions correct | 3/4 correct | 25,000 |
| Same words plus character3–5-grams | 4/4 completed,14/14 non-transactions correct | 3/4 correct | 600,105 |

Both misclassify the same Arabic cash withdrawal as incoming
(`synthetic-v1-0750`, expression `literal-L448-C15`). Arabic-containing completion
is10/10, direction1/2; English completion8/8, direction2/2. Those tiny, exposed
synthetic slices do not establish real-world accuracy. The scores are uncalibrated;
the larger wrong character-model score is not evidence of greater certainty.
Character features yielded no observed gain and about24 times the export size.
Neither candidate is promoted or connected to the active tester.

The direction training head had only two Arabic outgoing expressions, both bill
payments (50 repeated rows), versus three Arabic incoming expressions(105 rows).
The withdrawal word `سحب` is absent from both direction vocabularies. This is a
concrete coverage gap, not proof that one word alone explains the error. No
validation labels/templates were moved into training and no corrective refit was
run. The next data plan should broaden Arabic outgoing **event types**, preserving
the exposed holdout and existing reservation blocks; numeric/name repetition is
not a substitute for expression variety.

Export contract: `config/contracts/sms_semantics_model.json`; pure research scorers
`src/python/research/sms_semantics.py` and `src/typescript/research/SmsSemantics.ts`.
Aligned flat float64 weights are saved as
`data/models/sms_semantics_ab_v1_word_candidate.json` and
`data/models/sms_semantics_ab_v1_word_char_candidate.json`; the standalone browser
source is `data/models/sms_semantics_ab_v1_browser_runtime.js`. On967 texts per arm
(944 training,18 validation, five controls), complete normalized features, active
vectors, scores and both head decisions matched Python/TypeScript/browser-compatible
VM, maximum score difference0. Export versus sklearn training score gaps were at
most3.11e-14. This is not an interactive UI, device latency or Hermes benchmark.

The unchanged structural assessment is reported separately:12 exclude/4 review/
2 include,13/18 fully matching weak reviews. Remaining differences cover exact
party/operator boundaries, withdrawal purpose, and two ordinary requests/questions
conservatively reviewed by the existing path. Its guards were not combined with
the candidates and their outcomes must not be credited to either learned head.
The active model, caller and tester are unchanged.199 Python tests, ten TypeScript
suites and226 frozen active-engine cases pass; saved trial reproduction also
passes with fitting explicitly disabled.

The subsequent coverage/data milestone is complete in `docs/SMS_DATA_COVERAGE.md`:
74 explicitly authored weak messages/37 bilingual scenarios, preserved reservations
and no fitting/admission. Its concrete follow-up word-only proposal is separate
from the completed A/B authorization. Do not restart the old training attempt.
The owner subsequently approved that follow-up; its two heads are now fitted once.
Completion remains18/18 and direction improves3/4 to4/4 on the unchanged, exposed
weak validation. The Arabic withdrawal is the sole changed prediction. Export
parity is exact on1,037texts;214 Python safeguards and the existing TS/frozen gates
pass. See the coverage document for results, limits and the optional tester
comparison proposed next. No model was promoted.

## Historical structural review,2026-10-25

Later detailed-API repairs and the2026-10-26 cleanup supersede the implementation
status/line numbers below. Use docs/ARCHITECTURE.md for current paths and
BEHAVIOR_EVALUATION.md for current runtime evidence. Retired root brain/lock/
exporter paths are historical references. This historical review is retained as
the rationale, not a new authorization boundary.

**Review date:** 2026-10-25
**Review scope:** current ML engine, training/data workflows, tests, developer tester, and project documentation.
**Status:** review and proposal only. No runtime code was changed and tests were not run for this review.

**Follow-up:** the owner approved this plan on 2026-10-25 and authorized task 1. Its completed behavior/evaluation contract is `docs/TRANSACTION_BEHAVIOR.md`, with machine-readable rules, illustrative cases, and semantic validation. The original review below remains the rationale; its approval gate has been satisfied for task 1. Specific saved human category choices take precedence over generic purpose-based suggestions, as recorded in that contract.

## Project goal

Build a Jordan-focused Arabic/English system that recognizes completed bank or wallet transactions, extracts amount/currency and incoming/outgoing direction, identifies the merchant or counterparty where possible, and categorizes outgoing spending using the agreed 15 categories. Person-to-person transfers count as transactions. Transfers between the owner's own accounts are excluded; when ownership cannot be established, the result should remain uncertain. Text alone cannot prove that an SMS genuinely came from a bank.

## Assessment

The repository has useful safety foundations: a frozen 226-case behavior suite, versioned Python/TypeScript preprocessing and scoring contracts, provenance-aware business labels, protected category splits, and explicit rules against treating weak research labels as independent truth. Keep those safeguards.

The main problem is evidence and separation of responsibilities, not a lack of model files. The active engine is still the legacy path. The newer transaction/direction candidate fails the frozen-corpus comparison, the entity tagger's exact-sequence result is weak, and the merchant-name category candidate has very little human validation evidence and no independent Arabic success. None is ready to replace production behavior. Large-scale deletion or retraining now would discard safeguards without solving the actual gap: independently evaluated Jordanian transaction messages.

## Missing capabilities and risks, in priority order

### P0 — No independent real-message evaluation set

The 2,120-row transaction/direction dataset is generated by `training/expand_dataset.py`; its names and message forms are synthetic templates. The user's approximately 20 Arab Bank and 10 Capital Bank originals seeded Gemini-generated descendants, so those source families are already development-exposed. The intake guide says row-level origins and descendant links remain unresolved. The frozen 226 cases measure regression against current behavior, not generalization to new banks, templates, or real user messages.

**Proposed change:** make per-message provenance and family membership explicit before admitting these records to development. Obtain separately sourced, unexposed message families for final evaluation. Keep originals private and sanitized derivatives separate. Do not describe the seed set or synthetic descendants as independent test evidence.

### P0 — Category task does not yet match the product target

The active runtime exposes eight legacy categories in `src/typescript/MasroofEngine.ts:23-32`; its categorizer is a fixed token-to-category scoring map at `:337-436`. The required taxonomy has 15 categories. The newer standalone merchant-name classifier is not the same task as categorizing a transaction: one business can receive payments for different purposes, and a name alone cannot resolve fees, installments, cash withdrawals, or mixed-purpose merchants.

The V3 merchant experiment has only five human validation identities: two answered correctly and three abstained; all three Arabic validation identities abstained. It uses uncalibrated scores and does not establish transaction-category accuracy. The existing documentation correctly forbids treating these results as generalization evidence.

**Proposed change:** retain merchant defaults as weak supporting evidence only. Define the outgoing-expense target schema and train/evaluate transaction-context categorization separately. Migrate the active output to the 15-category contract only after the category data and evaluation gate are adequate.

### P1 — Transaction, direction, and transfer decisions are entangled

`MasroofEngine.analyze` combines sender/contact rejection, chat/decline/admin guards, the legacy transaction score, transfer detection, direction cues, amount gating, extraction, and categorization (`MasroofEngine.ts:475-622`). Contact and phone-number sender checks can reject a message before its body is considered. Direction uses lexical expense/income indicators plus a model fallback (`:596-607`). The current result has only valid/invalid rather than an explicit uncertain state.

Own-account transfer exclusion is implemented through phrase patterns and a heuristic involving account masks (`:252-259`, `:637-666`). This does not establish account ownership in every message. Ordinary personal chat is also rejected by phrase patterns. These are useful guardrails but do not fully encode the required distinction between a completed person-to-person transfer and an own-account transfer.

**Proposed change:** define a transaction-status outcome with `completed`, `non_transaction`, and `uncertain`; treat person-to-person transfers as valid; exclude own-account movement only when evidence supports common ownership; preserve uncertainty when it does not. Evaluate sender metadata as context rather than a universal rejection rule. Make direction independently measurable and allow uncertainty rather than forcing a guess.

### P1 — Entity extraction remains regex-based; BIO is not ready

Regex extraction remains active in TypeScript and Python. The BIO model is experimental; its current held-out report has 87.67% token accuracy but 4% exact-sequence accuracy, and the handoff warns that the split is only a coarse source-category holdout. The training-set score is not a replacement criterion. The BIO builder also derives source spans from expected values, so repeated or ambiguous values need reviewed span truth rather than value-only matching.

**Proposed change:** keep regex extraction as the measured baseline. Improve entity labels with explicit reviewed spans, then compare exact amount, currency, merchant/counterparty, account, and balance entities on an isolated holdout. Do not connect the tagger to production until it clears that comparison.

### P1 — The parity claim is broader than the enforced checks

There are three implementations of engine behavior: TypeScript runtime, Python mirror, and JavaScript embedded by `tools/browser/build_tester_ui.py` into `tester.html`. The runtime and mirror are large (772 and 605 lines); the generated browser file is 845 lines and its builder is 736 lines. The browser implementation is manually maintained and the handoff documents known drift.

The frozen runners compare transaction validity and several entity fields, but they do not establish full parity for predicted category, confidence, reason, and all optional FX fields. A browser smoke/parity check on selected inputs is not proof that all three implementations agree.

**Proposed change:** establish one canonical, versioned input/output and feature contract, then make parity checks compare complete structured outputs. Keep Python as a reference/training implementation and TypeScript as the runtime. Retain the browser UI, but generate its inference bundle from the canonical runtime implementation instead of maintaining another engine by hand; select a bundling path compatible with the existing local-file tester before removing the duplicate.

### P2 — Responsibilities and generated data are difficult to maintain

`MasroofEngine.ts` combines orchestration, model loading, BIO inference, corrections/overlay state, regexes, direction, entity extraction, and categorization. `verify_engine.py` mirrors those concerns. The 746-line synthetic generator combines templates, hardcoded fixture entities, randomness, and output generation. The 939-line adversarial builder currently performs generation at import time, according to the handoff. This makes reuse and safe inspection harder.

**Proposed change:** split implementation by stable responsibility—input/preprocessing contract, transaction decision, direction, entity extraction, category prediction, correction overlay, and orchestration. In training tools, separate data-only builders from command-line/file-writing entry points, use explicit output paths, and give generated examples stable template-family IDs. Preserve seeds and outputs while refactoring so experiment inputs remain reproducible.

## What I would keep, change, or retire

| Action | Candidate | Why / guard |
| --- | --- | --- |
| Keep | Frozen 226 cases, hashes/schema validation, Python/TypeScript contracts, provenance, split protection, and historical experiment reports | They preserve behavior and explain why candidates were rejected. |
| Change | `MasroofEngine.ts` and `verify_engine.py` | Split responsibilities while preserving the current public TypeScript API and regression behavior during migration. |
| Change | Active category contract and evaluation | Move from eight legacy labels toward the agreed 15 only with transaction-context evidence. |
| Change | Browser tester internals | Keep the optional UI; replace its hand-maintained inference implementation after canonical bundling and equivalence checks exist. |
| Change | `expand_dataset.py` and adversarial generator | Separate templates/data from CLI writes; add stable provenance/template IDs; do not silently regenerate frozen fixtures. |
| Retired in cleanup | `MSROOF_BRAIN.md` | Canonical scope, evidence and continuation live in README, docs, STATE and HANDOFF. |
| Retire later | `tests/legacy/run_test_suite.py` | Only after confirming and migrating any unique assertions or workflows; the handoff already calls out this condition. |
| Split decision in cleanup | Old `train_and_export.py` / active `masroof_model.json` | Retire the incompatible experimental exporter; preserve active weights and caller behavior until a replacement passes its gates. |
| Do not delete | V1/V2 reports, snapshots, source records, or the browser tester | Historical evidence and reproducibility are more useful than small storage savings. |

## Recommended implementation order

1. **Approve this review and freeze the behavior contract.** Write down the result fields, uncertainty rules, transfer cases, category assignment conditions, currency default, and acceptance metrics. Do not select performance thresholds without enough independent data to support them.
2. **Repair the evaluation foundation.** Audit row-level provenance and template families; define a sanitized canonical message schema; reserve genuinely independent evaluation data. Keep the 226 suite as regression only.
3. **Add complete behavior-level measurements.** Measure transaction false positives/negatives, direction, exact field extraction, category accuracy/coverage, Arabic/English/mixed-language slices, and internal/person-to-person transfer cases. Keep this separate from model fitting.
4. **Refactor without behavior changes.** Split the runtime and data tools into bounded modules and preserve the current API. Compare complete outputs across Python and TypeScript; then bundle the browser tester from the canonical source.
5. **Train replacement candidates on the corrected data flow.** Keep each task's candidate artifacts versioned. Compare candidates against both independent held-out data and the frozen regression baseline. Report abstentions and counts, not only percentages.
6. **Integrate by capability, then retire.** Introduce one accepted capability at a time. Delete a legacy implementation only after its replacement has passed the relevant gate and unique tests/data responsibilities have been migrated.

## Documentation corrections to make during implementation

- `MSROOF_BRAIN.md` says only four businesses have Arabic names; `STATE.md` and the later handoff report later enrichment. Its stated next action and review totals are stale.
- `README.md` still gives the original merchant research report as the current default in some command descriptions; V3 is the current tester candidate.
- `STATE.md` was condensed during the review to current scope, evidence, blockers, and next approved task.
- `.agents/HANDOFF.md` contained extensive chronological repetition and exceeded its stated size target. It was compacted during this review to current decisions, evidence, blockers, and the next approved sequence; detailed historical results remain in the referenced reports.
- `masroof-invariants.md` describes a Hermes performance SLA although the mobile app/Hermes is out of scope, and claims zero allocation while current string/regex paths allocate. Reword these as measured targets for a later runtime integration, not current guarantees.

## Decision boundary

This report does not authorize code removal, model promotion, test-set inference, or acquisition of private messages. No code was changed and no tests were run during this review. The next bounded task should be selected after the owner approves or corrects this proposal. The most valuable first implementation step is an explicit behavior/evaluation contract for the transfer, uncertainty, and category requirements; broad cleanup should follow behind that contract.
