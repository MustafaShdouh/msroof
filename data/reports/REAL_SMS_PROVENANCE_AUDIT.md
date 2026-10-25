# Real SMS source audit

Read-only audit of user-attested seed files. No bank authentication or independent accuracy claim.

Located **26 message blocks**; no new messages admitted for training or independent evaluation.

| Source | Message blocks | Raw copy identical |
| --- | ---: | --- |
| arab-seeds | 16 | yes |
| capital-seeds | 10 | yes |

| Corpus | Records scanned | Seeds with observed text overlap | Seeds with any candidate |
| --- | ---: | ---: | ---: |
| legacy_transaction_data | 2120 | 0 | 19 |
| bio_training | 83 | 7 | 14 |
| frozen_regression | 178 | 16 | 23 |
| frozen_adversarial | 48 | 0 | 5 |
| unresolved_raw:BANK_AL_ETIHAD | 12 | 0 | 0 |
| unresolved_raw:CHAT_NOISE | 17 | 0 | 0 |
| unresolved_raw:HOUSING_BANK | 11 | 0 | 0 |
| unresolved_raw:ORANGE_MONEY | 11 | 0 | 0 |
| unresolved_raw:REFLECT | 12 | 0 | 0 |
| unresolved_raw:UWALLET | 11 | 0 | 0 |
| unresolved_raw:ZAIN_CASH | 11 | 0 | 0 |

BIO rows verified as exact fixture copies by ID and text: 83/83.

Privacy finding: **16 seed blocks match text in a fixture included in the previously pushed snapshot**. Raw-file ignore rules do not protect embedded copies. Prepare a sanitized version and preserve the historical baseline privately; remote-history changes require separate authorization. Current repository visibility was not checked.
Training CSV equals the JSON's reduced fields after CRLF/LF normalization: True. Text rows differing only in line endings: 1463.

Historical AI account: 1950 rows; current generator/data: 2120 rows, reproducible in memory. The historical artifact is unavailable.

Other raw blocks with unresolved origins: 85. Seed blocks containing Arabic script: 5 (script presence only, not accuracy).

Observed normalized-text duplication across current training/validation: **16 groups / 150 rows**, across provider metadata. No existing-label conflicts in these groups: True.

Current training/validation numeric-mask proxy overlap: 50 groups across 424 rows. These are candidates, not verified source families; assignments remain unchanged.

Confirmed Gemini parent edges: **0**. Similarity scores are matching heuristics, not certainty probabilities.

Record locators, redaction drafts, and candidate links are stored only under ignored `data/private/sms_provenance/`.
No public report contains message text, party names, account values, dates, codes, or per-message content hashes.

Limits:

- File blocks are not authenticated SMS packet boundaries.
- Exact/normalized overlap establishes content reuse, not historical parentage.
- Number masking/similarity are candidate evidence only; unmatched rows do not prove independence.
- Current train/validation normalized duplicates cross provider metadata; provider-local grouping is not content isolation.
- The previously pushed fixture snapshot embeds original-seed text; ignoring raw/private files does not remove those historical copies. Versioned sanitization and separately authorized remote-history remediation are needed.
- Other raw files have unresolved origins. A user-pasted historical AI account supplies no per-row Gemini ancestry.
- Sanitized drafts are private and unadmitted; no new labels or public message text.
- The existing merchant final-test reservation remains separate and unevaluated.

Next: review/supplement origin evidence and sanitized drafts; acquire fresh unexposed families before independent evaluation.
