"""Build a sourced, brand-deduplicated shortlist without synthetic SMS padding.

Directory presence is not a measured popularity ranking. Preserve that distinction
in every record and the manifest rather than fabricating a top-200 claim.
"""

from __future__ import annotations

from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import re
import unicodedata

ROOT = Path(__file__).resolve().parents[2]
EXTRACTS = ROOT / "data/sources/businesses/directory_extracts.json"
LOCAL = ROOT / "data/annotations/local_merchant_sources.json"
REVIEWS = ROOT / "data/annotations/merchant_reviews.jsonl"
OUTPUT = ROOT / "data/annotations/businesses_200.jsonl"
MANIFEST = ROOT / "data/reports/businesses_200_manifest.json"
READABLE = ROOT / "data/annotations/BUSINESSES_200.md"
ARABIC_ALIASES = ROOT / "data/sources/businesses/arabic_aliases.json"


def normalize(name: str) -> str:
    text = unicodedata.normalize("NFKC", name).casefold()
    text = re.sub(r"[\u064b-\u065f\u0670]", "", text)
    return "".join(char for char in text if char.isalnum())


def build_pool() -> tuple[list[dict], dict]:
    extracts = json.loads(EXTRACTS.read_text(encoding="utf-8"))
    local = json.loads(LOCAL.read_text(encoding="utf-8"))
    aliases = {}
    for canonical, variants in extracts["canonicalAliases"].items():
        for variant in [canonical] + variants:
            aliases[normalize(variant)] = canonical
    pool = {}
    excluded = {normalize(name) for name in extracts.get("excludeUntilIdentityReview", {})}

    def add(name, category, cities, evidence):
        if normalize(name) in excluded:
            return
        canonical = aliases.get(normalize(name), name)
        key = normalize(canonical)
        if key not in pool:
            pool[key] = {
                "businessId": "business-" + hashlib.sha256(key.encode()).hexdigest()[:16],
                "name": canonical, "brandGroup": key,
                "aliases": set(), "cities": set(), "proposedCategories": set(), "sources": [],
                "popularityEvidence": [], "popularityRank": None,
                "estimatedCorrectnessPct": None,
                "datasetScope": "business_metadata_not_bank_sms",
            }
        row = pool[key]
        row["aliases"].add(name)
        row["cities"].update(cities)
        row["proposedCategories"].add(category)
        # Retain only source facts required for provenance, not descriptions,
        # contact details, reviews, or entire copyrighted directory pages.
        row["sources"].append(evidence)

    for source in extracts["sources"]:
        for category, names in source["groups"].items():
            for name in names.split(";"):
                evidence = {
                    "url": source["url"], "publisher": source["publisher"],
                    "type": source["type"], "listedName": name,
                    "cities": source["cities"], "accessedOn": extracts["accessedOn"],
                }
                if source.get("sourceDate"):
                    evidence["sourceDate"] = source["sourceDate"]
                if source.get("note"):
                    evidence["caveat"] = source["note"]
                review_count = source.get("reportedReviewCounts", {}).get(name)
                if review_count is not None:
                    evidence["reportedReviewCount"] = review_count
                    evidence["reviewCountCaveat"] = source.get("reviewCountCaveat", "Count belongs to this platform listing, not a citywide brand total.")
                add(name, category, source["cities"], evidence)

    local_sources = {row["id"]: row for row in local["sources"]}
    for merchant in local["merchants"]:
        source = local_sources[merchant["sourceId"]]
        add(merchant["name"], merchant["proposedCategory"], merchant["cities"], {
            "url": source["url"], "publisher": source["publisher"],
            "type": "previously_researched_public_listing", "listedName": merchant["name"],
            "cities": merchant["cities"], "accessedOn": local["accessedOn"],
            "caveat": source["evidence"],
        })

    enrich_aliases(list(pool.values()), json.loads(ARABIC_ALIASES.read_text(encoding="utf-8"))["aliases"])
    reviews = [json.loads(line) for line in REVIEWS.read_text(encoding="utf-8").splitlines() if line.strip()]
    approved = {normalize(row["name"]): row for row in reviews if row["status"] == "approved" and row["labelScope"] == "merchant_name"}
    for row in pool.values():
        matched_reviews = {approved[normalize(name)]["id"]: approved[normalize(name)] for name in row["aliases"] | {row["name"]} if normalize(name) in approved}
        apply_category_reviews(row, list(matched_reviews.values()))
        row["cities"] = sorted(row["cities"])
        row["aliases"] = sorted(row["aliases"] - {row["name"]})
        row["proposedCategories"] = sorted(row["proposedCategories"])
        row["popularityEvidence"] = [{"sourceUrl": source["url"], "reportedReviewCount": source["reportedReviewCount"], "caveat": source["reviewCountCaveat"]} for source in row["sources"] if "reportedReviewCount" in source]
        row["selectionBasis"] = "review activity reported by source" if row["popularityEvidence"] else "public business or operator directory presence; popularity unmeasured"
    return list(pool.values()), extracts


