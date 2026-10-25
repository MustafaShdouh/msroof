# Masroof Continuation Handoff

Pass this file to a new local model to continue the project. It is self-contained, intentionally compact, and should stay near 40,000 characters (about 10,000 technical tokens). Update it only after a material code change, verified result, user decision, or plan change. Do not recreate a separate running journal.

The user explicitly requires ongoing documentation hygiene: update `STATE.md` when a milestone, verified result, decision, blocker, or next action materially changes, and update this handoff with the technical detail needed to continue safely.

## Scope and decisions

- Workspace correction/migration (2026-10-24): USER explicitly identifies C:/Users/mustafa/Desktop/msroof as authoritative, authorizes merge, deletion of old C:/Users/mustafa/Desktop/Masroof only after verified merge, and GitHub push. Every command must set workdir=msroof; original chat may still have stale cwd. Compared149 source versus101 target project files:50 source-only,16 shared differing, only target-only files DATA_YOU_WANT/ARAB_BANK.txt and CAPITAL_BANK.txt. Copied/hash-verified all149 project files, retained both originals and all earlier50 human review records exactly. Verified ZIP backups of BOTH full pre-merge trees including .git under msroof/.local-backups/merge-20261024T201135Z/ with per-file/archive hashes in manifest.json; merge-verification.json records copied file count. Keep backups local/ignored. Original bank files are byte-identical to their data/raw copies, so those two raw files are user-identified real seeds; other raw origins stay unresolved. Per-message parsing, sensitive-field sanitization and generated-descendant auditing pending. Seeds remain development-exposed.
- Publication: remote origin=https://github.com/MustafaShdouh/msroof.git, initially empty. Imported original two commits into LOCAL main to retain history. Because that history contains private source SMS, publish a CLEAN root snapshot from codex/merged-project to origin/main, not old main/history. .gitignore excludes DATA_YOU_WANT/, data/raw/*.txt, .local-backups/, caches and local credentials. No raw originals/backups must enter GitHub index/history. Both original commits also preserved in verified archive. All226 regression cases/contracts and61 research/data checks pass FROM msroof; optional tester rebuilt there (one transient invalid-argument write error succeeded on retry). Before old-folder deletion verify archive hashes and source-to-target project match, allowing documented intentional migration edits; preserve target-only originals. Code committed as 7a4f63d (Consolidate Jordan SMS ML pipeline and merchant research tooling) and pushed from msroof codex/merged-project to origin/main; exact remote hash verified. On 2026-10-25 the old Masroof CONTENTS have been removed, with full verified archive retained. Only the empty directory remains: Windows refuses removal because another process holds it open. Retried after usage-limit interruption; still locked. Do not claim the directory is gone or kill user processes to force deletion. Codex saved project entry already points to msroof, but this chat environment still reports old cwd; always use explicit msroof workdir. Reopen/close any session or terminal holding old path, then remove only the empty old directory. Both archive hashes, original-bank byte copies and all9 model hashes were reverified. No model/data change in this final status update. Tester path must now be msroof/tools/browser/tester.html.


- Current continuation: acquisition/provenance work completed after V3. `data/sources/businesses/jordan_arabic_collection.json` has8 new Arabic-canonical identities (Education4, Health2, Transportation1, Entertainment1), all assistant labels with primary public source evidence; Children's Museum deferred because educational programs vs recreational birthday services require context. `training/prepare_arabic_collection.py` validates original15+round3's10+new8 together against original200; writes ONLY new8 to `data/annotations/merchant_arabic_collection.jsonl` and audit `data/reports/merchant_arabic_collection_audit.json`. No model fitted/new accuracy/test inference. All8 train-only/evaluationEligible=false/humanConfirmedCategory=null. Not yet loaded by trainer: its --additional-source currently accepts one source; compose multiple sources explicitly next time without dropping round3 or modifying historical files. Rebuild command `py -X utf8 training/prepare_arabic_collection.py`.
- User provenance clarification (2026-10-24): roughly20 real Arab Bank messages and10 Capital Bank messages seeded Gemini Flash generation. Exact originals/descendants not yet identified; do not call all data/raw rows real or synthetic based on filename/text plausibility. Originals are development-exposed through generated descendants, not fresh independent test even when found. Originals located in C:/Users/mustafa/Desktop/msroof/DATA_YOU_WANT during merge. Both bank files exactly match data/raw copies; per-message/descendant audit pending. Canonical provenance and5 official documentary context findings in `data/sources/transactions/jordan_context_evidence.json`; none are SMS or completed-transaction truth (smsText/isCompletedTransaction=null, train/evalEligible=false). Guide `data/annotations/REAL_SMS_INTAKE.md`, short pointer data/raw/README.md. Findings: withdrawal OTP precedes physical cash receipt; wallet/fuel-station channel does not determine purpose; tuition installments still Education; billing rail not purpose; Jeeny passenger spending vs driver income. Keep observations separate from assistant inferences. Identify/sanitize originals, record parent/template families, audit against all legacy training/frozen fixtures/category folds; acquire new unexposed real families for independent evaluation. No synthetic replacements.
- V3 completed candidate (still active in tester): user accepted recommendation to PRESERVE FINAL TEST and improve on development data (2026-10-24). One data-only V3 experiment completed; no threshold/feature tuning. V2 diagnosis: canonical155/156 training accepted correctly vs only1/5 human validation; feature scarcity and spurious confident name matches. New `data/sources/businesses/jordan_training_round3.json` records10 distinct source-backed assistant-reviewed Jordan providers (7 grocery,2 hospital,1 vehicle fuel), observed aliases, evidence/rationale/limitations. No synthetic SMS, branch padding or holdout enrichment. Original extension unchanged. Trainer supports --additional-source with --include-extension: combines raw source records then revalidates ALL additions against base identities/feature collisions/context restrictions; hashes additional source, uses copied training-only assignments. Command `py -X utf8 training/train_merchant_category.py --run-id jordan_data_v3 --include-extension --additional-source data/sources/businesses/jordan_training_round3.json`.166 training businesses(31human/135assistant),12 classes. Canonical/aliases/augmented forms166/227/378, features4249/5562/6898. Grocery support13, Health8, Transportation4, other counts unchanged; three context-only categories absent. Candidate paths `data/models/merchant_category_research_jordan_data_v3_{baseline,aliases,augmented}.json`; report `data/reports/merchant_category_research_jordan_data_v3.{json,md}`. Fixed human-only rule keeps baseline: all3 variants2 correct/0 wrong/3 abstain of5 vs V2 1/0/4; Fouad Supermarket now Groceries. Canonical raw top1 remains3/5: this is better acceptance on one existing development case, not broad accuracy evidence. Mixed baseline9 correct/3 wrong/16 abstain of28; aliases8/3/17, augmented8/4/16. Arabic validation all3 still abstain across variants. Stop after this single data experiment; no iterative fishing on five humans. Final test inference remains blocked/testMetrics=null; no production promotion. User manual testing and broader independent Arabic/real payment-context data are next.
- Original200 enrichment:11 observed aliases for nine training identities (Hashem, Habibah, Al-Hamwi, Dima Pharmacy, Al Maseyah Pharmacy, Rawan Cake, Yousef Afandi, Al Samah, Royal Jordanian). Alias source has30 entries; original Arabic coverage32, allocated26/3/3. Holdout names not enriched; human reviews unchanged. Split hash remains e2cfb583d1b62b9af72df0b985c6cdc84601bf052dc279dee4d611175c9fe99d. Extension rows explicitly train-only/evaluationEligible=false/humanConfirmedCategory=null. Validator rejects reserved identity/alias/feature collisions, conservative token-prefix relationships, missing evidence, duplicate identities and context-only labels. Bounded ownership audit only.
- V1 metrics remain HISTORICAL; exact five inputs/manifest frozen in `data/training/snapshots/merchant_category_research_v1/`, original model hashes verified. Changed-input overwrite guard retained. --include-extension now validates/adopts additions in copied training map and hashes source/output, no original split changes. V2 all variants: human1 correct/1 answered/5 total(4 abstain); mixed8 correct/11 answered/28 total(3 wrong/17 abstain/23 assistant labels). Raw top1 baseline17/28, aliases/augmented18/28. Arabic all3 abstain across variants. Baseline selected by unchanged human-only rule; V1 mixed baseline9/12/28 vs V2 8/11/28 is no improvement. Train155/156 accepted correctly, Other1 abstains, memorization only. Final test disabled/testMetrics=null/promotionAllowed=false. Three v2 models and two reports reproduced byte-for-byte. Next user tests, investigate failures, acquire independent broader data.
- Latest verification:61 research/data/model tests plus226 frozen Python/TS cases/contracts pass. Root runner includes21 model/extension/collection tests and browser parity over274 non-test names per variant. New8-record collection rebuilds byte-for-byte. All9 model hashes match existing reports; split e2cfb583d1b62b9af72df0b985c6cdc84601bf052dc279dee4d611175c9fe99d unchanged. No retraining or final-test inference this collection turn.

