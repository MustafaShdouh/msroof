# SMS training coverage and the first gap-filling batch

Milestone completed2026-10-27: inventory the measured research training cohort,
then prepare one broader bilingual training batch. No model was trained in this
milestone and the active tester remains on its existing engine.

The earlier research result was18/18 completion and3/4 direction for both word and
character candidates. Both missed an Arabic withdrawal. Those18 exposed weak
validation examples remain unchanged; they cannot become independent evidence
after training is adapted to their observed gaps.

## What the existing training cohort actually covers

These counts describe **source expressions**, not the many amount/name variations.
They cover the944 completion and321 direction rows selected for the completed A/B.
Protected, held and duplicate source rows are excluded from this measured cohort.
Arabic-containing messages may also contain English currency or service words.

| Completed event | Arabic-containing completion expressions | English completion expressions | Arabic-containing resolved-direction expressions | English resolved-direction expressions | New authored messages |
| --- | ---: | ---: | ---: | ---: | ---: |
| Transfers | 6 | 7 | 2 | 7 | 8 |
| Bill payments | 2 | 0 | 2 | 0 | 6 |
| Cash withdrawals | 0 | 1 | 0 | 1 | 4 |
| Cash deposits | 1 | 0 | 1 | 0 | 4 |
| Card purchases | 0 | 0 | 0 | 0 | 4 |
| Wallet merchant payments | 0 | 0 | 0 | 0 | 4 |
| Refunds | 0 | 0 | 0 | 0 | 4 |
| Monetary cashback | 0 | 0 | 0 | 0 | 4 |
| Posted fees | 0 | 0 | 0 | 0 | 4 |
| Paid installments | 0 | 0 | 0 | 0 | 4 |
| Salary credits | 0 | 0 | 0 | 0 | 4 |

Existing negatives are also uneven: there are no English declined/failed or
promotion expressions and no standalone pending-request expressions in this
selected cohort. Conversational transfer requests are present but are a different
kind of evidence. The new batch adds one bilingual scenario each for OTP, failed
withdrawal, pending transfer request, personal conversation, balance-only notice,
promotion, administration and loyalty points.

Blocked purchases/refunds elsewhere in the corpus remain blocked. This inventory
does not authorize extracting their text, erasing merchant names or bypassing
their reserved groups to increase training counts.

## The implemented batch

Dataset: `data/training/authored_sms_v1/messages.jsonl`.

- **74 distinct messages:37 Arabic and37 English**, grouped as37 paired scenarios.
- **54 completed**,16 non-transactions and4 uncertain-completion examples.
- Recording policy yields48 include,18 exclude and8 review judgments.
- Completed directions:30 outgoing,20 incoming,2 own-account/not-applicable and2
  uncertain. Missing-amount messages retain completed status but require review.
- Explicit foreign USD is preserved; missing currency visibly defaults to JOD.
  Arabic and Persian digits are retained in raw text and exact evidence spans.
- Each message has its own expression ID. Translation counterparts share an
  authoring group and must never be split across future folds.

These are **assistant-authored synthetic training examples**, not received Jordanian
bank messages, verified bank formats, human gold or independently reviewed truth.
The same assistant authored and weakly labeled them. The exposed development error
informed the coverage priorities; no old validation body was used as a template.
Do not claim independence from the earlier development process.

There is no business-name expansion or multiplication through amount substitutions.
The dataset focuses on event wording and contrasts. Exact raw text, per-field
evidence, explicit origin, authoring groups and false eligibility flags are kept
in each record. Own-account movements remain completed-but-excluded; a transfer
between unnamed account masks retains unknown ownership and direction. Uncertain
settlement does not acquire invented posted financial fields.

## Verification and reproducibility

```powershell
py -X utf8 -m training.corpus.coverage --check
```

Aggregate machine-readable inventory:
`data/reports/transactions/sms_coverage_batch_v1.json`.
Existing source-event reviews:
`data/annotations/sms_coverage_v1/source_event_reviews.json`.
Rules/provenance:
`config/contracts/sms_coverage_batch.json`.

The batch has zero detected normalized full-text or number-masked-text overlaps
with the2,120 old source rows and checked frozen/control bodies, and zero detected
protected merchant/related-brand matches. Either counterpart matching would block
the whole authored group. These are bounded checks, not proof of semantic isolation.
Every record remains `trainingEligible=false` and
`independentEvaluationEligible=false`; zero detected blocks does not grant admission.

