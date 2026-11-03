# Core validation preflight — 2026-11-02

The project now has a private intake for future independent evaluation and an
explicit startup contract for the existing parser. This is preparation, not new
real-world data, training, final scoring or a change to transaction decisions.

## Intake location and rules

The empty intake is `data/private/core_evaluation_v1/intake.json`. Original source
files for this intake belong under that same private directory. Everything there
is ignored by Git. No genuine messages were invented or copied into it, and no
existing reservation was opened. There is no new labeling assignment to complete
now; the structure is for a future source of genuinely fresh messages.

The record template and review formats are in
`config/contracts/core_validation_preflight_v1.json`. They reuse the source,
locator, exposure, family and eligibility conventions in
`config/contracts/sms_provenance_record.json` rather than changing the historical
26-block seed ledger. Records retain exact private text and source-file/hash/
Unicode-character-offset bindings. This intake does not certify anonymization
or create a public export.

The validator holds records with missing or stale provenance/consent/exposure/
family reviews, generated or unresolved origin, development exposure, unreviewed
families, incomplete core truth or inconsistent labels. Reviews bind the exact
text hash. Positive amount, nullable amount and missing annotation are distinct.
Human-reviewed “ownership unknown” is valid truth and requires review; it is not
a missing label and must not be changed to P2P from the counterparty's name.
Assistant-only/weak labels cannot become independent human truth by being copied
into this file. Default JOD is contract-policy truth, not independent evidence
that a bank ledger actually used JOD; preserve the label's evidence basis.

Both record and batch eligibility flags must stay false. Even a locally complete
record is merely ready for further review: this tool never grants admission,
training eligibility or permission to score. Declared reviews are not proof of
bank authenticity. Candidate freeze, audited family isolation, reviewed truth,
approved thresholds and final-test authorization remain separate gates.

Zero/signed amounts stay held pending the unresolved product policy. Duplicate
content remains present and held for evaluation review; it is not silently
deleted and does not implement an ingestion deduplication policy.

## Known-exposure checks

The private `known_exposure_v1.json` catalog covers 4,646 nonempty text entries
from the frozen R5 development snapshot, sanitized transaction corpus and the
226-case compatibility fixtures. It stores fingerprints, not another training
dataset: 3,148 distinct exact hashes, 2,613 normalized hashes and 1,922 numeric
proxies. It reuses the existing provenance normalizer and numeric-proxy logic.
Source hashes are retained, with the R5 snapshot checked against its frozen report.

Exact, normalized and numeric-proxy matches cause review holds. Proxy similarity
does not establish generation ancestry or a verified template family. The catalog
is explicitly **partial**: additional authored/context/scope inputs, original
sources, prompts, web examples and generated descendants still require a complete
exposure audit. Development family labels were not invented into verified source
families. Distinct text or no detected overlap does not prove independence.

Current intake: zero records; zero admitted or scored. Batch blockers are
`no_records` and `exposure_catalog_partial`. The validator emits aggregate counts
on the command line, never the private SMS body. It rejects sources outside the
new private intake directory before reading them.

```text
.local-backups/sms_completion_encoder_v1/env/Scripts/python.exe -X utf8 -m tools.contracts.core_preflight intake
```

## Startup requirements and observed behavior

The existing TypeScript caller must load the pinned JSON and call
`MasroofEngine.init(weights)` before `analyzeDetailed` or the ownership wrapper
can reliably use the financial-candidate fallback. Python's constructor loads
the default weights. The offline preflight checks the active model's exact hash,
finite intercepts and finite additive-IDF feature triples. The 2,545-feature
artifact passes. This does not execute initialization, prove that a caller
initialized correctly, measure accuracy or establish mobile support.

```text
.local-backups/sms_completion_encoder_v1/env/Scripts/python.exe -X utf8 -m tools.contracts.core_preflight runtime
```

Current TypeScript behavior is characterized, not changed:

