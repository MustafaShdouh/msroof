# Masroof Project Overview

Masroof is an offline SMS transaction-understanding engine. Given a sender and message body, it identifies genuine bank or wallet transactions, returns incoming or outgoing direction, extracts values such as amount, currency, merchant, account mask, and balance, then categorizes the transaction when enough evidence exists.

## Current scope

- Jordan only: Jordanian bank/wallet messages and local merchants in Arabic/English, with JOD as the default. Retain foreign-currency purchases made by Jordanian users; do not expand country coverage.
- Work on the ML engine only. The mobile application is in a separate project.
- `tools/browser/` is optional developer tooling. It is useful for manual inspection but does not establish runtime parity.
- Brand-to-category mappings are permitted. Do not add bank-sender registries or a general merchant registry.
- Preserve the existing runtime model until an independently evaluated replacement exceeds the documented gate.

## System layout

| Location | Contents |
| --- | --- |
| `src/typescript/` | Runtime TypeScript engine and contracts. |
| `src/python/` | Python regression mirror and contracts. |
| `training/` | Offline trainers, corpus preparation, and split generation. |
| `data/raw/` | Original SMS source material. |
| `data/training/` | Generated data, BIO labels, and grouped split. |
| `data/models/` | Legacy model and BIO perceptron exports. |
| `tests/fixtures/` | Frozen 226-case corpus and contract vectors. |
| `tests/python/`, `tests/typescript/` | Python and TypeScript checks. |
| `tools/browser/` | Optional static tester builder and generated tester. |
| `tools/generators/` | Corpus source generators. |
| `tools/legacy/` | Retired developer utilities. |

## Current evidence

- The frozen corpus has 226 cases: 106 valid transactions and 120 rejection cases.
- Both Python and TypeScript pass every frozen case, with zero false positives, false negatives, or entity mismatches.
- Preprocessing and additive transaction/direction scoring have fixed cross-language contracts.
- The BIO data and flat averaged-perceptron export are deterministic. Its training metrics are not model-selection evidence; held-out BIO evaluation is reported separately.
- The confirmed repeated-value BIO error is repaired: `TC_POS_CAP_001` labels its first `10.870` as amount and later `10.870` as balance. A 25-example coarse source-category holdout reports 87.67% token accuracy and 4% exact-sequence accuracy; BIO remains experimental and production regex extraction remains active.
- `data/training/splits/transaction_direction_split.json` is a deterministic, template-signature group split for the current 2,120-row synthetic dataset: 1,671 train rows and 449 validation rows.
- `data/models/masroof_transaction_direction_v2.json` is a separately trained candidate using exact shared additive scoring. It validates in both languages and is deterministic, but model-only frozen-corpus scoring has 17 false positives and 8 false negatives, so the legacy model remains active.
- Category learning now starts with existing merchant names and publicly sourced Amman/Irbid businesses, with human review of small batches. The 15-category target contract is in `data/annotations/`. Merchant-name labels and real SMS evaluation remain distinct.
- The rejected repetitive category experiment and its derived artifacts were removed. The replacement is a 200-business sourced corpus in `data/annotations/businesses_200.jsonl`, with readable `BUSINESSES_200.md` and a provenance manifest. It contains 142 Amman-listed and 77 Irbid-listed businesses, with 19 shared. It is not a verified popularity ranking. Existing 28 approved and 2 context-required reviews are preserved.

## Next model work

Arabic numeric formats are now supported under preprocessing contract 1.1.0: all 24 previously failing probes pass, the frozen 226-case baseline passes, and 678 numeric-script equivalence checks preserve full results per implementation. Next collect verified Arabic aliases for Jordanian merchants and improve independent Arabic category evaluation; only four businesses currently have Arabic names or aliases. Review totals are 48 approved and two context-required decisions. New batches use `batch --ambiguous --size 16`. The rejected transaction/direction v2 candidate and BIO tagger still need better evidence before integration.

## Continuation source of truth

`STATE.md` is the short status dashboard. `.agents/HANDOFF.md` is the detailed, self-contained handoff designed for a local model with a 32k context window. Keep the handoff current after material code, verification, or plan changes.

Workspace: `C:/Users/mustafa/Desktop/msroof` is authoritative. Original SMS inputs under `DATA_YOU_WANT/` and `data/raw/*.txt` stay local; `.local-backups/` contains verified pre-merge archives and is not published.