- Merchant-name research baseline/A-B complete (2026-10-24): `training/train_merchant_category.py` trains only the 141 labeled training businesses (31 human/110 assistant), no historical SMS. Three separate flat exports `data/models/merchant_category_research_{baseline,aliases,augmented}.json` and `data/reports/merchant_category_research.{json,md}` reproduce byte-for-byte. Canonical baseline 141 forms/3572 features; source aliases 167 forms/4073 features; augmented 297 forms/5242 features, including 130 synthetic forms capped one per eligible business. Every business has total view weight one; synthetic records in JSON report have baseName/businessId/dataKind/labelReviewerType (base label origin, not review of generated spelling). Perturbations remove one separator or repeat one internal Latin letter, no new identities/category words/transliterations/SMS. Filter held-out exact feature-form collisions before fitting. Pure-Python seeded softmax SGD (100 epochs, seed20261024), binary words and boundary char3/4/5-grams, sorted feature vocabulary fitted only on training views, inverse-sqrt known-feature normalization, feature-major flat double weights rounded10 decimals. Nine heads correspond to represented training classes, not all15. Contract `merchant-name-category-1.0.0` is implemented in standalone `src/python/merchant_category.py` and `src/typescript/MerchantCategory.ts`; NFKC/shared financial digits/lowercase/Arabic diacritics-tatweel removal/Latin-Arabic letters-and-digits; no SMS routing-prefix or NUM_LONG replacement, so LC Waikiki retains its prefix. Scorers remain disconnected from MasroofEngine and browser. Fixed pilot abstention: score<0.6, margin<0.15, known-feature fraction<0.15, empty/no known features, or winning-class business support<3. Scores explicitly uncalibrated, not percent certainty. Selection uses ONLY the five human validation businesses: prefer baseline unless a variant gives strictly more correct answered businesses without more wrong answers; assistant-label metrics do not select. Outcome: all three answer only 99GRILL correctly, abstain on Cinnabon/Fouad Supermarket/JETT/Manaseer; baseline retained. Combined validation 28 businesses (5human/23assistant): baseline9correct/12answered/28total; aliases and augmented8/11/28. Raw pre-abstention top1 is17/28 baseline versus18/28 each variant, a diagnostic not the selection criterion. Arabic observed validation: all3 abstained for every variant. Final test inference deliberately raises; testMetrics null and runtimePromotionAllowed false. No test predictions occurred even in actual-export parity tests (train/validation names plus handcrafted contract probes only). Ten new tests cover vectors, leakage/provenance/caps/equal weights, deterministic fitting, human-only selection, abstention, malformed models and actual Python/TS exported score parity; wired into root full runner. Total50 research/data checks plus226 frozen Python/TS cases and existing contracts pass. Split hash unchanged. Next: expand legitimately sourced Arabic names and sparse/missing classes, improve independent evaluation evidence, then reassess; do not tune against tiny validation until it appears impressive or create repetitive synthetic padding. These candidates are insufficient for integration or Arabic category claims.
- Category audit (2026-10-24): `training/audit_category_corpus.py` writes `data/reports/category_corpus_audit.{json,md}` (readable name is uppercase CATEGORY_CORPUS_AUDIT.md). Nine audit tests cover class absence, human/assistant separation, known families, word-sequence exposure and augmentation caps. Training class counts: Food60/Shopping54/Entertainment10/Health6/Groceries6/Telecom2/Education1/Travel1/Other1. Missing training classes: Water and Electricity, Transportation, Subscriptions, Cash Withdrawals, Installments, Fees; Transportation exists only in validation, Water/Electricity only in test. Never move them into training to repair coverage. Exact-form cross-fold conflicts0. Sourced Inditex family (Lefties/Massimo Dutti/Oysho/Stradivarius/ZARA/ZARA Home) all train; family audit is bounded, not exhaustive. Lexical held-out-name mentions: legacy training70 (Cozmo13, Starbucks28, H&M7, Manaseer11, Cinnabon11), regression4, adversarial1. Generic words may misidentify businesses and this is not a template audit. Do not mix legacy SMS into new category fitting. Augmentation protocol and completed experiment are described above/in CATEGORY_EVALUATION.md; it cannot create missing classes or independent truth.
- Merchant review (2026-10-24): all200 identities reviewed,198 defaults accepted (46human/152assistant), Juman/khuyoot.sharqieh unresolved. Storage220 decisions:216approved/4needs_context, including earlier Apple/Talabat illustrative deferrals. Check Downloads for newer human exports before AI review. Latest `...18-23-05-056Z.json` is imported; preserve Arkan Lab=Health, Calamantina=Shopping, Halib Halab=Food. Human split counts31/5/10; assistant110/23/19. Importer requires assistant evidence/rationale, protects human decisions and untouched source snapshots; legacy null candidate brandGroup uses existing business group for new labels. Source caveats are in review records: Catpuccino drinks differ from play admission, Bizantino prepared drinks differ from packaged beans, La Capitale meals are Food inside a hotel, Reem's Amman identity differs from a US site, Yaseen2015 is historical evidence. No user review pending. Merchant defaults never label all transaction contexts.
- Category split: `training/prepare_category_evaluation.py` preserves `data/training/splits/category_brand_split.json`, 142/29/29 businesses,17/3/3 with Arabic names. Existing group/alias and whole-token prefix rules pool ZARA/ZARA Home; frozen199 leakage groups are not an exhaustive corporate map. New cross-fold identity links/membership changes fail rather than reshuffle. Split SHA256 e2cfb583d1b62b9af72df0b985c6cdc84601bf052dc279dee4d611175c9fe99d. Reports count human/assistant separately, never claim independent SMS evidence or blind external benchmarks. Acquire provenance/sanitized real messages and audit templates/sources separately. Protocol: CATEGORY_EVALUATION.md.
- Communication preference (2026-10-24): end every user-facing message with an explicit next step.
- Arabic merchant enrichment: `data/sources/businesses/arabic_aliases.json` has19 observed names (6official/13directory matches), expanding coverage4->23/200;2canonical Arabic names/2human Arabic merchant-name records. Builder validates all alias targets/owners before mutation, rejects conflicts, and appends name-only provenance with no inferred cities. Preserve existing200 identities/order; only initial absent-output builds select anew. Corpus has142Amman/77Irbid,261researched identities,43attributed review-count entries; not a verified popularity ranking. No invented transliterations/SMS/extra category approvals. Source meanings and reviewer evidence remain distinct.
- Jordan-only scope and Arabic numerals (2026-10-24): user explicitly restricted this project to Jordan. Focus on Jordanian bank/wallet SMS and local merchants in Arabic/English; JOD stays the default, while foreign-currency purchases by Jordanian users remain valid. Preprocessing contract is now 1.1.0. Shared `normalize_financial_numbers` / `normalizeFinancialNumbers` in the preprocessing modules map Arabic-Indic and Persian digits to ASCII, Arabic decimal U+066B to dot and group U+066C to comma; preserve Arabic letters and Arabic comma U+060C. Apply numeric-only normalization before sender guards and raw entity extraction, and inside standalone number parsing; full model preprocessing still runs separately, so account/amount strings are not erased by NUM_LONG before extraction. Python long-number boundaries now use explicit ASCII word characters matching JS. Optional `build_tester_ui.py`/`tester.html` were updated and rebuilt; corrected its literal-CR regex too. Frozen 226 cases pass in Python/TS. Ten numeric vectors, 678 complete-result script-equivalence checks and three Unicode phone guards pass per Python/TS/browser; nine preprocessing vectors pass per core language. Browser checks execute the built script in an isolated Node VM, not UI automation. Both engines now pass all 24 formerly failing Arabic/Persian numeral probes and all four preprocessing parity probes. `evaluate_arabic_support.py` report is updated to 1.1.0/Jordan. Grouped split was regenerated with preprocessing 1.1.0 and unchanged 1671/449 counts; historical rejected v2 model/report still carry 1.0.0 preprocessing and were not relabeled or promoted. Additive score math contract remains 1.0.0; reference score vectors now declare preprocessing 1.1.0. Next: independent Jordan-specific Arabic evaluation with entire brands held out across scripts. Category coverage is now 2 canonical Arabic names/23 businesses with Arabic names or aliases; no learned new-taxonomy category accuracy exists. Diagnostics are not new training examples or generalization evidence.
- Latest human review import: `Downloads/masroof-merchant-review-2026-10-24T18-23-05-056Z.json` held16 ambiguity approvals, now imported. This supersedes earlier20-business import status. Future AI decisions cannot overwrite human labels.
- Reviewer preference: Codex performs future reviews directly, using evidence and the user's existing exact category decisions; ask the user only for an unresolved project/taxonomy preference that cannot be settled from authorized context. Keep assistant labels distinct from human approvals. The old manual review page is optional and currently has no pending ambiguity cases.
- Current category restart (2026-10-24); this supersedes earlier category acquisition and synthetic-expansion plans.
- Review workflow: the validated importer is shared by human and assistant decisions. Assistant records explicitly carry reviewerType and reviewEvidence; prior human reviews cannot be replaced by assistant imports. Browser local-file automation remains blocked; do not bypass it.
- First review imported: Mustafa approved 12 merchants across 10 categories; all 10 existing suggestions were confirmed and 2 previously unassigned names received labels. Al-Daya'a and Al-Israa Hospital family identifiers were normalized to their own brands after unrelated examples were entered. Categories were preserved.
- Boundary review imported: 16 approved illustrative cases and 2 needs-context cases (Talabat and Apple without purchase details). There are now 28 approvals and 2 deferred cases. Exact labels take priority over broad notes: monthly mobile remains Telecom even though a note calls monthly bills Subscriptions. Missing-biller Fees applies only to that reviewed example.
- Rejected experiment removed: repetitive 10k synthetic category dataset, generator, associated tests, model, report, scores, and guide were deleted at the user's request. Human reviews, sourced metadata, legacy transaction artifacts, and frozen tests are preserved. Do not recreate category diversity by varying amounts or repeating businesses.
- New category corpus: `data/annotations/businesses_200.jsonl` and readable `BUSINESSES_200.md` contain 200 sourced business identities selected from a 261-business pool; 142 have Amman evidence, 77 Irbid evidence, 19 both. Known aliases are grouped; two uncertain identities excluded. Forty-three have attributed review counts. Manifest: `data/reports/businesses_200_manifest.json`. No comparable citywide popularity metric was established, so this is a research shortlist, not a verified top-200 ranking.
- Keep exact reviewed decisions rather than inventing broad rules: HyperMax television=Groceries; Orange device/mixed bill=Telecom; device installments=Installments; tuition installments=Education; Netflix/monthly JETT=Subscriptions; monthly mobile=Telecom; missing-biller example=Fees. Do not infer all monthly payments are Subscriptions or all bill-channel payments are Fees. Talabat and Apple without purchase details need context.
- Focus only on the ML engine for Jordan. Do not work on the mobile app or Hermes integration.
- Product goal: from an SMS, decide whether it is a real bank transaction; return amount, incoming/outgoing direction, merchant, account/balance where present, and an expense category.
- `tester.html` and `build_tester_ui.py` remain optional developer playground tooling, outside the core ML architecture.
- Brand-to-category mappings are an approved exception to the no-hardcoded-merchant rule. Do not add bank-sender registries or a general merchant registry.
- User corrections are merchant-specific, persist through the overlay API, and override category inference at confidence `1.0`.
- Work directly in this repository. Do not use the former `delegate_to_executor` workflow.

