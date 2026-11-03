# Proposed direct-status model with auxiliary supervision

## Execution outcome — completed, quality gate failed (2026-10-28)

Owner go approved the concrete one-run protocol.444updates/3epochs completed; losses1.057463/0.583117/0.342179 (fitting losses, not accuracy). Candidate baselineinitial hashes,trainingIDs/all3orders matched frozenv2direct; zeroheads,finiteweights/frozengradients,checkpointfrozenhashes andexactreload verified. tools/evaluation/check_auxiliary_status.py independently passes checkpoint/baseline/order/metric/gate/metadata/slice/resource/reserved checks withoutnewinference.10executionpreflighttests passed(3objective/shuffle+7diagnostic); previous11designchecks remainhistorical. Designproposal snapshot preservedprivately; originaldesignreport untouched whenapprovalupdatedconfig.

| Saved status decisions | Frozen direct | Auxiliary candidate |
| --- | ---: | ---: |
| Old validation | 17/18 | 16/18 |
| Manual | 23/24 | 22/24 |
| Context probes | 23/24 | 23/24 |
| Quote controls | 8/14 | 7/14 |
| New development | 27/32 | 27/32 |

Primaryunique swaps:2fixes(Arabic no-longer-pending completeddebit;Arabic giftcreditunknownoutcome) versus4regressions(receiptrequest,Englishexample,Englishsalarytestexample,Arabicrefusedtuitionpayment). Quotecontrols repeatoneregression; don'tpoolduplicates. Outcomeuncertainty7/8vsdirect6/8;frame2/2both;scopepolicy0/4both. Candidatecontext16/32,event17/32; auxiliaries remainunreliable. Statusvsauxprojection disagreements bycohort2/3/2/3/2 (12entries,twoquotes/manualduplicates; not12independentcases). These savedlabel comparisons arediagnostic,notnewpredictions oralternate routing.

GateFAILED:morefalseacceptances/deferrals andcontrolcorrectregressions despitefixes. No threshold tuning/retry/student/promotion. Allweak/exposed diagnosticcounts,notindependent JordanSMSaccuracy. Scope32 andmerchant29 remainUNINFERRED,includingafterevaluation. No app/tester/publishedmodelchanges orpush.

Trainingworker109.282s/eval14.078s,total123.360s within720;peak sampledactualRSS1,554,325,504/1,116,631,040bytes,below6GiB;artifactlimitsverified. Samples nothardOSlimit. Deltasstillrequirefull471MBbase. Evidence data/reports/transactions/sms_auxiliary_status_v1{_attempt,,_diagnostics}.json; ignored .local-backups/sms_auxiliary_status_v1/{direct_status,training_monitor,evaluation_monitor,inference_journal.jsonl,supervision.json}. Diagnostics computedfromsavedoutputs only; scriptproducer/sourcebinding inoriginalreport retainsfullreproducibility. Allattemptsconsumed; originalhistoricalevidenceunchanged.

Next recommendation: keepfrozen directresearchbaseline and audit1177trainingrows for conflicting raw/normalized inputs acrossstatus/context/event targets before proposing morefits. Do notassumecausefromweakdiagnostics,editlabelsautomaticallyorstartanotherarchitecturetrial. Recommended GPT-6.1-Sol medium for conflictinventory (unbenchmarked). Allworklocaluncommitted/unpushed.

## Original pre-run design (preserved)

2026-10-28. Definition complete; **not approved for fitting or executed**.
Machine protocol: `config/experiments/sms_auxiliary_status_v1.json`.
Owner approval is null and authorized training runs are zero. A subsequent
approval of this concrete protocol authorizes implementation and its one fixed
training run plus evaluation, without repeated approvals for routine work.

## Question and proposed change

Can context/event supervision help a model that still learns and predicts the
final status directly? The previous factorized candidate derived status from
two independently predicted labels and lost uncertainty. This proposal keeps
a three-way status head as the sole decision source and adds context/event
heads only as auxiliary supervision. It cannot guarantee improvement; the
auxiliary labels may harm the shared representation on this small weak corpus.

One new run is proposed. Reuse the frozen v2 direct-status checkpoint and saved
scores as the primary reference. **Do not refit that reference or initialize
from its learned weights.** Begin from the same original pinned MiniLM encoder,
zero all three new heads, and verify original encoder hashes, row IDs and all
three dedicated shuffle orders against the saved direct-control attempt before
the first optimizer step. Abort if matching cannot be established; do not
silently create another control or change environments.

The only treatment is the new three-head objective/decision arrangement, including
its fixed loss scaling. It does not isolate a universal causal benefit of
auxiliary learning: extra parameters, the objective and gradient contributions
change together. Task coefficients are design choices, not measured optima.

## Fixed objective and training

For each row, compute unreduced, already class-balanced cross-entropy for status,
context and event, using the exact original training-only class factors:

```text
row_loss = (5/6)*statusCE + (1/12)*contextCE + (1/12)*eventCE
batch_loss = 1177/(129*b) * sum(base_group_weight * row_loss)
```

