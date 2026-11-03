# Context and event-state annotations

## Current completion status — full source review

The review phase is complete for the selected training sources. There are now
**1,194 source-bound annotations: 1,177 reviewed weak records and 17 holds**.
This is source labeling, not model fitting, canonical admission or accuracy
evidence. All six proposed context labels and all four event-state labels have
observed non-held examples, though some classes have very few source families.

| Separate annotation view | Records | Weak reviews | Holds |
| --- | ---: | ---: | ---: |
| Frozen research cohort | 1,158 | 1,143 | 15 |
| Existing training-designated uncertainty appendix | 36 | 34 | 2 |
| Total annotated union | 1,194 | 1,177 | 17 |

The earlier pilot and supplement results below are historical milestones. Their
files and all original labels remain unchanged.

### Frozen 1,158-row view

`remaining_queue.json` freezes the 1,122 previously unreviewed records. The
source-review producer shows exact base tokens plus **every record's raw
replacement strings**, with reconstruction checked character-for-character.
This saves repeated boilerplate without hiding names, words, digits or negation.
Every listed variant was inspected before its explicit row-bound assignment.
Bilingual authored texts were reviewed individually, not by inheriting the other
language's label. These are manual same-assistant decisions on explicit ID/hash
lists, not automatic family/keyword/model propagation to unseen records.

`source_review_log.jsonl` binds those explicit decisions to source packets.
`full_annotations.jsonl` reconciles them with the unchanged prior 36 reviews.
`data/reports/transactions/sms_factorization_v1_full.json` verifies all 1,158
records, all 129 groups, exact source hashes/spans and original completion labels.
There are **zero unreviewed records** in this view. All 15 cost fragments in one
group are held for unresolved context, leaving 1,143 weak records across 128
non-held groups. This cohort itself has no non-held unknown-context example;
that historical gap is not overwritten by the separate appendix below.

The non-held context counts here are 780 financial notices, 214 known-other,
65 personal conversations, 64 questions/requests and 20 instruction/examples.
Described states are 701 completed, 120 not completed, 170 no-event and 152
unknown. Ninety original nontransactions describe completed events, including
personal claims, quoted lessons and historical transfers mentioned by a reward
notice. Their old transaction targets remain negative.

Examples reviewed with explicit scope include login OTPs with no financial event
versus purchase/transfer OTPs with an unasserted outcome; loyalty awards that
refer to already completed transfers; pending messages versus merchant names;
and hypothetical posted statements versus actual execution. No text-only label
authenticates the sender or supplies missing amount/ownership facts.

### Separate uncertainty appendix

The old binary selection had excluded four uncertain authored-coverage messages
and 32 uncertain messages in the scope batch's proposed-training fold. These
already existed locally. They were reviewed separately in this task because
their uncertainty is relevant to the new fields. No development/reserved rows,
new generated examples or new model predictions were used.

`uncertainty_reviews.tsv` contains the manual field decisions and exact quotes;
`uncertainty_annotations.jsonl` contains validated spans and the unchanged
original `uncertain` target. The report is
`data/reports/transactions/sms_factorization_v1_uncertainty.json`. The original
1,158-row view, its weights and experiment artifacts are unchanged. This
appendix assigns **no training weights** and does not authorize a larger fit.

Eight non-held unknown-context annotations come from messages explicitly
withholding the financial/nonfinancial or example/notice frame. This is reviewed
semantic uncertainty, distinct from guessing the intent of the held cost
fragments. The forwarded-pension excerpts supply no underlying credit clause;
`no_event` describes their visible text, not invented content of an unseen SMS.
Two debit/cancellation conflicts remain held because final event focus cannot
be resolved. Neither annotation invents a chronology to remove that conflict.

The annotated union has 806 financial-notice, 214 known-other, 65 conversational,
64 question/request, 20 instruction/example and eight unknown-context weak
records. These are small related synthetic sources, not independent class
coverage or a real-world final test. No owner labeling task is pending; held
cases can remain excluded.

```powershell
py -X utf8 -m training.corpus.factorization_full --check
py -X utf8 -m training.corpus.factorization_uncertainty --check
py -X utf8 -m unittest tests.python.test_sms_factorization_full tests.python.test_sms_factorization_uncertainty tests.python.test_sms_factorization_supplement tests.python.test_sms_factorization_pilot
```

Next: define one fixed context/event-state training comparison using the reviewed
sources. It must explicitly select a new view, exclude holds, define supported
classes and normalize each group's weights after any uncertainty-row admission.
Do not append the new rows with old binary-view weights or treat these sidecars
as automatic training permission. The reserved diagnostics remain unscored.

The proposed contract is `config/contracts/sms_factorization_annotations.json`.
This folder contains a frozen training-only selection (`pilot_queue.json`), manual
weak interpretations (`reviews.json`), and validated Unicode evidence sidecars
(`pilot_annotations.jsonl`). The group-readiness inventory is
`data/reports/transactions/sms_factorization_v1_readiness.json`.

## Contract distinctions

| Field | Proposed values |
| --- | --- |
| Message context | financial_notice, personal_conversation, question_or_request, instruction_or_example, known_other, unknown |
| Described event state | completed, not_completed, no_event, unknown |

