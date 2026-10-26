# Architecture and repository maintenance

## Boundaries

The runtime understands one financial notification. Offline tools prepare data, train isolated candidates and measure behavior. Tests exercise both languages and the browser. Documentation defines semantics; historical reports preserve evidence.

| Area | Responsibility | Boundary |
| --- | --- | --- |
| `src/python/engine.py`, `src/typescript/MasroofEngine.ts` | Public engine entry points and the retained compatibility path | No dataset generation, raw-bank demo or console reconfiguration at import |
| `src/*/DetailedAssessment.*` / `detailed_assessment.py` | Canonical completion, ownership, direction and review assessment | Shared evidence in `config/contracts/`; names are not ownership facts |
| `src/*/Preprocessing.*`, `preprocessing.py`, `EntityText.*`, `entity_text.py` | Number normalization and source-aligned text | Preserve exact original names and shared numerical contracts |
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

## Data and evidence remain versioned

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
