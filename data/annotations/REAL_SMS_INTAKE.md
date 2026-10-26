# Real Jordan SMS provenance and collection

User clarification, 2026-10-24: approximately20 actual Arab Bank messages and10
actual Capital Bank messages were supplied to Gemini Flash to generate more
messages. The originals folder DATA_YOU_WANT is located in msroof. Its two files exactly match data/raw/ARAB_BANK.txt and data/raw/CAPITAL_BANK.txt. The hash-bound audit finds 16 Arab Bank and 10 Capital text blocks; the user's earlier counts remain approximate, not overwritten. File-block boundaries are recoverable, while authentic packet boundaries, reviewed labels, and exact Gemini parents remain unconfirmed.
Canonical source account: `data/sources/transactions/jordan_context_evidence.json`.

The files in `data/raw/` do not acquire real/synthetic labels based on their bank
filename, realistic wording, dates or masked accounts. Until traced, origin is
unresolved. Do not modify those files or count every row as a real bank message.

Owner clarification,2026-10-26: the four original Arab Bank “You have a purchase
transaction” blocks (`arab-seeds-001`,002,004,011) were actual purchases with money
deducted. Named Capital transfers remain **Mixed or unknown** for ownership;
no per-record own/external labels were assigned. Supplemental private evidence
and before/after diagnostics are `data/private/sms_provenance/completion_transfer_evidence_v1.json`
and `completion_transfer_after_v1.json`. All26 original blocks have three-runtime
parity; the four confirmed purchases now include. Original source bytes/audit
labels and admission flags remain unchanged; this clarification does not make
the exposed seeds an independent evaluation set or authenticate arbitrary SMS.

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

## Targeted web review,2026-10-26