207 Python tests, ten TypeScript suites and226 frozen active-engine cases pass.
Eight new safeguards check weak provenance, group/evidence/amount/currency integrity,
completion versus tracking, source bindings and whole-group quarantine. Student
and merchant-model inference are explicitly forbidden during preparation. Bound
inputs are preserved under the existing deduplicated private snapshot system.

## Follow-up experiment — completed once2026-10-27

The original A/B is finished and must not be rerun. The owner approved this follow-up with go on2026-10-27:
**one word-only follow-up, two fits total**, retaining the existing feature math
and fixed solver settings. Character features showed no benefit and24x larger export.

Select the944 original completion candidates plus70 new definite completion/non-
transaction targets:1,014 total (549 completed/465 non-transaction). Skip the four
new uncertain-completion messages in that binary head. Direction selects321 original
targets plus50 completed/resolved new targets:371 total (218 incoming/153 outgoing).
Own-account not-applicable and unresolved direction never become physical-flow
targets. Known direction can still be supervised when amount/ownership prevents
recording; it must not turn a review into automatic inclusion.

Give each old source expression total weight one per head and each new bilingual
scenario total weight one per head, not one per translation. Preserve all old blocks
and source groups. Freeze a new experiment/cohort manifest rather than editing
the old contract, candidate models or attempt ledger. Do not change original data
eligibility flags to implement this research-only selection.

Batch SHA256:
`18ca9e8b943a484ddab90b0f1536d3fed43d546b2d148a3e484591bdf02d409f`.
Coverage report SHA256:
`9830e7dbfc3b4ff29cf640c8a9dcb6ac7f1009931fe71fe726969020ee31acc0`.

Evaluation keeps the same18 weak validation representatives/four direction labels,
with feature/vector/score/head parity before metrics. Report its adaptive, exposed
development status openly; a better score will not establish real-world accuracy.
Only the specified two follow-up head fits are now approved. Independent final
testing, promotion or tester integration remains outside this approval. Useful real-world reliability still
requires fresh source-confirmed evaluation evidence.

## Follow-up results

The owner approved the specified follow-up with go; exactly two heads were fitted
once, with no parameter, feature or threshold search. New experiment protocol:
`config/experiments/sms_semantics_followup_v1.json`; producer:
`training/transactions/semantics_followup.py`. The original A/B and authored batch
remain unchanged, and the feature/solver/browser contract is reused without edits.

| Exposed development measure | Original word candidate | Follow-up word candidate |
| --- | ---: | ---: |
| Completion labels matched | 18/18 | 18/18 |
| Incoming/outgoing labels matched | 3/4 | 4/4 |
| Arabic-containing completion | 10/10 | 10/10 |
| Arabic-containing direction | 1/2 | 2/2 |

The only changed validation prediction is `synthetic-v1-0750`, the Arabic cash
withdrawal: incoming becomes outgoing. There are no changed completion decisions.
This is a useful development improvement after adaptive gap filling. Four completed
validation examples cannot establish unseen-message accuracy, and no independent
test or promotion occurred.

The completion view has1,014 rows and101 total expression/scenario weight units;
direction371 rows and38 units. New translation counterparts each receive0.5,
preventing bilingual copies from counting as independent scenarios. The local
cohort index addresses a concatenated source view; each row separately records
the original artifact/index, leaving all original dataset indices/folds intact.

The saved export is
`data/models/sms_semantics_followup_v1_word_candidate.json` (30,772 bytes).
It shares the frozen standalone browser scorer from the original A/B; there is
no duplicate browser implementation or active-tester change. On1,037 texts
(1,014 train,18 validation,five controls), both heads' normalized features,
active vectors, scores and decisions match Python/TypeScript/browser-compatible
VM exactly. Sklearn/export training-score gaps are at most1.34e-15. Both heads
converged (five/four iterations), without another fit.

Report, source-bound cohort and immutable attempt ledger are under
`data/reports/transactions/sms_semantics_followup_v1*`. Reproduce with no fitting:

```powershell
py -X utf8 -m training.transactions.semantics_followup --check
```

That check was verified with the fitter patched to fail if called. The ledger
prevents another training attempt.214 Python tests, ten TypeScript suites and226
frozen active-engine cases pass. Seven new safeguards cover exact selection,
source indices/folds, unchanged validation, bilingual weights, whole-group
quarantine, head-specific eligibility and repeated-fit refusal. Canonical
eligibility flags, active weights, tester and mobile code remain unchanged.

