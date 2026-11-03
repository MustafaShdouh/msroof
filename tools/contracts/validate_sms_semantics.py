"""Validate annotation evidence independently of inference or a model's predictions."""
import hashlib
import json
from pathlib import Path

from tools.contracts.validate_transaction_behavior import finite_positive_number, require

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = json.loads((ROOT / "config/contracts/sms_semantics_annotations.json").read_text(encoding="utf-8"))
SEMANTICS = json.loads((ROOT / SCHEMA["semanticsSource"]).read_text(encoding="utf-8"))


def value_of(annotations, field):
    entry = annotations.get(field)
    return entry["value"] if entry and entry["state"] == "weak" else None


def derive_tracking(annotations):
    status = value_of(annotations, "transactionStatus")
    relation = value_of(annotations, "transferRelationship")
    if status == "non_transaction" or (status == "completed" and relation == "own_accounts"):
        return "exclude"
    if status == "uncertain":
        return "review"
    if status == "completed":
        amount_entry = annotations.get("amount", {})
        direction = value_of(annotations, "direction")
        if relation == "unknown" or direction == "uncertain" or (amount_entry.get("state") == "weak" and amount_entry.get("value") is None):
            return "review"
        if finite_positive_number(value_of(annotations, "amount")) and direction in ("incoming", "outgoing") and relation in ("not_transfer", "other_person"):
            return "include"
    return None


def validate_annotations(annotations, text):
    require(isinstance(annotations, dict) and set(annotations) <= set(SCHEMA["annotationFields"]), "unknown annotation field")
    for field, entry in annotations.items():
        require(isinstance(entry, dict) and set(entry) == set(SCHEMA["annotationEntryFields"]), "annotation entry fields differ")
        require(entry["state"] in SCHEMA["annotationStates"], "unsupported annotation state")
        if entry["state"] == "unannotated":
            require(all(entry[key] is None for key in ("value", "origin", "reviewer", "note")) and entry["evidence"] == [], "unannotated cannot assert facts")
            continue
        require(entry["origin"] in SCHEMA["annotationOrigins"] and entry["reviewer"] == "assistant", "drafts cannot claim human review")
        require(isinstance(entry["note"], str) and bool(entry["note"].strip()), "weak annotation needs an explanation")
        value = entry["value"]
        if field in SEMANTICS["enums"]:
            require(value in SEMANTICS["enums"][field], "invalid canonical enum")
        elif field == "amount":
            require(value is None or finite_positive_number(value), "invalid annotated amount")
        elif field == "expenseCategory":
            require(value is None or value in SEMANTICS["categories"], "invalid expense category")
        elif field == "currency":
            require(value is None or (isinstance(value, str) and len(value) == 3 and value.isascii() and value.isupper() and value.isalpha()), "invalid currency")
        else:
            require(value is None or (isinstance(value, str) and bool(value.strip())), "invalid source party")
        evidence = entry["evidence"]
        require(isinstance(evidence, list) and bool(evidence), "weak annotation needs evidence")
        if field == "trackingDecision":
            require(entry["origin"] == "derived_policy", "decision cannot be imported from a legacy label")
            require(all(isinstance(item, dict) and set(item) == {"kind", "field"} and item["kind"] == "annotation_field" and item["field"] != "trackingDecision" and item["field"] in annotations and annotations[item["field"]]["state"] == "weak" for item in evidence), "decision evidence must reference annotated facts")
            require(derive_tracking(annotations) == value, "decision is unsupported by annotated facts")
            require(derive_tracking({item["field"]: annotations[item["field"]] for item in evidence}) == value, "cited evidence does not establish the decision")
        else:
            require(entry["origin"] == "assistant_reviewed_text", "facts require text review, not predictions")
            for span in evidence:
                require(isinstance(span, dict) and set(span) == {"kind", "start", "end", "text"} and span["kind"] == "text_span", "invalid text evidence")
                start, end = span["start"], span["end"]
                require(type(start) is int and type(end) is int and 0 <= start < end <= len(text) and text[start:end] == span["text"], "evidence is not an exact source span")
            if field == "merchantOrCounterparty" and value is not None:
                require(any(span["text"] == value for span in evidence), "party value must preserve an exact source span")
    category = value_of(annotations, "expenseCategory")
    if category is not None:
        require(value_of(annotations, "trackingDecision") == "include" and value_of(annotations, "direction") == "outgoing" and value_of(annotations, "categoryStatus") == "assigned", "expense category requires eligible outgoing purpose")


def validate_record(record, source, index, fold, group_id):
    require(isinstance(record, dict) and set(record) == set(SCHEMA["recordFields"]), "draft fields differ")
    require(type(record["sourceIndex"]) is int and record["sourceIndex"] == index and record["recordId"] == source["recordId"], "source identity mismatch")
    require(record["textSha256"] == hashlib.sha256(source["text"].encode("utf-8")).hexdigest(), "source text hash mismatch")
    require(record["sourceExpressionId"] == source["sourceTemplateId"] and record["leakageGroupId"] == group_id, "source family/group mismatch")
    require(fold == "train" and record["fold"] == fold, "validation records cannot enter drafts")
    expected = {key: source[field] for key, field in SCHEMA["legacyFields"].items()}
    require(isinstance(record["legacyClaims"], dict) and set(record["legacyClaims"]) == set(expected)
            and all(type(record["legacyClaims"][key]) is type(value) and record["legacyClaims"][key] == value for key, value in expected.items()), "legacy claim was altered")
    require(isinstance(record["admissionBlockers"], list) and all(isinstance(x, str) for x in record["admissionBlockers"]), "invalid blockers")
    require(record["trainingEligible"] is False and record["independentEvaluationEligible"] is False, "drafts cannot grant data admission")
    validate_annotations(record["annotations"], source["text"])
