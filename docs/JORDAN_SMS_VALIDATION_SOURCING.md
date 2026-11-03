# Jordan SMS validation sourcing — 2026-11-02

No suitable publicly downloadable **independent Jordan transaction-SMS corpus**
was confirmed in this bounded search. This is a finding about the checked leads,
not proof that no dataset exists. No messages were manufactured, no new message
bodies were collected, and no fitting, inference, reservation access or outreach
occurred. The private evaluation intake remains empty.

The source ledger is
`data/sources/transactions/validation_source_review_20261102.json`: 15 English/
Arabic search queries, nine reviewed sources and two incompletely inspected
leads. It records dates, publisher statements, task fit, prior exposure and holds.
Dataset licensing metadata is recorded as a claim, not a reuse determination.

## Checked sources

| Source | What was established | Decision for this project |
| --- | --- | --- |
| [APG Jordan-context phishing project](https://github.com/hashme-husban/APG-Arabic-Phishing-Guard/blob/main/docs/DATASET_SUMMARY.md) | Its documentation identifies synthetic SMS/challenges. This lead was already checked in the project. | No fresh genuine validation records. |
| [Arabic SMS threat reproducibility repository](https://github.com/msaadaast/arabic-sms-threat-detection-reproducibility) | The README says its SMS data is not yet included; its task is spam/smishing. | Watchlist only; no accessible core-field corpus established. |
| [FinEE financial extraction](https://huggingface.co/datasets/Ranjit0034/finee-dataset/blob/main/README.md?code=true) | Indian banking languages/formats; claimed real component mixed with much larger synthetic components. | Relevant extraction topic, but unsuitable as independent Jordan evidence. |
| [Arabic SMS Spam Data](https://github.com/KhalidAlsantali/Arabic-SMS-Spam-Data) | The author describes 495 Arabic spam/non-spam records. | Core movement truth and Jordan provenance are not established; ham does not mean a completed transaction. |
| [English malicious/benign SMS dataset](https://huggingface.co/datasets/notd5a/malicious-benign-sms-mms-dataset/blob/main/README.md) | The card discloses synthetic content and label revisions; it lists English. | Does not establish Jordan receipt/amount/direction/ownership truth. |
| [Bank of Jordan SMS service](https://bankofjordan.com/en/digital-banking/short-messaging-service-sms) | Documents many notification types, including cancellations, OTPs and balance notices. | Useful coverage guide; the inspected page is not a customer-message dataset. |
| [Arab Bank SMS Express](https://www.arabbank.com.jo/mainmenu/home/ways-to-bank/sms) | Lists transaction/reversal alerts alongside optional balance and rate updates. | Collection guide, not receipt bodies or final-test labels. |
| [JoPACC CliQ services](https://www.jopacc.com/what-we-do/systems-platforms/instant-payment-system-cliq/cliq-services) | Distinguishes recipient checks, payment requests and post-transfer credit confirmation. | Workflow evidence; neither completed-SMS text nor proof of counterparty ownership. |
| [Previously reviewed money-tracker examples](https://github.com/AvAl4nch/money-tracker/tree/6616c7d85c5599e5da1c46613e444c4738d76a58/app/src/test/java/ava/sluff/money_tracker/sms) | Four examples already exist in our reviewed/exposed diagnostics. | Retain their quarantine/history; they cannot become a fresh holdout. |

An official CliQ handbook opened with insufficient text extraction; no sample
was transcribed. A separate tracker bank-list page timed out. Neither was
converted into an available dataset or evidence of genuine message collection.

## Recommended acquisition route

Prepare a small **opt-in discovery pilot**, subject to the owner's route choice.
As a planning suggestion, roughly 30–50 naturally occurring messages from a few
willing contributors could reveal missing formats without creating another huge
synthetic corpus. This is a debugging pilot, not an approved sample size or a
claim of statistical accuracy. Access to willing contributors is not assumed.
The owner does not need to type a large labeled dataset; the assistant can
organize source files and draft annotations from evidence that is actually supplied.

1. Participants deliberately select messages they permit to be used. Collect
   no credentials or active verification codes. Store originals only in the
   ignored `data/private/core_evaluation_v1/` area; do not upload or publish them.
2. Keep each complete SMS packet and its real envelope metadata when available.
   Preserve source hashes and exact boundaries. Do not turn a transaction date
   in the body into a fabricated received timestamp.
3. Seek natural variation: Arabic/English/mixed wording, debit and credit,
   purchases, incoming transfers/refunds, bills and naturally available cash
   movements. Include non-movement bank notices and ordinary-message controls.
   Do not make someone perform a withdrawal or transaction just to populate data.
4. Record completion, primary amount/currency and owner-relative direction.
   Keep field-specific evidence and review. Actual own-account/P2P knowledge
   must come from explicit context, not a party's name. If unknown, retain a
   reviewed unknown relationship and expect review.
5. Review proposed labels without treating parser predictions as truth. A
   source owner can confirm actual deductions/credits and account ownership;
   assistant proposals alone remain weak. Missing amount annotation and a
   reviewed absent amount are different states. JOD default-policy agreement
   is separate from independently known ledger currency.
6. Apply the existing private intake preflight. Known text/numeric-proxy overlap
   causes a hold, not an ancestry claim. The partial exposure catalog still
   needs completion; genuine origin alone cannot establish a fresh source family.

Use pilot records for discovery under recorded exposure. If they are used to
repair the parser, they become development evidence. Preserve a **later sealed
validation batch**, with reviewed labels and source/template-family isolation
before any approved final scoring. New dates, different people and changed
amounts do not by themselves make a known template an unseen family.

An alternative is a separately authorized request to a bank/wallet provider for
de-identified genuine notifications, associated field/ownership truth and clear
permitted use. UAT/demo templates can improve format coverage, but must remain
labeled examples; they do not establish customer-message accuracy. No request
has been sent and no institution's willingness or access is assumed.

## What remains open

On 2026-11-03 the owner chose continued testing with existing development data.
Source collection is deferred; no outreach or pilot acquisition is authorized
by that choice. The dated source ledger retains the earlier research state.
No release thresholds or final-test authorization are set. Protected scope32/
merchant29 remain uninferred and unreassigned.

This sourcing review changes no engine code or weights. Its result is a realistic
data-acquisition choice, not a reason to fit another model. Until new evidence is
available, report the current machine as passing exposed development checks;
independent real-world accuracy remains unmeasured.
