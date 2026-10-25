# Real Jordan SMS provenance and collection

User clarification, 2026-10-24: approximately20 actual Arab Bank messages and10
actual Capital Bank messages were supplied to Gemini Flash to generate more
messages. The originals folder DATA_YOU_WANT is located in msroof. Its two files exactly match data/raw/ARAB_BANK.txt and data/raw/CAPITAL_BANK.txt. The hash-bound audit finds 16 Arab Bank and 10 Capital text blocks; the user's earlier counts remain approximate, not overwritten. File-block boundaries are recoverable, while authentic packet boundaries, reviewed labels, and exact Gemini parents remain unconfirmed.
Canonical source account: `data/sources/transactions/jordan_context_evidence.json`.

The files in `data/raw/` do not acquire real/synthetic labels based on their bank
filename, realistic wording, dates or masked accounts. Until traced, origin is
unresolved. Do not modify those files or count every row as a real bank message.

The original seeds can support development once individually identified, sanitized
and checked. They are already development-exposed through generated descendants;
they do not become a fresh independent test just because the originals are found.
Keep originals and all descendants/template relatives together when allocating data.
The existing merchant final-test reservation remains separate and unevaluated.

For each identified original, retain: stable record ID, source file/record locator,
origin `real_user_supplied`, sanitization history, collection date if known,
template/source-family ID, and links to known generated descendants. Unknown values
stay null. Sender/bank strings may be provenance metadata, not a runtime registry.
Capture Gemini output origin and parent families separately. Untraceable rows remain
unresolved; do not fabricate parent IDs or original text.

Before admitting a record, check normalized exact duplicates, template overlap and
brand aliases against legacy training, the226 frozen fixtures and category folds.
Classify completed/failed/OTP/notice status first. Then review amount, currency,
direction and purpose where present. Abstain when a service, fee, installment or
transfer purpose cannot be recovered from message/context. Human-reviewed completed
category records still follow `category_annotation_schema.json`; assistant merchant
defaults are not human SMS labels.

Official FAQ/service pages collected in the evidence file describe workflows and
annotation pitfalls. They contain no newly collected completed transaction SMS.
Their paraphrases are not extra training examples, held-out truth or measured accuracy.
Do not manufacture realistic messages to fill that gap.

Next: review sanitized drafts and labels, repair development split isolation in a
new version, and obtain newly collected unexposed Jordanian Arabic template/source
families for independent evaluation.
No specific collection license, sharing permission or bank-message availability is
inferred from a public webpage.

Repository merge: msroof is the authoritative workspace. DATA_YOU_WANT, raw text inputs and .local-backups are local-only and excluded from GitHub. Earlier Git history containing raw inputs is retained locally; the published main branch begins with a clean project snapshot.

## Audited records and reproducible exposure report

Run `py -X utf8 training/audit_sms_provenance.py`; use `--check` to recompute and
compare saved outputs without writing. Source hashes/counts are frozen in
`data/sources/transactions/seed_audit_manifest.json`; a changed original or raw
copy requires explicit source review. Original messages, models, frozen fixtures,
and existing splits are checked for unchanged hashes across the audit.

The canonical provenance-record contract is `config/contracts/sms_provenance_record.json`.
Private output is `data/private/sms_provenance/seed_audit.json`, ignored by Git:
26 stable IDs with source line/character locators, private fingerprints, redaction
drafts/span maps, and candidate exposure links. Sender/collection time/labels/
verified family/parent fields stay null where unknown. Drafts are not certified
anonymization or admitted training data. Numbered placeholders identify matched
spans/values, not proven distinct people or account ownership; fragmented wrapped
names require review before labels or model use. All 26 seeds are development-exposed and
ineligible for independent evaluation even after sanitization.

Public outputs are aggregate counts only: `data/reports/real_sms_provenance_audit.json`
and `REAL_SMS_PROVENANCE_AUDIT.md`. Exact or normalized matching proves content
overlap; number masking and lexical similarity suggest template overlap, not
parentage. No Gemini parent edges are fabricated. Whole-word business-name scans
flag lexical candidates only and perform no category predictions or final-test inference.

The user's pasted historical AI account describes 1,950 generated rows; the
current inspected generator reproduces all 2,120 current records and their order
in memory. Evidence/hashes are recorded in `generation_history.json`. The original
1,950-row artifact and per-row Gemini ancestry were not supplied. AI claims of
100% accuracy, near-zero false positives, or production readiness are not
independent evaluation evidence.

The current split contains 16 normalized-identical groups (150 rows: 109 train,
41 validation) across provider metadata, with no existing-label conflicts. A
further 50 numeric-mask proxy groups span 424 rows across folds. The latter are
candidate template links, not proven families. This audit preserves historical
assignments; future development must isolate content/templates across providers
in a new version before training comparisons.

Historical publication finding: 16 source blocks match normalized text in the
tracked regression fixture included in the previously verified pushed snapshot
`f840390df1a7c6cbca668eb38bdf363297156f64`. Local Git blob identity confirms this;
current remote visibility/revision was not queried. Excluding raw files did not
exclude their embedded copies. Prepare a reviewed sanitized corpus version,
preserve the historical baseline privately, and obtain separate approval for
remote history changes. This audit performs no removal, rewrite, or push.

Prepared follow-up: `docs/SANITIZED_CORPUS.md` describes a synthetic privacy-transformed
replacement and a provider-agnostic grouped split. It does not admit the real seeds,
change this audit's historical inputs, or solve prior publication by itself. A
recorded maintenance-notice false positive blocks active regression-gate migration.