1. Before initialization, a strong structural receipt can still parse correctly.
   That successful example does not establish fallback readiness.
2. An unrecognized test string reaches the fallback. Without weights, that
   fallback returns false. A fixed toy positive-intercept test control changes
   the resulting uncertainty; this is a startup contrast, not bank-SMS truth or
   a trained replacement model.
3. `init` currently assigns an invalid object without checking it. A later
   fallback call can throw. After loading the real pinned model, the checked
   calls work again.

`tests/typescript/test_runtime_initialization.ts` checks these conditions in a
fresh process, plus Node support for the regex features used by the parser.
It does not establish Hermes support. The canonical engines, browser build,
model weights, public inference APIs and initialization failure behavior remain
unchanged. A future approved guard must distinguish **engine not ready** from
**message is not a transaction**, rather than manufacturing an exclude decision.

The subsequent caller-side tester guard is implemented; see below. The canonical
engine's startup behavior described above remains unchanged, and the separate app
was not modified.

## Evidence and verification

Public aggregate report: `data/reports/behavior/core_validation_preflight_v1.json`.
Exact inputs are preserved under the existing private hash-deduplicated report
archive, manifest `core_validation_preflight_v1.json`. The reference catalog and
all old data/reports remain versioned; changed inputs require a new report/version.
The report builder creates an intake only when absent and never overwrites a
user's existing records.

Ten Python safeguards cover weak/generated/exposed records, source/hash/label
binding, private path boundaries, content and family overlap, duplicate retention,
unknown ownership, null versus missing truth, unresolved signs/zero, model shape
and pinned bytes, eligibility envelopes and catalog coverage declarations.
The separate TypeScript startup suite verifies the observed current behavior.
The full suite passes **337 Python tests, 13 TypeScript suites and 226 frozen
cases**. All 16 core-graph source hashes, tester source hashes and 23 model
artifacts match the prior verified state.

```text
.local-backups/sms_completion_encoder_v1/env/Scripts/python.exe -X utf8 -m unittest tests.python.test_core_preflight
```

No source acquisition, final evaluation, model fit, reserved-set inference,
runtime migration, publication or deletion occurred. Independent accuracy,
release thresholds and actual target-runtime support remain unestablished.

## Optional tester startup guard complete — 2026-11-02

`tools/browser/startup_guard.js` checks JavaScript/regex capabilities and finite
model structure before compiling the canonical core bundle and calling `init`.
The builder pins the model bytes before replacing the page; a mismatch leaves
the existing page intact. Blocked local compilation is a startup error.

Failure shows **Engine not ready**, clears stale primary/legacy fields and
confirmations, and prevents SMS, ownership and optional research predictions.
Startup JSON contains no transaction status or recording decision. Valid startup
preserves all prior outputs and the optional developer ground. The healthy
indicator updates through the normal page handler so DOM-free probes still work.
No original assertions, canonical engine APIs, weights or app code changed.

Final evidence: `data/reports/behavior/core_money_r6_startup_guard_final_v1.json`.
It supersedes the earlier regression-only build snapshot for the final page;
historical reports and exact source archives are retained. Full **338 Python
tests, 14 TypeScript suites and 226 frozen cases** pass. All 2,302 detailed/legacy
results, 70 ownership requests, 23 models and 16 core-graph files are unchanged.
The generated page reproduces byte for byte. Edge checks at 440px cover Arabic
input and a deliberately failed startup, with no horizontal overflow. These are
browser checks, not mobile/Hermes validation.

Source discovery is complete for the bounded 2026-11-02 review; see
[JORDAN_SMS_VALIDATION_SOURCING.md](JORDAN_SMS_VALIDATION_SOURCING.md). No qualifying
public Jordan transaction-SMS corpus was confirmed, and no new message records
were collected. An opt-in pilot and a provider-request route are prepared as
choices. Keep all new records private/held until provenance, exposure and truth
are reviewed. No outreach, final/reserved scoring or new training is authorized.
