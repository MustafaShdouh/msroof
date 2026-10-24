# Real Jordan SMS provenance and collection

User clarification, 2026-10-24: approximately20 actual Arab Bank messages and10
actual Capital Bank messages were supplied to Gemini Flash to generate more
messages. The originals folder DATA_YOU_WANT has now been located in msroof. Its two files exactly match data/raw/ARAB_BANK.txt and data/raw/CAPITAL_BANK.txt. Per-message boundaries and generated descendant links still need audit.
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

Next: locate originals, audit their development exposure, and obtain newly collected
unexposed Jordanian Arabic template/source families for independent evaluation.
No specific collection license, sharing permission or bank-message availability is
inferred from a public webpage.

Repository merge: msroof is the authoritative workspace. DATA_YOU_WANT, raw text inputs and .local-backups are local-only and excluded from GitHub. Earlier Git history containing raw inputs is retained locally; the published main branch begins with a clean project snapshot.
