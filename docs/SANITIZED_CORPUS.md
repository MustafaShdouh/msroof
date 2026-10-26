# Sanitized corpus v1 and grouped development split

This version provides replacements for the exposed legacy data. The sanitized
226-case suite is now the active regression gate after the service-notice repair.
The model weights are unchanged; this work has not trained a replacement model.
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
| `data/reports/sanitized_corpus_v1_service_notice_v1_evaluation.json` | Passing diagnostic after the service-notice repair; retains the earlier failing report. |

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
Twelve legacy working files are now retired after private hash-checked preservation;
the mapping is `config/contracts/corpus_layout.json`. Old Git objects and learned
legacy model vocabulary remain. This is not complete repository anonymization;
remote-history changes require separate authorization.

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

## Compatibility and active gate

The historical `legacy_v1` diagnostic agreed in Python and TypeScript:
225/226 classification matches, one false positive, zero false negatives, and no
entity mismatches on correctly accepted transactions.

`TC_EDGE_MAINTENANCE_TRAP_001` describes temporary transfer-service unavailability,
with a numeric transfer limit. Changing numeric values exposed the legacy model's
false positive. Its expected non-transaction label and the original diagnostic
remain intact.

The shared grammar in `config/contracts/service_notice.json` now rejects service
unavailability/restoration notices while allowing explicit completed receipts
with an appended maintenance reminder. Python, TypeScript and the generated
browser use the same patterns. This is a runtime safeguard, not model retraining.
The new `service_notice_v1` evaluation records 226/226 correct classifications,
zero false positives/negatives/entity mismatches and Python/TS metric parity.
The original 226-case gate also passed before switching defaults to sanitized_v1.

The consolidated runner, standalone Python/TS suite runners, corpus validator and
numeric-script checks now default to the frozen sanitized fixtures. Seventeen
authored notice/control cases check the grammar and full canonical results in
Python, TS and browser; Python's duplicate compatibility aliases are validated
before comparison. Existing confidence conventions are not calibrated certainty.
This bounded grammar is not a complete multi-event message parser. A separate
task has migrated historical data consumers and retired exposed copies using the
private snapshots, as described below. These results do not measure real-world accuracy.

## Reproduction and verification

Run from `C:/Users/mustafa/Desktop/msroof`:

```powershell
py -X utf8 -m training.corpus.prepare --check
py -X utf8 -m training.evaluation.regression --run-id canonical_exact_names_v1 --check
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

## Consumer migration and recovery

`training/corpus_io.py` identifies the active dataset, frozen split, fixtures and
sanitized BIO drafts. It checks active dataset/split hashes against the preparation
report. Historical readers resolve only registered, contained, hash-matching files,
with no silent fallback to a different working version.

| Consumer | Current inputs and outputs |
| --- | --- |
| Transaction/direction split tool | Validates the existing global split; does not recreate the old provider-local split. |
| Transaction/direction trainer | Sanitized rows/split/fixtures. `--check-inputs` does no fitting; fitting requires a fresh `--run-id` and writes candidate artifacts. |
| Legacy TF-IDF trainer | Retained experiment, with sanitized grouped input/shared preprocessing and direction fitted on training rows only. Requires a new `--output`; export/runtime math remains unsuitable for promotion. |
| BIO builder/train/evaluator | 83 sanitized heuristic drafts under `data/training/sanitized_v1/`; metadata binds source/builder hashes and marks labels unreviewed. Trainer/evaluator require new run IDs. Label repair remains a separate task. |
| Historical provenance audit | Reproduces its frozen report from private original inputs and original auditor/BIO-builder hashes. Its findings describe the old corpus/split. |
| Corpus preparation | Reproduces byte-identical artifacts from the closed snapshot. The frozen builder hash refers to the archived preparation implementation; the current access adapter has evolved. |
| Category exposure audit | Reads old SMS from private archives and writes `category_corpus_archive_audit_v1.json`/Markdown, preserving earlier reports. No category prediction or final-test inference. |
| Arabic diagnostic | Reads sanitized fixtures; writes `arabic_support_sanitized_v1_*`. |
| Merchant candidate preparation | Reads 57 extracted commercial names from `synthetic_merchant_names_v1.json`, avoiding the old personal-message generator. Writes a new candidate file; existing reviewed inputs stay intact. |
| Browser tester | All 14 controls use synthetic examples from `tools/browser/presets.json`. |

The old dataset JSON/CSV, BIO file, split, three fixture files, three generators,
saved Arabic probe and duplicate test runner are removed from the working tree.
Their paths are ignored against accidental recreation. The duplicate runner's
exact amount/direction checks are retained on all 106 accepted cases; currency
checks honor the historical `$`/`€` ISO aliases without editing truth. Result:
`data/reports/legacy_corpus_retirement_v1.json`.

Original data/code/model versions remain in `data/private/historical_corpus_v1/`.
Fifteen additional pre-migration tools/probe files are preserved under
`data/private/legacy_tools_v1/`. Both manifests bind exact hashes. For recovery,
inspect a registered private copy or copy it to another ignored private location;
preserve the closed snapshots. These archives are local and need a private backup
when moving the workspace. A public clone can use sanitized inference/regression
without originals; private-evidence tests skip when unavailable. Never recover
private evidence from old Git history just to run public-clone tests.

```powershell
py -X utf8 -m training.transactions.split
py -X utf8 -m training.transactions.train --check-inputs
py -X utf8 -m training.corpus.retire --check
py -X utf8 -m training.corpus.scan --check
py -X utf8 -m training.corpus.audit --check
```

At the sanitization milestone,79 safeguards and the226-case Python/TS gate passed; current behavior/refactor
details are in `docs/BEHAVIOR_EVALUATION.md`. The sanitized Arabic
diagnostic passes 111 Arabic-containing cases (49 accepted transactions with
correct amount/currency/direction), plus three eight-case digit/separator groups
in each engine. These remain development checks.

`known_seed_copy_scan_v1.json` records zero matching working paths for the 26 known
complete seed blocks after Unicode/digit/whitespace normalization and JSON decoding.
The scan includes tracked and nonignored working text. Partial identifiers,
paraphrases, unknown private data, model vocabulary and old Git objects are outside
that check. Retirement changes the working tree; commit/publication/history cleanup
are separate actions. That migration step performed no fitting or promotion.
Subsequent research trained two transaction candidates and rejected both; existing
weights remain unchanged, and no reserved merchant-test inference occurred.
