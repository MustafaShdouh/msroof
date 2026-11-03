# Adaptation error review — 2026-10-28

The adapted encoder improves several diagnostics but still fails the completion
gate. The remaining nine distinct failing messages comprise one false completion
and eight missed completions. This review retains all existing labels, which are
still assistant-authored weak labels. No training, new model inference, threshold
search, ensemble selection or reserved-fold access was performed.

Reproducible machine evidence:
`data/reports/transactions/sms_completion_adaptation_v1_error_review.json`.
Run `py -X utf8 -m tools.evaluation.review_sms_adaptation_errors` to reconstruct
the same result from the frozen scores and input texts. The analyzer rejects
source/protocol drift and requires the exact nine-case inventory.

## Retained label review

| Failure pattern | Cases | Why the existing label is retained |
| --- | ---: | --- |
| Question accepted | 1 | “did you finish the transaction?” asks for information; it does not report an account movement |
| Posted ATM deposit rejected | 1 | The message explicitly says funds have been credited as an ATM deposit |
| Settled foreign purchase rejected | 1 | The USD purchase is explicitly debited and settled; the JOD amount is an available balance |
| Arabic completed payment rejected | 1 | “لم يعد الطلب معلقاً” says the request is no longer pending; it does not negate the preceding finished debit |
| Shop names treated as example instructions | 2 | The control language is inside the merchant name after “at”/«لدى»; the message states a debit |
| Completed incoming pay rejected | 3 | One Arabic salary and two bilingual wage messages explicitly report booked or available funds |

No amounts, party names or field-extraction labels were changed. A completed
event can still require review for missing amount or unknown transfer ownership.
Classifying notification wording also does not establish sender authenticity.

The ATM deposit and English shop-name cases are new regressions against the
frozen encoder. The question, foreign purchase and other listed misses already
failed that reference. The Arabic completed-payment and Arabic wage-credit cases
are wrong in all four models (word, word sequences, frozen encoder and adapted
encoder). Simple voting cannot recover those two cases from their existing
binary outputs. Selecting whichever model happens to be correct on each exposed
case would be an oracle, not a validated prediction method.

## What training coverage establishes

Literal queries over the exact 1,158-row training view find:

- 36 messages with a question mark across 13 groups, all labeled nontransaction.
- Two USD messages in one bilingual group, both completed.
- Eighteen new shop-name scope messages in three groups: 12 completed and six
  nontransaction. Uncertain messages were excluded from fitting.
- No literal English word “wage”. This does not establish that equivalent pay,
  salary or incoming-credit meanings are absent.

The model had relevant question and shop-scope supervision, yet failed related
diagnostics. That weakens the explanation that those entire themes were simply
missing. The small USD group shows narrow coverage; it does not prove currency
caused the foreign-purchase error. More merchant names, numeric substitutions or
copies of the failed test messages are not a justified next step.

New scope examples deliberately contain no numeric amounts, whereas the older
training view includes many bank-format messages. This is a distribution
difference worth controlling in a future experiment. It is not evidence that
amount absence alone caused misses: several unpriced completions are accepted.

## What remains uncertain

The task still combines two different questions into one binary training label:
what kind of message this is, and what event state it describes. A teaching
example or personal claim can describe a completed transfer while remaining
ineligible for transaction detection. Conversely, a completed payment can
contain negated words such as “not pending” or a merchant called “Teaching
Example”. These distinctions need scope; spotting financial or negative words
does not settle them.

The error pattern is consistent with incomplete learning of those distinctions,
but does not identify a single cause. This run changed both training data and
encoder parameters. It does not separate effects of limited weak supervision,
normalization, mean pooling, optimization or adaptation. Falling training loss
and valid checkpoint math do not demonstrate generalization.

Scores use different scales across models and are not confidence percentages.
Do not interpret the changed magnitudes as stronger certainty. There is also a
direct obstruction to fixing everything with one new threshold on the adapted
scores: the nontransaction question scores +0.984, while the completed USD
purchase scores −3.209. Accepting the latter and rejecting the former cannot
both be achieved by shifting the same positive-above-threshold boundary. No
threshold sweep was performed.

## Recommended next step

Pause additional fitting and prepare **factorized supervision** on existing
training data: separate labels for message context and the event state described
inside it. This is a proposed modeling direction, not a proven improvement.

| Proposed field | Candidate labels | Example distinction |
| --- | --- | --- |
| Message context | financial notification; personal conversation; question/request; instruction/example; unknown | A quoted debit inside a lesson is an example, not a notification |
| Described event state | completed; not completed; unknown | A lesson may describe a completed debit, while a genuine notification may report a refused payment |

The existing `eventMention`, `messageContext` and `scopeQualifier` spans in the
scope batch support reviewing these distinctions; they are not already these
new categorical labels. They must not be mapped automatically from keywords or
model predictions. Define how context covers the event mention, how uncertain
cases are held, and how contradictions are represented before training a head.

The next bounded deliverable should define that annotation contract and audit
its applicability across the 129 existing training groups. Prepare a small
training-only pilot with explicit evidence and unresolved cases; report which
groups need a source-level review before this can become a training view. Do not
relabel development failures into successes, admit validation cases to training,
or change the original reserved split. A future architecture/compute protocol
would need its own fixed budget and approval after those labels are reviewable.

Keep the remaining 32 reserved messages unscored. The teacher is still research
only and needs its full base model; compression cannot be justified by the
failed quality gate. No new model, automatic ensemble, calibration, student or
runtime change is authorized by this review.

The original run's memory-monitor defect remains documented in
`sms_completion_adaptation_v1_resource_audit.json`. The corrected future monitor
does not retroactively verify historical memory use. That caveat remains separate
from this inspection of saved, reproducible numerical results.
