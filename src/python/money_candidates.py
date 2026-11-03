"""Source-linked monetary candidates and existing primary-amount policy."""
import math
import re
from .entity_text import EntityText
from .money_syntax import RULES, ALIASES, currency, number, bare_amount
from .account_movement import bare_account_spans
RX = {key: re.compile(value, re.I | re.ASCII) for key, value in RULES["patterns"].items()}
MONEY = re.compile("(" + currency + r")\s*(" + number + ")|(" + number + r")\s*(" + currency + ")", re.I | re.ASCII)
PRIMARY = re.compile(RULES["patterns"]["explicitPrimary"] + "(?:" + MONEY.pattern + ")", re.I | re.ASCII)
RECEIVER = re.compile(RULES["patterns"]["amountReceiverAnchor"] + "(?:" + MONEY.pattern + ")", re.I | re.ASCII)
CURRENCY = re.compile(currency, re.I | re.ASCII)
balance_value = "(?:" + currency + r"\s*)?[+-]?" + number + "(?:\\s*" + currency + ")?"
BALANCE = re.compile("(?:" + RULES["patterns"]["balance"] + ")" + RULES["patterns"]["balanceJoin"] + balance_value, re.I | re.ASCII)
BALANCE_SUFFIX = re.compile(balance_value + RULES["patterns"]["balanceSuffix"], re.I | re.ASCII)
UNMARKED = re.compile("(?:" + RULES["patterns"]["amountAnchor"] + ")(" + number + ")", re.I | re.ASCII)
BARE_PRIMARY = re.compile(RULES['patterns']['explicitPrimary'] + bare_amount, re.I | re.ASCII)
BARE_LIST = re.compile(RULES['unmarkedAccountAmount']['list'], re.I | re.ASCII)
RECEIVER_ID = re.compile(RULES['unmarkedAccountAmount']['receiverIdentifierPrefix'], re.I | re.ASCII)


def bare_primary_spans(text):
    return [dict(start=m.start(1),end=m.end(1),contextStart=m.start(),resolution='default_ambiguous' if m[2] else 'default_missing')
            for m in BARE_PRIMARY.finditer(text)]

def mask_balances(text, on_excluded=None):
    # Prefixes win: in "20 JOD الرصيد 100 JOD", only 100 is a balance.
    def blank(match):
        if on_excluded is not None: on_excluded(match.start(),match.end())
        return " " * len(match.group())
    working = BALANCE.sub(blank, text)
    return BALANCE_SUFFIX.sub(blank, working)


def collect_candidates(source, parse_number):
    """Offsets are Unicode code points in the original source, never masked text."""
    exclusions = []
    def excluded(start,end):
        a,b=source.starts[start],source.ends[end-1]
        exclusions.append(dict(role="balance",start=a,end=b))
    working = mask_balances(source.text,excluded)
    account_spans=[];primary_spans=[]
    for role, pattern in (("date", RX["date"]), ("identifier", RX["identifier"])):
        # Receipt amounts after an account subject are not account identifiers.
        # This protection does not give them explicit-primary selection priority.
        protected=[(m.start(2 if m[2] else 3),m.end(2 if m[2] else 3))
                   for rx in (PRIMARY, RECEIVER) for m in rx.finditer(working)] if role=="identifier" else []
        if role=='identifier':
            account_spans=list(bare_account_spans(working));primary_spans=bare_primary_spans(working)
        bare_protected=account_spans+primary_spans
        def is_protected(match):
            return (any(match.start()<end and match.end()>start for start,end in protected)
                    or any(span['contextStart']<match.start()<=span['start']<match.end() and RECEIVER_ID.fullmatch(working[match.start():span['start']])
                           for span in bare_protected))
        for match in pattern.finditer(working):
            if is_protected(match):continue
            exclusions.append(dict(role=role, start=source.starts[match.start()], end=source.ends[match.end()-1]))
        working = pattern.sub(lambda match: match.group() if is_protected(match) else " " * len(match.group()), working)
    def candidate(match, group, unit, role):
        value = parse_number(match[group])
        if value is None or not math.isfinite(value) or value <= 0: return None
        start, end = match.start(group), match.end(group)
        a,b=source.starts[start],source.ends[end-1]
        return dict(value=value,currency=unit,role=role,start=a,end=b,text=source.source[a:b])
    monetary=[];anchored=[];primary=[]
    for match in MONEY.finditer(working):
        c=candidate(match,2 if match[2] else 3,ALIASES[(match[1] or match[4]).upper()],"currency_amount")
        if c is not None:monetary.append(c)
    for match in UNMARKED.finditer(working):
        c=candidate(match,1,None,"anchored_amount")
        if c is not None:anchored.append(c)
    for match in PRIMARY.finditer(working):
        c=candidate(match,2 if match[2] else 3,ALIASES[(match[1] or match[4]).upper()],"explicit_primary")
        if c is not None:primary.append(c)
    for spans, target, role in ((account_spans,anchored,'account_amount'),
                                 (primary_spans,primary,'explicit_primary')):
        for span in spans:
            start,end=span['start'],span['end']
            if working[start:end] != source.text[start:end]:continue
            value=parse_number(working[start:end])
            if value is None or not math.isfinite(value) or value<=0:continue
            a,b=source.starts[start],source.ends[end-1]
            # The explicit branch of an account template can cover the same number.
            if any(c['start']==a and c['end']==b for c in monetary):continue
            target[:]=[c for c in target if (c['start'],c['end'])!=(a,b)]
            target.append(dict(value=value,currency=None,role=role,start=a,end=b,text=source.source[a:b],currencyResolution=span['resolution']))
    return dict(working=working,monetary=monetary,anchored=anchored,primary=primary,exclusions=exclusions)


