# Diagnostic evaluation contract v1

Implemented 2026-10-28. This is a metadata view of saved development results,
not a new model, relabeling exercise or independent accuracy measurement.

`config/contracts/sms_diagnostic_evaluation_v1.json` binds the existing records
to uncertainty reasons and the single explicitly in-sample control.
`training/evaluation/content_preflight.py` provides reusable content checks.
`tools/evaluation/build_sms_evaluation_contract.py` applies them to the frozen
v2 comparison and creates `data/reports/transactions/sms_diagnostic_evaluation_v1.json`.

The view covers 112 cohort entries / 110 unique texts. One entry is explicitly
in-sample conformance: `quoteControls/qualified-en`, bound by exact text hash and
the matching training record ID. The other 111 entries are text-disjoint exposed
diagnostics. They are not independent or previously unseen real-world evidence.
Two manual/quote duplicate texts are listed explicitly. Slice counts refer to
cohort entries; do not add them as if all were independent samples.

## Content checks

Raw and research-normalized text are checked against training. Normalization
includes number replacement, spacing, case and Arabic mark handling, matching
the existing research pipeline. Therefore changing only an amount does not
avoid the check. Unacknowledged overlaps fail. In-sample exceptions require the
exact diagnostic text hash, all matching training IDs and a stated rationale.
Changed text, changed provenance and unused exceptions fail rather than silently
expanding the exception. Duplicate IDs, stale reason entries, unknown targets,
missing uncertainty reasons and reasons on definite labels also fail.

This guard runs in the new metadata builder and is available for future
experiment preflights. Historical hash-bound training producers remain unchanged;
this does not retroactively install safeguards into those old runners. Future
experiments must explicitly invoke the guard before fitting. Text disjointness
does not establish absence of related templates or paraphrases.

## Existing uncertainty, separated by reason

| Reason | Entries | Direct status correct | Context/event status correct |
| --- | ---: | ---: | ---: |
| Unspecified event outcome | 8 | 6/8 | 0/8 |
| Unresolved governing context | 2 | 2/2 | 1/2 |
| Conservative scope policy | 4 | 0/4 | 0/4 |

These scores use saved predictions only. Reasons describe the frozen targets:
they do not replace them, enter model inputs, or claim human adjudication. The
scope-policy slice includes the conservative mixed/multisentence review cases;
its errors must remain visible alongside semantic outcome/context uncertainty.

## Verification and continuation

Ten targeted safeguards passed: seven content/metadata tests, including the
112-record integration check, and three prior error-review tests. The builder
reproduces the saved report byte for byte. The original v2 checkpoint/metrics/
resource audit also passes, including reserved-set exclusion. No fitting, new
predictions, text/target edits, historical gate changes or publication occurred.

Run from the repository root using the existing isolated research environment:

```text
.local-backups/sms_completion_encoder_v1/env/Scripts/python.exe -X utf8 -m tools.evaluation.build_sms_evaluation_contract
.local-backups/sms_completion_encoder_v1/env/Scripts/python.exe -X utf8 -m unittest tests.python.test_diagnostic_evaluation tests.python.test_factorization_error_review
```

Keep the frozen direct-status model as the stronger research reference. The
next proposed task is a bounded learning protocol that keeps direct status as
the primary decision and considers context/event supervision as auxiliary,
using this evaluation contract. No such training or architecture change is
authorized by this metadata task. Neither existing candidate is deployable.
The 32 scope and 29 merchant-final reservations remain uninferred.