The owner has no additional original withdrawal messages and requested an
internet search. Four published examples were located in the
[money-tracker source tests](https://github.com/AvAl4nch/money-tracker/tree/6616c7d85c5599e5da1c46613e444c4738d76a58/app/src/test/java/ava/sluff/money_tracker/sms):
one Arabic ATM movement, two Arabic authorization formats and one English OTP.
Two have explicit author claims of a real message/format, including sanitized
digits on one format. The other two are fixtures with unresolved origins. The
[MIT notice](https://github.com/AvAl4nch/money-tracker/blob/6616c7d85c5599e5da1c46613e444c4738d76a58/LICENSE)
and exact source bytes are preserved locally. This is a source lead, not a
verified real-message dataset or a claim that the source author's parser is
correct.

Private review: `data/private/entity_intake/web_review_v1/review.json`; its
companion README describes the source snapshots and optional future intake file.
Assistant annotations record exact visible amount/currency/account/balance/name
spans without copying old validation failures. Zero exact/numeric-proxy matches
were observed against active synthetic transactions, BIO and226 fixtures; this
limited audit does not establish independent families. All four remain
quarantined, with training/BIO/independent-evaluation admission false. Initial
collection ran no inference; the subsequent diagnostic is recorded below. No
fitting was run. The ATM wording does not state direction, one
merchant boundary contains unresolved city/country text, and authorization
completion is unconfirmed. The OTP is not a completed movement.

Other checked leads were unsuitable for the requested real Jordan evidence:
[APG's disclosure](https://github.com/hashme-husban/APG-Arabic-Phishing-Guard/blob/main/docs/DATASET_SUMMARY.md)
describes synthetic SMS, the visible
[FlashFlow bank-SMS rows](https://huggingface.co/datasets/4-alokk/flashflow-bank-sms)
use Indian banking/INR/UPI formats, and
[Sarfi's page](https://sarfi.app/) presents a product demonstration rather than
a received-message dataset. Bank/provider service pages, including
[Arab Bank SMS Express](https://www.arabbank.jo/mainmenu/home/ways-to-bank/sms)
and [UWallet's withdrawal flow](https://uwallet.jo/our-services/), explain alert
types or OTP-before-cash workflow without supplying new completed-SMS bodies.
No usable credited-cashback SMS or source-confirmed Arabic ATM/operator-name
example was located in this search. This does not claim none exists online.

Review disposition,2026-10-26: retain all four outside training and independent
evaluation. Their supported uses are source-attributed development diagnostics:
the OTP requires exclusion, while the ATM direction and settled completion of
the authorization examples remain unresolved. Observed numeric/name spans are
partial annotations, not complete receipt labels. In particular, an unknown
merchant boundary must not become an absent-merchant label. No training admission
is implied by this review or its diagnostic run.

Private diagnostic: `data/private/entity_intake/web_review_v1/diagnostic_v1.json`.
Before the OTP repair, with the sender left empty, the Python/TypeScript/browser engines accept
all four as outgoing transactions. The OTP is a definite false inclusion under
the approved specification and produces the spurious merchant `complete`.
For the other three, the legacy boolean API cannot express the required review
outcome; this is not evidence that those messages were definitely failed or
definitely settled. All three runtimes agree after removing validated Python
compatibility aliases. Scores are uncalibrated, not correctness probabilities.

The isolated context BIO candidate also agrees across Python/TypeScript features
and predictions. On these new formats, none of the annotated numeric/account
slots match; the one reviewed absent merchant remains absent. The known JO-PETROL
name also does not match. The unresolved C TOWN boundary is not scored as absent,
and positive receipt BIO metrics are not applied to the OTP. This tiny,
assistant-reviewed, now-exposed diagnostic is not a general accuracy estimate.
The report binds source/model hashes; no fitting or reserved merchant-final
inference was performed and input/model bytes stayed unchanged.

Additional official context checked: [UWallet's Arabic FAQ](https://uwallet.jo/faqs/)
distinguishes a pre-withdrawal OTP from the alert after successful cash collection;
[Arab Bank SMS Express](https://www.arabbank.jo/mainmenu/home/ways-to-bank/sms)
lists both ATM withdrawals and deposits. These workflow descriptions do not
resolve the direction of the published generic ATM fixture and supply no new SMS
bodies. The extended search yielded no additional usable credited-cashback body.

OTP repair completed2026-10-26: the source OTP is now rejected in Python/TS/browser,
without returning entity data. The private
`data/private/entity_intake/web_review_v1/diagnostic_after_otp_fix_v1.json` records
the replay and source hashes; other three outputs are unchanged. Before/after
inputs are preserved in deduplicated private snapshots. Public authored controls
and the shared grammar are described in `docs/BEHAVIOR_EVALUATION.md`. All four
source examples remain diagnostic-only. The broader uncertain/review API remains
a separately scoped contract gap.

Detailed API replay after parsing repair,2026-10-26:
`data/private/entity_intake/web_review_v1/detailed_parsing_v2.json` confirms
the OTP as non_transaction/exclude and the other three as uncertain/review in
Python, TypeScript and the browser. The legacy path is still retained separately.
This resolves output representation in the new API, not source authenticity or
the unresolved C TOWN name boundary. All four remain exposed development
diagnostics, with no training or independent-evaluation admission.

Repository merge: msroof is the authoritative workspace. DATA_YOU_WANT, raw text inputs and .local-backups are local-only and excluded from GitHub. Earlier Git history containing raw inputs is retained locally; the published main branch begins with a clean project snapshot.

## Audited records and reproducible exposure report

Run `py -X utf8 -m training.corpus.audit`; use `--check` to recompute and
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

The archived historical split contains 16 normalized-identical groups (150 rows: 109 train,
41 validation) across provider metadata, with no existing-label conflicts. A
further 50 numeric-mask proxy groups span 424 rows across folds. The latter are
candidate template links, not proven families. This audit preserves historical
assignments. Current development uses the new globally grouped sanitized split;
the historical audit reads checked private snapshots after working-copy retirement.

Historical publication finding: 16 source blocks match normalized text in the
tracked regression fixture included in the previously verified pushed snapshot
`f840390df1a7c6cbca668eb38bdf363297156f64`. Local Git blob identity confirms this;
current remote visibility/revision was not queried. Excluding raw files did not
exclude their embedded copies. Prepare a reviewed sanitized corpus version,
preserve the historical baseline privately, and obtain separate approval for
remote history changes. This audit performs no removal, rewrite, or push.

Current follow-up: `docs/SANITIZED_CORPUS.md` describes the synthetic replacement,
global development split, migrated consumers and 12 retired working copies. The
service-notice repair clears all 226 sanitized regression cases. Real seeds remain
unadmitted and the historical audit's archived inputs remain unchanged. Old Git
history and learned vocabulary still require separate consideration; retirement
does not solve prior publication by itself.