## Repository layout after 2026-10-24 cleanup

- `src/typescript/`: `MasroofEngine.ts`, `Preprocessing.ts`, and `TransactionDirection.ts`.
- `src/python/`: `verify_engine.py`, `preprocessing.py`, and `transaction_direction.py`.
- `data/raw/`: original SMS source material; `data/training/`: generated training/BIO data; `data/training/splits/`: deterministic split artifacts; `data/models/`: runtime model exports.
- `tests/fixtures/`: frozen 226-case corpus and contract vectors; `tests/python/` and `tests/typescript/`: runners and contract checks; `tests/legacy/`: retained old runner pending audit/removal.
- `training/`: offline model/data scripts. `tools/browser/`: optional tester. `tools/generators/`: corpus-source generators. `tools/legacy/`: unused executor bridge.
- The repository root intentionally retains only project documentation, state, the full-test entry point, `.agents/`, and the top-level directories.

## Current architecture

- `MasroofEngine.ts`: production-style TypeScript engine. It combines preprocessing, linear transaction classification, direction scoring, regex entity extraction, category scoring, user overlays, and an inference-only BIO tagger.
- `verify_engine.py`: Python mirror used for parity checks; it is not the training implementation.
- `masroof_model.json` + `train_and_export.py`: legacy linear transaction/direction model and trainer.
- `build_bio_training_set.py`: derives BIO examples from the 178 regression fixtures.
- `bio_training_data.json`: 83 valid messages, 2,011 tokens; rejected messages are excluded because tagging follows transaction validation.
- `train_sequence_tagger.py`: seeded 25-epoch averaged perceptron; exports `masroof_sequence_tagger.json`.
- `masroof_sequence_tagger.json`: 410 normalized-token features, 4,510 emission weights, 121 transition weights, 11 biases.
- `test_suite_cases.json`: 178 regression cases. `qa_adversarial_cases.json`: 48 adversarial cases. Together: 226.
- `test_suite_runner.py`, `test_suite_runner.ts`, `run_all_tests.py`: Python, TypeScript, and consolidated verification.
- `tester.html` and `build_tester_ui.py`: optional browser playground. Keep out of the core refactor until the model contracts stabilize.

