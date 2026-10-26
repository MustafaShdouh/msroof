"""Validate Masroof's frozen regression corpus without modifying it."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
FIXTURE_ROOT = ROOT / "tests" / "fixtures" / "sanitized_v1"
MANIFEST_PATH = FIXTURE_ROOT / "test_corpus_manifest.json"
REQUIRED_CASE_FIELDS = {
    "id", "category", "provider", "sender", "description", "body", "expected",
}
ALLOWED_EXPECTED_FIELDS = {
    "isValidTransaction", "type", "amount", "currency", "merchantOrParty",
    "merchant_or_party", "accountMask", "account_mask", "balance",
}
ALIAS_PAIRS = (
    ("merchantOrParty", "merchant_or_party"),
    ("accountMask", "account_mask"),
)
VALID_TRANSACTION_TYPES = {"EXPENSE", "INCOME"}


def _load_cases(payload: Any, fixture_name: str) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict) and isinstance(payload.get("testCases"), list):
        return payload["testCases"]
    raise ValueError(f"{fixture_name}: expected a list or an object with testCases")


def _hash_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_baseline(root: Path = FIXTURE_ROOT) -> list[str]:
    """Return corpus problems. An empty list means the frozen baseline is valid."""
    manifest_path = root / MANIFEST_PATH.name
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("schemaVersion") != 1:
        return ["manifest: unsupported schemaVersion"]

    fixtures = manifest.get("fixtures")
    if not isinstance(fixtures, dict) or not fixtures:
        return ["manifest: fixtures must be a non-empty object"]

    errors: list[str] = []
    all_ids: set[str] = set()
    for fixture_name, expected in fixtures.items():
        path = root / fixture_name
        if not path.is_file():
            errors.append(f"{fixture_name}: missing fixture")
            continue

        digest = _hash_file(path)
        if digest != expected.get("sha256"):
            errors.append(f"{fixture_name}: SHA-256 does not match frozen manifest")

        try:
            cases = _load_cases(json.loads(path.read_text(encoding="utf-8")), fixture_name)
        except (OSError, ValueError, json.JSONDecodeError) as error:
            errors.append(str(error))
            continue

        valid_count = 0
        for position, case in enumerate(cases):
            prefix = f"{fixture_name}[{position}]"
            if not isinstance(case, dict):
                errors.append(f"{prefix}: case must be an object")
                continue
            missing = REQUIRED_CASE_FIELDS.difference(case)
            if missing:
                errors.append(f"{prefix}: missing required fields {sorted(missing)}")
                continue
            if not isinstance(case["id"], str) or not case["id"].strip():
                errors.append(f"{prefix}: id must be a non-empty string")
            elif case["id"] in all_ids:
                errors.append(f"{prefix}: duplicate id {case['id']}")
            else:
                all_ids.add(case["id"])
            if not isinstance(case["body"], str) or not case["body"].strip():
                errors.append(f"{prefix}: body must be a non-empty string")

            expected_fields = case["expected"]
            if not isinstance(expected_fields, dict):
                errors.append(f"{prefix}: expected must be an object")
                continue
            unknown = set(expected_fields).difference(ALLOWED_EXPECTED_FIELDS)
            if unknown:
                errors.append(f"{prefix}: unknown expected fields {sorted(unknown)}")
            is_valid = expected_fields.get("isValidTransaction")
            if type(is_valid) is not bool:
                errors.append(f"{prefix}: isValidTransaction must be boolean")
                continue
            valid_count += int(is_valid)
            if is_valid:
                if expected_fields.get("type") not in VALID_TRANSACTION_TYPES:
                    errors.append(f"{prefix}: valid transaction type must be EXPENSE or INCOME")
                if expected_fields.get("amount") is None:
                    errors.append(f"{prefix}: valid transaction requires amount")
                if not expected_fields.get("currency"):
                    errors.append(f"{prefix}: valid transaction requires currency")
            for camel_case, snake_case in ALIAS_PAIRS:
                if camel_case in expected_fields and snake_case in expected_fields:
                    if expected_fields[camel_case] != expected_fields[snake_case]:
                        errors.append(f"{prefix}: {camel_case} and {snake_case} disagree")

        if len(cases) != expected.get("caseCount"):
            errors.append(f"{fixture_name}: expected {expected.get('caseCount')} cases, found {len(cases)}")
        if valid_count != expected.get("validCaseCount"):
            errors.append(f"{fixture_name}: expected {expected.get('validCaseCount')} valid cases, found {valid_count}")
        if len(cases) - valid_count != expected.get("invalidCaseCount"):
            errors.append(f"{fixture_name}: invalid case count does not match manifest")
    return errors


def main() -> int:
    errors = validate_baseline()
    if errors:
        print("Frozen test corpus validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("Frozen test corpus valid: 226 cases across 2 fixtures.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
