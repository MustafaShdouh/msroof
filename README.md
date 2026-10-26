# Masroof

An offline engine for Jordanian bank and wallet SMS, in Arabic and English. It identifies completed transactions, extracts amounts and direction, preserves exact party names, and categorizes spending when the message supplies enough context. Missing or ambiguous currency defaults to JOD with a visible marker.

Person-to-person transfers count. Own-account transfers are excluded. Unclear completion, direction or ownership requires review. The mobile app is maintained separately.

## Start here

- [Architecture and file map](docs/ARCHITECTURE.md): where code belongs, active versus research components, and recovery.
- [Transaction contract](docs/TRANSACTION_BEHAVIOR.md): current rules and the proposed optional ownership API.
- [Measured behavior](docs/BEHAVIOR_EVALUATION.md): development results, known gaps and rejected candidates.
- [Entity research](docs/BIO_EVALUATION.md): corrected BIO labels and isolated experiments.

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

# Reproduce the current source-bound layout/behavior measurement
py -X utf8 -m training.evaluation.detailed --run-id cleanup_layout_v1 --check

# Check transaction candidate inputs without fitting
py -X utf8 -m training.transactions.train --check-inputs

# Rebuild the standalone offline tester
py -X utf8 tools/browser/build_tester_ui.py
```

Open [the tester](tools/browser/tester.html). It uses the canonical TypeScript bundle. Its detailed assessment comparison supports review/uncertainty; the default legacy caller path is retained while compatibility is evaluated.

For merchant review, use `py -m training.categories.review --help` and [the labeling workflow](data/annotations/MERCHANT_REVIEW.md). Merchant-name research is separate from transaction-purpose classification; its reserved final identities must remain untouched.

## Runtime versus research

Python callers import `MasroofEngine` from `src.python.engine`. TypeScript callers use `src/typescript/MasroofEngine.ts`. The active weights remain `data/models/masroof_model.json`. Research models, reports and reservations retain their original paths and bytes so prior results remain auditable; they are not automatically loaded as replacements.

Historical reports bind their original code hashes. Run historical reproduction from those recorded sources, not by overwriting frozen artifacts to match relocated code. The new cleanup report records the current paths. Training, final evaluation and model promotion remain separate decisions.

## Private files and recovery

`STATE.md`, `.agents/`, `DATA_YOU_WANT/`, `data/raw/*.txt`, `data/private/` and `.local-backups/` stay local and ignored. Real seeds are development-exposed and cannot serve as an independent final test. See [source intake](data/annotations/REAL_SMS_INTAKE.md) and [corpus provenance](docs/SANITIZED_CORPUS.md).

Before this cleanup, all publishable work was pushed at `fbb96e19293cb61a140ecfe6a65551613d93d9b9`, tagged **`checkpoint/pre-cleanup-2026-10-26`**. The checkpoint preserves the old source layout and removed public files. Private source archives need their own local backup and were preserved.
