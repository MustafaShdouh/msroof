# Sanitized corpus v1 and grouped development split

This version prepares replacements for the exposed legacy data. It does not change
the active engine, replace its regression gate, fit a model, or modify GitHub.
Historical originals remain unchanged and are also preserved in the ignored
`data/private/historical_corpus_v1/` snapshot with a checked hash manifest.

## Prepared artifacts

| Artifact | Purpose |
| --- | --- |
| `data/training/sanitized_v1/transactions.json` | Same 2,120 synthetic source rows, with new values and person identifiers plus explicit synthetic provenance. No redundant CSV copy. |
| `data/training/splits/transaction_direction_sanitized_v1.json` | New grouped development partition: 1,702 train / 418 validation. |
| `tests/fixtures/sanitized_v1/` | 226 transformed compatibility cases plus their own frozen hash manifest. |
| `data/reports/SANITIZED_CORPUS_V1.md` and JSON companion | Preparation methods, source/hash checks, partition counts and limitations. |
| `data/reports/sanitized_corpus_v1_legacy_v1_evaluation.json` | Separate versioned Python/TypeScript diagnostic, tied to exact data/model/runtime hashes. |

These are synthetic privacy transformations, not newly collected real messages or
additional independent examples. They preserve legacy binary labels for compatibility;
they are not human gold under the new three-outcome transaction behavior contract.
The 26 original seeds remain unadmitted and development-exposed. The merchant
category dataset and its final-test reservation are unchanged.

## Privacy transformation

Known personal phrases are discovered from the pinned private generator and
transfer cases, then replaced by varied synthetic identifiers in the same script.
Identifiers contain no repeated semantic marker such as RECIPIENT that could
become a label shortcut. Public merchant names are retained to preserve wording
and merchant/preposition edge cases; these are not new researched businesses.

Financial values, masked account digits, codes, references, dates, times and numeric
senders are regenerated from a record/slot-seeded random process. This is not an
invertible substitution of the original digits. Amount/balance expected values
are updated together; repeated-value equality, zeros, field missingness, currency,
direction and original classification labels are preserved. Numeric separators and
financial digit scripts are preserved. Local phone prefixes remain compatible with
the wallet-message structure. Full transformation plans remain private.

Automated checks establish that the known person phrases are absent from the new
artifacts. This is not certification that all possible identifiers have been found.
The previous tracked legacy data, generators and Git history still contain old
material: preparing replacements alone does not complete repository privacy cleanup.
Review/migration/retirement are still required, with separate authorization for any
remote-history rewrite or push.

## Source-template grouping

The current generator is pinned by SHA-256. A temporary AST transformation tags each
chosen text literal/f-string expression without changing random choices. It
reproduces all 2,120 historical record values and their order exactly, recovering
102 observed template expressions. The generator itself is not edited.

Grouping unions each entire source-expression family with global normalized text,
numeric-mask and party/account-slot matches across providers, on both original
and sanitized views. This prevents sanitization from hiding earlier duplicates.
Provider IDs do not define isolation. All eight checked overlap views have zero
cross-partition matches. Allocation targets roughly 20% per existing label and
retains examples of every label in both partitions; no model score selects the split.

| Existing label | Train | Validation |
| --- | ---: | ---: |
| ANNOUNCEMENT | 121 | 39 |
| CHAT_NOISE | 280 | 70 |
| DECLINED | 101 | 19 |
| OTP | 187 | 53 |
| PROMO | 98 | 22 |
| TRANSACTION_CREDIT | 310 | 65 |
| TRANSACTION_DEBIT | 605 | 150 |

Expression provenance is verified for this source revision. The grouping is
conservative; it does not prove isolation of every semantic paraphrase or identify
which original Gemini seed produced a row. This remains a synthetic development
partition, with no independent final test or calibrated certainty claim.

## Compatibility finding before migration

The separate `legacy_v1` diagnostic agrees in Python and TypeScript:
225/226 classification matches, one false positive, zero false negatives, and no
entity mismatches on correctly accepted transactions.

`TC_EDGE_MAINTENANCE_TRAP_001` describes temporary transfer-service unavailability,
with a numeric transfer limit. After the values change, the current model accepts
the notice as a transaction. Its expected non-transaction label is retained. The
diagnostic records `migrationGatePassed: false`; do not adopt the sanitized suite
as the active passing gate or report a full compatibility pass yet.

The original 226-case baseline remains active. Fix the measured semantic failure
before migration, then retire the old exposed copies using the private snapshot
for historical comparison. None of these development results measures real-world
accuracy.

## Reproduction and verification

Run from `C:/Users/mustafa/Desktop/msroof`:

```powershell
py -X utf8 training/prepare_sanitized_corpus.py --check
py -X utf8 training/evaluate_sanitized_corpus.py --check
py -X utf8 -m unittest tests.python.test_sanitized_corpus
py -X utf8 run_all_tests.py
```

Initial preparation requires the local historical inputs and creates their private
snapshot. Subsequent checks regenerate artifacts in memory and compare exact
contents/hashes. Versioned outputs reject changed-input overwrites. A changed model,
runtime or evaluation implementation needs a new diagnostic `--run-id` rather than
rewriting `legacy_v1`. An evaluation command finishing successfully means it recorded
the measurement; `migrationGatePassed` controls whether the result clears migration.

The private snapshots and plans can exceed a local model's context window. Read
aggregate reports first and query individual IDs or fields instead of loading the
whole files.
