# Masroof

An offline engine for Jordanian bank and wallet SMS, in Arabic and English. Current work focuses on transaction recognition, amount/currency and incoming/outgoing direction. Categorization and business-name prediction are deferred; existing category APIs remain for compatibility. Missing or ambiguous currency defaults to JOD with a visible marker.

Person-to-person transfers count. Own-account transfers are excluded. Unclear completion, direction or ownership requires review. The mobile app is maintained separately.

## Start here

- [Tester checklist](docs/CORE_TESTER_CHECKLIST.md) for examples and expected results.
- [Current readiness](docs/CORE_MONEY_READINESS.md) for verified behavior and remaining gaps.
- [Core-money roadmap](docs/CORE_MONEY_ROADMAP.md) for the current scope and next steps.
- [Transaction contract](docs/TRANSACTION_BEHAVIOR.md) for recording, amounts and ownership.
- [Architecture](docs/ARCHITECTURE.md) for the runtime and research components.

Historical experiment reports remain under `data/reports/transactions/`. Six older research summaries are available in Git history at commit `923b701`.

## Layout

```text
src/
  python/engine.py          Python reference engine
  typescript/MasroofEngine.ts  TypeScript engine
  */research/              Isolated candidate scorers
training/
  corpus/                  Privacy, provenance and corpus preparation
  transactions/            Transaction/direction candidates
  entities/                BIO labels, learner and evaluation
  categories/              Merchant collection, review and research
  evaluation/              Runtime behavior and compatibility reports
  corpus_io.py             Frozen inputs, immutable outputs and snapshots
tools/
  browser/                 Offline tester and review pages
  evaluation/              TypeScript/browser diagnostic bridges
  contracts/               Target-contract validation
tests/                     Discovered Python/TypeScript safeguards and frozen fixtures
data/                      Versioned inputs, annotations, models and evidence
config/                    Shared contracts and development dependencies
docs/                      Specifications, architecture and evaluation notes
```

## Set up and verify

The checked development environment uses Python 3.14 and Node.js 24. The Python runtime engine itself uses the standard library; training and the full research checks also need:

```powershell
py -m pip install -r config/requirements-dev.txt
py -X utf8 run_all_tests.py
```

The runner discovers all Python test modules and TypeScript suites, then checks the frozen 226-case legacy corpus. It does not train or promote a production candidate. Development results are not independent real-world accuracy.

```powershell
# Validate the transaction contract
py -X utf8 tools/contracts/validate_transaction_behavior.py

# Check ownership controls and unchanged no-context behavior
py -X utf8 -m training.evaluation.arabic_semantics --run-id arabic_message_semantics_v1 --check

# Check transaction candidate inputs without fitting
py -X utf8 -m training.transactions.train --check-inputs

# Rebuild the standalone offline tester
py -X utf8 tools/browser/build_tester_ui.py
```

Open [the tester](tools/browser/tester.html). Its main assessment uses the detailed TypeScript engine. The optional ownership panel and legacy comparison have separate results.

Expand **Try an ownership confirmation** to test a transfer with an explicit
**My own accounts**, **Another person**, or **I'm not sure** choice. The panel shows
the optional assessment separately. Editing the message or sender, changing the
contact setting, loading a sample, choosing **New message**, or refreshing clears
the confirmation. It stays in page memory and is never saved as a training label.
The **Paired debit / credit** sample now supports this panel: confirming own accounts
excludes the completed movement; confirming another person keeps review when the
message does not resolve direction.
The primary **Message-only assessment** shows include/review/exclude, completion,
amount, visible currency defaults, direction, ownership and reasons from the
repaired parser. **Legacy comparison** retains the previous caller in a collapsed
panel. Ownership confirmations remain separate from the message-only result.
If startup checks fail, the page shows **Engine not ready** and does not analyze
messages. This is separate from include, review and exclude decisions.

For merchant review, use `py -m training.categories.review --help` and [the labeling workflow](data/annotations/MERCHANT_REVIEW.md). Merchant-name research is separate from transaction-purpose classification; its reserved final identities must remain untouched.

## Runtime versus research

Python callers import `MasroofEngine` from `src.python.engine`. TypeScript callers use `src/typescript/MasroofEngine.ts`. The active weights remain `data/models/masroof_model.json`. Research models, reports and reservations retain their original paths and bytes so prior results remain auditable; they are not automatically loaded as replacements.

To try the saved transaction/direction candidate, open `tools/browser/tester.html`
and expand **Try the trained model** in Analysis. This optional local comparison
shows learned predictions separately from existing extraction and recording
checks. **Research model** lets you switch between **Word reference** (the default)
and **Word sequences · experimental**. The latter has known regressions, including
an OTP false acceptance. Neither replaces the current engine; see
[tester instructions and measured limits](docs/SMS_DATA_COVERAGE.md#completion-context-experiment-2026-10-27).

The [next completion-model proposal](docs/SMS_DATA_COVERAGE.md#proposed-pretrained-completion-benchmark-2026-10-27)
compares a frozen pretrained multilingual encoder before investing in a compact
sequence student. It is a proposed research benchmark; no new model has been
trained or selected for deployment.

For an explicit human ownership confirmation, use `predict_with_ownership(request)`
or `analyzeWithOwnership(request)`; see the transaction contract for the message-bound
request. Existing detailed and legacy entry points keep their behavior.

Historical reports bind their original code hashes. Run historical reproduction from those recorded sources, not by overwriting frozen artifacts to match relocated code. The new cleanup report records the current paths. Training, final evaluation and model promotion remain separate decisions.

## Private files and recovery

`STATE.md`, `.agents/`, `DATA_YOU_WANT/`, `data/raw/*.txt`, `data/private/` and `.local-backups/` stay local and ignored. Real seeds are development-exposed and cannot serve as an independent final test. See [source intake](data/annotations/REAL_SMS_INTAKE.md) and [corpus provenance](docs/SANITIZED_CORPUS.md).

Before this cleanup, all publishable work was pushed at `fbb96e19293cb61a140ecfe6a65551613d93d9b9`, tagged **`checkpoint/pre-cleanup-2026-10-26`**. The checkpoint preserves the old source layout and removed public files. Private source archives need their own local backup and were preserved.
