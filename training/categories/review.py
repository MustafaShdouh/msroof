"""Create small offline merchant review batches and import explicit decisions.

Proposals, human decisions, and generated queues live in separate files.
No proposal is automatically accepted and no confidence is fabricated.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
ANNOTATIONS = ROOT / "data" / "annotations"
CANDIDATES = ANNOTATIONS / "merchant_candidates.jsonl"
REVIEWS = ANNOTATIONS / "merchant_reviews.jsonl"
BATCH_PATH = ANNOTATIONS / "merchant_review_batch.json"
HTML_PATH = ROOT / "tools" / "browser" / "merchant_review.html"
TEMPLATE = HTML_PATH.with_name("merchant_review_template.html")
TAXONOMY = ANNOTATIONS / "category_annotation_schema.json"
EDGE_CASES = ANNOTATIONS / "category_edge_cases.json"
BUSINESSES = ANNOTATIONS / "businesses_200.jsonl"
AMBIGUITIES = ANNOTATIONS / "business_ambiguities.json"


def read_lines(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows = []
    for number, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
        if not line.strip():
            continue
        row = json.loads(line)
        if not isinstance(row, dict):
            raise ValueError(f"{path.name}:{number}: expected an object")
        rows.append(row)
    return rows


def categories() -> list[str]:
    return json.loads(TAXONOMY.read_text(encoding="utf-8-sig"))["allowedCategories"]


def indexed_candidates() -> dict[str, dict]:
    rows = read_lines(CANDIDATES)
    known = {row["id"]: row for row in rows}
    for business in read_lines(BUSINESSES):
        name_key = " ".join(business["name"].split()).casefold()
        candidate_id = "merchant-" + hashlib.sha256(name_key.encode("utf-8")).hexdigest()[:16]
        if candidate_id in known:
            known[candidate_id]["curatedBusinessId"] = business["businessId"]
            continue
        row = {
            "id": candidate_id, "name": business["name"],
            "brandGroup": business["brandGroup"], "cities": business["cities"],
            "proposedCategory": business["proposedCategories"][0] if len(business["proposedCategories"]) == 1 else None,
            "modelConfidence": None, "reviewed": False,
            "curatedBusinessId": business["businessId"],
            "origins": [{"kind": "public_business_listing", "url": source["url"], "publisher": source["publisher"], "evidence": "Business name and city supported by public listing; category is a proposal, popularity ranking unestablished."} for source in business["sources"]],
        }
        rows.append(row)
        known[candidate_id] = row
    if EDGE_CASES.exists():
        edge_payload = json.loads(EDGE_CASES.read_text(encoding="utf-8"))
        if edge_payload.get("schemaVersion") != "1.0.0":
            raise ValueError("Unsupported edge-case version")
        for case in edge_payload["cases"]:
            if case.get("labelScope") != "illustrative_transaction" or not isinstance(case.get("exampleText"), str) or not case["exampleText"].strip():
                raise ValueError("Edge cases must explicitly identify illustrative transaction text")
            rows.append({
                **case, "proposedCategory": None, "cities": [],
                "reviewed": False, "modelConfidence": None,
                "origins": [{"kind": "illustrative_scenario", "evidence": "Authored example, not a collected bank SMS. Service sources support the ambiguity only."}]
                + [{"kind": "service_context_source", "url": url, "publisher": "Service information"} for url in case["sources"]],
            })
    allowed = categories()
    for row in rows:
        if not isinstance(row.get("id"), str) or not isinstance(row.get("name"), str) or not row["name"].strip():
            raise ValueError("Candidate identifiers and names must be text")
        if row.get("proposedCategory") is not None and row["proposedCategory"] not in allowed:
            raise ValueError("Candidate has unsupported proposed category")
        if any(label not in allowed for label in row.get("possibleCategories", [])):
            raise ValueError("Edge case has unsupported alternative category")
    result = {row["id"]: row for row in rows}
    if len(result) != len(rows):
        raise ValueError("Duplicate candidate identifiers")
    return result


def decision(raw: dict, candidates: dict[str, dict]) -> dict:
    candidate_id = raw.get("id")
    if not isinstance(candidate_id, str) or candidate_id not in candidates:
        raise ValueError("Unknown merchant identifier")
    candidate = candidates[candidate_id]
    if raw.get("name") != candidate["name"]:
        raise ValueError(f"{candidate_id}: name differs from candidate")
    if candidate.get("labelScope") == "illustrative_transaction" and raw.get("exampleText") != candidate["exampleText"]:
        raise ValueError(f"{candidate_id}: illustrative example text changed or missing")
    status = raw.get("status")
    if status not in {"approved", "needs_context", "skipped"}:
        raise ValueError(f"{candidate_id}: invalid review status")
    reviewer = raw.get("reviewer")
    if not isinstance(reviewer, str) or not reviewer.strip():
        raise ValueError(f"{candidate_id}: reviewer is required")
    group = raw.get("brandGroup")
    if group is not None and (not isinstance(group, str) or not group.strip()):
        raise ValueError(f"{candidate_id}: brand group must be nonempty text")
    if status == "approved":
        if raw.get("category") not in categories():
            raise ValueError(f"{candidate_id}: unsupported category")
        if not group:
            raise ValueError(f"{candidate_id}: approval requires a brand group for evaluation splitting")
        if candidate.get("brandGroup") and group != candidate["brandGroup"]:
            raise ValueError(f"{candidate_id}: preserve the sourced brand group {candidate['brandGroup']!r}")
    notes = raw.get("notes", "")
    if not isinstance(notes, str):
        raise ValueError(f"{candidate_id}: notes must be text")
    reviewer_type = raw.get("reviewerType", "human")
    if reviewer_type not in {"human", "assistant"}:
        raise ValueError(f"{candidate_id}: invalid reviewer type")
    evidence = raw.get("reviewEvidence", [])
    if not isinstance(evidence, list) or any(not isinstance(item, dict) or not isinstance(item.get("url"), str)
            or not item["url"].startswith("https://") or not isinstance(item.get("summary"), str)
            or not item["summary"].strip() for item in evidence):
        raise ValueError(f"{candidate_id}: invalid review evidence")
    if reviewer_type == "assistant" and (not evidence or not notes.strip()):
        raise ValueError(f"{candidate_id}: assistant review requires source evidence and rationale")
    result = {
        "schemaVersion": "1.0.0", "id": candidate_id, "name": candidate["name"],
        "status": status, "category": raw.get("category") if status == "approved" else None,
        "brandGroup": group, "reviewer": reviewer.strip(), "notes": notes,
        "labelScope": candidate.get("labelScope", "merchant_name"), "origins": candidate["origins"],
        "reviewerType": reviewer_type,
        "reviewEvidence": evidence,
    }
    if candidate.get("labelScope") == "illustrative_transaction":
        result.update({
            "exampleText": candidate["exampleText"],
            "reviewQuestion": candidate["reviewQuestion"],
            "dataKind": f"{reviewer_type}_reviewed_illustrative_scenario" if status == "approved" else "illustrative_scenario",
        })
    return result


def existing_reviews(candidates: dict[str, dict]) -> dict[str, dict]:
    result = {}
    for raw in read_lines(REVIEWS):
        row = decision(raw, candidates)
        # Source snapshots belong to the recorded review, not today's regenerated candidates.
        if isinstance(raw.get("origins"), list):
            row["origins"] = raw["origins"]
        if row["id"] in result:
            raise ValueError("Duplicate persisted review identifiers")
        result[row["id"]] = row
    return result


def import_reviews(path: Path) -> int:
    candidates = indexed_candidates()
    saved = existing_reviews(candidates)
    original_records = {row["id"]: row for row in read_lines(REVIEWS)}
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict) or payload.get("schemaVersion") != "1.0.0":
        raise ValueError("Unsupported review export")
    if not isinstance(payload.get("reviews"), list) or not payload["reviews"]:
        raise ValueError("Review export has no decisions")
    pending = {}
    for raw in payload["reviews"]:
        if not isinstance(raw, dict):
            raise ValueError("Review decisions must be objects")
        row = decision(raw, candidates)
        if row["id"] in pending:
            raise ValueError("Duplicate identifiers in review export")
        prior = saved.get(row["id"])
        if row["reviewerType"] == "assistant" and prior and prior["reviewerType"] == "human":
            raise ValueError("Assistant reviews cannot overwrite existing human decisions")
        pending[row["id"]] = row
    # Apply only after every incoming record validates; proposal regeneration
    # never writes this file. A reviewer may explicitly revise an older decision.
    # Preserve untouched serialized decisions, including their original source snapshot.
    original_records.update(pending)
    temp = REVIEWS.with_suffix(".jsonl.tmp")
    temp.write_text("".join(json.dumps(original_records[key], ensure_ascii=False, sort_keys=True) + "\n" for key in sorted(original_records)), encoding="utf-8")
    os.replace(temp, REVIEWS)
    print(f"Imported {len(pending)} decisions; {len(original_records)} saved reviews.")
    return len(pending)


def create_batch(size: int, include_deferred: bool = False, businesses_only: bool = False) -> dict:
    if size < 1 or size > 100:
        raise ValueError("Batch size must be between 1 and 100")
    candidates = indexed_candidates()
    saved = existing_reviews(candidates)
    groups = defaultdict(list)
    for row in candidates.values():
        if row.get("labelScope", "merchant_name") != "merchant_name":
            continue
        if businesses_only and not row.get("curatedBusinessId"):
            continue
        review = saved.get(row["id"])
        if review and (review["status"] == "approved" or not include_deferred):
            continue
        groups[row.get("proposedCategory") or "Unassigned"].append(row)
    for rows in groups.values():
        # Surface documented ambiguity, followed by sourced examples. This is
        # bootstrap selection, not a model confidence ordering.
        rows.sort(key=lambda row: (
            not any(origin.get("note") for origin in row["origins"]),
            not any(origin["kind"] == "public_business_listing" for origin in row["origins"]),
            row["name"].casefold(),
        ))
    selected = []
    selected_groups = set()
    while len(selected) < size and any(groups.values()):
        for label in ["Unassigned"] + categories():
            rows = groups.get(label, [])
            while rows and (rows[0].get("brandGroup") or rows[0]["id"]) in selected_groups:
                rows.pop(0)
            if rows and len(selected) < size:
                row = rows.pop(0)
                selected.append(row)
                selected_groups.add(row.get("brandGroup") or row["id"])
    return write_batch(selected, "category-diverse bootstrap; documented ambiguity first; no fitted confidence model")


def create_edge_batch(size: int, include_deferred: bool = False) -> dict:
    if size < 1 or size > 100:
        raise ValueError("Batch size must be between 1 and 100")
    candidates = indexed_candidates()
    saved = existing_reviews(candidates)
    selected = []
    for candidate in candidates.values():
        if candidate.get("labelScope") != "illustrative_transaction":
            continue
        previous = saved.get(candidate["id"])
        if previous and (previous["status"] == "approved" or not include_deferred):
            continue
        selected.append(candidate)
    return write_batch(selected[:size], "curated taxonomy-boundary cases; illustrative transactions; no model confidence")


def create_ambiguous_batch(size: int, include_deferred: bool = False) -> dict:
    if size < 1 or size > 100:
        raise ValueError("Batch size must be between 1 and 100")
    candidates = indexed_candidates()
    saved = existing_reviews(candidates)
    by_name = {row["name"].casefold(): row for row in candidates.values() if row.get("curatedBusinessId")}
    registry = json.loads(AMBIGUITIES.read_text(encoding="utf-8"))
    selected = []
    groups = set()
    for item in registry["businesses"]:
        candidate = by_name.get(item["name"].casefold())
        if candidate is None:
            raise ValueError(f"Ambiguous business is absent from sourced pool: {item['name']}")
        if any(category not in categories() for category in item["categories"]):
            raise ValueError("Ambiguity question has unsupported categories")
        review = saved.get(candidate["id"])
        if review and (review["status"] == "approved" or not include_deferred):
            continue
        group = candidate.get("brandGroup") or candidate["id"]
        if group in groups:
            continue
        groups.add(group)
        selected.append({**candidate, "reviewMode": "ambiguity", "reviewQuestion": item["question"], "possibleCategories": item["categories"]})
    return write_batch(selected[:size], "ambiguous real-business names and category boundaries; editorial selection, not model confidence")


def write_batch(selected: list[dict], method: str) -> dict:
    digest = hashlib.sha256(CANDIDATES.read_bytes() + (EDGE_CASES.read_bytes() if EDGE_CASES.exists() else b"") + (BUSINESSES.read_bytes() if BUSINESSES.exists() else b"")).hexdigest()
    batch = {
        "schemaVersion": "1.0.0", "candidateSha256": digest,
        "selectionMethod": method,
        "categories": categories(), "candidates": selected,
    }
    BATCH_PATH.write_text(json.dumps(batch, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    embedded = json.dumps(batch, ensure_ascii=False).replace("<", "\\u003c").replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")
    HTML_PATH.write_text(TEMPLATE.read_text(encoding="utf-8").replace("__BATCH_JSON__", embedded), encoding="utf-8")
    print(f"Created {len(selected)}-merchant review: {HTML_PATH}")
    return batch


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    batch_parser = commands.add_parser("batch")
    batch_parser.add_argument("--size", type=int, default=12)
    batch_parser.add_argument("--include-deferred", action="store_true")
    batch_parser.add_argument("--edge-cases", action="store_true", help="Review illustrative category-boundary examples")
    batch_parser.add_argument("--businesses", action="store_true", help="Select only from the sourced 200-business shortlist")
    batch_parser.add_argument("--ambiguous", action="store_true", help="Select ambiguous sourced businesses only")
    import_parser = commands.add_parser("import")
    import_parser.add_argument("path", type=Path)
    commands.add_parser("status")
    args = parser.parse_args()
    if args.command == "batch":
        if args.ambiguous:
            if args.edge_cases:
                raise ValueError("Choose ambiguous businesses or illustrative edge cases")
            create_ambiguous_batch(args.size, args.include_deferred)
            return
        if args.edge_cases:
            if args.businesses:
                raise ValueError("Choose edge-case or business mode, not both")
            create_edge_batch(args.size, args.include_deferred)
        else:
            create_batch(args.size, args.include_deferred, args.businesses)
    elif args.command == "import":
        import_reviews(args.path)
    else:
        candidates = indexed_candidates()
        saved = existing_reviews(candidates)
        print(json.dumps({"candidates": len(candidates), "reviews": dict(Counter(row["status"] for row in saved.values()))}, indent=2))


if __name__ == "__main__":
    try:
        main()
    except (ValueError, KeyError, TypeError, OSError) as error:
        print(f"Merchant review error: {error}", file=sys.stderr)
        raise SystemExit(1)
