# Existing-message formatting robustness — 2026-11-03

The owner chose continued testing with existing development data, deferring the
collection-route decision. This pass found and fixed a display-formatting defect:
invisible direction marks could change transaction recognition, amounts and
direction, while a leading BOM also caused Python/TypeScript disagreements.
The matching view now ignores the specified display controls and preserves the
original source text and exact ownership-confirmation binding.

## Frozen checks and measured defect

`tests/fixtures/core_format_robustness_v1.json` defines 12 transformations of
existing messages: identity, repeated spaces, tabs, nonbreaking and narrow
nonbreaking spaces, physical/literal CRLF wrapping, a BOM prefix, directional
wrapping, RTL marks at word boundaries, lowercase and uppercase. No numbers,
currency tokens, semantic words or ownership facts are added. Only previously
asserted core fields are inherited; optional exact-name outputs are not assumed
to be invariant after text changes.

The source is the checksum-bound R5 development snapshot. Selecting one canonical
digit/contact variant per existing repair case plus all original diagnostics
gives 582 base entries. Twelve transformations give 6,984 checks: 3,480 Arabic,
3,480 English and 24 mixed-language variants. These counts are exposed development
checks, not independent messages, new training data or real-world accuracy.

| Measure | Before | After |
| --- | ---: | ---: |
| All inherited core assertions match in every runtime | 6,451/6,984 | 6,984/6,984 |
| Full-result Python/TypeScript/browser parity failures | 56 | 0 |
| Python false includes of labeled nontransactions | 74/2,868 | 0/2,868 |
| Python labeled nontransactions reported completed | 101/2,868 | 0/2,868 |

All ordinary whitespace, wrapping and case transformations already passed. BOM
prefixes and directional wrappers each failed 55 cases; RTL word-boundary marks
failed 423. A nontransaction false include here means an inherited nontransaction
expectation became includable after formatting alone. It does not measure a
population false-positive rate or authenticate the sender of any notification.

## Repair and source preservation

`config/contracts/source_text_view.json` defines the source-view contract:
Arabic letter mark, left/right marks, directional embeddings/overrides/isolates
and BOM are omitted from logical matching. Python `entity_text.py` and TypeScript
`EntityText.ts` consume the same control pattern. Arbitrary zero-width characters
and joiners are not removed, letters are not reordered, and numbers are unchanged.
Statistical preprocessing, feature/export contracts and learned weights are intact.

Source starts/ends still refer to the exact original text. Removed controls inside
a selected numeric/name span remain in its raw substring; controls outside the
selected token are not attached to it. Arabic diacritics and source spacing are
preserved by projection. The detailed assessors classify an empty logical view
as `empty_or_malformed` without invoking candidate scoring.

Format equivalence does not permit reusing a confirmation for different raw text.
The new tests retain the exact ownership wrapper: adding a BOM, directional
wrapper or RTL marks invalidates the old raw-message confirmation. No name,
account mask or display control supplies account ownership.

## Historical integrity

The existing ownership-baseline replay previously required the current source
view to have the original hash. It now recovers that original, checksum-matching
`EntityText` and injects it into both historical assessor and historical extractor
namespaces. Other unchanged-dependency hash checks remain. A new safeguard proves
the old baseline retains its old view while the current parser uses the repaired
view. Original expectations, reports and source hashes were not rewritten.

The original 2,302 full detailed and legacy results, 70 ownership requests and
23 model artifacts remain identical to the frozen R5 snapshot. The tester is
rebuilt from canonical sources and reproduces byte for byte. These invariance
claims apply to the original measured inputs, not to every future SMS or to
improved legacy accuracy on the new transformed inputs.

Five new safeguards cover the complete format matrix, raw Unicode numeric/name
projection, empty logical input without model scoring, exact ownership binding
and historical source-view isolation. Full verification passes **343 Python
tests, 14 TypeScript suites and 226 frozen cases**.

Evidence:

- `data/reports/behavior/core_format_robustness_before_v1.json`
- `data/reports/behavior/core_format_robustness_after_v1.json`
- `data/reports/behavior/core_format_robustness_integrity_v1.json`
- Private `.local-backups/core_format_robustness_v1/{before,after}.json`
- Exact input/source archives under the existing private `report_inputs` manifests

The before artifact and producer bytes remain historical. Do not rerun a current
producer over an old report path. New transformations or a further repair require
a new version/run path, preserving the current fixture and inherited assertions.

No fitting, new research trial, source acquisition, reserved inference, publication
or app change occurred. These transformed inputs are now exposed development
evidence and must be included in future exposure audits. The independent intake
remains empty and its catalog remains explicitly partial.

Next: continue development testing of competing amount roles and transfer ownership
using the existing corpus, with ambiguity retained for review. Source collection
is deferred under the owner's choice; independent release evidence remains open.
