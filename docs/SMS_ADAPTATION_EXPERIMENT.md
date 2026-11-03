# Proposed completion adaptation experiment — 2026-10-28

## Completed result — continuation gate failed

The owner approved and executed the single run on 2026-10-28. All 435 optimizer
updates completed over three epochs, in 92.33 seconds of recorded worker training
time (113.22 seconds total supervisor time). Training losses were 0.1656, 0.09345,
and 0.03054. The result did not pass the pre-reserved gate, so **none of the 32
reserved messages were inferred**. The proposal below remains the pre-run plan;
the immutable attempt/report record the consumed approval and budget.

| Exposed definite diagnostic | Frozen encoder correct | Adapted encoder correct | Adapted FP / FN |
| --- | ---: | ---: | ---: |
| Old validation | 15/18 | 16/18 | 1 / 1 |
| Manual challenge | 20/22 | 21/22 | 0 / 1 |
| Context probes | 19/24 | 22/24 | 0 / 2 |
| Quote controls | 7/10 | 8/10 | 0 / 2 |
| New scope development | 19/24 | 22/24 | 0 / 2 |

Do not pool the rows: quote controls duplicate two manual examples, and uncertain
truth is excluded from every denominator (two manual, four quote and eight new
development messages). These remain weak synthetic diagnostics, not independent
accuracy measurements. No distillation, promotion or integration follows.

The remaining false completion is the ordinary question “did you finish the
transaction?”. Missed completions include an English posted ATM deposit, a
settled foreign-currency purchase, two Arabic completion/context probes,
purchases at names containing control language in both languages, and a new
wage-credit scenario in both languages. The ATM deposit and English merchant
name are regressions against the frozen encoder. Overall gains do not erase
those failures. Arabic manual cases remain 11/11, but Arabic probes are 10/12
and new Arabic development 11/12; Arabic is still not uniformly reliable.

The 14,201,332-byte delta contains exactly 3,549,313 parameters. It needs the
pinned full base encoder. Frozen tensor hashes match, all trained tensors are
finite, a reconstructed base-plus-delta model reproduces saved reload scores
exactly, and the copied head's initial maximum score gap is 8.59e-7. Evidence:
`data/reports/transactions/sms_completion_adaptation_v1{,_attempt}.json`;
ignored delta: `.local-backups/sms_completion_adaptation_v1/final.safetensors`.
Verify without fitting or new inference:

```powershell
.local-backups/sms_completion_encoder_v1/env/Scripts/python.exe -X utf8 -m tools.evaluation.check_sms_adaptation
```

### Resource monitoring defect

The original supervisor sampled the Windows virtualenv launcher PID, which is
different from the actual interpreter PID. Its reported peak of 4,878,336 bytes
is therefore not valid training-process memory evidence. Its termination path
also targeted only that launcher. **The historical 6 GiB memory limit and
process-tree termination are not verified.** The worker did complete below the
time allowance, and the numerical outcome remains inspectable, but the run is
not fully conformant to the resource-monitoring protocol. Its real memory peak
cannot be recovered from the saved logs. Do not present it as a fully budget-
verified experiment or silently overwrite the original supervision report.

The separate immutable `sms_completion_adaptation_v1_resource_audit.json` records
this limitation and the launcher/interpreter PID reproduction. The original
bound producer is preserved so its evidence remains reproducible; it refuses
another attempt. No training was repeated to repair the monitor.

For future experiments, `tools/evaluation/python_worker_monitor.py` identifies
the real interpreter through a token-bound startup handshake, samples its memory,
and terminates the owned process tree on limits. Three real harmless-process
tests verify the PID/allocation measurement, deadline termination and memory
termination. Seven prior safeguards cover split exclusion, gradients, gates,
resource predicates and corpus spans/admission. The new helper is not a claim
that the historical run was monitored correctly.

Next: review the remaining question-versus-notification and valid-name/context
errors before choosing another experiment. Keep the untouched reserved set and
failed references. No additional fitting is authorized by this negative result.

The next experiment would let the last two layers of the existing multilingual
encoder learn the completion task, together with its existing classifier. It
tests whether task supervision can improve the measured context/scope failures.
The earlier experiment froze the entire encoder. Improvement is a hypothesis,
not a measured result or a promise that a compact student will work.

Exact settings: `config/experiments/sms_completion_adaptation_v1.json`.
Current status is proposed, owner approval is null, and authorized training runs
are zero. This task wrote the design only. The owner's next approval of this
specific protocol can authorize implementation, preflight, one bounded training
run and the conditional evaluation below; do not ask for repeated approval of
routine implementation steps inside that scope.

## Model and local budget

Read-only inspection of the cached model confirms 117,653,760 encoder parameters.
Only its last two transformer layers (3,548,928 parameters) and the 385-parameter
linear classifier would change: **3,549,313 trainable parameters**. Freeze the
embeddings, first ten layers and unused pooler. Initialize the head from the
completed frozen-encoder benchmark, not a random restart. Copy it to float32
and verify initial scores against the old scorer before training.

Use the pinned encoder/tokenizer, same research text normalization, masked mean
pooling, 128-token maximum and no truncation or embedding normalization. Keep
all modules in evaluation mode so dropout stays disabled, while enabling
gradients only on the selected tensors. Evaluation mode does not itself disable
autograd; the implementation must explicitly verify parameter gradients and
frozen tensor hashes. Scope annotation spans are review evidence, never hidden
input features or extra supervised targets.

