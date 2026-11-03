# Context/event-state comparison — 2026-10-28

## Fresh v2 comparison completed; continuation gate failed — 2026-10-28

Owner go approved a fresh attempt using the corrected supervisor. Both models completed444updates each (888total); same initial encoder hashes and all three epoch orders verified. Checkpoint tensor/frozen-weight hashes, exact reload, confusion matrices, gates and actual interpreter resource evidence independently verified by tools/evaluation/check_sms_factorization_v2.py (passed, no fit/new inference). Original v1 failure records/source/protocol unchanged.

| Diagnostic status decisions | Direct control | Context/event model |
| --- | ---: | ---: |
| oldExposedValidation | 17/18 | 17/18 |
| exposedManual | 23/24 | 20/24 |
| authoredProbe | 23/24 | 23/24 |
| quoteControls | 8/14 | 5/14 |
| scopeDevelopment | 27/32 | 23/32 |

Counts include uncertain targets; binary-only historical results have different denominators. Quote controls overlap two manual cases; do not pool these into independent accuracy. All data are exposed/synthetic/assistant weak labels, not independent Jordan SMS evidence.

Candidate fixes4unique primary controlerrors but regresses on other control-correct cases. Arabic direct→candidate:old10/10→9/10,manual11/12→10/12,probes11/12→11/12,quotes4/7→2/7,newdev14/16→11/16. Newdev context19/32 andevent19/32 exactfields (Arabic9/16 and10/16); jointall-exact gate fails. No known_other context/no_event event truth support, so those component accuracies unsupported. Of8trueuncertain newdevrows, control keeps7uncertain, candidate only1. Context mistakes include8/18financial notices labeled instructional; event mistakes include10/16unknown outcomes labeled not_completed. This is evidence of current label-boundary/generalization errors; it does not prove a universal architectural failure. No calibrated confidence claim.

Continuation gate FAILED (false acceptances, wrong certainty, control regressions, component conformance). Reserved scope32 UNINFERRED, merchant-final29 UNINFERRED. No runtime/tester/model promotion, student, downloads or push. Neither candidate is ready for deployment; direct also misses uncertainty and has false positives. No further fitting authorized by this consumed attempt.

Worker wall seconds: direct 152.688, factorized 150.375, evaluation 39.531; total 342.594 (<1200). Peak sampled actual interpreter working set: direct1,374,621,696bytes, factorized1,179,459,584bytes, evaluation1,186,390,016bytes; all below6GiB, artifact limits passed. Samples1s, not hard OS reservations. Warm CPU single-input timings including local journal:direct23.93–30.41ms,candidate28.66–55.05ms,10calls each; NOT mobile/Hermes timing.

Evidence: config/experiments/sms_factorization_comparison_v2.json; training/transactions/factorization_comparison_v2.py; data/reports/transactions/sms_factorization_comparison_v2{_attempt,}.json; ignored .local-backups/sms_factorization_comparison_v2/{direct_status,factorized,*_monitor,inference_journal.jsonl,supervision.json}. New producer is the frozen v1 snapshot with exactly3source substitutions (run identity, corrected supervisor import, child import), deliberately retaining v1 source for immutable reproduction. v2 protocol freezes original producer/protocol plus corrected supervisor; data/cohort hashes unchanged. Numerical checker shared through explicit trial argument.12pre-run safeguards passed, no full runtime suite rerun.

NEXT: analyze paired error swaps and context/event label boundaries using saved outputs only; prioritize uncertainty versus noncompletion and instructional wording scope, Arabic and English. Assess what evidence supports retaining direct status versus revising factorized supervision; propose one bounded change only after the analysis. No automatic refit/threshold sweep/newlabels/student/reserved inference. Recommended GPT-6.1-Sol high for interpreting conflicting component/status evidence (recommendation unbenchmarked). Work local/uncommitted/unpushed.


## Attempt outcome: infrastructure failure, no quality comparison

The owner approved implementation and execution with “go” on 2026-10-28.
The exclusive `sms_factorization_comparison_v1` attempt is consumed. Its direct
status control logged all **444 updates / three epochs**, with training losses
0.978987, 0.488912 and 0.242602. These are fitting losses, **not accuracy**.
A 14,204,412-byte delta checkpoint exists, containing the expected 3,550,083
finite trainable parameters. Checkpoint reload and final frozen-parameter hash
verification were not durably completed; do not treat this as a verified model.

