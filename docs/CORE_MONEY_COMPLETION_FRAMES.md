# R5a completion frames: first repair — 2026-10-31

The first safety repair excludes explicit reward-point postings and instructional
exercise headers from monetary completion evidence. It does not expand recognition
of genuine transaction paraphrases. R5 remains active; the broader coverage problem
is unresolved.

## Reviewed evidence

All 37 priority-one entries in the frozen R5 repair queue were read against their
source messages. Their existing expectations were retained: 29 nontransactions
and eight uncertain outcomes/contexts. The new review manifest binds queue hash,
cohort/record ID, raw-text hash, exact code-point evidence span/hash and rationale.
These are assistant reviews of exposed weak labels, not human gold, training
admission or independent evaluation evidence. Original labels and queue are intact.

The remaining failures include explicit denials, approval requests, conversation,
administrative notices and unknown outcomes that are incorrectly rejected. Their
review does not mean their recognition has been repaired.

## Runtime change

Shared `transaction_evidence.json` grammar 1.0.10 adds explicit noncash posting
phrases and instructional exercise/test headers in Arabic and English. Python and
TypeScript apply the same rules:

- Remove only the reward-point posting phrase before checking monetary completion.
  A separate cash credit in the same clause can still supply completion evidence.
  A noncash-only posting is excluded with `promotion_or_administration`.
- Route explicit comprehension/translation/grammar exercise introductions through
  existing reported-speech handling. A financial sentence within that frame is
  excluded. Existing conservative multi-sentence mixed-context review is retained.
- Keep amount, direction, ownership, recording policy and legacy model paths intact.
  No sender, bank, merchant or fixture-ID exceptions were introduced.

The optional browser tester was regenerated from canonical sources. Its layout
and public result contract were not changed. The historical frozen grammar 1.0.5
assertion remains; only the live-version assertion advances to 1.0.10.

This is bounded language coverage: other ways to describe points, quotations,
questions and cash movements can still fail. It is not a general quote parser or
a claim of complete Arabic understanding. Hermes performance remains unmeasured.

## Measurement

The new versioned fixture has 28 authored development cases: points/cash contrasts,
instructional/receipt contrasts, merchant-name traps and mixed/unknown controls.
Three digit scripts and two sender/contact variants yield 168 checks, not 168
independent examples. All asserted fields now match in all three runtimes:
**90/168 before → 168/168 after**. The amount-bearing instructional examples had
36 false includes before the fix, counting the six variants of each base case;
none remain in this pack. No completed-event miss was introduced there.

The same comparison rechecked all 238 original diagnostic entries:

| Cohort | Status agreement before | After |
| --- | ---: | ---: |
| Authored 74 | 21/74 | 22/74 |
| Scope development | 9/32 | 11/32 |
| Other diagnostic cohorts | Unchanged | Unchanged |
| Core cases | 51/51 status assertions; 52/52 asserted cases | Unchanged |

The two original false completions (reward points and English teaching exercise)
are now excluded, as is the corresponding Arabic teaching exercise. One English
points notice already excluded gains a more appropriate reason code. Those are
the only four original detailed-result changes. No previously correct expected
field regressed. The authored set still misses **43 of 54** completed cases.

Across all 406 entries, full Python/TypeScript/browser results agree. All legacy
results remain equal to their before snapshots. All 70 ownership requests retain
their full outputs in all runtimes; all 23 model artifacts are unchanged. No new
learned inference, fitting or reserved evaluation occurred.

## Reproduction and continuation

- Review: `data/reports/behavior/core_money_r5a_priority1_review.json`.
- Fixture: `tests/fixtures/completion_frame_cases_v1.json`.
- Immutable comparison: `data/reports/behavior/core_money_r5a_frame_repair.json`.
- Producer: `tools/evaluation/evaluate_completion_frames.py`; private complete
  before/after snapshots in `.local-backups/core_money_r5a/`.
- Safeguards: `tests/python/test_completion_frames.py`, including source/truth/span
  mutation rejection, numeric/metadata parity and rejection without learned scores.

Verification: the full runner passes **294 Python tests, 11 TypeScript suites and
226 frozen compatibility cases**. A fresh strict report,
`data/reports/behavior/core_money_v1_after_r5a_frames.json`, passes 52/52 asserted
cases in all three runtimes with zero parity mismatches. Three new tests cover
168 runtime variants and source-bound review safeguards. Historical reports remain
unchanged.

Next: write focused contrasts for the **34 remaining priority-one status errors**,
starting with explicit unknown outcomes versus explicit denials. Repair one
general boundary at a time, then remeasure the same exposed cohorts. The 68
completed-status misses and one remaining-field mismatch in the original queue
also remain pending. Never overwrite historical reports or silently admit reviewed
examples to training. No fresh fitting experiment is recommended yet.