The original five/three candidate labels needed two explicit additions during
this source review: `known_other` for clear promotions/other purposes, and
`no_event` for a balance or price without a movement proposition. Clear absence
must not be confused with an unknown outcome. These additions are a proposed
annotation design, not a newly trained model or canonical output change.

`financial_notice` describes report-style wording, including refused transactions
and balance reports; it does not authenticate a sender. `completed` describes
the selected event in its frame: a friend or a teaching example can describe
completion without reporting an actual eligible account movement. A quotation's
governing scope and control words inside a party name require source review.

Do not automatically compose these two labels into a replacement for the old
completion target. In the pilot, a friend's “I sent my rent share” is completed
within a conversational claim while the existing transaction target stays
nontransaction. A completed own-account movement remains excluded under recording
policy. Missing amount and ownership decisions stay separate.

## Selection and review result

Selection was frozen before annotation. It chooses six groups from each of four
provenance strata by a fixed hash, then one hash-selected training record from
each group. No labels, scores or model predictions rank candidates. The 24
messages belong to 24 distinct training groups. Both the 32 reserved scope
messages and all development/final rows are excluded.

All 129 groups were inventoried for provenance, existing evidence and review
readiness: 66 legacy expressions, 35 authored coverage groups, 12 authored
context groups and 16 scope groups. **This is not semantic review of every row.**
Twenty-eight groups contain both completed and nontransaction targets, so even
an earlier constant completion label cannot be propagated across them.

The pilot has 23 reviewed weak records and one hold. The hold is
`synthetic-v1-0922`: “the bill was 72.6 JOD each”. It asserts no movement, but its
context could be discussion or a bill fragment. The review does not infer that
context from a legacy source label. It remains excluded, with an explicit reason;
no owner answer is required to leave it held.

| Pilot dimension | Counts, including the held record |
| --- | --- |
| Context | 20 financial notices; one conversation; one question/request; one known-other; one held unknown |
| Described event | 17 completed; three not completed; two no-event; two unknown |

The fixed pilot contains **no instruction/example**, and its only unknown context
is held. It therefore does not validate all proposed context classes. No cases
were substituted to hide that gap. There are 105 groups without a factorized
pilot review, 24 only partially reviewed groups, and 1,134 unreviewed training
records. One pilot record does not label its group or bilingual counterpart.

The first in-task annotation draft is preserved privately under
`.local-backups/sms_factorization_v1_draft/`. Final review changed the cost
fragment's provisional conversational interpretation to a hold. The selection,
raw text and all pre-existing completion labels remained unchanged. This was
annotation review, not a model-driven relabeling or a benchmark update.

## Boundaries and checks

Labels remain same-assistant weak supervision. No canonical training admission,
independent evaluation eligibility, fitting, inference, automatic propagation or
product integration is enabled. Unannotated fields are not semantic unknowns;
unknown is a reviewed message meaning, while a hold records unresolved review.
Evidence offsets use exact original Unicode code points, end exclusive.

```powershell
py -X utf8 -m training.corpus.factorization_pilot --check
py -X utf8 -m unittest tests.python.test_sms_factorization_pilot
```

## Completed 12-message coverage supplement

`supplement_queue.json` freezes a separate source-directed selection before
annotation. It hash-selects one eligible training family in each of three
declared themes, excluding original pilot families, then takes two source states
and both languages. This is targeted coverage selection, not a random or
label-blind sample; model predictions were not used. The selected families are
pension-demo, reward-credit and bookshop-pending. No new messages were generated.

Manual weak interpretations are in `supplement_reviews.json`; exact span
sidecars are `supplement_annotations.jsonl`. The audit is
`data/reports/transactions/sms_factorization_v1_supplement.json`. Existing pilot
artifacts, raw text, old targets and all diagnostic assignments are unchanged.

| Contrast | Annotation outcome |
| --- | --- |
| Pension notice versus demo quotation | Both describe completed credit; only the notice has financial-notice context |
| Cash reward versus loyalty points | Not points does not negate credited cash; the points update denies monetary credit |
| Pending Books versus pending settlement | The merchant's name does not make its recorded debit pending; a temporary hold without final debit is not completed |

The points message has `known_other` context because it is a noncash loyalty
update; that label is not the expense category Other. Its selected financial
proposition explicitly denies a cash credit, so the event-state review is
`not_completed`. A bare balance with no movement proposition remains `no_event`.
These are weak source-specific interpretations, not keyword-derived labels.

All 12 supplement records are reviewed weak: eight financial notices, two
instruction/examples and two known-other contexts; eight completed and four
not-completed described events. The combined 36 messages have **35 weak reviews
and the original one hold**. Instruction/example coverage is now present, while
there is still no unheld unknown-context example. That remaining gap is explicit;
no annotation has been fabricated to fill it.

There are now 27 partially reviewed training groups, 102 without a factorized
review, and 1,122 unreviewed training records. None of the 129 groups is claimed
fully reviewed. These 36 messages are not a training-ready factorized corpus.
All admission/fitting flags remain false; no inference or training occurred.

```powershell
py -X utf8 -m training.corpus.factorization_supplement --check
py -X utf8 -m unittest tests.python.test_sms_factorization_supplement tests.python.test_sms_factorization_pilot
```

That remaining source review is now complete; see the current completion status
at the top. The next modeling step requires a new fixed protocol. Preserve all
historical pilot outputs, ambiguity holds, diagnostic assignments and original
labels; neither this supplement nor the full review grants training permission.