While saving the checkpoint, the artifact monitor inventoried an atomic-save
temporary file (`.tmpGZDN3D`). The file disappeared before `p.stat()`, causing
`FileNotFoundError`. The monitor's `finally` cleanup ran; the worker was observed
stopped afterward. The exception escaped before its resource summary was saved.
Consequently peak memory, elapsed worker time and peak artifact usage cannot be
verified. The parent recorded the failure and stopped the comparison.

**The factorized arm and evaluation worker never started.** The journal contains
only eight intended training sentinels before reload. No development/control
diagnostic inference or reserved scope inference occurred in this attempt.
There is no component accuracy, comparative quality result or gate pass/fail.
The 32 reserved scope records and 29 merchant-final records remain uninferred.
No runtime, tester or shipped model changed; no student was trained or push made.

Evidence:

- `data/reports/transactions/sms_factorization_comparison_v1_attempt.json`
- `data/reports/transactions/sms_factorization_comparison_v1_failure.json`
- `data/reports/transactions/sms_factorization_comparison_v1_failure_audit.json`
- Ignored `.local-backups/sms_factorization_comparison_v1/` contains the control
  start ledger, log, partial journal and checkpoint; retain them all.

`tools/evaluation/check_sms_factorization_comparison.py` now audits this failure
without fitting or encoding any text. It verifies frozen bindings, the cohort,
logged update counts, checkpoint tensor set/finiteness, absence of later arms and
reserved exposure, and the exclusive attempt's refusal to restart. It explicitly
leaves reload, frozen post-training hashes and resource compliance unverified.
This command passed in the isolated research environment:

```text
.local-backups/sms_completion_encoder_v1/env/Scripts/python.exe -X utf8 -m tools.evaluation.check_sms_factorization_comparison
```

The original bound producer, protocol and `python_worker_monitor.py` remain
unchanged for auditability. Future experiments must use the corrected
`tools/evaluation/worker_supervision.py`: tolerate only disappearing inventory
entries, stop on other scan errors, and persist monitor/cleanup failures and
sampled resource observations. It also checks artifacts after normal exit.
Sixteen targeted tests passed across the future supervisor, original resource
safeguards, factorization protocol and loss/gate tests. They include a controlled
rename-race simulation, unreadable-artifact rejection, real interpreter memory,
time/memory/disk limits, and termination of a worker **and spawned child** after
an injected monitor failure. No task-model fitting occurs in these tests.
These checks do not retroactively validate the failed worker's resource use.

Historical recovery proposal (fulfilled by completed v2 above): a **new versioned two-arm attempt**, using this corrected
supervisor and exactly the same frozen data, initialization and training/loss/
evaluation settings. Both arms must start fresh from the original pinned base;
do not resume or evaluate the partial control. Register and approve the new
attempt before fitting. No model search or test-set expansion is proposed.

## Frozen pre-run design

This proposal tests whether separating message context from described event state
improves completion decisions. It compares **two matched training runs**:

1. A direct three-way status classifier: completed, nontransaction, uncertain.
2. A factorized classifier: six context classes and four described-event states,
   combined through the fixed research projection below.

Both arms use the same reviewed messages, base group weights, initial pretrained
encoder, batch orders and training budget. This controls the data change that
confounded earlier comparisons. It still compares different supervision/head
structures and effective class-balanced losses; it does not isolate a single
causal effect or promise that factorization will win.

Exact settings: `config/experiments/sms_factorization_comparison_v1.json`.
Its recorded approval authorized two runs; the failed attempt consumed this
execution authorization. The design below describes the frozen intended
comparison, not a claim that both runs or their evaluations completed.

## Matched data and targets

The proposed view contains **1,177 non-held records across 129 groups**, with
17 interpretation holds excluded from both arms. Original overall statuses stay
611 completed, 532 nontransaction and 34 uncertain. Context targets use all six
reviewed labels, and event-state targets use all four. Evidence spans, group IDs,
prior status claims, annotations, sender identities and other metadata are never
input features: both arms receive only the same normalized message text.

