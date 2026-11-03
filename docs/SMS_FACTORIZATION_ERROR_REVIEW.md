# Saved comparison error review — 2026-10-28

The current context/event candidate should not replace the direct-status research
baseline. On 98 unique primary diagnostic messages it fixes four direct errors,
introduces eleven regressions, leaves four cases wrong in both, and agrees on
79 correct cases. The unchanged 17/18 validation totals conceal an Arabic
regression and an English fix. These are exposed weak diagnostics, not population
accuracy or proof that factorization cannot work.

The review uses saved predictions and existing labels only. No encoder was
loaded, no new prediction made, no truth changed, and no reserved set scored.
Producer: `tools/evaluation/review_sms_factorization_errors.py`; reproducible
evidence: `data/reports/transactions/sms_factorization_comparison_v2_error_review.json`.
It verifies original protocol/source bindings, text hashes and row alignment.
Three analysis safeguards pass: opposite swaps behind equal accuracy, duplicate
control handling, and correct status concealing a wrong component.

## What fails

**Uncertainty collapses into noncompletion.** All eight newer uncertain cases
receive event=`not_completed`. Five receive instructional context, one question
context, one financial-notice context and one unknown context. The last is the
only uncertain status retained; the direct model retains seven of eight.
Examples include an unconfirmed wage posting and an unavailable tuition-payment
result. Neither establishes refusal or a payment still pending. The frozen
event definition explicitly distinguishes an unspecified outcome from confirmed
noncompletion. Older authorization holds fail too: both models are wrong on
the Arabic hold; the factorized model additionally regresses on the English hold.

**Context mistakes run in both directions.** Quoted completed debits in explicitly
educational messages become real notices, producing false transactions. Conversely,
eight of eighteen newer financial-notice examples become instructions. Four of
these are genuine pending/refusal notices: their final negative status happens
to be correct despite the wrong context. A generic rule rejecting every example
word would be inappropriate because educational words can also occur in shop
names; existing party-name contrasts remain valid transactions.

**Negation scope remains shared work.** Both models reject the Arabic case saying
the debit finished and the request is *no longer pending*. The factorized event
head predicts noncompletion. This is consistent with a scope error; saved outputs
alone do not establish an internal causal explanation.

**A few fixes conceal other wrong fields.** The factorized model correctly rejects
the English accountant's request and both lesson-editor notes, improving three
newer statuses. However, those three event labels are wrong against existing
weak component truth. Across all 32 newer cases, only thirteen have both fields
correct; ten of the 23 correct statuses hide at least one component error.

Symbolically replacing only context with its existing weak truth yields 26/32
status matches; replacing only event yields 24/32, compared with saved 23/32.
These are label-substitution diagnostics, **not achievable performance estimates**.
They show that repairing only one component would leave errors; they do not
authorize truth-assisted inference or a new routing rule.

## Data and evaluation findings

The requested distinctions are already represented in training: instructional
context has twenty examples across seven groups; unknown context has eight
examples across four groups. Of 34 uncertain training rows, 26 are financial
notices with unknown event outcome, and eight have unknown context. Class
weighting does not establish sufficient semantic variety. The small support,
task-specific loss balancing, optimization and weak annotation boundaries are
plausible contributors; this comparison cannot isolate their causal effects.
The evidence does not justify adding repeated variants or merely increasing epochs.

An exact **and normalized** training/diagnostic overlap exists:
`quoteControls/qualified-en` duplicates training
`instruction-quote-non_transaction-en`. Both models answer it correctly. It is
a training-exposed conformance control, not an unseen-text success. No other
exact/normalized match was found in the scored diagnostic cohorts. This check
does not establish absence of template, paraphrase or family exposure. In
particular, all newer data remain authored weak diagnostics. The overlap does
not explain the separate manual/newer-development regressions.

Two quote controls also duplicate manual cases. Including quotes yields 110
unique scored texts: twelve regressions, four fixes, ten wrong in both, 84
correct in both. Do not pool the raw 112 cohort entries or call these independent
accuracy. Frozen report counts and gates remain unchanged.

Four quote controls use uncertain truth as a conservative mixed/multisentence
scope policy. For example, a clearly introduced teaching quote with two sentences
is marked for review under the current parser boundary. These targets measure
that policy, rather than solely whether a payment outcome is unspecified.
Do not relabel them retrospectively. Report this scope-policy slice separately
from unknown event outcomes and unresolved message frames.

## One bounded next revision

Prepare an **evaluation-contract revision before any more fitting**:

1. Add a reusable raw/normalized-content overlap preflight. Fail if a purported
   unseen diagnostic overlaps training. Explicitly identified in-sample controls
   may remain in a separate conformance slice; keep their exposure visible.
2. Give diagnostic uncertainty a reason field: unspecified event outcome,
   unresolved governing context, or conservative scope policy. Preserve existing
   raw texts, class targets, record IDs and historical scores. These metadata
   describe the evaluation contract; they are not new input features or human gold.
3. Retain the frozen direct-status model as the stronger research reference.
   Recompute only metadata/counts from saved outputs; no refit, threshold search,
   new examples, model integration, or reserved scoring in this revision.

This is evaluation plumbing, not a promise that it fixes the learned classifier.
After that revision, a future learning proposal can test whether final-status
supervision should remain primary while context/event fields serve as auxiliary
diagnostics. No such experiment or new training budget is approved here.

The final scope 32 and merchant 29 reservations remain uninferred. No app/tester
or shipped weights changed, and nothing was committed or pushed.
