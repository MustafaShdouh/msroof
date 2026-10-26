"""Contract assessment from structural event evidence, independent of sender gates."""
import json
import math
import re
from pathlib import Path

from .authorization_request import is_authorization_request
from .entity_text import EntityText
from .service_notice import is_service_notice

RULES = json.loads((Path(__file__).resolve().parents[2] / "config/contracts/transaction_evidence.json").read_text(encoding="utf-8"))
RX = {key: re.compile(value, re.I | re.ASCII) for key, value in RULES["patterns"].items()}
PURPOSE = {key: re.compile(value, re.I | re.ASCII) for key, value in RULES["purpose"].items()}
ALIASES = {key.upper(): value for key, value in RULES["currencyAliases"].items()}
currency = r"(?<![A-Za-z\u0621-\u064A])(?:" + "|".join(re.escape(key) for key in sorted(ALIASES, key=len, reverse=True)) + r")(?![A-Za-z\u0621-\u064A])"
number = r"(?<![0-9*])" + RULES["number"] + r"(?![0-9]|[.,][0-9])"
MONEY = re.compile("(" + currency + r")\s*(" + number + ")|(" + number + r")\s*(" + currency + ")", re.I | re.ASCII)
CURRENCY = re.compile(currency, re.I | re.ASCII)
BALANCE = re.compile("(?:" + RULES["patterns"]["balance"] + ")" + RULES["patterns"]["balanceJoin"] + "(?:" + currency + r"\s*)?" + number + "(?:\\s*" + currency + ")?", re.I | re.ASCII)
UNMARKED = re.compile("(?:" + RULES["patterns"]["amountAnchor"] + ")(" + number + ")", re.I | re.ASCII)


def non_transaction(reasons):
    return {"contractVersion": "1.0.0", "transactionStatus": "non_transaction", "trackingDecision": "exclude",
            "reasonCodes": sorted(set(reasons)), "amount": None, "currency": None, "currencyResolution": "not_applicable",
            "direction": "not_applicable", "transferRelationship": "not_applicable", "merchantOrCounterparty": None,
            "expenseCategory": None, "categoryStatus": "not_applicable"}


def amounts(text, extracted, parse_number):
    # Mask balances before looking for monetary mentions. Bare identifiers/dates
    # never become amounts: a currency or a financial amount introducer is needed.
    working = BALANCE.sub(lambda match: " " * len(match.group()), text)
    pairs = []
    for match in MONEY.finditer(working):
        value = parse_number(match[2] or match[3])
        unit = ALIASES[(match[1] or match[4]).upper()]
        if value is not None and math.isfinite(value) and value > 0:
            pairs.append((value, unit))
    units = {unit for _, unit in pairs} or {ALIASES[m.group().upper()] for m in CURRENCY.finditer(working)}
    explicit = len(units) == 1
    resolution = "explicit" if explicit else ("default_ambiguous" if units or RX["ambiguousCurrency"].search(working) else "default_missing")
    unit = next(iter(units)) if explicit else "JOD"
    if RX["amountAlternatives"].search(working):
        return None, unit, resolution
    if len(pairs) == 1:
        return pairs[0][0], unit, resolution
    if len(pairs) > 1:
        # Only reuse the existing FX interpretation if every monetary mention is
        # accounted for by its tested primary/original pair and conversion cue.
        original, primary = extracted.get("originalAmount"), extracted.get("amount")
        expected = {(primary, extracted.get("currency")), (original, extracted.get("originalCurrency"))}
        if len(pairs) == 2 and original and RX["fx"].search(text) and set(pairs) == expected:
            return primary, extracted["currency"], "explicit"
        return None, unit, resolution
    candidates = [parse_number(m[1]) for m in UNMARKED.finditer(working)]
    candidates = [value for value in candidates if value is not None and math.isfinite(value) and value > 0]
    return (candidates[0] if len(candidates) == 1 else None), unit, resolution


def exact_party(raw):
    source = EntityText(raw)
    for anchor in RX["partyAnchor"].finditer(source.text):
        match = RX["partyValue"].search(source.text[anchor.end():])
        if not match:
            continue
        candidate = match[1].rstrip(" .;,")
        if not candidate or RX["partyReject"].search(candidate):
            continue
        chosen = source.exact(anchor.end(), anchor.end() + len(candidate))
        if chosen and not RX["alignedLocation"].search(chosen):
            return chosen
    return None


def assess(input_value, extract, parse_number, financial_candidate):
    raw = input_value.get("text") if isinstance(input_value, dict) else None
    if not isinstance(raw, str) or not raw.strip():
        return non_transaction(["empty_or_malformed"])
    text = EntityText(raw).text
    clauses = [part for part in RX["sentence"].split(text) if part.strip()]
    has_completion = any(RX["completion"].search(part) and not RX["completionDenied"].search(part)
                         and not RX["reportedSpeech"].search(part) for part in clauses)
    completed, negative, relevant = [], [], []
    for clause in clauses:
        complete = bool(RX["completion"].search(clause) and not RX["completionDenied"].search(clause)
                        and not RX["reportedSpeech"].search(clause))
        reasons = []
        if RX["chat"].search(clause) or RX["reportedSpeech"].search(clause): reasons.append("personal_conversation")
        if is_authorization_request(clause) or RX["otpRequest"].search(clause) or (RX["otp"].search(clause) and not has_completion): reasons.append("otp_or_authorization")
        if RX["declined"].search(clause): reasons.append("declined_or_failed")
        if RX["deferred"].search(clause) or RX["completionDenied"].search(clause): reasons.append("pending_or_requested")
        if RX["promotion"].search(clause) or (RX["serviceScope"].search(clause) and is_service_notice(clause)): reasons.append("promotion_or_administration")
        if complete: completed.append(clause)
        if reasons: negative.extend(reasons)
        if not reasons: relevant.append(clause)
    conflicts = bool(completed and set(negative) - {"promotion_or_administration"})
    if not completed and negative:
        return non_transaction(negative)
    if not completed and RX["balanceInquiry"].search(text):
        return non_transaction(["balance_only"])
    if not completed and not RX["financial"].search(text):
        if RX["balance"].search(text): return non_transaction(["balance_only"])
        if not financial_candidate(text): return non_transaction(["personal_conversation"])
    status = "completed" if completed and not conflicts else "uncertain"
    semantic = " ".join(relevant)
    incoming, outgoing = bool(RX["incoming"].search(semantic)), bool(RX["outgoing"].search(semantic))
    direction = "uncertain" if incoming == outgoing or RX["directionDenied"].search(text) else ("incoming" if incoming else "outgoing")
    relation = "not_transfer"
    if RX["transfer"].search(semantic):
        relation = "own_accounts" if RX["own"].search(semantic) else ("other_person" if RX["otherPerson"].search(semantic) else "unknown")
    if relation == "own_accounts": direction = "not_applicable"
    extracted = extract(raw, "INCOME" if direction == "incoming" else "EXPENSE")
    amount, unit, resolution = amounts(text, extracted, parse_number)
    if sum(bool(MONEY.search(BALANCE.sub(" ", part))) for part in completed) > 1:
        status, amount = "uncertain", None
    decision = "review"
    if status == "completed":
        if relation == "own_accounts": decision = "exclude"
        elif amount is not None and direction != "uncertain" and relation != "unknown": decision = "include"
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