## Try the saved model in the tester

The optional comparison is implemented in `tools/browser/tester.html`. Refresh
that page, then expand **Try the trained model** in the Analysis panel and paste
a message or select a sample. The model initializes and predicts only while this
panel is open. Editing, clearing, closing or reopening cannot reuse a stale result.

**Model prediction** and **Money flow** come directly from the saved follow-up
export. Direction is hidden as not applicable for a predicted non-transaction.
The amount row and message-only recording check come from the existing detailed
assessment, visibly separate from learned heads. Ownership confirmations remain
in their own panel and cannot alter the text-only model. The current legacy
output remains unchanged. The comparison exposes no confidence percentages;
uncalibrated decision scores are available only under Model details.

`tools/browser/sms_research.py` checks the frozen candidate/runtime/source hashes
before embedding them. `sms_research.js` contains only UI handling; feature/scoring
logic is the same source-derived frozen browser runtime. No fetch, persistence,
training, model promotion or network connection is added. The generated page works
directly from a local file. Rebuild with:

```powershell
py -X utf8 tools/browser/build_tester_ui.py
```

The builder preserves Unicode separators in embedded JavaScript strings by
splitting only actual file newlines.216 Python tests,11 TypeScript suites and226
frozen cases pass, including real built-page handlers/score parity, opt-in behavior,
non-transaction/empty/error handling, unchanged legacy output, sender/contact
independence and ownership separation. Headless Edge clicks/edits at1440px and390px
passed with no page errors or horizontal overflow. Private screenshots/checks are
under `.local-backups/sms_research_tester_v1/`. This is manual development testing,
not independent evaluation or an active-model replacement.

## Manual-style challenge review,2026-10-27

After the owner authorized trying the comparison,24 assistant-authored messages
were exercised through real Edge input events in the built page. Expected weak
judgments were frozen **before inference** in
`.local-backups/sms_research_manual_v1/cases.json`. These are12 bilingual scenarios,
not genuine bank SMS, independent human labels or24 independent source families.
They remain diagnostic-only: no training/evaluation admission or model fitting.
Exact UI outputs, input/model/page hashes and linear feature contributions are
saved beside the cases in `results.json` and `summary.json`.

| Completion scenario | Matched expectations |
| --- | ---: |
| Completed cash withdrawal | 1/2 |
| Credited refund | 2/2 |
| Settled foreign-currency purchase | 2/2 |
| Incoming transfer, ownership unknown | 2/2 |
| Completed own-account transfer | 2/2 |
| Completed bill payment, amount missing | 0/2 |
| Declined transfer | 1/2 |
| Ordinary personal money request | 2/2 |
| Pending payment | 1/2 |
| Purchase confirmation code request | 2/2 |
| Explicitly quoted example, not a notification | 0/2 |
| Unconfirmed authorization hold | Not scored as binary truth;2 require uncertainty |

The raw completion head matches15/22 definite expectations: **four false completed
predictions** (Arabic declined transfer, English pending payment, both quoted
examples) and **three missed completions** (Arabic withdrawal and both bills with
missing amounts). The two unsettled holds are not forced into binary truth.
The earlier18/18 development result did not establish broad recognition.

Raw direction matches10/10 direction-checkable completed examples. The UI displays
only7/10 correctly because three correct direction predictions are suppressed by
wrong completion rejection. Own-account direction is not scored against a binary
incoming/outgoing head; ownership exclusion is a separate responsibility.

The displayed existing message-only recording check agrees with13/24 weak recording
expectations. Many differences are conservative reviews, but **both quoted examples
are incorrectly marked Include**. It also misses several completion/owner-role
expressions. These are distinct from the raw learned-head errors and must not be
hidden by combining their scores or reporting a single accuracy percentage.

All displayed model scores match the saved Python model exactly, with no page
errors. This is a recognition/coverage problem, not browser/TypeScript numerical
drift. The full unit/compatibility suite remains216 Python tests,11 TS suites and226
frozen cases; those passing checks do not mean these new semantic expectations pass.
No implementation, labels, thresholds, exports or original holdout records changed
during this review. Existing model/experiment/source hashes remain pinned.

The failure analysis supports a focused completion-recognition milestone:

1. Teach status context and negation, with balanced completed versus
   declined/pending/quoted/conversational contrasts in both languages. Generic
   financial words must not outweigh explicit failure or example-only context.
2. Preserve completed status when a receipt omits an amount; recording can still
   require review. Do not make amount presence a substitute for completion.
3. Treat quoted/example false inclusion in the existing assessment as a separate
   safety defect. Repairing that path must not be described as improving the
   learned classifier.
4. Keep the direction model and all original datasets/results frozen as references.
   These24 cases are now exposed development diagnostics, not a new independent
   test or a license to tune the threshold until they pass. A model feature/data
   change needs a separately specified, owner-approved research trial.

The optional comparison is useful for finding failures; the candidate is **not
ready for automatic recording or promotion**. More category training, layout work
or repeated-business expansion would not address these completion errors.

## Completion context experiment, 2026-10-27

The owner's next “go” authorized the scoped completion improvement. One logistic
completion head was fitted with fixed word unigrams, bigrams and trigrams and the
original normalization, solver settings and zero decision boundary. This changes
both representation and training coverage; the results cannot attribute a gain
to word sequences alone. There was no parameter search, threshold adjustment or
second fit. The follow-up direction head, original data, earlier experiments and
active engine remain unchanged.

`data/training/authored_sms_context_v1/scenarios.json` was frozen before fitting:
48 training messages in 12 bilingual contrast groups and 24 separate probes in
six other groups. Each group has a completed and nontransaction counterpart in
both languages. Training contrasts cover refusal, pending versus settled,
examples/quotes, personal claims, OTP versus completion, reminders, withdrawals
and completed payments without amounts. Each four-message training group shares
one unit of weight; the original 1,014 rows and their weights are retained, for
1,062 training rows. Probe groups and the previous 24 manual cases never enter
fitting or vocabulary construction. Checked exact/normalized/number-proxy and
protected-alias overlaps are zero; these are bounded checks, not semantic
independence guarantees.

All new labels are assistant-authored weak judgments, with production training
and independent-evaluation flags still false. The same author designed both
contrasts and probes after seeing the earlier failures. The probes are held out
from this fit, but **are not independent real-world test evidence**.

| Completion check | Word reference | Context candidate |
| --- | ---: | ---: |
| Previously exposed validation | 18/18 | 18/18 |
| Earlier manual challenge, definite cases | 15/22 | 17/22 |
| False acceptances in that challenge | 4 | 4 |
| Missed completions in that challenge | 3 | 1 |
| Separate authored probes | 12/24 | 18/24 |
| False acceptances in those probes | 2 | 0 |
| Missed completions in those probes | 10 | 6 |

The two uncertain manual holds are excluded from binary truth, as before.
The context candidate fixes five manual cases: Arabic withdrawal, both missing-
amount bills, English pending payment and the English quoted example. It also
introduces **three regressions**: the completed foreign-currency English purchase
is rejected, and the English declined transfer and Arabic purchase OTP are
accepted. Arabic declined transfer and Arabic quoted example remain false
acceptances. Manual completion matches are 8/11 Arabic and 9/11 English;
the separate probes match 9/12 in each language. Six probe misses are completed
withdrawals, missing-amount payments and approval-completed messages, in both
languages. Short sequences have not solved general completion context.

The saved export has 1,854 completion features, converged in six iterations, and
is 128,230 bytes. Export scores differ from the fitted solver by at most
9.33e-15. All 1,133 training/development/control texts have exact normalized
features, active indices, scores and predictions across Python, TypeScript and
the source-derived browser runtime. The direction head is identical, as are its
outputs on all 1,133 texts; its earlier four validation targets still match.
This is no device/Hermes performance measurement.

Protocol: `config/experiments/sms_completion_context_v1.json`. Model and browser
bundle: `data/models/sms_completion_context_v1_*`. Frozen attempt and results:
`data/reports/transactions/sms_completion_context_v1{,_attempt}.json`. Reproduce
the checks with `py -X utf8 -m training.transactions.completion_context --check`;
the immutable attempt ledger rejects another fit. All three experiment checks
were also run with fitting patched to fail, confirming no hidden refit.

To compare in `tools/browser/tester.html`, expand **Try the trained model** and
choose **Word sequences · experimental** under **Research model**. **Word
reference** stays the default, including after reload. Changing the selector
does not change the active engine, existing recording assessment or ownership
decisions. No storage, network, fitting or automatic model promotion was added.
The page explicitly discloses the known OTP false acceptance.

