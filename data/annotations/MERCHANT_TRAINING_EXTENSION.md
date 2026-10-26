# Jordan training-only merchant expansion

This is sourced business metadata with assistant-reviewed default categories, not
bank SMS, measured certainty, human gold labels, or a popularity ranking.

`data/sources/businesses/jordan_training_extension.json` records 15 distinct
providers/services with public source URLs, observed names, rationale and reviewer
provenance. Run `py -X utf8 -m training.categories.extend_training` to
validate and write `data/annotations/merchant_training_extension.jsonl` and
`data/reports/merchant_training_extension_audit.json`.

The additions are training-only: utilities 3, transportation 3, subscriptions 3,
education 3, travel 2 and telecom 1. Combined with the original labeled training
businesses, this prepares 156 identities covering 12 of 15 categories. Fourteen
additions have an observed Arabic name or alias. City evidence is recorded only
where established; Jordan service availability does not imply a physical branch.
Historical sources establish identity/activity rather than current operating status.

The original 200-business corpus remains separate, with the same 142/29/29
training/validation/test assignments. Eleven additional sourced Arabic aliases
enrich nine original training identities, bringing Arabic coverage there to 32/200
(26 train, 3 validation, 3 test). Aliases are name views, not extra businesses.

The validator rejects original identities, alias/feature collisions, conservative
whole-token prefix relationships with the reserved corpus, missing source evidence
and name-only labels for Cash Withdrawals, Installments or Fees. This is a bounded
identity audit; it does not establish exhaustive corporate ownership independence.

The original v1 experiment remains preserved, with exact inputs frozen under data/training/snapshots/merchant_category_research_v1/. Expanded training completed with --run-id jordan_expansion_v2 --include-extension. The extension is validated and admitted only to a copied training assignment map; both source and output hashes are recorded.

Three models use156 businesses and12 classes. Canonical/aliases/augmented have156/209/350 name forms. All variants give human validation1 correct,0 wrong,4 uncertain out of5; mixed validation8 correct,3 wrong,17 uncertain out of28. All3 Arabic validation businesses abstain. Baseline retained by unchanged human-only selection; no gain over v1. Final test remains unevaluated.

Historical V2 report: data/reports/merchant_category_research_jordan_expansion_v2.md.
Manual tester: tools/browser/tester.html. Rebuild with py -X utf8 tools/browser/build_tester_ui.py. The panel accepts Arabic/English merchant names, switches between treatments and automatically categorizes extracted outgoing-SMS merchants separately from the existing engine category. Scores are uncalibrated and uncertainty is visible.

Round3 is now the tester candidate. Ten additional distinct providers (7 grocery,
2 hospital,1 fuel) are recorded separately in
`data/sources/businesses/jordan_training_round3.json`; prior sources remain intact.
Run `py -X utf8 -m training.categories.train --run-id jordan_data_v3 --include-extension --additional-source data/sources/businesses/jordan_training_round3.json`.
All additions are revalidated together against reserved identities before fitting;
the extra source is hashed. No thresholds/features or final-test assignments change.
This gives166 training businesses; baseline human validation2 correct,0 wrong,
3 uncertain of5, mixed9 correct,3 wrong,16 uncertain of28. All3 Arabic validation
businesses still abstain. The improvement concerns one existing development case,
not independent accuracy. V3 report is
`data/reports/merchant_category_research_jordan_data_v3.md`. Preserve final test;
collect broader independent evidence rather than repeatedly tuning to five humans.
