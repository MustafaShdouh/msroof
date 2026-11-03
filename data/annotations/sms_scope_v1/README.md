# Scope contrasts v1

192 short Arabic/English messages in 24 authored scenario groups. The source is
`scenarios.txt`; inline evidence marks are removed in the generated
`data/training/authored_sms_scope_v1/messages.jsonl`. `manifest.json` freezes the
split and review/evaluation policy. Preparation evidence is
`data/reports/transactions/sms_scope_v1_preparation.json`.

The assistant authored and reviewed these labels. They are weak supervision,
not received SMS, verified bank formats, human gold, or independent evaluation.
The owner delegated this review; no owner review is pending. Uncertainty is an
explicit retained label, not a negative training target.

| Proposed fold | Groups | Messages |
| --- | ---: | ---: |
| Training | 16 | 128 |
| Development | 4 | 32 |
| Reserved diagnostics | 4 | 32 |

Both languages and all four semantic states stay in the same group. All rows
remain ineligible for canonical training and independent evaluation. No model
has scored this batch, and fitting is not enabled. Reserved diagnostics require
a future frozen experiment protocol before inference; they cannot select
parameters, thresholds, or training examples.

The labels total 56 completed, 88 nontransaction and 48 uncertain. All uncertain
rows are held outside binary fitting/scoring. Event mentions inside quotes can
have exact `eventMention` spans while the full message is nontransaction;
`messageContext` and `scopeQualifier` explain the interpretation. Offsets are
Unicode code points with exclusive end positions. Ownership is not inferred.

Six themes cover personal claims, questions/requests, pending/settled states,
negated failures, illustrative quotations, and control words within party names.
The last four groups contain deliberate shop-name minimal pairs, with fictional
names, to test whether control words are interpreted at the correct scope. They
are not a list of real stores or a merchant-name augmentation pipeline.

These are completion/context diagnostics. They deliberately omit numeric
amounts and do not supply amount, direction, category or entity-extraction gold.
A completed label does not imply the record is ready for automatic logging.
Do not use this narrow batch as the sole training data for a financial tracker.

Exact/full-normalized/number-and-punctuation proxy checks against existing
training and fixture texts and the exposed manual challenge report no matching
full messages. Protected merchant validation/final aliases are also checked
without running any merchant model. The preparation report lists every checked
file and hash. A future change to those inputs can correctly invalidate checks;
preserve the historical report rather than refreshing it silently.

Source groups are new authored provenance IDs, not proof of new semantic
families. The themes intentionally revisit exposed failures; cash payout,
examples, and refusal contrasts have semantic relatives in earlier training.
The split therefore does not establish source-family independence from the
existing corpus. It is prospective synthetic diagnostics within this batch.
Short financial expressions and broad themes cross folds. No real-world
generalization or final-test accuracy claim follows from this split.

Rebuild/check without fitting:

```powershell
py -X utf8 -m training.corpus.scope_contrasts --check
py -X utf8 -m unittest tests.python.test_sms_scope_contrasts
```

Next: write one fixed, separately budgeted task-supervised adaptation protocol
using these reviewed contrasts and explicit uncertainty/admission rules. Keep
the failed frozen encoder and compact references intact. No fitting or model
promotion is authorized by the dataset itself.
