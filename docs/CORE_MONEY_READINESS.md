# Core money readiness — 2026-11-01

The repaired detailed parser is ready for further developer testing. It is not
yet supported by independent accuracy evidence or a verified mobile runtime.
R5's finite development exit remains complete; R6's release exit remains open.
This audit changes no engine behavior, model weights, test truth or caller.

Tester follow-up is complete: the primary view now shows the message-only
assessment, with the legacy comparison collapsed and ownership confirmations
separate. See the verification section at the end. The inventory below describes
the earlier frozen audit snapshot; it is not rewritten as a new accuracy result.

## What was measured

The inventory reads the frozen R5 before/after evidence and saved outputs. It
verifies the comparison's source hashes, private after-snapshot hash, all 23
model artifacts and the browser's core-source manifest. It does not import an
engine, execute inference, train anything or open either protected reservation.
Exact inputs are preserved in the existing private hash-deduplicated report
archive (`data/private/report_inputs/manifests/core_money_r6_inventory_v1.json`).
The reproduction test uses an isolated historical view so later approved UI or
runtime changes cannot silently rewrite this audit or break its historical truth.

- 2,302 saved development entries, representing 1,098 distinct non-null texts
  plus one null-input entry. Distinct text is not the number of independent
  source families; digit variants and repeated sender wrappers share scenarios.
- Full Python/TypeScript/browser result agreement was verified at R5. All
  asserted core fields still match the stored expectations. This audit checks
  the bindings to that evidence rather than repeating inference.
- 70 ownership-wrapper requests have prior parity/binding checks. Their stored
  outputs do not create new independently known ownership truth.
- Zero independently eligible final-test cases in this inventory. Rates below
  are development agreement, not estimates of future bank-SMS accuracy.

Machine evidence: `data/reports/behavior/core_money_r6_inventory_v1.json`.
It contains per-cohort language, declared-family, input-digit and separator
slices. Keep cohorts separate; no pooled accuracy or independent-sample
confidence interval is computed. The report contains aggregates, not SMS text.

## Which fields actually have labels

“All asserted fields pass” does not mean every record labels every field. The
inventory separates status, positive extraction truth and complete core truth.

| Cohort | Entries | Status assertions correct | Positive amount assertions correct | All seven core fields on an eligible accepted event |
| --- | ---: | ---: | ---: | ---: |
| Core fixture | 52 | 51/51 | 29/29 | 26/26 |
| Authored SMS | 74 | 74/74 | 52/52 | 48/48 |
| Manual diagnostics | 24 | 24/24 | Unlabeled | Unlabeled |
| Authored probes | 24 | 24/24 | Unlabeled | Unlabeled |
| Old exposed validation | 18 | 18/18 | Unlabeled | Unlabeled |
| Quote controls | 14 | 14/14 | Unlabeled | Unlabeled |
| Scope development | 32 | 32/32 | Unlabeled | Unlabeled |
| Unmarked-amount variants | 276 | 276/276 | 126/126 | Unlabeled ownership field |
| Income/transfer variants | 276 | 276/276 | 126/126 | 90/90 |
| Settlement variants | 360 | 360/360 | 174/174 | 132/132 |

The other five repair packs also retain all their asserted matches; the JSON
contains their exact denominators. Variant rows are not additional independent
messages. “Unlabeled” means the artifact cannot score that claim, not a parser
failure. No missing label was filled from a prediction.

The seven core fields are status, tracking decision, amount, currency, currency
resolution, direction and transfer relationship. Requiring all seven explains
why the core fixture has 26 strict complete-event cases while the earlier,
looser accepted-event assertion metric has 28. The unmarked pack's 126/126
accepted-event assertion matches remain valid; none supplies the seventh
ownership field. This does not reopen or weaken its frozen expectations.

Null amount truths are counted separately from positive amount extraction.
The report provides all-known, expected-include and accepted-only amount/currency
and direction views, plus miss/review and false-include denominators. A slice
with no eligible labels has a null rate, never a fabricated 100%.
Unsafe includes cover expected exclusions and reviews, including own-account
events. Ordinary-message false inclusion is reported separately. All observed
counts are zero where such truth is available; status-only cohorts cannot score
unannotated include/review correctness.

## Coverage gaps that passing counts conceal

