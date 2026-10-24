"""Build unreviewed merchant-name candidates without generating SMS or labels.

Extract only the explicit MERCHANTS list from the synthetic source, avoiding
personal transfer recipients, then merge the public local-business seed file.
"""

from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "training" / "expand_dataset.py"
LOCAL_SOURCE = ROOT / "data" / "annotations" / "local_merchant_sources.json"
OUTPUT = ROOT / "data" / "annotations" / "merchant_candidates.jsonl"


def prepare() -> list[dict]:
    candidates: dict[str, dict] = {}

    def add(name: str, origin: dict, category=None, cities=None, brand_group=None):
        key = re.sub(r"\s+", " ", name).strip().casefold()
        if key not in candidates:
            candidates[key] = {
                "id": "merchant-" + hashlib.sha256(key.encode("utf-8")).hexdigest()[:16],
                "name": name, "origins": [], "cities": [],
                "brandGroup": brand_group,
                "proposedCategory": category,
                "categoryLabelStatus": "unreviewed",
                "modelConfidence": None,
                "reviewed": False,
                "eligibleForSupervisedTraining": False,
            }
        row = candidates[key]
        row["origins"].append(origin)
        row["cities"] = sorted(set(row["cities"]) | set(cities or []))
        if category:
            row["proposedCategory"] = category
        if brand_group:
            row["brandGroup"] = brand_group

    tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
    merchants = None
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name) and target.id == "MERCHANTS" for target in node.targets):
            merchants = ast.literal_eval(node.value)
            break
    if not isinstance(merchants, list) or not all(isinstance(name, str) and name.strip() for name in merchants):
        raise ValueError("Expected a literal list of merchant names in MERCHANTS")
    for name in merchants:
        add(name, {"kind": "existing_synthetic_merchant_list", "path": SOURCE.relative_to(ROOT).as_posix(), "existenceVerified": False})

    local = json.loads(LOCAL_SOURCE.read_text(encoding="utf-8"))
    categories = set(json.loads((ROOT / "data/annotations/category_annotation_schema.json").read_text(encoding="utf-8-sig"))["allowedCategories"])
    sources = {source["id"]: source for source in local["sources"]}
    for merchant in local["merchants"]:
        if merchant["proposedCategory"] not in categories:
            raise ValueError("Unknown proposed category")
        source = sources[merchant["sourceId"]]
        origin = {
            "kind": "public_business_listing", "url": source["url"],
            "publisher": source["publisher"], "accessedOn": local["accessedOn"],
            "evidence": source["evidence"],
            "categoryBasis": "assistant inference from listed business type; unreviewed",
            "reuseLicense": "not established; research seeds only",
        }
        if merchant.get("note"):
            origin["note"] = merchant["note"]
        add(merchant["name"], origin, merchant["proposedCategory"], merchant["cities"], merchant["brandGroup"])
    return [candidates[key] for key in sorted(candidates)]


if __name__ == "__main__":
    rows = prepare()
    OUTPUT.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows), encoding="utf-8")
    public_count = sum(any(origin["kind"] == "public_business_listing" for origin in row["origins"]) for row in rows)
    print(f"Prepared {len(rows)} candidates, {public_count} with public source evidence: {OUTPUT}")