The direct arm learns the unchanged three-way status. The factorized arm learns
the two reviewed fields. Reviewed semantic unknowns are valid targets;
unresolved interpretation holds are excluded entirely. No validation case is
admitted into training. The original 1,158-row binary view and all prior reports
remain unchanged.

Each selected row gets base weight `1 / selected rows in its source group`.
Recompute after combining the uncertainty appendix and excluding holds; never
append the new rows with the old weights. For example, the new scope groups now
contain eight selected rows at 1/8 each, rather than six at 1/6 plus unweighted
extras. The old held cost-fragment group is absent; the reviewed authorization
uncertainty group is present. Every base group totals one, total weight 129.

The cohort manifest is
`data/reports/transactions/sms_factorization_comparison_v1_cohort.json`.
Exact ordered training-view SHA256:
`e169213308c680ba7e5210ad6922ec6f8dee77f0f14c11d3539f2d22697919a3`.
`training/transactions/factorization_protocol.py` reconstructs and validates it.
Canonical admission/fitting flags stay false; an approved experiment may select
only this explicit local weak research view.

## Models and loss

Reuse the original pinned multilingual MiniLM base, **not** weights from the
failed adaptation or from the direct arm. Both arms update only encoder layers
10 and 11 (3,548,928 parameters); embeddings, the first ten layers and the unused
pooler stay frozen. Entire models remain in evaluation mode with dropout off,
but gradients enabled on the selected tensors. CPU float32, two threads, unchanged
normalization/tokenizer, 128-token limit including special tokens, no truncation,
published masked mean pooling and no embedding normalization.

All classifier weights and biases start at zero. The direct head has 1,155
parameters; the two factorized heads total 3,850. Total trainable parameters are
3,550,083 versus 3,552,778. Epoch order uses a dedicated seeded generator so head
construction cannot change row order. Argmax ties take the first frozen declared
class; unknown/uncertain is first in each head's declared order.

Three epochs, batch size eight including the final partial batch: **444 updates
per arm, maximum 888 total**. Fixed AdamW: encoder learning rate 2e-5, head rate
2e-4, betas (0.9,0.999), epsilon 1e-8, decay 0.01 on all trainable tensors,
global norm clip 1.0. No scheduler, warmup, best-epoch selection, auxiliary/span
loss, pairwise loss, distillation, mixed precision or parameter search. Both
training arms finish before final diagnostic comparisons. Per-arm checkpoint
reload checks use fixed training sentinels, not validation selection.