Verification: 222 Python tests, 11 TypeScript suites and all 226 frozen cases
pass. Real Edge input events checked both selections on all 24 manual messages
against frozen scores. Desktop/mobile widths 1440/390 have no horizontal overflow
or page errors; selector/reload/empty/closed-panel behavior passes. Private browser
proofs are under `.local-backups/sms_completion_context_v1/`. These regression
passes do not erase the semantic failures above.

**Decision:** retain both candidates only for research comparison. Do not replace
the active classifier, declare general Arabic reliability, or run another trial
by tuning these exposed failures. At this experiment's freeze, both explicitly
quoted examples were still Include in the existing assessment. The separate
correction below resolves that recording-path defect without improving these
frozen learned heads. A subsequent fit needs a concrete scope for contextual
evidence beyond this bag of short sequences.

## Explicit-example recording correction, 2026-10-27

The owner authorized fixing the separate recording assessment. Shared structural
evidence version 1.0.6 extends explicit example introductions in Arabic/English;
ordinary quotes and quoted merchant names are not rejection evidence. Both
original `quoted-example-ar/en` now return nontransaction/exclude with no extracted
transaction fields. Mixed actual/example evidence and multi-sentence quoted
completion conflicts conservatively require review. This is bounded introduction
recognition, not a full quote-scope parser; see the policy in
`docs/TRANSACTION_BEHAVIOR.md`.

The 436-input before/after comparison changes only those two assessments. All
436 legacy caller results and six saved learned-model/browser artifacts remain
unchanged. The original word/context completion scores and their known OTP,
decline and quote failures are unchanged. No fitting, automatic promotion or
test-data admission happened. The old manual tracking-decision comparison improves
from 13/24 to 15/24 weak matches, entirely through the structural change. These
counts compare tracking decisions, not all expected extracted fields.

`tests/fixtures/quoted_example_cases.json` contains 14 authored conformance
contrasts; three numeric scripts and two sender/contact settings produce 84 full
Python/TypeScript/built-browser comparisons. Real Edge inputs verify all 14 under
both research selections, with no page errors. Private before/after and browser
proofs are in `.local-backups/quoted_examples_v1/`.

Historical trials bind the old structural rule bytes. Their original reports,
models and producer sources remain frozen. Replay them in a temporary tree of
checksum-verified recorded inputs, rather than changing old measurements to match
the current rules:

```powershell
py -X utf8 -m tools.evaluation.replay_sms_research sms_semantics_ab_v1
py -X utf8 -m tools.evaluation.replay_sms_research sms_semantics_followup_v1
py -X utf8 -m tools.evaluation.replay_sms_research sms_completion_context_v1
```

Each command invokes only the original `--check` path, never training. All three
checks pass. The original 23 model/follow-up/validation safeguards also run from
their exact source snapshots through the current test entry points; none were
removed or relaxed. Direct historical checks against the live repository can
correctly reject changed rule/test-source hashes; use replay for old results.

The complete current suite passes: 226 Python tests, 11 TypeScript suites and
226 frozen compatibility cases. The tester rebuild is byte-identical. This does
not change the learned-head error counts reported for the context experiment.

## Proposed pretrained completion benchmark, 2026-10-27

**Executed 2026-10-28 after explicit owner approval; continuation gate FAILED.**
The proposal below remains the pre-run design. Results and reproducible settings
are in `data/reports/transactions/sms_completion_encoder_v1.json`, its immutable
`_attempt.json`, `data/models/sms_completion_encoder_v1_candidate.json`, and
`training/transactions/completion_encoder.py`. The producer refuses another fit
once any attempt/result exists. Its default command is tokenizer preflight only;
`--run` consumes the single-fit budget. Do not delete the ledger to retry.

| Exposed weak diagnostic | Previous context correct | Frozen encoder correct | Encoder FP / FN |
| --- | ---: | ---: | ---: |
| Old validation | 18/18 | 15/18 | 3 / 0 |
| Manual definite cases | 17/22 | 20/22 | 1 / 1 |
| Authored context probes | 18/24 | 19/24 | 2 / 3 |
| Quote controls, definite only | 6/10 | 7/10 | 2 / 1 |

