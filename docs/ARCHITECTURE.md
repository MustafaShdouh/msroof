# Architecture and repository maintenance

Active scope and incremental target design are in [CORE_MONEY_ROADMAP.md](CORE_MONEY_ROADMAP.md): recognition, amount/currency and direction, with ownership review. Category work is deferred. The map below describes existing components, including retained compatibility and research code; it is not a mandate to continue those experiments.

## Boundaries

The runtime understands one financial notification. Offline tools prepare data, train isolated candidates and measure behavior. Tests exercise both languages and the browser. Documentation defines semantics; historical reports preserve evidence.

| Area | Responsibility | Boundary |
| --- | --- | --- |
| `src/python/engine.py`, `src/typescript/MasroofEngine.ts` | Public engine entry points and the retained compatibility path | No dataset generation, raw-bank demo or console reconfiguration at import |
| `src/*/DetailedAssessment.*` / `detailed_assessment.py` | Canonical completion, ownership, direction and review assessment | Shared evidence in `config/contracts/`; names are not ownership facts |
| `src/typescript/OwnershipContext.ts`, `src/python/ownership_context.py` | Opt-in human ownership confirmation for one exact message and profile | Separate versioned wrapper; no persistence, account registry or automatic caller migration |
| `tools/browser/ownership_tester.js` | Explicit confirmation controls in the offline tester | Page-memory only; new records and input edits revoke confirmation; legacy display remains independent |
| `src/*/Preprocessing.*`, `preprocessing.py`, `EntityText.*`, `entity_text.py` | Number normalization and source-aligned text | Preserve exact original names and shared numerical contracts |
| `config/contracts/source_text_view.json` | Display controls omitted from logical matching in both source views | Raw source offsets and exact ownership bindings remain intact; independent of learned preprocessing; see `CORE_FORMAT_ROBUSTNESS.md` |
| `src/python/money_candidates.py`, `src/typescript/MoneyCandidates.ts` | Source-linked amount candidates, balance/date/identifier exclusions and primary amount selection | Same shared evidence contract; explicit posted totals/account charges only, no invented sums or conversions; see `CORE_MONEY_AMOUNT_LAYER.md` |
| `src/python/money_syntax.py`, `src/typescript/MoneySyntax.ts` | Shared currency/number syntax and guarded unmarked quantities | No event classification or selection; breaks the dependency cycle between account roles and amount collection |
| `src/python/account_movement.py`, `src/typescript/AccountMovement.ts` | Owned-account cash effects and unmarked numeric spans from the same compiled templates | Context and recording remain in the assessor; source exclusions and currency resolution remain in the collector; see `CORE_MONEY_UNMARKED_AMOUNTS.md` |
| `src/python/direction_policy.py`, `src/typescript/DirectionPolicy.ts` | Direction, transfer relationship refinement and recording eligibility | Completion/amount remain independent; relationship override comes only from validated ownership wrapper; see `CORE_MONEY_DIRECTION_LAYER.md` |
| `src/*/research/` | BIO, merchant and transaction candidate scorers | Isolated from default SMS inference; the optional merchant lab calls its research scorer explicitly |
| `training/corpus/` | Provenance audit, sanitization, retired-copy checks and known-copy scan | Private originals immutable; no automatic data admission |
| `training/transactions/` | Candidate split validation, training and comparison | Export to new versioned outputs; never replace the active model implicitly |
| `training/entities/` | Corrected labels, reusable perceptron, context trial and held-out evaluation | Existing labels/folds frozen; superseded v1 preparation/evaluation CLIs retired |
| `training/categories/` | Business sourcing, annotation/review, holdout reservation and merchant research | Merchant defaults are not purchase-purpose truth; final identities protected |
| `training/evaluation/` | Behavior, detailed assessment, Arabic and frozen-corpus measurements | Counts, abstentions, source hashes; no final-test or promotion shortcut |
| `training/corpus_io.py` | Explicit frozen paths, immutable writes and recorded source recovery | Reject changed artifacts, tampered snapshots and escaped paths |
| `tools/browser/` | Minimal offline tester and merchant review pages | Generated HTML comes from its builder/CSS; inference comes from canonical modules |
| `tools/evaluation/` | Small Node/TypeScript bridges for cross-runtime checks | No duplicated Python/TypeScript decision logic |
| `tools/node_runtime.py` | Shared Node executable discovery for tooling and tests | Explicit MASROOF_NODE override, then PATH/standard installation; never silently ignore an invalid override |
| `tests/` | Automatically discovered safeguards and versioned fixtures | Preserve unique checks; adding a test does not require another root-runner list |

