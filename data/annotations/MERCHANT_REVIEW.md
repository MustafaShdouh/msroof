# Review a few merchants

Open `tools/browser/merchant_review.html` in your browser. This is a local developer tool and works without a server.

1. Enter your name or initials.
2. For businesses you recognize, select **Confirm category below** and choose the correct category. A suggestion is not an approval until you select this decision.
3. Use **Needs transaction context** for names that could fit several categories. Use **Skip** for unfamiliar businesses.
4. Merchant-family identifiers are handled by the data tooling. You only need to choose the category and decision. Existing names without a confirmed family receive provisional identifiers; these must be reconciled before evaluation splitting.
5. Click **Download my decisions**. Keep the downloaded `masroof-merchant-review.json`. The page does not write directly into the repository. You can reload that file to resume the same batch.

Give the downloaded file to the coding agent, or import it from the repository root:

```powershell
py training/merchant_review.py import "C:\path\to\masroof-merchant-review.json"
py training/merchant_review.py batch --size 12
```

Imported decisions are saved in `data/annotations/merchant_reviews.jsonl`. Rebuilding candidates or review batches preserves that file. Import validates every record before saving. Re-importing an explicitly revised decision updates that merchant. Deferred businesses can be revisited using `batch --include-deferred`.

## What this batch measures

For ambiguous real businesses only, run `py training/merchant_review.py batch --ambiguous --size 16`. The curated questions in `business_ambiguities.json` identify opaque names, insufficient source descriptions, and overlaps in the taxonomy. Category selections start empty. Unknown businesses can be skipped, and missing transaction details can be flagged without forcing Other. This is editorial ambiguity selection, not model confidence. Clear source-based proposals elsewhere remain unreviewed; excluding them from this batch does not make them gold labels.

The current primary corpus is `businesses_200.jsonl`, with a readable source-linked list in `BUSINESSES_200.md`. Build using `py training/build_business_shortlist.py` and select only this pool using `py training/merchant_review.py batch --businesses --size 20`. It has one row per normalized business identity and no invented SMS variations. Popularity ranks are unmeasured; directories support presence and some entries have separately attributed review counts. This shortlist is not an independently established top-200 city ranking. Reuse of existing approved labels is exact-name/known-alias based; all other category mappings remain proposals.

The first batch uses a mix of categories and documented ambiguity, with at most one known brand family per batch. There is no trained confidence score yet. This is preparation for active learning; it does not yet rank model uncertainty or retrain a model.

## Review difficult category boundaries

```powershell
py training/merchant_review.py batch --edge-cases --size 18
```

This uses `category_edge_cases.json` to display 18 deliberately ambiguous or contrasting payment scenarios. The cases are authored examples, never presented as actual collected SMS. Public links support the business-service facts, not the example amounts or text. Contrasting cases intentionally repeat a brand to establish which transaction details should change its category.

No category is preselected in this mode. Decide which category you want for the stated payment; select **Needs transaction context** if the text is insufficient. `Other` is an explicit category, not an automatic substitute for uncertainty. Notes can explain rules such as whether subscription payment form or spending purpose takes priority. Use the same download/import workflow as merchant review; filenames include a timestamp to distinguish batches.

Saved records carry `labelScope: illustrative_transaction`, the exact example text, and a data-kind marker. The importer rejects changed or missing example text. These decisions must be kept distinct from merchant-default labels and from real SMS evaluation; reviewing them does not create independent test data.

Review confirms a category for a merchant name. It does not establish the category of every payment to that merchant: a device bought from a telecom provider may be Shopping, and a separately charged service fee may be Fees. Other unresolved boundaries include recurring entertainment versus Subscriptions and transport versus Travel. Flag those cases instead of inventing a label.

The existing generated-data names are explicitly marked as unverified business names. Public business listings provide evidence of names and locations, not actual bank SMS wording. Public pages have not been established as openly licensed training datasets. Merchant evaluation must group aliases and branches together and stay separate from real SMS evaluation. Brands without a verified family must be resolved before a model split.
# Reviewer delegation

The user authorized Codex to review and categorize businesses directly on 2026-10-24.
Manual browser review is optional. Research each identity using its public sources,
assign a merchant default only when supported, and retain uncertainty explicitly.
Do not turn source proposals into approvals without examining the evidence.
Before starting assistant reviews, inspect newer `masroof-merchant-review*.json`
exports in Downloads and reconcile the latest relevant human decisions through the
validated importer. Do not assume the repository already includes the latest export,
or reimport older exports over a newer human correction. The user's latest imported
merchant defaults include Arkan Lab=Health, Calamantina=Shopping and Halib Halab=Food.

Assistant imports use `reviewer: "Codex"`, `reviewerType: "assistant"`, a rationale in
`notes`, and nonempty `reviewEvidence` entries with HTTPS `url` and factual `summary`.
Record the access date in that evidence. Use the normal validated import path; it
rejects assistant attempts to overwrite a human decision. Legacy decisions lacking
`reviewerType` are human records. Imports preserve earlier record/source snapshots.

The business corpus keeps `assistantReviewedCategory` separate from
`humanConfirmedCategory`; human decisions take priority. Assistant labels are usable
as disclosed research/weak supervision under the user's delegation, not independent
human test truth. Readiness reports count both sources separately and never calculate
accuracy against the assistant's own labels. Deferred identity/payment ambiguities
remain `needs_context`, not an invented `Other` label. Keep all aliases of a held-out
business in its frozen fold regardless of who labels it.
