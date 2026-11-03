"""Owner-relative direction and relationship policy, independent of completion scoring."""
import json
import re
from pathlib import Path
from .money_candidates import MONEY,currency,number,mask_balances
from .account_movement import has_account_debit,has_account_credit
RULES=json.loads((Path(__file__).resolve().parents[2]/"config/contracts/transaction_evidence.json").read_text(encoding="utf-8"))
RX={k:re.compile(v,re.I|re.ASCII) for k,v in RULES["patterns"].items()}
PAIRED = [re.compile(template.replace("{money}", "(?:" + currency + r"\s*" + number + "|" + number + r"\s*" + currency + ")")
                     .replace("{account}", RULES["pairedMovement"]["account"]), re.I | re.ASCII)
          for template in RULES["pairedMovement"]["templates"]]
PAIRED_REJECT = re.compile(RULES["pairedMovement"]["reject"], re.I | re.ASCII)


def paired_movement(text, amount, negative):
    # Strict templates allow only linked endpoint roles (including Acc. labels),
    # not unrelated sentences or ownership/direction guesses from two masks.
    if negative or PAIRED_REJECT.search(text) or amount is None or len(list(MONEY.finditer(mask_balances(text)))) != 1:
        return False
    working = mask_balances(text)
    for pattern in PAIRED:
        match = pattern.search(working)
        if match and match[1].lower() != match[2].lower():
            remaining = working[:match.start()] + " " * len(match.group()) + working[match.end():]
            if (not any(RX[key].search(remaining) for key in ("financial", "completion", "postedDebit", "postedCredit"))
                    and not has_account_debit(remaining) and not has_account_credit(remaining)):
                return True
    return False


def owner_posting(part, key):
    match = RX[key].search(part)
    return bool(match and RX["postedOwnerSuffix"].search(part[match.end():]))


def transfer_content(semantic):
    if not RX["transferPurpose"].search(semantic):
        return semantic
    # Purpose words describe fees/payroll, not an extra person-to-person event.
    # Explicit ownership/person/CliQ or linked endpoints retain transfer semantics.
    if (any(RX[key].search(semantic) for key in ("own", "otherPerson", "explicitTransfer"))
            or any(pattern.search(semantic) for pattern in PAIRED)):
        return semantic
    if RX["salaryPurpose"].search(semantic) and (not has_account_credit(semantic) or has_account_debit(semantic)):
        return semantic
    return RX["transferPurpose"].sub("", semantic)


def initial_direction(text, relevant):
    semantic = " ".join(relevant)
    incoming = any(RX["incoming"].search(part) or
                   (RX["transfer"].search(part) and RX["transferOwnerRecipient"].search(part)) for part in relevant)
    outgoing = any((RX["outgoing"].search(part) or
                    (RX["transfer"].search(part) and RX["transferOwnerSource"].search(part)))
                   and not RX["returnMovement"].search(part) for part in relevant)
    posted_in = any(owner_posting(part, "postedCredit") or has_account_credit(part) for part in relevant)
    posted_out = any(owner_posting(part, "postedDebit") or has_account_debit(part) for part in relevant)
    if posted_in or posted_out:
        incoming, outgoing = posted_in, posted_out
    direction = "uncertain" if incoming == outgoing or RX["directionDenied"].search(text) else ("incoming" if incoming else "outgoing")
    relation = "not_transfer"
    if RX["transfer"].search(transfer_content(semantic)):
        relation = "own_accounts" if RX["own"].search(semantic) else ("other_person" if RX["otherPerson"].search(semantic) else "unknown")
    if relation == "own_accounts": direction = "not_applicable"
    return direction, relation


def resolve_relationship(text, semantic, amount, negative, direction, relation, ownership_override=None):
    if relation == "not_transfer" and paired_movement(text, amount, negative):
        relation = "own_accounts" if RX["own"].search(semantic) else ("other_person" if RX["otherPerson"].search(semantic) else "unknown")
        direction = "not_applicable" if relation == "own_accounts" else "uncertain"
    # Only the separate, validated ownership wrapper supplies this internal override.
    # Apply after extraction so confirmation cannot supply monetary/event evidence.
    if ownership_override is not None:
        relation = ownership_override["relationship"]
        if ownership_override["uncertainDirection"] or direction == "not_applicable":
            direction = "uncertain"
        if relation == "own_accounts":
            direction = "not_applicable"
    return direction, relation


def recording_decision(status, amount, direction, relation):
    decision = "review"
    if status == "completed":
        if relation == "own_accounts": decision = "exclude"
        elif amount is not None and direction != "uncertain" and relation != "unknown": decision = "include"
    return decision