Use `py -m training.<area>.<module>` from the root for offline commands. Related
modules share a package rather than relying on another directory being inserted
into Python's import path. Module names describe the operation within their area.

`training.corpus.semantics` prepares the reference-only SMS annotation view and
training-expression queue under `data/annotations/sms_semantics_v1/`. Its contract
and validator live in `config/contracts/sms_semantics_annotations.json` and
`tools/contracts/validate_sms_semantics.py`. It never predicts labels or grants
admission; later reviews belong in a separate versioned layer.
`training.corpus.review_semantics` validates/materializes that layer from explicit
source-bound assistant decisions, using the same evidence/policy validator. It
does not call a student/merchant classifier or expand labels to descendants.
`training.corpus.propagation` audits a separate proposal layer for completion and
resolved direction only. Literal/slot guards, reservation blocks, normalized-text
deduplication and equal expression weights limit proposed inheritance; they do
not turn it into reviewed truth or training admission. Its validation queue is
reference-only and unannotated. Reproduce with `--check`; read
`data/reports/sms_semantics_propagation_v1.json` before individual records.
`training.corpus.validation_semantics` materializes separate explicit weak
validation judgments without predictions or descendant inheritance. It preserves
the reference queue, blocks and false admission flags, using the existing shared
annotation/evidence validator rather than allowing validation rows into training
drafts. Its current report is `data/reports/sms_semantics_validation_review_v1.json`.

`training.corpus.coverage` inventories source-reviewed event types in the measured
training cohort and validates a separately authored weak training batch. The batch
lives in `data/training/authored_sms_v1/`, with no automatic admission, model calls
or fitting. `docs/SMS_DATA_COVERAGE.md` explains the human-readable coverage matrix,
paired authoring groups, provenance and next experiment proposal.

## Isolated weak-SMS A/B research

`training.transactions.semantics_ab` implements the owner-approved single fixed
word versus word+character trial. `config/contracts/sms_semantics_model.json`
defines research normalization, binary features, ordered flat float64 weights and
head decisions. Python/TS scorers stay under `src/*/research/`; their standalone
browser export serves only the optional tester comparison. Source-derived browser VM checks use
`tools/evaluation/probe_sms_semantics.ts`, without copying scorer logic.

Results/cohort/start ledger are under `data/reports/transactions/sms_semantics_ab_v1*`;
versioned candidates and browser source under `data/models/sms_semantics_ab_v1*`.
The immutable attempt ledger prevents refitting. `--check` only loads those models,
verifies frozen cohorts/source bindings/parity and recomputes the report. Neither
candidate is promoted. Read `docs/REFACTOR_REVIEW.md` for the tiny validation sample,
shared Arabic withdrawal failure and lack of benefit from character features.

## Data and evidence remain versioned

`training.transactions.semantics_followup` implements the separately approved
word-only extension using the frozen authored batch. Its protocol is under
`config/experiments/`; it reuses the original feature/math/solver/browser contract
without changing the previous experiment. Source-artifact/index references explain
its concatenated source view, while each bilingual scenario shares total weight
one. Its own immutable ledger permits two fits once; `--check` only reproduces
saved results. The follow-up export stays isolated from the active SMS caller.
`tools/browser/sms_research.py` verifies frozen model/runtime hashes before embedding
them in the local tester; `sms_research.js` controls the collapsed opt-in panel,
lazy initialization, display and clearing. It adds no model/scoring implementation,
storage or network. Existing extraction/ownership/recording checks remain separate
from raw model predictions; legacy output and defaults remain unchanged.

`training.transactions.completion_context` adds a separate versioned completion
experiment. `sms_completion_context.json` defines binary word sequences of lengths
one through three; Python and TypeScript research modules reuse the original
normalization. One completion fit uses the frozen prior cohort plus 48 authored
contrasts; 24 additional authored probes stay outside fitting/vocabulary. The
direction head is copied exactly from the follow-up. Its own attempt ledger blocks
refitting, and `--check` verifies saved results without training. The source-derived
browser bundle is checked before embedding. Both candidates are selectable in the
optional tester; the word reference stays default. The context candidate introduces
three manual-challenge regressions and is not a production replacement. Results
and remaining defects are in `docs/SMS_DATA_COVERAGE.md`.