def apply_category_reviews(row: dict, reviews: list[dict]) -> None:
    """Human labels retain priority; assistant labels never become human gold."""
    human = {item["category"] for item in reviews if item.get("reviewerType", "human") == "human"}
    assistant = {item["category"] for item in reviews if item.get("reviewerType") == "assistant"}
    row["humanConfirmedCategory"] = next(iter(human)) if len(human) == 1 else None
    row["assistantReviewedCategory"] = next(iter(assistant)) if len(assistant) == 1 else None
    row["categoryReviewIds"] = sorted(item["id"] for item in reviews)
    row["labelStatus"] = ("human_reviewed_merchant_default" if len(human) == 1 else
                          "assistant_reviewed_merchant_default" if not human and len(assistant) == 1 else "needs_review")


def enrich_aliases(rows: list[dict], evidence: list[dict]) -> None:
    """Validate the whole enrichment before changing any existing identity."""
    by_name = {row["name"]: row for row in rows}
    owners = {}
    for row in rows:
        for name in {row["name"]} | set(row["aliases"]):
            key = normalize(name)
            if key in owners and owners[key] != row["businessId"]:
                raise ValueError(f"Ambiguous existing alias: {name}")
            owners[key] = row["businessId"]
    for item in evidence:
        row = by_name.get(item["businessName"])
        alias = item["alias"]
        if row is None or not re.search(r"[\u0621-\u064a]", alias):
            raise ValueError(f"Unknown business or non-Arabic alias: {item}")
        if not item["url"].startswith("https://") or not all(item.get(key) for key in ("publisher", "accessedOn", "identityEvidence", "type")):
            raise ValueError("Arabic alias requires source and identity evidence")
        key = normalize(alias)
        if key in owners and owners[key] != row["businessId"]:
            raise ValueError(f"Arabic alias belongs to multiple businesses: {alias}")
        owners[key] = row["businessId"]
    for item in evidence:
        row = by_name[item["businessName"]]
        row["aliases"].add(item["alias"])
        row["sources"].append({
            key: item[key] for key in ("url", "publisher", "type", "accessedOn", "identityEvidence")
        } | {"listedName": item["alias"], "cities": [],
             "caveat": "Arabic name evidence only; not an observed bank SMS descriptor or a new category approval."})


def preserve_selection(pool: list[dict], existing: list[dict]) -> list[dict]:
    """Enrichment must not silently re-rank the already reviewed shortlist."""
    by_id = {row["businessId"]: row for row in pool}
    if len(existing) != 200 or len({row["businessId"] for row in existing}) != 200:
        raise ValueError("Existing shortlist must contain 200 distinct identities")
    result = []
    for prior in existing:
        row = by_id.get(prior["businessId"])
        if row is None or row["brandGroup"] != prior["brandGroup"] or row["name"] != prior["name"]:
            raise ValueError(f"Existing business identity changed: {prior['name']}")
        result.append(row)
    return result


def select(pool: list[dict], count: int = 200, anchors: list[str] | None = None) -> list[dict]:
    if len(pool) < count:
        raise ValueError(f"Only {len(pool)} distinct sourced businesses available; do not pad to {count}")
    def priority(row):
        return (
            row["humanConfirmedCategory"] is None,
            not bool(row["popularityEvidence"]),
            -max((item["reportedReviewCount"] for item in row["popularityEvidence"]), default=0),
            -len({source["url"] for source in row["sources"]}),
            row["name"].casefold(),
        )
    ordered = sorted(pool, key=priority)
    selected = {}
    anchor_keys = {normalize(name) for name in (anchors or [])}
    for row in ordered:
        if normalize(row["name"]) in anchor_keys:
            selected[row["businessId"]] = row
    # Ensure both cities receive attention; this is a coverage quota, not an
    # inferred ranking or claim that the remaining businesses are less popular.
    for row in [row for row in ordered if "Irbid" in row["cities"]][:60]:
        selected[row["businessId"]] = row
    categories = sorted({category for row in pool for category in row["proposedCategories"]})
    for category in categories:
        for row in [row for row in ordered if category in row["proposedCategories"]][:8]:
            selected[row["businessId"]] = row
    for row in ordered:
        if len(selected) >= count:
            break
        selected[row["businessId"]] = row
    if len(selected) != count:
        raise ValueError("Coverage constraints exceeded requested count")
    return sorted(selected.values(), key=lambda row: row["name"].casefold())


