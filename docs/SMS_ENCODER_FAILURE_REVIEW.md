# Frozen encoder failure review — 2026-10-28

The completed benchmark does not justify deployment or distillation. It improves
some exposed diagnostics, but still confuses financial subject matter with an
actual completed financial notification. This review uses saved vectors and
scores only: no fit, new encoder inference, threshold search or data relabeling.

Reproduce with the isolated research environment:

```powershell
.local-backups/sms_completion_encoder_v1/env/Scripts/python.exe -X utf8 -m tools.evaluation.analyze_sms_completion_encoder
```

Machine evidence: `data/reports/transactions/sms_completion_encoder_v1_failure_analysis.json`.
The analyzer checks source/model/protocol/vector bindings, reconstructs every
saved diagnostic score exactly, and selects three distinct training groups per
class as cosine neighbours. Similarity is diagnostic, not causal attribution or
a confidence percentage. Normalized vectors are used only for this analysis;
the classifier still uses its original unnormalized embeddings.

## What failed

| Pattern | Measured evidence | Implication |
| --- | --- | --- |
| Ordinary chat | Three old validation false completions: dinner-money claim, transaction question, receipt request | Financial vocabulary and implied action are insufficient to establish a notification |
| Examples versus real notices | English manual example scores +0.958; closely related training example scores −0.524 | An example with very similar wording already exists in training; simply adding that theme is insufficient |
| Completed Arabic messages with negative words | Approval no longer pending and settlement without refusal are missed; two Arabic training positives involving refusal/OTP also fail | Scope of negation and completed state remain unreliable, even on related training examples |
| Currency/balance context | Actual settled USD purchase scores −0.0206 despite a close positive training neighbour (cosine 0.849) | A nearby correct example does not guarantee the linear head assigns the right class; proximity is not confidence |
| Merchant names resembling control language | Arabic purchase at «متجر نموذج تعليمي» is rejected | Control language inside a party name must be distinguished from message-level scope |

The cached training predictions have seven errors across four weighting groups:
six completed messages and one nontransaction. Three are one Arabic synthetic
CliQ expression, one is Arabic credited cashback, and three are authored
refusal/OTP contrasts. Their combined sample weight is 1.35 of 113 weight units.
This is resubstitution evidence, not training accuracy that predicts deployment.
The weighted objective can tolerate these mistakes; a converged solver does not
mean every critical scenario was learned. The experiment does not isolate whether
encoder information loss, linear capacity, regularization, or weighting is the
main cause. Do not claim any one of those has been proven.

There are 12 distinct definite failing texts across the exposed diagnostics after
removing the duplicated English example. In six, the nearest negative training
group is more similar than the nearest positive group. Nearest-neighbour voting
is therefore not justified as an automatic repair; these comparisons are not a
benchmark of a different fitted classifier.

## Useful signal, with limits

All 12 pre-existing bilingual matched probe pairs rank the completed message
above its negative counterpart, but only seven pairs put both messages on the
correct side of the fixed zero boundary. The representations carry some useful
signal. This does not establish consistent ordering between different scenarios
or show that distillation would preserve the useful distinctions.

A threshold change cannot repair all current errors with these fixed scores:
accepting the Arabic completed approval at −0.608 requires a lower boundary,
while rejecting the English illustrative example at +0.958 requires a higher
boundary. This is a conflicting pair of observed inequalities, not a threshold
sweep. Language-specific thresholds are also unjustified by these tiny exposed
slices. The all-correct Arabic manual result does not generalize to the Arabic
probe/quote cases.

Truncation, missing amounts alone, solver nonconvergence and export arithmetic
are not explanations supported by this run: maximum length was 56/128, multiple
unpriced completions pass, convergence took five iterations, and all 80 saved
diagnostic scores reproduce exactly from cached vectors and exported weights.
That check does not prove that the pretrained encoder preserves every semantic
distinction or exclude all implementation problems.

## Recommended bounded revision

Prepare a task-specific contrast dataset and a fixed evaluation plan before
another fit. Preserve the failed models as references. More merchant names,
amount substitutions, a threshold adjustment, or compressing the failed teacher
would not address the measured problems directly.

Proposed next deliverable: 24 distinct scenario families, each with four semantic
states in Arabic and English (192 assistant-authored messages, no paraphrase
multiplication). Cover personal claim versus posted transfer; question/request
versus receipt; pending/declined versus settled; negated failure versus failure;
illustrative quotation versus real notice; and control words inside party names
versus message-level instructions. Group related states and both languages in
one family; do not split those across training/development/reserved diagnostics.
Freeze a 16/4/4 family assignment before model inference (128/32/32 messages).
The small counts are a bounded diagnostic design, not a claim of sufficiency.

Review labels before inference: completed versus nontransaction versus genuinely
uncertain, plus explicit evidence spans for event completion, message context,
and negation/quotation scope where present. Keep ownership separate from event
completion. Preserve raw Arabic text and exact names. Assistant labels remain
weak; all canonical training/evaluation admission flags stay false. Hold any
ambiguous authored case for review instead of forcing a binary label.

Use new scenario families and check normalized/source-family overlap with all
existing training and diagnostic texts. Since this batch is informed by exposed
failures and shares the same author, its reserved fold remains prospective
synthetic diagnostics, not independent real-world evaluation. Do not copy these
12 failures into a new test set, label neighbours automatically, or report
scenario counts as independent received SMS evidence.

After that data is reviewable, specify one task-supervised encoder adaptation
comparison against the frozen encoder and compact references. It must have a
separate approved fit/compute budget, fixed stopping criteria, and an evaluation
plan before execution. This review recommends investigating supervised
adaptation; it does not establish that fine-tuning will work or be deployable.
Student training remains conditional on measured improvement with no critical
regressions. Mobile size/runtime constraints still apply to any eventual export.

No model fitting is authorized by this report. The next bounded task is preparing
the contrast data and its review/evaluation manifest, not another training run.
