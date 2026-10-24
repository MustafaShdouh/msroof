# Jordan merchant-category corpus audit

Metadata audit, not a model evaluation. All counts are distinct businesses; aliases do not increase sample size.

| Category | Train human | Train assistant | Train total | Validation total | Test total |
| --- | ---: | ---: | ---: | ---: | ---: |
| Telecom | 2 | 0 | 2 | 0 | 0 |
| Water and Electricity | 0 | 0 | 0 | 0 | 1 |
| Food | 4 | 56 | 60 | 15 | 11 |
| Groceries | 4 | 2 | 6 | 1 | 2 |
| Transportation | 0 | 0 | 0 | 2 | 0 |
| Subscriptions | 0 | 0 | 0 | 0 | 0 |
| Shopping | 10 | 44 | 54 | 8 | 11 |
| Health | 5 | 1 | 6 | 1 | 2 |
| Entertainment | 3 | 7 | 10 | 1 | 2 |
| Education | 1 | 0 | 1 | 0 | 0 |
| Travel | 1 | 0 | 1 | 0 | 0 |
| Cash Withdrawals | 0 | 0 | 0 | 0 | 0 |
| Installments | 0 | 0 | 0 | 0 | 0 |
| Fees | 0 | 0 | 0 | 0 | 0 |
| Other | 1 | 0 | 1 | 0 | 0 |

Missing training categories: Water and Electricity, Transportation, Subscriptions, Cash Withdrawals, Installments, Fees.

Cross-fold exact-form conflicts: 0. Verified-family cross-fold conflicts: 0. Family coverage is bounded, not exhaustive.

Known family: Inditex (Lefties, Massimo Dutti, Oysho, Stradivarius, ZARA, ZARA Home), all in training. Source: https://annualreport.inditex.com/anrpxxvui/en/our-drivers

Historical SMS mentions and input hashes are in category_corpus_audit.json. Generic names may produce false identity matches. Do not mix legacy SMS into new fitting data without auditing its held-out business and template overlap.

Bounded augmentation protocol: begin with observed training aliases, then at most one feature-changing synthetic variant per training business; keep equal business weight and untouched holdouts. It cannot create missing categories or independent test truth. This audit does not train models; see merchant_category_research.json for experiment status.

Research basis: [EDA text augmentation paper](https://aclanthology.org/D19-1670/) and [scikit-learn leakage guidance](https://scikit-learn.org/stable/common_pitfalls.html). These do not establish effectiveness for Jordanian SMS; use a controlled local A/B experiment.