## Verified state

- Milestones 1–2 are complete: bilingual category scorer, exact normalized merchant corrections, persistence, and correction isolation.
- BIO Task 3.1: deterministic source-spanned training data. Rebuild produced 83 examples and zero unresolved fields.
- BIO Task 3.2: TypeScript loader converts flat weights once to `Float32Array`; inference uses an indexed loop, shared score buffer, and caller-owned `Uint8Array`. It is deliberately disconnected from `extractEntities`.
- BIO Task 3.3: deterministic export. Rebuilding `bio_training_data.json` and `masroof_sequence_tagger.json` produced unchanged SHA-256 hashes. Training-set token accuracy: 97.31% (1,957/2,011); exact sequences: 43.37% (36/83). These are not held-out metrics.
- The actual exported BIO JSON loaded into `MasroofEngine` and tagged a 32-token training example. TypeScript and Python architecture tests pass.
- Latest consolidated run: 226/226 passing, zero false positives, zero false negatives. Latest Node TypeScript regression mean: 0.0834 ms. Node timing is not a Hermes measurement and is no longer in scope.
- Test gates were hardened on 2026-10-24: standalone Python and TypeScript runners now exit nonzero on failures; the consolidated runner fails when Node is missing, the TypeScript subprocess cannot start, or it exits unsuccessfully. Python type mismatches now enter the mismatch list.
- Phase A and Phase B are complete: the 226-case corpus is frozen by manifest; both engines now use preprocessing contract `1.1.0`; and both pass fixed additive transaction/direction score vectors under math contract `1.0.0`.

## Known ML issues to address

1. Training and inference normalize/tokenize differently in several places. `train_and_export.py` also has a `JO` replacement that can alter `JOD`. Do not trust existing training-library accuracy as runtime accuracy.
2. The linear trainer uses vectorizer behavior that does not exactly match TypeScript's direct feature summation.
3. The BIO tagger has only exact-token emissions and previous-tag transitions. A coarse source-category-held-out evaluation now exists (87.67% token, 4% exact sequence); true template isolation remains unproven and extraction must stay disconnected.
4. The confirmed repeated-value BIO error was repaired for TC_POS_CAP_001. Continue auditing ambiguous source spans; zero unresolved values alone does not prove every occurrence is semantically correct.
5. `MasroofEngine.ts` mixes unrelated responsibilities. `verify_engine.py` and the browser engine have drift risks.
6. Browser tooling is manually duplicated. Keep it optional until stable core contracts can drive it.
7. The current test corpus is valuable as a frozen regression gate, but much training data is synthetic. Model replacement needs a template-separated held-out set and ideally more labeled real examples.