The status coefficient is five times the combined auxiliary coefficient. This
does not guarantee a corresponding gradient ratio because class factors and
examples differ. Do not average the three losses again or renormalize by the
minibatch's weight total. `combine_losses()` in
`training/transactions/auxiliary_status_protocol.py` defines this objective and
rejects missing heads or shape broadcasting. Toy gradient checks perform no fit.

- Same 1,177 rows / 129 group-weight units; 17 interpretation holds excluded.
  All original text, status/context/event targets and per-group weights stay fixed.
- Same CPU float32 encoder, two threads, dropout off, mean pooling, tokenizer,
  last two trainable layers, no truncation, maximum 128 tokens including specials.
  No new downloads, dependencies or model selection.
- Status/context/event heads: 3/6/4 classes, with the frozen class order and
  first-class tie breaking. Total trainable parameters: **3,553,933**.
- Three epochs, batch eight, seed 20261028, **444 updates**. Same AdamW settings:
  encoder rate 0.00002, head rate 0.0002, decay 0.01, gradient norm limit one.
  Remaining exact settings and class factors are in the machine protocol.
- Final checkpoint only. No early stopping, best-epoch selection, threshold
  tuning, scheduler, distillation, new labels or augmentation.

The sole status prediction is `argmax(status_logits)`. Auxiliary predictions
never override it. Report disagreement with the old context/event projection
as a diagnostic; do not present these fields as trustworthy explanations.
Status completion still does not prove authenticity, ownership or eligibility
to log a transaction. Existing downstream policy remains unchanged.

## Evaluation and fixed gates

Run `content_preflight` on every development/control input **before fitting**.
Apply the new diagnostic contract and its exact in-sample exception. An unexpected
raw/normalized overlap or changed exposure binding stops the attempt. No new
exceptions, reason labels or scope decisions may be invented during execution.

After fitting and training-only sentinel reload verification, score the new final
candidate on the existing exposed development/control cohorts. Reuse the v2
saved outputs for direct, factorized and four binary references; verify their
hashes before comparisons. Binary references cannot express uncertainty.
Report per-cohort/language confusion, the three uncertainty-reason slices,
case swaps, exposed-control performance, duplicate texts and component results.
Keep metadata, labels and exposure status out of input features.

All status gates must pass:

1. Every definite nontransaction must predict nontransaction. Uncertain output
   is a deferral, not a correct rejection.
2. Every uncertain target must remain uncertain, including all four conservative
   scope-policy controls. Separating slices does not forgive their errors.
3. Completion misses, including deferrals, may not exceed the direct control or
   the best frozen reference per cohort/language, including quote controls.
4. No direct-control-correct status case may regress. Correct at least one
   unique primary direct error; duplicated quotes or an in-sample control cannot
   supply the required benefit. Preserve the known in-sample correct control.

Component accuracy on the existing 32 weak reviewed development records is
diagnostic in this new experiment. Unlike the old factorization experiment,
all-fields-exact is not a new pass condition: the research question is status
prediction with auxiliary supervision. **The old experiment's gates and failed
result remain unchanged.** No component truth is fabricated for old cohorts;
known-other context and no-event state have zero support in this component slice.
Even a status pass would not establish accurate auxiliary explanations.

**No reserved evaluation is authorized, even if every development gate passes.**
Both the scope 32 and merchant-final 29 reservations remain uninferred. These
exposed synthetic/assistant-weak cohorts do not establish real-world accuracy.
There is no deployment threshold, student training, app/tester integration or
automatic follow-on experiment.

## Budget, checks and next action

One sequential training worker: maximum 480 seconds. Evaluation worker: maximum
240 seconds. Total worker budget: **720 seconds**, including loading, preflight,
saving and checkpoint checks. Use the corrected real-interpreter supervisor,
sampled working set limit 6 GiB at one-second intervals, and maximum 2 GiB of
new artifacts. These are sampled limits, not instantaneous OS reservations.
No retry, resume or evaluation of a partial checkpoint after failure.

Before fitting, create exclusive attempt/arm ledgers with protocol, producer,
environment, initial encoder and order bindings. Check selected parameter names,
zero heads, finite loss/gradients/weights, absent frozen gradients, unchanged
frozen hashes and exact base-plus-delta reload on eight training sentinels.
Journal intended diagnostic batch IDs before encoding. Independently verify
saved tensors, confusion/gates, slices and actual-process resource measurements.
No original experiment artifacts may be overwritten.

The delta remains research-only and requires the full roughly 471 MB cached
encoder. It is not a standalone or mobile model. Publication is not authorized.

The design preflight verifies all frozen hashes, data/metadata, baseline checkpoint
digest and original settings. Eleven targeted safeguards pass, including toy
loss gradients, stored shuffle reproduction and the diagnostic-contract checks.
The preflight report lives at
`data/reports/transactions/sms_auxiliary_status_v1_design_preflight.json`.
No training attempt or candidate cache was created.

Next: after approval, implement and execute this one-run protocol, then audit
the evidence. Stop after reporting its result; do not silently tune or promote.
