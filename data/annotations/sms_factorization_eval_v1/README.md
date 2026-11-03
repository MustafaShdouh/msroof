# Factorized development annotations

`development_reviews.tsv` contains 32 manually reviewed, same-assistant weak
context/event labels on the existing scope **development** fold.
`development_annotations.jsonl` binds exact original Unicode evidence spans.
Original texts and completed/nontransaction/uncertain statuses are unchanged.

These rows are evaluation-only, with no training weight or canonical admission.
They must never enter the proposed 1,177-row training view, vocabulary fitting,
class balancing, gradients or checkpoint selection. There is no reserved-fold
component annotation here and no model inference was used to create these labels.
Existing development predictions were already exposed; this is not human gold
or independent accuracy evidence.

Context support: 18 financial-notice, six question/request, four instruction/
example, two conversational and two unknown. Known-other has no examples.
Event-state support: 12 completed, four not-completed and 16 unknown; no-event has
no examples. Report absent-class accuracy as unsupported, not zero or perfect.

The same fixed research projection matches all 32 original overall statuses;
that is label consistency, not a successful classifier result. See
`docs/SMS_FACTORIZATION_EXPERIMENT.md` and
`config/experiments/sms_factorization_comparison_v1.json` for the proposed
paired experiment. No training is authorized by this annotation file.