The live structural grammar may advance while research measurements stay frozen.
`tools.evaluation.replay_sms_research` reconstructs a temporary source tree from
recorded input hashes and invokes the original check-only command. The three
historical model/validation test entry points retain all 23 original test methods
through `tests/python/frozen_sms_tests.py`; the original assertions execute against
their saved sources. This avoids changing old reports or forcing live recording
rules to stay at evidence 1.0.5. New quote controls exercise the current 1.0.6
grammar and current Python/TypeScript/built browser directly.

The `data/` tree contains source records, reviewed annotations, frozen training and
split artifacts, model exports, and reports/snapshots. These are useful even when
a candidate is rejected: they establish what was tried and why it was not
promoted. Existing artifact paths, label text, split membership and model bytes
are preserved during source organization. Moving them would invalidate recorded
hashes and report links without improving the algorithm.

Only `data/models/masroof_model.json` is the current SMS model. Merchant V3 exports
serve the separate developer research panel. The BIO/context/transaction exports
remain research candidates. A future accepted replacement must pass its own
selection and compatibility gates before an active-path retirement.

The canonical behavior specification is `docs/TRANSACTION_BEHAVIOR.md`. Actual
measurements are in `docs/BEHAVIOR_EVALUATION.md` and the referenced JSON reports.
`docs/REFACTOR_REVIEW.md` is the earlier assessment, with its cleanup status noted.
Local continuation uses only `STATE.md` and `.agents/HANDOFF.md`; there is no
second root-level project brain or duplicate journal.

## What this cleanup retired

| Removed entry | Why / where the useful part went |
| --- | --- |
| `MSROOF_BRAIN.md` | Duplicated state/README and stale facts; canonical links above |
| `config/skills-lock.json` | Unused lock for absent skills, including mobile guidance outside this repository's scope |
| `training/train_and_export.py` | Superseded TF-IDF export whose math is unsuitable for runtime promotion; active weights and exact candidate trainer retained |
| `training/build_bio_training_set.py` | Superseded heuristic-label CLI; exact tokenization helper lives in `training/entities/prepare_labels.py`; original producer checksum remains auditable |
| `training/evaluate_bio_sequence_tagger.py` | Superseded coarse-holdout CLI; historical grouping helper retained for the corrected-label audit |
| Old raw-bank-file demo in the Python engine | Referenced removed root files and mixed I/O into inference; frozen suite is the supported verification entry point |
| Old sequence-tagger CLI | Reusable learner/export math retained in `training/entities/perceptron.py`; corrected-label/context workflows remain supported |
| Fifteen unused regex caches | Definitions had no live references; shared preprocessing remains authoritative |

The root test command now discovers all Python modules and TypeScript suites.
Existing FX/name/correction assertions became a discovered capability test rather
than executing as a side effect of importing a test file. No inference behavior
is intentionally changed by this cleanup.

## Recovery and source-bound reports

GitHub recovery checkpoint: `fbb96e19293cb61a140ecfe6a65551613d93d9b9`, annotated tag
`checkpoint/pre-cleanup-2026-10-26`. The old layout and retired public source are
recoverable from that checkpoint. Local STATE/HANDOFF copies were also preserved
under the ignored `.local-backups/pre-cleanup-fbb96e1/` directory.

A report's input paths describe the version that was measured. Historical reports
and datasets were not rewritten to pretend relocated code produced them.
`recorded_source()` reads checksum-matching source from a current path, private
snapshot/archive or the public checkpoint, without restoring files or fetching
from the network. Its checksum and path guards remain mandatory. The retirement
audit resolves only the two explicitly moved replacement tools for its frozen
layout contract; this is provenance support, not an alternate runtime import path.

Current no-context results must match the pre-cleanup measurement. Preserve the
frozen226 gate, all model bytes, dataset/split bytes and the merchant final-test
reservation. Source-location changes get a fresh measurement ID and input
snapshot; they do not justify refitting a model or changing reviewed truth.

Cleanup verification:146 discovered Python tests, nine TypeScript suites and the
226-case legacy gate pass. The new runner includes41 previously omitted existing
tests/capability checks plus three Node-resolution safeguards. The current report
is `data/reports/behavior/cleanup_layout_v1.json`; all measured outcomes match the
pre-cleanup report. Complete detailed and legacy outputs also match the preserved
pre-cleanup implementation across389 development controls plus26 originals and4
web diagnostics (419 inputs). The106 previously tracked data/model/fixture
checksums remain unchanged. Private proof: `data/private/cleanup_v1/verification.json`.