Use unreduced [cross entropy](https://docs.pytorch.org/docs/2.14/generated/torch.nn.CrossEntropyLoss.html),
with class balancing derived once from training labels only. For each head,
`alpha_c = 129 / (number of classes * group-weighted class mass_c)`.
The protocol freezes exact rational masses/factors before any run. This gives
unknown status a factor of 8.6 and unknown context 21.5. The latter rests on only
eight related examples in four groups: balancing gives a learning signal but
can amplify weak-source artifacts and does not create diverse evidence.

Each minibatch loss is `1177/(129*b) * sum(base_weight_i * row_loss_i)`, where b
is actual batch size. Direct row loss is class-balanced status cross entropy;
factorized row loss is half context cross entropy plus half event cross entropy.
Do not normalize by the accidental minibatch weight sum. Base group weights are
identical between arms, but task-specific class factors intentionally change
effective loss contributions. Softmax/logit values remain uncalibrated; do not
show them as certainty percentages. Optimizer API reference:
[AdamW](https://docs.pytorch.org/docs/2.14/generated/torch.optim.AdamW.html).
The numerical settings are project choices, not values established as optimal.

## Fixed research projection

| Predicted context | Predicted described state | Completion output |
| --- | --- | --- |
| unknown | Any state | uncertain |
| conversation, question/request, instruction/example, known-other | Any state | nontransaction |
| financial notice | completed | completed |
| financial notice | unknown | uncertain |
| financial notice | not completed or no event | nontransaction |

Unknown context takes precedence even over no-event. A personal claim or a lesson
can describe a completed payment while the overall output stays nontransaction.
The symbolic projection agrees with every selected unchanged training status
and the 32 component-development reviews. That is annotation consistency, not
model performance. This is a new **research completion projection**; it does not
replace canonical behavior, authenticate a sender or authorize logging. Own-account
exclusion, ownership uncertainty, amount/direction/entities and category remain
separate existing policy and extraction tasks.

## Evaluation and acceptance

Before any new fit, 32 existing development messages received separate weak
context/event reviews under `data/annotations/sms_factorization_eval_v1/`.
Raw text and original statuses are unchanged. They are evaluation-only and not
part of the training view. This small component slice lacks known-other context
and no-event truth: report zero support, not invented accuracy for those classes.
Older diagnostic cohorts lack factorized field truth; do not manufacture component
accuracy there. No reserved component labels were created or inferred.

Compare final status outputs on the existing 18 validation, 24 manual, 24 context
probe and 32 scope-development messages; handle 14 quote controls separately and
flag their two duplicate manual examples. Report three-way confusion by cohort
and language. The four old binary references (word, word sequence, frozen
encoder, adapted encoder) remain fixed. Their uncertainty capability is
unsupported; do not confuse a binary negative with an uncertain prediction.

Pre-reserved continuation gates for the factorized candidate:

- Every definite nontransaction must be rejected as nontransaction. Returning
  uncertain is reported as unnecessary deferral, not a correct rejection.
- Completed messages predicted negative **or uncertain** count as misses. Misses
  must be no worse than the best fixed reference or matched direct control in
  each cohort/language; report all case swaps.
- Every existing uncertain truth case must remain uncertain, rather than become
  a falsely decisive positive or negative.
- No status-correct matched-control case may regress, and the candidate must fix
  at least one unique primary-cohort control error. A tie is no measured status
  advantage for factorization.
- Both component labels must match all 32 reviewed development records exactly.
  This is a strict finite conformance gate, not a real-world release threshold.

If any gate fails, stop without scoring the 32 reserved scope messages. If all
pass, score both final arms and the unchanged references on those reserved rows
once, using original 24 definite/eight uncertain status labels only. Require
correct negative/uncertain decisions and no worse completion misses or
control-correct regressions per language/overall. No adjustment after observation.
Write intended reserved batch IDs before encoding so interruption conservatively
records exposure; never claim an interrupted batch remains unseen or retry it.

These cohorts remain exposed or related same-assistant synthetic data. Neither a
pass nor component interpretability establishes independent Jordan SMS accuracy.
No student, automatic alternative model, threshold change or promotion follows.
A strong direct-control result can be reported, but it does not authorize
deployment if the factorization comparison has no advantage.

## Compute and implementation boundary

Use the existing isolated CPU environment and cached base weights. No dependency,
model or CUDA downloads. Sequential workers: **eight minutes per training arm
plus four minutes for evaluation**, at most 20 minutes of worker compute total.
Deadlines cover whole workers after the actual-interpreter handshake, including
loading and preflight. Monitor actual process working set once per second with
a 6 GiB stop limit, and at most 2 GiB of additional experiment artifacts. These
are sampled limits, not instantaneous OS reservations.

The corrected `python_worker_monitor.py` now also supports declared artifact
paths and disk limits. Four harmless-worker tests verify real PID/allocation,
time, memory and disk termination with process-tree cleanup. The original faulty
adaptation supervisor is forbidden for new runs. Its historical memory caveat is
retained; this design does not retroactively verify that run's resource use.

Exclusive experiment/arm ledgers must bind source/environment hashes, initial
weights and row orders before training. Any resource or numerical failure
consumes the attempt and stops the comparison; no retry, resume or evaluation of
partial final candidates. Verify finite gradients/weights, frozen tensor hashes
and base-plus-delta reload equality. Checkpoints remain ignored research deltas
requiring the full roughly 471 MB encoder. **They do not enter the tracker or
tester.** Python/TypeScript/browser parity and measured device budgets would be
required under a separate future deployable-model proposal.

Before fitting, four protocol safeguards and four real-process monitor safeguards
passed. They did not cover the temporary-file race that later stopped execution.
See the outcome above for the additional safeguards and the current next step.