| Area | Existing evidence | Missing evidence |
| --- | --- | --- |
| Arabic / English | Authored74 has 37 messages per language and 24 fully annotated eligible events per language. All match. | Independent Jordan notifications, spelling/layout/provider variation and unfamiliar wording. |
| Mixed-language text | Core52 declares one mixed-language case, with one full-core accepted event. | Breadth across mixed sentences and scripts; one case cannot establish generalization. |
| Digits / formatting | Repair packs exercise ASCII, Arabic-Indic and Eastern Arabic numerals plus sender/contact wrappers. | Independent formats and ambiguous punctuation/layout. The report's profiles inspect all message numbers, including dates/IDs, not just the gold amount. |
| Event families | Authored examples include purchases, deposits, withdrawals, cashback, refunds, salary, fees, installments, bills and transfers. | Real notifications spanning these families; often only four authored examples cover a family, two per language. |
| Transfers / ownership | Authored74 labels eight P2P, two own-account and two unknown relationships; core52 labels two P2P, one own and one unknown. Binding/revocation tests cover the wrapper. | Independently known ownership and real sender/account combinations. A counterparty name is insufficient. |
| Completion / negative context | Exposed question/chat/OTP/decline/noncash/conditional/unknown contrasts pass. | Independent ordinary messages and adversarially similar receipts, with reviewed truth. |
| Amount roles | Exposed primary-total, FX charge, balance, date, identifier and competing-value tests pass. | Independent receipts with multiple plausible monetary values; no inferred conversion or totals. |
| Policies | Fee-total and FX-primary decisions are resolved. | Zero/signed adjustments and duplicate-ingestion identity remain uncontracted and unscored. |

The scope-development32 above is not the protected scope32 reservation. Neither
that reservation nor merchant-final29 was inferred on or relabeled here.

The R2 provenance audit found 26 user-attested source blocks already exposed in
the project/Gemini history, with packet boundaries and generation parentage not
fully established. Existing synthetic/generated messages and already-seen web
examples cannot be promoted into independent final evidence. See
`CORE_MONEY_DATA_AUDIT.md`. Genuine origin, unseen evaluation and known labels
are three separate requirements.

Future evaluation intake must preserve provenance and consent, source/template
family, previous exposure, exact message boundaries, reviewed completion and
amount/currency evidence, and separately known ownership. Unknown truth stays
unknown. Freeze candidate, labels and partitions before scoring; approve the
thresholds and final-test run first. Do not consume the reserved sets merely
because the development cases pass. The old proposed percentage targets remain
proposals; `releaseThresholds` is still null. Categories are outside this phase.

## Runtime and tester findings

The inspected TypeScript core graph has 16 source/contract files totaling
117,001 bytes. Legacy weights are another 92,497 bytes. The standalone tester
HTML is 3,579,292 bytes because it also embeds optional research material. These
are disk/source sizes, not an application package or memory measurement.
No research module is imported by the inspected core graph. The large research
encoder is not a dependency in that graph; this audit did not inspect or modify
the separate app's packaging.

The TypeScript detailed path is `MasroofEngine.analyzeDetailed({text, ...})`;
the Python reference is `predict_detailed`. The ownership wrapper uses its own
versioned request. The legacy path remains `analyze({body, ...})` / `predict`.
Those APIs intentionally have different policies and schemas.

**At the audit snapshot, the tester's primary table called the legacy API.**
The repaired result was in “Detailed assessment comparison.” On core52, the saved
legacy and detailed results differ on eight recording decisions in each runtime.
Python also has one uncomparable legacy malformed-input exception; it is not
silently counted as an agreement. These are API disagreements, not a new score
for the legacy path. Making the detailed result the tester's primary view is
the next useful developer-facing change; retain a clearly marked legacy
comparison. Preserve the approved visual style and optional research ground.

TypeScript parity checks initialize the legacy weights explicitly. Its detailed
fallback returns false if no model is initialized, whereas the Python engine
loads weights through its constructor. Caller setup must preserve this contract;
an uninitialized caller is not covered by initialized-runtime parity. A future
adapter should make readiness explicit and test the initialization path.

Node/browser-VM evidence does not establish Hermes behavior. The source uses
regular-expression lookbehind, match indices (`d`), `matchAll`, module/JSON
loading and a generated TypeScript bundle. Verify these features, complete
output parity, cold/warm timings, allocations and packaged assets on the actual
target runtime/device before deployment. The local 0.10 ms SLA is unverified;
neither source size nor desktop timings proves it. No app work or mobile
benchmark was performed here.

## Dependency map before cleanup

