# Masroof ML Engine

Masroof analyzes bank and wallet SMS messages. It decides whether a message is a real transaction, extracts transaction details, determines incoming or outgoing direction, and assigns an expense category when possible.

The project focuses on Jordanian bank/wallet transactions and local merchants, in Arabic and English. JOD is the default; foreign-currency purchases made by Jordanian users remain supported. The mobile app is maintained elsewhere.

Arabic-Indic and Persian digits and Arabic decimal/group separators are canonicalized under preprocessing contract 1.1.0 in training, both runtimes, and the optional browser tester. Example: `١٬٢٣٤٫٥٦٧` becomes `1,234.567` and parses as 1234.567 JOD.

## Directory layout

| Directory or file | Purpose |
| --- | --- |
| `src/typescript/` | TypeScript runtime engine and shared contracts. |
| `src/python/` | Python mirror for parity and regression evaluation. |
| `training/` | Offline dataset, split, legacy-model, and BIO tooling. |
| `data/raw/` | Source SMS samples. |
| `data/training/` | Generated training data and deterministic split artifacts. |
| `data/models/` | Runtime model artifacts. |
| `data/annotations/` | Human-reviewed category-labeling contract and future category corpus. |
| `tests/fixtures/` | Frozen regression corpus and versioned contracts. |
| `tests/python/`, `tests/typescript/` | Regression and contract runners. |
| `tools/` | Corpus generators, optional browser tester, and retired developer utilities. |
| `STATE.md` | Concise current status. |
| `.agents/HANDOFF.md` | Detailed continuation record for a new coding model. |

## Verify the baseline

Run this from the repository root:

```powershell
py run_all_tests.py
```

The command validates the frozen 226-case corpus, both cross-language contracts, and the Python and TypeScript regression engines.

## Developer commands

```powershell
# Architecture checks
py tests/python/test_new_architectural_features.py
& 'C:\Program Files\nodejs\node.exe' tests/typescript/test_new_architectural_features.ts

# Rebuild deterministic BIO data and its flat perceptron model
py training/build_bio_training_set.py
py training/train_sequence_tagger.py
py training/evaluate_bio_sequence_tagger.py

# Recreate the transaction/direction grouped split
py training/prepare_transaction_direction_split.py

# Train and evaluate the separate v2 transaction/direction candidate
py training/train_transaction_direction_v2.py

# Audit and train standalone merchant-name category research candidates
py training/audit_category_corpus.py
py training/train_merchant_category.py

# Rebuild the optional browser playground
py tools/browser/build_tester_ui.py

# Prepare a small merchant-category review batch
py training/prepare_merchant_candidates.py
py training/merchant_review.py batch --size 12

# Review ambiguous category boundaries using clearly marked illustrative examples
py training/merchant_review.py batch --edge-cases --size 18

# Build the sourced 200-business corpus and review a small batch
py training/build_business_shortlist.py
py training/merchant_review.py batch --businesses --size 20
```

Open `tools/browser/merchant_review.html` to review the batch. It downloads decisions for import with `py training/merchant_review.py import <downloaded-file>`. See `data/annotations/MERCHANT_REVIEW.md` for the workflow.

The legacy transaction/direction trainer remains available at `training/train_and_export.py`. The v2 candidate is written to `data/models/masroof_transaction_direction_v2.json` with its report in `data/reports/`. Do not replace `data/models/masroof_model.json` until a candidate has passed the documented held-out and frozen-baseline gates in `.agents/HANDOFF.md`.

Merchant-category research uses only labeled training businesses and preserves the
reserved validation/test split. Three separate flat exports compare canonical names,
sourced aliases and bounded synthetic perturbations. Results are in
`data/reports/merchant_category_research.md` and its JSON companion. Human and assistant
label metrics are separate, scores are uncalibrated, and final test inference is
disabled during development. These candidates do not change the active SMS engine.

Workspace: `C:/Users/mustafa/Desktop/msroof` is authoritative. Original SMS inputs under `DATA_YOU_WANT/` and `data/raw/*.txt` stay local; `.local-backups/` contains verified pre-merge archives and is not published.