def main():
    pool, extracts = build_pool()
    existing = [json.loads(line) for line in OUTPUT.read_text(encoding="utf-8").splitlines() if line.strip()] if OUTPUT.exists() else None
    rows = preserve_selection(pool, existing) if existing is not None else select(pool, anchors=extracts.get("coverageAnchors", []))
    if len({row["brandGroup"] for row in rows}) != 200:
        raise ValueError("Duplicate brands in shortlist")
    OUTPUT.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows), encoding="utf-8")
    manifest = {
        "version": "1.1.0", "accessedOn": extracts["accessedOn"],
        "selectionPreserved": existing is not None,
        "businessesWithArabicNameOrAlias": sum(any(re.search(r"[\u0621-\u064a]", name) for name in [row["name"]] + row["aliases"]) for row in rows),
        "businessCount": len(rows), "distinctBrandCount": len({row["brandGroup"] for row in rows}),
        "researchedDistinctPoolSize": len(pool),
        "cityCoverage": {city: sum(city in row["cities"] for row in rows) for city in ("Amman", "Irbid")},
        "proposedCategoryCounts": dict(Counter(category for row in rows for category in row["proposedCategories"])),
        "withReviewCountEvidence": sum(bool(row["popularityEvidence"]) for row in rows),
        "withReusedHumanMerchantLabel": sum(row["humanConfirmedCategory"] is not None for row in rows),
        "withAssistantMerchantLabel": sum(row["labelStatus"] == "assistant_reviewed_merchant_default" for row in rows),
        "sourceUrlCount": len({source["url"] for row in rows for source in row["sources"]}),
        "sha256": hashlib.sha256(OUTPUT.read_bytes()).hexdigest(),
        "popularityRankingStatus": "NOT_ESTABLISHED: no comparable citywide footfall, sales, or review metric. This is a sourced 200-business coverage shortlist, not a verified top-200 ranking.",
        "selectionMethod": "Include explicit sourced coverage anchors, up to 60 Irbid-listed brands, and category coverage. Prioritize reviewed defaults, attributed review activity and multiple-source evidence for remaining capacity. Anchor choices are editorial, not a measured popularity ranking. Output alphabetic, not rank order.",
        "editorialCoverageAnchors": extracts.get("coverageAnchors", []),
        "identityExclusions": extracts.get("excludeUntilIdentityReview", {}),
        "limitations": ["Names and presence do not establish bank SMS descriptor spelling.", "Review counts are attributed to each platform/branch and may be stale; never compare them as a universal popularity score.", "Most entries are Food or Shopping because directory coverage is biased.", "Directory listings may be outdated; research evidence does not establish a reuse license.", "Proposed categories are unreviewed assistant mappings; no certainty percentage is available.", "Fees, Installments and Cash Withdrawals require transaction context rather than distinct store names."]
    }
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    lines = ["# Amman and Irbid — 200 distinct businesses", "", "This is a sourced research shortlist, not a verified popularity ranking. One row represents one brand/business; branches and known aliases are grouped. Alphabetic numbering is only a row identifier. Proposed categories need review. Rebuilds preserve existing identities. Arabic names are public-source spellings, not verified bank SMS descriptors or independent category labels. Assistant decisions are sourced research labels and are distinct from human approvals.", "", "| # | Business | Arabic names / source | Cities with source evidence | Proposed category | Reviewed default / reviewer | Source |", "| --- | --- | --- | --- | --- | --- | --- |"]
    for number, row in enumerate(rows, 1):
        source = row["sources"][0]
        arabic = [f"[{item['listedName']}]({item['url']})" for item in row['sources'] if item['type'] in ('official_arabic_name', 'directory_arabic_name')]
        reviewed = (row['humanConfirmedCategory'] + ' / human' if row['humanConfirmedCategory'] is not None else
                    row['assistantReviewedCategory'] + ' / assistant' if row['labelStatus'] == 'assistant_reviewed_merchant_default' else '')
        lines.append(f"| {number} | {row['name']} | {'; '.join(arabic)} | {', '.join(row['cities'])} | {', '.join(row['proposedCategories'])} | {reviewed} | [{source['publisher']}]({source['url']}) |")
    READABLE.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({key: manifest[key] for key in ("businessCount", "researchedDistinctPoolSize", "cityCoverage", "withReviewCountEvidence", "withReusedHumanMerchantLabel")}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