The machine reports a Ryzen 5 5600 (six cores/twelve logical processors) and
17,087,152,128 bytes of installed RAM. The existing research PyTorch build is
CPU-only; CUDA is unavailable in that environment. Reuse it without new downloads
or a GPU installation. Hardware availability does not establish training time.

| Limit | Proposed setting |
| --- | --- |
| Training runs | One, with no retry/resume or automatic alternative |
| CPU threads | Two |
| Data passes | Three full epochs |
| Batch size | Eight, retaining the final partial batch |
| Updates | 145 per epoch, maximum 435 |
| Training wall time | 20 minutes from first training forward pass; parent watchdog terminates at deadline |
| Process memory | Stop if sampled working set exceeds 6 GiB; poll every second |
| Additional artifacts | At most 2 GiB |

The memory limit is monitored, not an instantaneous OS memory reservation. Time,
memory or disk failure consumes the attempt and retains a failure report; it
does not authorize a smaller batch, alternate seed, another device or extra run.
Do not evaluate a partially trained model as the planned final candidate.

Save only the adapted layers and head with exact tensor names, the base model
hash and tokenizer/math bindings. Those research weights still need the full
encoder. They are not a small standalone SMS model or a tracker dependency.

## Frozen training view

Combine the earlier 1,062 training rows with only the 96 definite rows in the new
scope batch's proposed-training fold. Exclude its 32 uncertain training rows.
The resulting **1,158 rows contain 611 completed and 547 nontransaction labels**
in 129 weighting groups. The original weights stay intact. Each new group has
six definite messages, each weighted 1/6, so every group totals one.

The exact ordered training-view SHA256 is
`ec7fd9f887b9a5bb060284b14891ac0430b0d96a900337665377ec5a1db67e70`.
The protocol defines the JSON encoding and freezes all required source hashes.
The code must reconstruct and check this before training. Canonical dataset
admission flags stay false; approved selection is confined to this local weak
research view. Ownership is not inferred from completion.

All 32 development and 32 reserved messages stay outside training. Each fold
has eight uncertain rows, excluded from binary truth. Do not turn uncertainty
into a negative target, train a third class from these labels, or invent a
confidence-based review threshold in this experiment. Report raw decisions on
uncertain cases separately.

Train with a fixed AdamW optimizer: learning rates 2e-5 for the last two layers
and 2e-4 for the head, betas (0.9, 0.999), epsilon 1e-8, weight decay 0.01 on all
trainable tensors including biases/LayerNorm, global gradient norm clipping at
1.0. No schedule, warmup, class rebalancing, auxiliary/pairwise loss, mixed
precision or development-driven early stopping. These are bounded engineering
choices, not settings established as optimal for this project.

Use unreduced binary cross entropy on logits. For a minibatch of actual size b,
the loss is `1158 / (129 * b) * sum(weight_i * BCE_i)`. This targets the
group-weighted objective under uniformly shuffled rows without normalizing each
batch to its accidental weight total. Shuffle once per epoch using the specified
seed and dedicated generator. Keep only the final state after all three epochs;
never choose the best epoch based on diagnostics.

The official [AdamW documentation](https://docs.pytorch.org/docs/2.14/generated/torch.optim.AdamW.html)
and [binary cross entropy documentation](https://docs.pytorch.org/docs/2.14/generated/torch.nn.functional.binary_cross_entropy_with_logits.html)
define the APIs; the numerical choices above are ours. Record exact library and
hardware details, enable deterministic operations and stop on an unsupported
operation. PyTorch's [reproducibility guidance](https://docs.pytorch.org/docs/2.14/notes/randomness.html)
does not guarantee identical results across environments or versions.

## Evaluation and stop conditions

Write an exclusive attempt ledger before the first training forward pass. It
must bind source/protocol/environment hashes, initial parameters and row order.
Check finite loss, gradients and weights during training, frozen tensor equality
afterward, and candidate reload/score agreement before reporting results. The
existing fixed zero boundary stays unchanged: positive logit means completed.
Scores are not calibrated confidence percentages.

Evaluate the final candidate against all three unchanged references: word,
word-sequence context, and frozen encoder. The initial gate uses the old 18
validation, 24 manual and 24 context-probe cases, new 32 development messages,
and 14 quote controls. Keep uncertain truth separate and flag duplicate quote
examples instead of pooling them as new evidence. Report confusion counts by
cohort and language, individual fixes/regressions, theme/contrast consistency,
time, memory, bytes and warm CPU inference timings.

To proceed, require zero false completions on every definite cohort/language
slice and no more misses than the best fixed reference on that same slice.
List every case swap, including OTPs, declines, ordinary chat and examples. These
are research continuation gates, not a release standard or an accuracy claim.

**If the initial gate fails, stop without scoring reserved messages.** If it
passes, score the final candidate and three references on the reserved fold
once. Require zero false completions and no more misses than the best reference
per language and overall. No adjustments after seeing those results. Even a
pass does not authorize distillation, tracker/tester integration or promotion.

The authored diagnostics share an author and known semantic relatives with old
training. They remain weak synthetic evidence; the reserved fold is not an
independent real-world final test. This experiment changes both task training
and the selected dataset versus the older model; any gain cannot be attributed
solely to adapting the encoder. A separate ablation is not part of this budget.

No direction, entity or category training, merchant-final inference, new model
downloads, cloud SMS inference, publication or runtime integration belongs to
this experiment. The next concrete step is implementing and executing this
single protocol after its scope is approved.