## Authorized ML refactor direction

1. Freeze the 226-case regression corpus and define one versioned preprocessing contract shared by Python training and TypeScript inference.
2. Separate core responsibilities into preprocessing, transaction decision, direction, entity extraction, category inference, corrections, and orchestration. Preserve the public `MasroofEngine` API during the migration.
3. Make the transaction/direction export exactly match runtime feature calculation.
4. Repair BIO span labels; add deterministic template-separated train/validation/test splits and field-level entity metrics.
5. Evaluate learned transaction, direction, entity, and category outputs against regex and current baseline. Replace a legacy path only after the held-out result meets the agreed gate.
6. Retire `run_test_suite.py` only after its useful cases are in the canonical suite. Move browser tooling under developer tools; do not delete it.

## Immediate next action

The merchant-name baseline and bounded augmentation comparison are complete and reproducible; baseline retained, with insufficient validation evidence and no runtime promotion. Expand sourced Arabic names/underrepresented classes and independent evaluation evidence before tuning further; keep the final test unevaluated and do not pad data with repetitive variants. Preserve label provenance and frozen splits. Independent Jordanian SMS/full-taxonomy/runtime gates remain unmet. The v2 transaction/direction candidate also failed its gate; do not integrate either experiment. Earlier descriptions below are historical; current scope and reports take precedence.

## Commands

- Full regression: `py run_all_tests.py`
- Python architecture checks: `py tests/python/test_new_architectural_features.py`
- TypeScript architecture checks: `& 'C:\Program Files\nodejs\node.exe' tests/typescript/test_new_architectural_features.ts`
- BIO data rebuild: `py training/build_bio_training_set.py`
- BIO training/export: `py training/train_sequence_tagger.py`
- Recreate grouped split: `py training/prepare_transaction_direction_split.py`

## Detailed code map

### Runtime engine: `MasroofEngine.ts`

The public entry point is `MasroofEngine.analyze({ sender, body, isContact?, defaultCurrency? })`. It returns a transaction decision, confidence, reason, and structured data. Its current order is roughly: reject contact/phone senders and obvious chat, declined, or administrative messages; lazily load the legacy linear model; normalize and tokenize; score transaction validity; reject internal transfers; score direction; then use regex extraction for amount, currency, account, merchant, balance, foreign-exchange fields, and category.

The TypeScript runtime preprocessing decodes literal `\\n`, strips an uppercase two-letter routing prefix, strips basic Arabic diacritics, normalizes whitespace, replaces six-or-more-digit values with `NUM_LONG`, and lowercases. Its tokenizer emits words and Arabic-aware tokens, then appends word bigrams to the same feature array. The legacy transaction model is additive: for every emitted feature found in `masroof_model.json`, it adds `idf * transactionWeight` and `idf * directionWeight`, then applies a sigmoid threshold. This direct scoring is the model behavior that future Python training must reproduce exactly.

Entity extraction is currently regex-based and remains the production baseline. It finds and masks balance first, then detects billed/original FX amounts, currency, account masks, merchant text, and category. The production categorizer first checks the user overlay, then combines permitted brand/category mappings and semantic category scores. The overlay is global static state with public apply, import, export, and clear APIs. Keep its merchant-normalization behavior and exact correction priority stable during refactors.

The same file also holds the experimental BIO runtime. `SequenceTaggerModel` accepts `version`, `tagCount`, `featureIndex`, `emissionWeights`, `transitionWeights`, and `bias`. `loadSequenceTaggerModel` validates array lengths, converts them once to `Float32Array`, and stores a runtime model. `tagNormalizedTokens(tokens, outTags)` takes already-normalized tokens, uses a single reusable 11-element score buffer, greedily predicts the best tag with prior-predicted-tag transitions, and writes to the caller-owned `Uint8Array`. It does not allocate an output array and is not invoked by `extractEntities`.

Important current limitations: `MasroofEngine.ts` owns multiple unrelated responsibilities; the tokenizer feeds both unigrams and bigrams into the same scoring list; model shape validation does not protect against every malformed property or non-finite number; and comments claiming zero allocation are broader than the actual string-normalization work. Preserve the public API while moving internals behind modules.

### Python runtime mirror: `verify_engine.py`

`verify_engine.py` mirrors most TypeScript behavior for regression evaluation. It has its own preprocessing, tokenization, extraction, category scoring, overlay handling, and result shape. It also supplies both camelCase and snake_case aliases for extracted fields. This makes it useful for test reports but increases drift risk: it has separate regex and Unicode semantics from JavaScript, creates per-call lists for category scores, and does not contain a mirror of BIO inference.

Known parity differences already observed: sender preprocessing differs; TypeScript and Python use different word-boundary semantics; some merchant delimiter patterns differ; Python accepts a boolean where JavaScript rejects it in overlay category data; category confidence rounding can differ on ties; and TypeScript browser tooling has its own manually copied implementation. Do not claim full parity until a shared fixture suite tests the same preprocessing and model scores in both engines.

### Legacy transaction and direction trainer: `train_and_export.py`

The trainer reads `dataset_expanded.json`, labels `TRANSACTION_DEBIT` and `TRANSACTION_CREDIT` as transactions, uses detailed labels for a stratified random 80/20 split, and trains sklearn TF-IDF unigram/bigram logistic-regression models. The direction model is trained on all positive rows rather than a held-out subset. It exports `masroof_model.json` as a feature dictionary containing rounded `[idf, transactionWeight, directionWeight]` triples plus intercepts.

This is not exact runtime parity. sklearn TF-IDF normalizes a document vector and applies its own feature-space behavior, whereas TypeScript directly repeats additive token and bigram contributions. The trainer replaces every `JO` substring after replacing `JO\\n`; that can corrupt `JOD` into `D`. It uses a different token regex and Arabic handling from runtime. It reports a held-out classifier score from its own vectorizer, not the actual exported-model score under TypeScript runtime math. Treat its metadata accuracy as historical only.

The replacement must use a single documented feature extractor and scoring formula in both languages. The trainer must export enough metadata to validate contract version, labels, threshold, feature count, weights, intercepts, and data split. The runtime should fail closed if the model contract does not match its preprocessing version.

### Synthetic data: `expand_dataset.py`, `dataset_expanded.json`, and `dataset_expanded.csv`