def standalone_total(clause):
    clean = clause.strip().rstrip('.!?؟;').strip()
    return bool(RX['amountSummaryPrefix'].search(clean) and (PRIMARY.fullmatch(clean) or BARE_PRIMARY.fullmatch(clean)))


def movement_values(clause, parse_number):
    """Canonical posted-value evidence inside one fragment, not new event truth."""
    if standalone_total(clause):
        return set()
    evidence = collect_candidates(EntityText(clause), parse_number)
    posted = evidence['primary'] + [c for c in evidence['anchored'] if c['role'] == 'account_amount']
    candidates = posted or evidence['monetary'] + evidence['anchored']
    return {c['value'] for c in candidates}


def has_movement_amount(clause, parse_number):
    """A standalone inclusive total describes a movement, not another movement."""
    if standalone_total(clause):
        return False
    # Keep existing explicit-money safeguards; bare amounts use the same ID/date
    # masks and guarded account/primary roles as canonical amount selection.
    if MONEY.search(mask_balances(clause)):
        return True
    evidence = collect_candidates(EntityText(clause), parse_number)
    return bool(evidence['primary'] or any(c['role'] == 'account_amount' for c in evidence['anchored']))


def amounts(text, extracted, parse_number, source=None, allow_unmarked=True):
    # Mask balances before looking for monetary mentions. Bare identifiers/dates
    # never become amounts: a currency or a financial amount introducer is needed.
    evidence=collect_candidates(source if source is not None else EntityText(text),parse_number)
    working=evidence["working"]
    pairs=[(c["value"],c["currency"]) for c in evidence["monetary"]]
    units = {unit for _, unit in pairs} or {ALIASES[m.group().upper()] for m in CURRENCY.finditer(working)}
    explicit = len(units) == 1
    resolution = "explicit" if explicit else ("default_ambiguous" if units or RX["ambiguousCurrency"].search(working) else "default_missing")
    unit = next(iter(units)) if explicit else "JOD"
    bare=[c for c in evidence['anchored'] if c['role']=='account_amount']+[c for c in evidence['primary'] if c['currency'] is None]
    if bare:
        # Currency belongs to the selected source mention, never a fee or balance.
        def resolved(c):
            return c['value'], c['currency'] or 'JOD', ('explicit' if c['currency'] else c['currencyResolution'])
        candidates={(c['start'],c['end']):c for kind in ('anchored','monetary','primary') for c in evidence[kind]}
        if not allow_unmarked or RX['amountAlternatives'].search(working) or BARE_LIST.search(working):
            return None,'JOD','default_ambiguous' if any(c['currencyResolution']=='default_ambiguous' for c in bare) else 'default_missing'
        if len(evidence['primary'])==1:return resolved(evidence['primary'][0])
        if not evidence['primary'] and len(candidates)==1:return resolved(next(iter(candidates.values())))
        return None,'JOD','default_ambiguous' if any(c['currencyResolution']=='default_ambiguous' for c in bare) else 'default_missing'
    if RX["amountAlternatives"].search(working):
        return None, unit, resolution
    if len(pairs) == 1:
        return pairs[0][0], unit, resolution
    if len(pairs) > 1:
        if len(evidence["primary"]) == 1:
            chosen=evidence["primary"][0]
            if (chosen["value"],chosen["currency"]) in pairs:
                return chosen["value"],chosen["currency"],"explicit"
        # Only reuse the existing FX interpretation if every monetary mention is
        # accounted for by its tested primary/original pair and conversion cue.
        original, primary = extracted.get("originalAmount"), extracted.get("amount")
        expected = {(primary, extracted.get("currency")), (original, extracted.get("originalCurrency"))}
        if len(pairs) == 2 and original and RX["fx"].search(text) and set(pairs) == expected:
            return primary, extracted["currency"], "explicit"
        return None, unit, resolution
    candidates = [c["value"] for c in evidence["anchored"]]
    return (candidates[0] if len(candidates) == 1 else None), unit, resolution


