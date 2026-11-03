"""Message-bound human ownership confirmation; no persistence or authentication."""
import json
import re
from pathlib import Path

CONTRACT = json.loads((Path(__file__).resolve().parents[2] / "config/contracts/ownership_context.json").read_text(encoding="utf-8"))


def identifier(value):
    return isinstance(value, str) and re.fullmatch(CONTRACT["blankIdentifierPattern"], value) is None


def fields(value, required, optional=()):
    return isinstance(value, dict) and set(required) <= value.keys() <= set(required) | set(optional)


def context_error(request):
    """Closed error precedence; compare IDs and raw text without normalization."""
    c = CONTRACT
    if not fields(request, c["requestRequired"], c["requestOptional"]):
        return "invalid_request"
    message = request["message"]
    if not all(identifier(request[key]) for key in ("ownerScopeId", "messageId")) or not fields(message, c["messageRequired"], c["messageOptional"]):
        return "invalid_request"
    if not isinstance(message["text"], str):
        return "invalid_request"
    if any(key in message and message[key] is not None and not isinstance(message[key], str) for key in ("sender", "receivedAt")):
        return "invalid_request"
    if "isContact" in message and type(message["isContact"]) is not bool:
        return "invalid_request"
    context = request.get("ownershipContext")
    if context is None:
        return None
    if not fields(context, c["contextFields"]) or not all(isinstance(context[key], str) for key in c["contextFields"]):
        return "invalid_context"
    if not all(identifier(context[key]) for key in ("ownerScopeId", "messageId")) or context["relationship"] not in c["relationships"]:
        return "invalid_context"
    if context["schemaVersion"] != c["contractVersion"]:
        return "unsupported_version"
    if context["evidence"] != "user_confirmed":
        return "untrusted_evidence"
    if context["ownerScopeId"] != request["ownerScopeId"]:
        return "owner_mismatch"
    if context["messageId"] != request["messageId"] or context["text"] != message["text"]:
        return "message_mismatch"
    return None


def assess_with_ownership(request, evaluate):
    message = request.get("message") if isinstance(request, dict) else None
    error = context_error(request)
    assessment = evaluate(message)
    transfer = assessment["transferRelationship"] in CONTRACT["relationships"]
    status, reason = "absent", "not_provided"
    override = None
    if error:
        status, reason = "invalid", error
        if transfer:
            override = {"relationship": "unknown", "uncertainDirection": False}
    elif request.get("ownershipContext") is not None:
        relationship = request["ownershipContext"]["relationship"]
        body_relation = assessment["transferRelationship"]
        if assessment["transactionStatus"] == "non_transaction":
            status, reason = "not_applicable", "non_transaction"
        elif not transfer:
            status, reason = "not_applicable", "not_a_transfer"
        elif relationship == "unknown":
            status, reason = "unresolved", "confirmation_unknown"
        elif body_relation != "unknown" and body_relation != relationship:
            status, reason = "conflict", "text_context_conflict"
            override = {"relationship": "unknown", "uncertainDirection": True}
        else:
            status, reason = "applied", "confirmed_relationship"
            override = {"relationship": relationship, "uncertainDirection": False}
    if override is not None:
        assessment = evaluate(message, override)
    return {"ownershipContractVersion": CONTRACT["contractVersion"], "assessment": assessment,
            "contextStatus": status, "contextReason": reason}
