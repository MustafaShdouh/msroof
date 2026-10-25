"""Validate target-contract examples; this does not classify text or run a model."""
import json
import math
import re
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONTRACT_PATH = ROOT / "config/contracts/transaction_behavior.json"
CASES_PATH = ROOT / "tests/fixtures/transaction_behavior_cases.json"


def load_contract():
    return json.loads(CONTRACT_PATH.read_text(encoding="utf-8-sig"))


def require(condition, message):
    if not condition:
        raise ValueError(message)


def finite_positive_number(value):
    if type(value) not in (int, float):
        return False
    try:
        return value > 0 and math.isfinite(value)
    except OverflowError:
        return False


def validate_input(value, contract):
    require(isinstance(value, dict), "input must be an object")
    spec = contract["input"]
    require(set(spec["required"]) <= value.keys(), "input text is required")
    require(value.keys() <= set(spec["required"] + spec["optional"]), "unknown input field")
    require(isinstance(value["text"], str), "input text must be a string")
    if "sender" in value:
        require(value["sender"] is None or isinstance(value["sender"], str), "sender must be text or null")
    if "isContact" in value:
        require(type(value["isContact"]) is bool, "isContact must be boolean")
    if value.get("receivedAt") is not None:
        require(isinstance(value["receivedAt"], str), "receivedAt must be text or null")
        timestamp = datetime.fromisoformat(value["receivedAt"].replace("Z", "+00:00"))
        require(timestamp.utcoffset() is not None, "receivedAt must include an offset")


def validate_result(result, contract=None):
    contract = contract or load_contract()
    require(isinstance(result, dict), "result must be an object")
    require(set(result) == set(contract["resultFields"]), "result fields do not match the contract")
    require(result["contractVersion"] == contract["contractVersion"], "unsupported contract version")
    for field, choices in contract["enums"].items():
        require(result[field] in choices, f"invalid {field}")
    reasons = result["reasonCodes"]
    require(isinstance(reasons, list) and all(isinstance(x, str) for x in reasons), "reasonCodes must be strings")
    require(len(reasons) == len(set(reasons)), "duplicate reason code")
    require(set(reasons) <= set(contract["reasonCodes"]), "unknown reason code")
    amount = result["amount"]
    require(amount is None or finite_positive_number(amount),
            "amount must be a finite positive number or null")
    party = result["merchantOrCounterparty"]
    require(party is None or (isinstance(party, str) and bool(party.strip())), "invalid merchant/counterparty")
    label = result["expenseCategory"]
    require(label is None or label in contract["categories"], "unsupported expense category")

    status = result["transactionStatus"]
    relation = result["transferRelationship"]
    direction = result["direction"]
    category_status = result["categoryStatus"]
    expected_reasons = set()
    if status == "non_transaction":
        require(result["trackingDecision"] == "exclude", "non-transactions must be excluded")
        require(amount is None and result["currency"] is None and party is None, "non-transaction financial fields must be null")
        require(all(result[x] == "not_applicable" for x in
                    ("currencyResolution", "direction", "transferRelationship", "categoryStatus")),
                "non-transaction fields must be not_applicable")
        require(label is None, "non-transactions cannot have an expense category")
        require(bool(reasons) and set(reasons) <= set(contract["nonTransactionReasonCodes"]),
                "non-transaction requires a non-transaction reason")
        return

    require(isinstance(result["currency"], str) and re.fullmatch(r"[A-Z]{3}", result["currency"]), "invalid currency code")
    require(result["currencyResolution"] != "not_applicable", "currency resolution is required")
    if result["currencyResolution"].startswith("default_"):
        require(result["currency"] == contract["defaultCurrency"], "default currency must be JOD")
    require(relation != "not_applicable", "transfer relationship is required")
    if relation == "own_accounts":
        require(direction == "not_applicable", "own-account movement has no net direction")
        expected_reasons.add("own_account_transfer")
    else:
        require(direction != "not_applicable", "direction must be resolved or uncertain")
        if direction == "uncertain":
            expected_reasons.add("direction_unresolved")
    if amount is None:
        expected_reasons.add("amount_unresolved")
    if relation == "unknown":
        expected_reasons.add("transfer_ownership_unresolved")

    if status == "uncertain":
        decision = "review"
        expected_reasons.add("completion_unresolved")
    else:
        expected_reasons.add("completed_transaction")
        if relation == "own_accounts":
            decision = "exclude"
        elif amount is None or direction == "uncertain" or relation == "unknown":
            decision = "review"
        else:
            decision = "include"
    require(result["trackingDecision"] == decision, "tracking decision contradicts evidence state")
    if decision == "include" and direction == "outgoing":
        require(category_status in ("assigned", "uncertain"), "outgoing category must be assigned or uncertain")
        if category_status == "uncertain":
            expected_reasons.add("category_unresolved")
    else:
        require(category_status == "not_applicable", "category is only applicable to included outgoing transactions")
    require((category_status == "assigned") == (label is not None), "category label/status mismatch")
    require(set(reasons) == expected_reasons, "reason codes contradict result fields")


def validate_bundle(bundle, contract=None):
    contract = contract or load_contract()
    require(set(contract["fieldTypes"]) == set(contract["resultFields"]), "result type definitions drifted")
    taxonomy = json.loads((ROOT / contract["taxonomySource"]).read_text(encoding="utf-8"))
    require(contract["categories"] == taxonomy["allowedCategories"], "canonical category taxonomy drift")
    require(bundle["contractVersion"] == contract["contractVersion"], "scenario contract version mismatch")
    require(bundle["dataKind"] == "authored_policy_contract_examples", "scenario provenance missing")
    require(bundle["trainingEligible"] is False and bundle["evaluationEligible"] is False,
            "contract examples cannot become training or independent evaluation data")
    ids = set()
    for case in bundle["cases"]:
        require(isinstance(case["id"], str) and bool(case["id"].strip()) and case["id"] not in ids, "invalid/duplicate scenario ID")
        ids.add(case["id"])
        require(case["language"] in ("arabic", "english", "mixed"), "invalid language slice")
        require(case["labelSource"] == "assistant_authored_contract_example", "authored case cannot claim human truth")
        validate_input(case["input"], contract)
        validate_result(case["expected"], contract)

    reviews = [json.loads(line) for line in (ROOT / "data/annotations/merchant_reviews.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    reviewed = {row["id"]: row for row in reviews if row.get("labelScope") == "illustrative_transaction"
                and row.get("reviewerType", "human") == "human"}
    policies = bundle["reviewedCategoryPolicies"]
    require(len(policies) == len(reviewed) and {x["reviewId"] for x in policies} == set(reviewed),
            "reviewed category-policy membership drift")
    for case in policies:
        source = reviewed[case["reviewId"]]
        require(case["text"] == source["exampleText"], "reviewed scenario text changed")
        require(case["reviewer"] == source["reviewer"], "reviewer attribution changed")
        category = source["category"] if source["status"] == "approved" else None
        require(case["expectedCategory"] == category, "human category decision changed")
        require(case["categoryStatus"] == ("assigned" if category else "uncertain"), "reviewed category status changed")
        require(case["scope"] == "exact_reviewed_scenario_only", "human policy scope broadened")


def main():
    bundle = json.loads(CASES_PATH.read_text(encoding="utf-8"))
    validate_bundle(bundle)
    print(f"Behavior contract valid: {len(bundle['cases'])} authored cases, {len(bundle['reviewedCategoryPolicies'])} reviewed category policies; no model inference")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, KeyError, TypeError) as error:
        print(f"Behavior contract invalid: {error}", file=sys.stderr)
        raise SystemExit(1)