Do not pool these cohorts: two quote controls duplicate manual messages; two
manual and four quote cases have uncertain truth and are excluded from binary
counts. All are exposed development diagnostics, not independent accuracy.
The encoder gets 11/11 Arabic manual cases, but only 9/12 Arabic context probes
and 3/5 definite Arabic quote controls. Arabic capability remains uneven.

The three new old-validation false completions are ordinary chat: a claim about
sending dinner money, asking whether a transaction finished, and requesting a
receipt/screenshot. New probe false completions include an English uncompleted
cash receipt and an illustrative example. The manual English quoted example
also regresses against the context reference; an actual foreign-currency
purchase remains missed. Arabic probe misses include two previously correct
completed examples. These failures rule out automatic student training or
promotion under the agreed gate, despite improvements elsewhere.

Reconstruction verified 1,062 rows, 573 positive/489 negative and 113 unit-weight
groups against the predeclared training-view hash. All 1,142 tokenizer inputs
fit; maximum 56 tokens with no truncation. Pinned safetensors SHA verified;
actual weights 470,641,600 bytes. Isolated Python 3.12 environment and dependency
lock, tokenizer assets/hashes, preflight, vector cache/bindings remain ignored
under `.local-backups/sms_completion_encoder_v1/`. No SMS upload took place.
The classifier converged in five iterations in its single fit. Ordered float64
export differs from solver by at most 5.33e-15; all 80 saved diagnostic scores
were independently reconstructed from cached vectors and flat weights exactly.
Repeated encoding of the first batch was byte-identical and all vectors finite.

CPU encoding of all inputs took 23.76 seconds with batch size 16/two threads;
ten warm single-message calls measured 29.36–46.69 ms, excluding load/download.
These are local research observations, not Hermes/mobile performance. Peak
resident memory and total dependency download bytes were not captured; model
and tokenizer asset sizes are recorded, so no complete resource-budget claim
is supported. The encoder and classifier remain outside the tracker/tester.

Next: inspect the failure contrasts and propose a bounded revision based on
evidence, including whether this generic sentence encoder suits the task.
No additional model/threshold search, fitting or student is authorized by this
failed experiment. Keep the negative result and all older artifacts intact.

**Recommendation: test a frozen multilingual encoder in Python before building
another deployable model.** Then consider a compact sequence student only if that
comparison clears the proposed continuation gates. This task produced a design,
not a new trained model, download or runtime change. The reviewable settings are
in `config/experiments/sms_completion_encoder_v1.json`; status is proposed, owner
approval is null and authorized fits are zero until that scope is approved.

The last trial added useful local sequences but still accepts four manual
nontransactions, including an Arabic OTP, and misses six completed probe messages.
Its 1,062 rows share **113 weighting groups**, all synthetic/assistant-labeled;
these are not 1,062 independent language examples or 113 independent real SMS
sources. Counts and unit group weights were independently reconstructed before
writing this proposal. Current normalized word lengths are median 19, 95th
percentile 26, maximum 32. These are word counts, not transformer token counts.

| Approach | Why consider it | Main problem here | Decision |
| --- | --- | --- | --- |
| More sparse word/character features | Already portable and cheap to fit | Measured word-sequence trial has critical regressions; another local feature tweak does not bring pretrained language knowledge | Retain as references |
| Tiny bidirectional GRU trained from scratch | Reads order across a sequence; flat weights and plain-JS inference are feasible design goals | Still has to learn Arabic/English semantics from the same small set of related messages; new training/export/latency work with no quality evidence | Defer |
| Frozen pretrained multilingual encoder plus one supervised linear head | Imports pretrained language representation while fitting very few task-specific parameters | Generic sentence semantics may still miss negation/quotation scope; larger research environment and model cache | Recommended first comparator |
| Ship a pretrained transformer directly | Avoids student compression | The selected weights alone are approximately 471 MB; no compatible small flat-weight runtime or Hermes latency evidence | Outside this scope |

