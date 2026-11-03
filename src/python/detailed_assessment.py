"""Contract assessment from structural event evidence, independent of sender gates."""
import json
import re
from pathlib import Path

from .authorization_request import is_authorization_request
from .entity_text import EntityText
from .money_candidates import mask_balances, amounts, has_movement_amount
from .direction_policy import initial_direction, resolve_relationship, recording_decision
from .service_notice import is_service_notice
from .account_movement import has_account_debit, has_account_credit

RULES = json.loads((Path(__file__).resolve().parents[2] / "config/contracts/transaction_evidence.json").read_text(encoding="utf-8"))
RX = {key: re.compile(value, re.I | re.ASCII) for key, value in RULES["patterns"].items()}
PURPOSE = {key: re.compile(value, re.I | re.ASCII) for key, value in RULES["purpose"].items()}
def non_transaction(reasons):
    return {"contractVersion": "1.0.0", "transactionStatus": "non_transaction", "trackingDecision": "exclude",
            "reasonCodes": sorted(set(reasons)), "amount": None, "currency": None, "currencyResolution": "not_applicable",
            "direction": "not_applicable", "transferRelationship": "not_applicable", "merchantOrCounterparty": None,
            "expenseCategory": None, "categoryStatus": "not_applicable"}


def exact_party(raw):
    source = EntityText(raw)
    for key in ("partyLabelAnchor", "partyAnchor"):
        for anchor in RX[key].finditer(source.text):
            match = RX["partyValue"].search(source.text[anchor.end():])
            if not match:
                continue
            candidate = match[1].rstrip(" .;,")
            if not candidate or RX["partyReject"].search(candidate) or RX["partyAccountRole"].search(candidate):
                continue
            chosen = source.exact(anchor.end(), anchor.end() + len(candidate))
            if chosen and not RX["alignedLocation"].search(chosen):
                return chosen
    return None


def completion_evidence(clause):
    return bool(RX["completion"].search(clause) or RX["postedDebit"].search(clause) or RX["postedCredit"].search(clause)
                or has_account_debit(clause) or has_account_credit(clause))


def conditional_clause(clause):
    return bool(RX["conditionalStart"].search(clause) and completion_evidence(clause))



def personal_context(clause):
    return any(RX[key].search(clause) for key in ("chat", "personalFrame", "reportedSpeech", "evidenceInquiry"))


def pending_clause(clause):
    return bool(RX["deferred"].search(RX["resolvedPending"].sub("", clause)))


def completed_clause(clause, allow_purchase):
    if conditional_clause(clause) or RX["completionDenied"].search(clause) or personal_context(clause) or RX["outcomeUnknown"].search(clause):
        return False
    # Posting loyalty points is not monetary completion. Remove only that
    # event phrase so an independent cash posting in the same clause survives.
    if RX["nonCashPosting"].search(clause):
        clause = RX["nonCashPosting"].sub("", clause)
    if RX["resolvedPending"].search(clause):
        clause = RX["resolvedPending"].sub("", clause)
    purchase = allow_purchase and RX["purchaseEvidence"].search(clause) and not any(
        RX[key].search(clause) for key in ("purchaseUnsettled", "purchaseConditional", "deferred", "declined", "chat"))
    return bool(completion_evidence(clause) or purchase)



def unresolved_completion(clauses):
    # Unknown outcomes are evidence, not a low financial-candidate score.
    # Ignore explicit conversational/example/authorization scope first.
    noncash_seen = financial_context = unknown = final_unknown = False
    for clause in clauses:
        if personal_context(clause) or RX["otpRequest"].search(clause) or RX["promotion"].search(clause) or is_authorization_request(clause):
            continue
        if RX["nonCashPosting"].search(clause):
            noncash_seen = True
            clause = RX["nonCashPosting"].sub("", clause)
        financial_context = financial_context or bool(RX["financialOutcomeContext"].search(clause)
            or RX["postedDebit"].search(clause) or RX["postedCredit"].search(clause)
            or has_account_debit(clause) or has_account_credit(clause))
        unknown = unknown or bool(RX["outcomeUnknown"].search(clause) or RX["contextUnknown"].search(clause))
        final_unknown = final_unknown or bool(RX["finalOutcomeUnknown"].search(clause))
    if noncash_seen and not financial_context:
        return False
    return unknown or (financial_context and final_unknown)