`expand_dataset.py` is a deterministic seeded synthetic generator. It creates Arabic and English templates for debit, credit, OTP, declined, announcement, promotion, and chat-like messages. It stores text, detailed label, provider label, transaction direction, amount, currency, and merchant data in JSON, then writes a CSV with a reduced schema. It contains long lists of synthetic merchants, names, billers, and branches. These are training fixtures, not runtime registries; the user-approved category brand exception does not make them appropriate as runtime sender switches.

The dataset currently contains 2,120 rows, with repeated template shapes and duplicate messages. A random row split allows related template variants into both train and validation sets, so its score is optimistic. A replacement evaluation must split by template family or another group key, not random rows. Before changing generated training data, preserve the current artifact and record the generator seed and output hash.

### BIO data generator: `build_bio_training_set.py`

The builder reads `test_suite_cases.json`, includes the 83 valid transactions, excludes 95 rejection cases, finds exact text spans for expected amount, currency, merchant, account, and balance, tokenizes the original message, and writes BIO tags. It records unresolved fields rather than silently inventing a label. Current result: 83 examples, 2,011 tokens, zero unresolved fields. Label counts include 83 amount starts, 83 currency starts, 76 merchant starts plus 121 merchant continuations, 64 account starts plus 18 account continuations, and 81 balance starts.

The confirmed repeated-value error in `TC_POS_CAP_001` was repaired by nearest balance-context selection: first 10.870 is amount, later 10.870 near الرصيد is balance. Keep this regression assertion. Zero unresolved values does not prove every occurrence is correct; broader source-span auditing is still needed.

The currency span selector finds a nearby currency token but does not fully enforce that it corresponds to the expected ISO value. The account and merchant selectors are literal matching. Overlap handling discards later overlapping entities. A refactor should make the expected span contract explicit in fixtures where automatic source alignment is ambiguous; do not hide ambiguity behind a value-only comparison.

### BIO trainer: `train_sequence_tagger.py`

The trainer is standard-library-only and deterministic through `SEED = 20261024` and 25 epochs. It normalizes tokens by lowercasing, removing broader Arabic diacritics, and normalizing alef, yeh, teh marbuta, and tatweel. It uses sparse token/tag emissions and previous-tag transitions, timestamped averaged weights, greedy inference, and a dense flat export ordered by sorted vocabulary.

It is a lightweight baseline with exact-token features, no shape/context features or BIO constraints. Transition updates are not a full structured-perceptron update. The full export's 97.31% token and 43.37% sequence scores are training metrics. Separate `evaluate_bio_sequence_tagger.py` now provides coarse held-out metrics; neither training scores nor weak held-out results justify replacing regex extraction.

The next BIO implementation should preserve the export's compact flat-array property but add a deterministic group split, span-level precision/recall/F1, entity exact-match rates, confusion reporting by field type, and an A/B comparison to regex extraction. It may retain greedy inference initially, provided the report makes that choice explicit. Add only features that can be reproduced in TypeScript with stable allocation behavior.

### Test corpus and runners

`test_suite_cases.json` has 178 regression cases: 83 valid transactions and 95 rejections. `qa_adversarial_cases.json` has 48 cases: 23 valid and 25 invalid. Together they are the current 226-case behavior baseline. The master runner invokes Python and TypeScript cases for both files. It now returns nonzero for any Python failure, missing Node runtime, TypeScript startup failure, or TypeScript nonzero exit.

`test_suite_runner.py` compares classification, type, amount, currency, merchant, account, and balance. It now records type mismatches, which earlier versions failed to add to the mismatch list. `test_suite_runner.ts` reports analogous fields and now sets a nonzero exit code when mismatches exist. Both runners currently allow normalized substring equality for merchant and account values. They do not assess category, structured confidence, reason, or FX optional fields in the 226-case run. Separate architecture tests cover a smaller set of FX and overlay scenarios.

Freeze means: retain exact current fixture contents, compute and commit a manifest of their SHA-256 hashes and case counts, add a schema/duplicate-ID validator, and have the full runner validate the manifest before evaluating models. Clean means: establish one canonical expected-field naming and test schema without changing the 226 semantics; preserve backward aliases only in an explicit migration adapter. Do not regenerate fixture sources as part of model training.

### Browser developer tooling

`tools/browser/build_tester_ui.py` renders a static tester using its own embedded JavaScript engine and generates `tools/browser/tester.html`. It is useful for manual message inspection. It is not the ML core and should not be deleted. It already lives under the developer-tools boundary and now reads `data/models/masroof_model.json` through a project-relative path. Do not use it as proof of TypeScript/Python parity; its implementation has known drift, including missing guards and no experimental BIO runtime.

## Exact refactor sequence and completion gates

### Phase A: freeze and clean the corpus

1. Add a baseline manifest containing SHA-256, case count, valid/invalid count, and schema version for both fixture files.
2. Add a validator that checks manifest hashes, top-level structure, globally unique IDs, required input fields, allowed expected fields, and valid type values. It must be read-only.
3. Make `run_all_tests.py` invoke the validator first and fail fast if the baseline is modified.
4. Define a canonical expected schema. Preserve old aliases in a fixture-normalization adapter until all fixtures are migrated under explicit review.
5. Completion gate: current two fixtures validate and all 226 existing cases still pass unchanged.

### Phase B: preprocessing and export contract

1. Define a versioned preprocessing contract: routing-prefix handling, literal newline handling, Unicode normalization, Arabic diacritic behavior, whitespace normalization, long-number placeholder rule, token pattern, and bigram rule.
2. Add shared test vectors containing raw input, expected normalized text, expected tokens, and expected features. Python and TypeScript must produce byte-for-byte equivalent normalized text and feature arrays for every vector.
3. Define a versioned model contract with labels, feature encoding, threshold semantics, intercepts, finite numeric requirements, and artifact metadata. Validate model shape before loading.
4. Do not replace the legacy model yet. Add the new contract and parity tests beside it.
5. Completion gate: every preprocessing vector and exported-model score matches in Python and TypeScript.

### Phase C: transaction and direction model