These are project-specific engineering judgments, not comparative accuracy
results. The [GRU paper](https://arxiv.org/abs/1406.1078) motivates sequence
representations; it does not show that a small GRU will solve this SMS task.
PyTorch's [GRU documentation](https://docs.pytorch.org/docs/main/generated/torch.nn.GRU.html)
also warns that its candidate-state equation differs from the original paper;
a future Python/TypeScript student must choose one exact equation, not mix them.

### Selected research representation

Use `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`, pinned to
revision `e8f8c211226b894fcb81acc59f3b34ba3efd5f42`. The publisher lists Arabic and
English and documents 384-dimensional mean-pooled embeddings with a default
128-token limit. Its card declares Apache-2.0; the published safetensors file is
approximately 471 MB. Record actual bytes and verify the pinned checksum before
use. Sources: [publisher model card](https://huggingface.co/sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2/raw/main/README.md),
[revision metadata](https://huggingface.co/api/models/sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2),
[weight file](https://huggingface.co/sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2/blob/main/model.safetensors).

Freeze the encoder: evaluation mode, CPU float32, no gradient updates, attention-
mask mean pooling. Reuse the existing research normalization exactly, so only
representation changes against the context trial; do not silently introduce raw
text, new prompts, lowercasing choices or a different data batch. The model's own
default preserves case; retaining our existing lowercasing is a deliberate
controlled-input compromise, not a claim that it is optimal for this encoder.
Apply no embedding normalization, scaling or feature selection. Cache vectors
with input/tokenizer/encoder/normalizer hashes for reproducibility.

Preflight tokenizer lengths for every train/scored diagnostic input. Preserve
the published 128-token limit, including special tokens, and **never truncate a
tail that might deny or qualify the transaction**. If any input overflows, stop
before fitting and report it. Do not silently exclude its group, change its label
or increase the limit. Short word counts do not establish that this preflight
will pass.

This is a **Python research comparator outside every runtime engine**, not a
replacement SMS export. A flat classifier head without the encoder is not a
working SMS model. Existing Python/TypeScript/browser runtime parity remains
required and unchanged. No teacher scores enter the tester or recording policy.

### One fixed comparison

Keep the exact prior 1,062 training rows, 573 completed / 489 nontransaction,
and all 113 group-weight units. Train no direction, entity, ownership or category
head and author no new data. The protocol binds the reconstructed training view
and original artifacts; old preparation functions must be used through recorded
sources because live structural rule hashes have advanced.

Fit **one** weighted logistic completion head on the 384 frozen features, with
the existing liblinear C=1, seed, tolerance and iteration limit. Use a zero signed
decision boundary, negative ties, no calibration, no parameter search and no
automatic second attempt. Persist the attempt ledger before fitting. Record
dependency versions and finite embedding checks. Export the head with exact
encoder/tokenizer/pooling bindings and verify ordered float64 dot-product scores
against the solver. The current Python environment has NumPy/scikit-learn but
no PyTorch/Transformers/tokenizer runtime; use an isolated environment, not changes
to the working engine setup. Dependency downloads are additional to the weights;
no installed compatibility or training-time claim is made in advance.

Evaluate the same exposed 18 validation representatives, 24 manual diagnostics
(two uncertain holds excluded from binary truth) and 24 authored probes. Report
the 14 exposed quote controls separately, skipping uncertain truth and explicitly
identifying duplicated manual examples rather than counting them as new evidence.
Compare both frozen word and context references per case, per language and per
contrast, not just a pooled accuracy. Keep structural quote rejection separate
from raw learned-head results. Scores are uncalibrated; no certainty percentages.

The proposed **research continuation gate** requires zero false completions on
each definite development cohort, no additional misses versus the context
reference in each primary cohort/language slice, and no new OTP/refusal/chat
acceptance versus either reference. Inspect individual case swaps. Failure means
retain the negative result and stop; it does not trigger another encoder, fit,
threshold adjustment or automatic data generation. These gates guide whether to
consider student research; `releaseThresholds` stays null and no final test or
production promotion is authorized.

### Conditional compact student

Only after a useful comparator result, specify a separate compact sequence
student experiment. A small bidirectional GRU with word/punctuation tokens is a
candidate to assess, not a selected architecture or authorized fit. If teacher
soft targets are used, retain their weak provenance; do not overwrite human
decisions, manufacture independent gold, or let held-out inputs teach the student.
Group weighting, uncertain truth, vocabulary boundaries and all teacher/student
training folds need a new fixed contract.

Before any runtime migration, that student needs aligned flat-weight export,
Python/TypeScript/built-browser token/vector/score tests, and real Hermes size,
memory and latency measurements. Keep the under-0.10-ms requirement as an
unmeasured constraint; no source or calculation here establishes it. Distillation
is not guaranteed to retain the comparator's behavior. If it fails those gates,
retain the current runtime. The current model cards describe sentence similarity,
not verified SMS completion or Jordanian dialect accuracy; the benefit proposed
here remains a hypothesis to measure.