def assess(input_value, extract, parse_number, financial_candidate, ownership_override=None):
    raw = input_value.get("text") if isinstance(input_value, dict) else None
    if not isinstance(raw, str) or not raw.strip():
        return non_transaction(["empty_or_malformed"])
    source = EntityText(raw)
    text = source.text
    if not text:
        return non_transaction(['empty_or_malformed'])
    # Separate a trailing conditional so it cannot erase an earlier receipt fact.
    clauses = [part for sentence in RX["sentence"].split(text)
               for part in RX["conditionalBoundary"].split(sentence) if part.strip()]
    allow_purchase = not RX["purchaseQualification"].search(text)
    unresolved = unresolved_completion(clauses)
    has_completion = any(completed_clause(part, allow_purchase) for part in clauses)
    completed, negative, relevant = [], [], []
    for clause in clauses:
        complete = completed_clause(clause, allow_purchase)
        reasons = []
        if personal_context(clause): reasons.append("personal_conversation")
        if is_authorization_request(clause) or RX["otpRequest"].search(clause) or (RX["otp"].search(clause) and not has_completion): reasons.append("otp_or_authorization")
        if RX["declined"].search(clause): reasons.append("declined_or_failed")
        if conditional_clause(clause) or pending_clause(clause) or RX["completionDenied"].search(clause) or RX["purchaseConditional"].search(clause): reasons.append("pending_or_requested")
        if ((RX["nonCashPosting"].search(clause) or RX["administration"].search(clause)) and not complete) or RX["promotion"].search(clause) or (RX["serviceScope"].search(clause) and is_service_notice(clause)): reasons.append("promotion_or_administration")
        if complete: completed.append(clause)
        if reasons: negative.extend(reasons)
        if not reasons: relevant.append(clause)
    conflicts = bool(completed and set(negative) - {"promotion_or_administration"})
    if not completed and negative and not unresolved:
        if (set(negative) == {"personal_conversation"} and RX["evidenceInquiry"].search(text)
                and not RX["chat"].search(text) and not RX["personalFrame"].search(text) and RX["balance"].search(text)
                and not RX["financial"].search(text) and not any(completion_evidence(part) for part in clauses)):
            return non_transaction(["balance_only"])
        return non_transaction(negative)
    if not completed and not unresolved and RX["balanceInquiry"].search(text):
        return non_transaction(["balance_only"])
    if not completed and not unresolved and not RX["financial"].search(mask_balances(text)):
        if RX["balance"].search(text): return non_transaction(["balance_only"])
        if not financial_candidate(text): return non_transaction(["personal_conversation"])
    status = "completed" if completed and not conflicts and not unresolved and not RX["outcomeUnknown"].search(text) else "uncertain"
    semantic = " ".join(relevant)
    direction, relation = initial_direction(text, relevant)
    extracted = extract(raw, "INCOME" if direction == "incoming" else "EXPENSE")
    amount, unit, resolution = amounts(text, extracted, parse_number, source, allow_unmarked=status=='completed')
    if len(completed) > 1 and sum(has_movement_amount(part, parse_number) for part in completed) > 1:
        status, amount = "uncertain", None
    direction, relation = resolve_relationship(text, semantic, amount, negative, direction, relation, ownership_override)
    decision = recording_decision(status, amount, direction, relation)
    purpose = [label for label, pattern in PURPOSE.items() if pattern.search(semantic)] if decision == "include" and direction == "outgoing" else []
    label = purpose[0] if len(purpose) == 1 else None
    category_status = ("assigned" if label else "uncertain") if decision == "include" and direction == "outgoing" else "not_applicable"
    reasons = ["completed_transaction" if status == "completed" else "completion_unresolved"]
    if amount is None: reasons.append("amount_unresolved")
    if direction == "uncertain": reasons.append("direction_unresolved")
    if relation == "unknown": reasons.append("transfer_ownership_unresolved")
    if relation == "own_accounts": reasons.append("own_account_transfer")
    if category_status == "uncertain": reasons.append("category_unresolved")
    return {"contractVersion": "1.0.0", "transactionStatus": status, "trackingDecision": decision, "reasonCodes": sorted(reasons),
            "amount": amount, "currency": unit, "currencyResolution": resolution, "direction": direction,
            "transferRelationship": relation, "merchantOrCounterparty": None if relation == "own_accounts" else exact_party(raw),
            "expenseCategory": label, "categoryStatus": category_status}