1. Build a custom deterministic trainer using the exact additive feature formula that TypeScript will run. Avoid sklearn TF-IDF unless the complete transform, including normalization, is faithfully exported and duplicated.
2. Split data by template family/group, not individual rows. Record split seed and group assignment in the report.
3. Export a new model artifact rather than overwriting `masroof_model.json` during evaluation.
4. Run it in shadow/A-B mode against the frozen corpus and a held-out synthetic or real-message set. Report transaction precision, recall, false positives, false negatives, direction accuracy, and per-source-group results.
5. Completion gate: no regression on frozen 226 and an agreed held-out improvement or equivalence. Only then wire it into `MasroofEngine.analyze` and retire legacy scorer.

### Phase D: BIO repair and evaluation

1. Correct source spans where values repeat. Add fixture-level expected spans or audit exceptions rather than relying solely on numeric equality.
2. Group-split BIO examples and evaluate only on examples withheld from training.
3. Report token accuracy, exact sequence accuracy, per-label precision/recall/F1, and entity exact-match rate for amount, currency, merchant, account, and balance.
4. Load the exported model through TypeScript in a permanent validation runner; compare decoded spans to Python evaluation on shared examples.
5. Completion gate: held-out entity results meet the explicitly chosen threshold and do not regress the regex baseline before extraction replacement is considered.

### Phase E: category prediction

1. Establish category labels for training messages. Keep user overlay and permitted brand mappings as high-confidence overrides.
2. Train a compact category model using the same preprocessing contract. Include an `Other`/general fallback with calibrated confidence.
3. Split and report category results by template/provider group. Test correction isolation separately from model accuracy.
4. Completion gate: held-out category accuracy is meaningful, error analysis is reviewed, and the fallback avoids unsupported confident guesses.

### Phase F: retirement

Remove a legacy path only after its replacement passes the specified A/B gate, all frozen regression cases, Python/TypeScript parity vectors, and artifact shape checks. Remove `run_test_suite.py` only after any unique checks it contains are migrated. Keep the browser developer playground.

## Operational guardrails

- Never alter the frozen 226 corpus to make a new model appear better. Add new cases in a distinct reviewed corpus version.
- Keep inference on-device and network-free.
- Do not claim Hermes benchmarks; app/Hermes work is out of scope.
- Prefer small independently testable patches. After each material patch, run the smallest relevant check and then `py run_all_tests.py` before declaring success.
- Treat model artifacts as generated outputs. Record generator version, seed, schema/contract version, input corpus hash, split definition, and evaluation metrics.
- Do not replace regex entity extraction based on training-set metrics.
- The local model should read this file first, then `STATE.md`, then the exact source files relevant to the active phase. It should not reopen every historical document unless a detail here is insufficient.

## Refactor progress log

### Completed corpus and contract work

The frozen corpus manifest, schema validator, fail-fast test gates and shared preprocessing/additive-score vectors are implemented; see the corresponding fixture/test paths above. Preserve fixture bytes and manifest hashes. Contract 1.1.0 preserves whitespace-collapse-before-NUM_LONG replacement, including double spaces, and exact feature ordering; Python/TS vectors verify it. Older version-1.0 vectors/timings are historical, superseded by current reports. The separate v2 additive model contract/trainer/validators exist; exact score is intercept plus each emitted feature occurrence's weight, followed by sigmoid. The legacy TF-IDF artifact cannot be relabeled as this contract. Candidate rejection and grouped-split evidence below remain authoritative.

### 2026-10-24: Phase C preparation complete — grouped training split

Added `training/prepare_transaction_direction_split.py`. It reads `data/training/dataset_expanded.json` without changing it and writes `data/training/splits/transaction_direction_split.json`. The script masks the record's expected merchant, account-mask formats, and numeric values before preprocessing to form a provider-and-label template signature. A stable seeded group assignment keeps every identical signature entirely in either train or validation. The artifact records dataset SHA-256, split version, seed, preprocessing version, indices, group counts, and per-label train/validation counts.

Current split result: 2,120 records; 1,671 train; 449 validation; 503 train template groups; 111 validation template groups. Rebuilding it produced the same SHA-256 hash. Per-label validation counts are ANNOUNCEMENT 32, CHAT_NOISE 82, DECLINED 24, OTP 48, PROMO 28, TRANSACTION_CREDIT 78, and TRANSACTION_DEBIT 157.

This grouping is an improvement over random rows, but it is only an inferred template signature because the old generator does not emit a true `templateId`. Report it as a deterministic proxy, not as proof that all semantic template leakage is eliminated. A future generator refactor should emit a stable source-template ID directly.


### 2026-10-24: v2 candidate trained and rejected for integration

Added `training/train_transaction_direction_v2.py`. It trains deterministic, sparse L2-regularized logistic heads directly on `tokenize_features(preprocess_message(text))`, so its exported weights use the exact runtime formula: `intercept + sum(weight(feature) for every emitted feature occurrence)`. It validates the dataset hash and complete, disjoint grouped split before training. The candidate artifact is `data/models/masroof_transaction_direction_v2.json`; its reproducible SHA-256 is `79a91780a3289169fd9de8f4fbfa8fb7d3636e8c2ce483a019ba67934e40e835`. The report is `data/reports/transaction_direction_v2_evaluation.json`.

The candidate validates with both `src/python/transaction_direction.py` and `src/typescript/TransactionDirection.ts`. Re-running the trainer produced the same artifact hash. Its signature-grouped synthetic validation results are transaction F1 `1.0` with zero false positives/negatives and direction accuracy `1.0` on 235 actual transactions. Treat that result cautiously: the split is a deterministic signature proxy, not a source-template split.

The independent frozen corpus reveals that it is not ready: model-only shared-contract scoring yields 98/106 transaction true positives, 103/120 true negatives, 17 false positives, 8 false negatives, F1 `0.8869`; direction is 104/106 (`0.9811`) on actual transactions. The report explicitly excludes sender and regex guards, so it is not a full runtime A/B result. Still, the candidate fails the no-regression gate and must not be integrated, wired into `MasroofEngine`, or used to replace `data/models/masroof_model.json`. The legacy 226-case runtime regression remains fully passing after the candidate was added.

### 2026-10-24: BIO label repair and held-out entity report

Updated `training/build_bio_training_set.py` so balance span selection scores every nearby value against balance-context terms and selects the closest candidate, instead of returning the first candidate within a broad 64-character window. The Arabic term `رصيد` is now accepted as a balance hint. This repairs the confirmed `TC_POS_CAP_001` gold-label error: the first `10.870` is `AMT` with `JOD`; the later `10.870` before `الرصيد` is `BAL`. The rebuilt 83-example artifact has zero unresolved fields and remains structurally valid.