| Component | Current dependency | Safe next action |
| --- | --- | --- |
| Legacy transaction scorer and `masroof_model.json` | Detailed assessment still calls it for financial-candidate fallback. | Keep. Removing it requires a replacement or an explicit fallback contract change and regression evidence. |
| Legacy entity extractor inside both engine classes | Detailed assessment calls it with categorization disabled; the money resolver retains its bounded FX interpretation when applicable. | Extract the needed adapter behind the detailed contract before any retirement. Preserve existing FX/name/mask compatibility checks. |
| Legacy `analyze` / `predict` | Public compatibility surface, tester comparison and frozen226 gate. | Keep until callers and unique behavior are mapped. Changing the tester's primary view is not app migration or removal of these APIs. |
| Category overlays and BIO skeleton | Retained public/compatibility or explicit research surfaces, not proof of completion in the detailed path. | Map exports, actual call sites and unique tests before considering a separate compatibility module. Do not silently remove them. |
| Optional merchant / SMS research panels | Browser builders and dedicated lab tests; the core graph has no research imports. | Preserve the developer ground. A later core-only build profile could omit these assets without deleting research evidence. |
| Training producers, attempt ledgers and source-bound reports | Reproduction, consumed-fit accounting and rollback evidence. | Preserve versioned files/snapshots. Do not rewrite their inputs or retry failed fits during cleanup. |

Current repairs include local modified/untracked files; the historical Git
checkpoint does not by itself capture this complete working state. Establish a
reviewed current checkpoint before physical deletion or directory moves. This
audit did not commit, push, delete or relocate anything.

## Completion and next action

R6's existing-evidence inventory is complete. Seven audit safeguards pass,
including null/missing-label denominators, all-eligible versus accepted-only
metrics, own-account/review false includes, changed-source rejection and exact
report reproduction. Runtime source hashes still match R5's full 320 Python /
11 TypeScript / 226-case check. That historical suite was not rerun for this
offline-only report; no runtime source changed.

Reproduce without inference:

```text
.local-backups/sms_completion_encoder_v1/env/Scripts/python.exe -X utf8 -m unittest tests.python.test_core_readiness_inventory
```

The test reconstructs the audit's exact historical inputs. The CLI's direct
`--check` validates the original live input hashes; it intentionally rejects a
changed tester. Use the isolated historical test after later UI/runtime changes,
and a new report version for a new readiness measurement.

## Tester primary view verified — 2026-11-01

The main table now renders `analyzeDetailed` directly: include/review/exclude,
completion, amount, explicit versus default currency, direction, ownership and
plain-language reasons. Main values remain visible for unresolved and excluded
events where the engine supplies them. Empty input clears all previous values.
Ownership confirmations keep their separate, explicitly labeled result; they
do not silently replace the message-only assessment. Existing binding/revocation
checks remain intact.

The previous API's table and raw response are available under collapsed
“Legacy comparison.” Its failure cannot suppress the primary result. Optional
research panels remain available and preserve their existing lazy behavior.
No engine API, learned model, app integration or inference policy changed.
Display code lives in `tools/browser/assessment_view.js`, embedded by the
canonical builder; the approved layout and colors are retained.

Evidence: `data/reports/behavior/core_money_r6_tester_v1.json`. All 2,302 saved
development results (detailed and legacy), 70 ownership requests and 23 model
hashes are unchanged. The tester build reproduces byte for byte. New UI checks
exercise 13 amount/context contrasts, Arabic input, contact metadata, resets,
separate ownership results and failure isolation using real page handlers.
The full suite passes 327 Python tests, 12 TypeScript suites and 226 frozen cases.
Actual Edge screenshots were checked at desktop and 440px viewport widths,
including Arabic incoming money with a visible JOD default; no horizontal
overflow was observed at the narrow viewport. This is browser validation,
not a mobile-app or Hermes performance claim.

The intake and initialization preflight were completed on 2026-11-02; see
[CORE_VALIDATION_PREFLIGHT.md](CORE_VALIDATION_PREFLIGHT.md). The private intake
is empty, known-exposure coverage is explicitly partial, and no scoring was
authorized. Current weights and startup behavior are checked without changing
the engine. Full337Python+13TS+226frozen passes.

The tester startup guard is complete; see `CORE_VALIDATION_PREFLIGHT.md` and
`core_money_r6_startup_guard_final_v1.json`. Startup errors are separate from
transaction decisions; no inference runs until the caller is ready.
Full338Python+14TS+226frozen passes; prior outputs and models are unchanged.

The source review is complete; [JORDAN_SMS_VALIDATION_SOURCING.md](JORDAN_SMS_VALIDATION_SOURCING.md)
records nine checked sources, two incomplete leads and a proposed collection
route. No qualifying public corpus was confirmed; the intake is still empty.
On 2026-11-03 the owner chose continued development testing and deferred collection.
[CORE_FORMAT_ROBUSTNESS.md](CORE_FORMAT_ROBUSTNESS.md) records a measured format-control
repair: 6,984/6,984 checks pass with original outputs/models preserved. Independent
provenance/reviewed truth, release thresholds, final scoring, model promotion,
actual mobile deployment and destructive cleanup remain separate decisions.