Added `training/evaluate_bio_sequence_tagger.py`, which keeps complete `sourceCategory` groups in one seeded train or validation partition, trains an evaluation-only perceptron on 58 examples, and writes `data/reports/bio_sequence_tagger_evaluation.json` for 25 held-out examples from `EDGE_CASE_TYPOS` and `POSITIVE_PURCHASE`. This is a coarse source-category grouping, not template isolation. Results: token accuracy `0.8767`, exact sequence accuracy `0.0400`; exact entity-span F1 is ACCT `0.9545`, AMT `0.5128`, BAL `0.4375`, CURR `0.6557`, MERCHANT `0.6512`. The full 83-example export still trains deterministically for the experimental artifact, but it remains disconnected from production regex extraction. The full Python/TypeScript 226-case regression and TypeScript architecture/BIO-load check passed after this work.

## Data and evaluation detail

### Raw message sources

The workspace has raw text files for Arab Bank, Bank al Etihad, Capital Bank, Housing Bank, Orange Money, Reflect, UWallet, Zain Cash, and chat noise. They are source material and should remain separate from the frozen 226 regression fixtures. The current fixture generators are hand-authored and do not automatically consume all raw text files. Do not claim “generated from raw samples” without tracing a generator path.

`tools/generators/generate_test_suite.py` defines the regression corpus. `tools/generators/build_qa_adversarial_cases.py` defines the adversarial corpus. Both now write explicitly to `tests/fixtures/`; the latter still performs generation at module import time, so avoid importing it casually in new validation code. Both should eventually expose data-only build functions with explicit output paths, but do not change them during Phase B unless required by the frozen-corpus migration.

### Dataset labels

The synthetic dataset has detailed labels including `TRANSACTION_DEBIT`, `TRANSACTION_CREDIT`, OTP, declined, announcement, promotion, and chat/noise categories. Transaction data includes direction, amount, currency, and a merchant/party field. It does not supply a verified expense-category label per row. Category training cannot be honestly evaluated until a separate category-labeled corpus is created or generated under a documented taxonomy.

Do not derive category truth solely from the hardcoded category maps and then report that a learned category model “understands” categories. If synthetic category labels are generated, record their origin as synthetic and hold out template/merchant families so direct memorization is visible.

### 2026-10-24: category-label source decided

The user chose manually reviewed real completed transactions as the only ground truth source for a learned category model. Added `data/annotations/CATEGORY_LABELING.md` and `data/annotations/category_annotation_schema.json`. The canonical target taxonomy has 15 allowed labels: Telecom; Water and Electricity; Food; Groceries; Transportation; Subscriptions; Shopping; Health; Entertainment; Education; Travel; Cash Withdrawals; Installments; Fees; Other. A future `category_labels.jsonl` must contain unique `id`, sanitized transaction `text`, allowed `category`, human `labeler`, and `reviewed: true`. Do not train category prediction before there are reviewed records. The future validator must reject unreviewed, duplicate, unsupported, or non-transaction records and preserve a template/merchant-separated holdout. The current runtime's eight-category heuristic is legacy behavior; migrate it only when a learned model has evaluation evidence under the canonical taxonomy.

Do not treat a 750-message manual-entry exercise as the project’s data-acquisition plan. The user needs legitimately sourced real-world data. `data/annotations/category_labels.jsonl` remains an ingestion target for records from an approved source; `category_labels.example.jsonl` demonstrates the required shape. Public searches so far found English or synthetic transaction data, but no verified open dataset of Arabic/Jordanian bank SMS messages paired with the canonical taxonomy. Before training category prediction, identify a source with transaction-description text, category truth, clear usage rights, and a documented mapping to the 15 target categories. Never present synthetic data as real-world evidence.

### Group splitting

The existing `data/training/dataset_expanded.json` has no explicit template ID. `training/prepare_transaction_direction_split.py` now supplies a deterministic audited proxy grouping function and records the dataset hash and group assignments. It does not prove template-family isolation, so describe held-out results as signature-grouped. A future generator refactor should emit a stable source-template ID for every row.

A random row split is not acceptable for model-selection claims because account masks, amount forms, merchant slots, and provider wording repeat across rows. Training-set accuracy is also never replacement evidence. The frozen 226 suite is a behavior regression gate, not a generalization test; it must remain separate from trainer fitting data whenever possible.

### Metrics required before replacement

For transaction decision: report held-out true positives, true negatives, false positives, false negatives, precision, recall, F1, and provider/template-group breakdown. False positives deserve a hard review because ordinary user chat must not become a bank transaction.

For direction: among held-out valid transactions, report incoming/outgoing accuracy and confusion counts. Do not calculate direction accuracy using invalid messages. For entity extraction: report exact entity span/value matches per AMT, CURR, MERCHANT, ACCT, and BAL, plus token BIO precision/recall/F1 and full-sequence accuracy. For category: report held-out top-1 accuracy, confusion matrix, coverage above a confidence threshold, and fallback rate.

For each candidate replacement, report the frozen 226 result separately from held-out data. A candidate that passes 226 but has weak held-out metrics has not surpassed the legacy path. A candidate with a strong held-out score but a frozen regression failure also cannot replace it until the failure is understood and approved.

## File ownership during the refactor

- Safe to add now: contract JSON, contract tests, model validators, new v2 trainer and artifact, evaluation scripts, explicit generated reports, and test-only fixtures.
- Preserve until measured replacement: `masroof_model.json`, `train_and_export.py`, runtime legacy scoring inside `MasroofEngine.ts`, regex extraction, existing category scorer, `run_test_suite.py`, and browser tooling.
- Update when behavior changes: `.agents/HANDOFF.md` first, then short `STATE.md` if next action or completed milestone changed. Do not restore the deleted journal or duplicate brain file.
- Never overwrite a model artifact during experimental training. Write a new versioned artifact, evaluate it, then choose whether to integrate.

## Immediate implementation checklist

1. Define an audited category taxonomy and labeled corpus, then train and evaluate category prediction with held-out metrics and fallback criteria.
2. Review and improve v2 only through separate candidate artifacts and reports; keep legacy runtime live until a candidate clears the frozen-corpus gate.
3. Improve BIO only through separate held-out reports; do not connect it to production extraction until field metrics materially improve.
