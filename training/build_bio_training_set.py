"""Build legacy heuristic BIO drafts from sanitized regression expectations.

The sequence tagger will run only after Layer 1 accepts a transaction, so this
builder keeps the suite's valid transactions and records exact-alignment gaps
instead of creating guessed labels.
"""

import json
import re
import sys
import hashlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from training.corpus_io import FIXTURES, BIO, write_immutable
SOURCE_PATH = FIXTURES / "test_suite_cases.json"
OUTPUT_PATH = BIO

CURRENCY_TERMS = (
    "USD|EUR|GBP|JPY|CAD|AUD|CHF|CNY|INR|TRY|BRL|MXN|ZAR|JOD|SAR|AED|KWD|QAR|"
    "BHD|OMR|EGP|ILS|IQD|LBP|SR|KD|BD|RO|QR|DH|DHS|د\\.أ|دينار|دنانير|دينارا|"
    "ر\\.س|ريال|ريالات|ريالا|د\\.إ|درهم|دراهم|درهما|د\\.ك|ر\\.ق|د\\.ب|ر\\.ع|"
    "ج\\.م|جنيه|جنيها|\\$|€|£|¥|₹|₪"
)
CURRENCY_TOKEN_PATTERN = (
    r"(?<![A-Za-z\u0621-\u064A])(?:" + CURRENCY_TERMS + r")(?![A-Za-z\u0621-\u064A])"
)
TOKEN_RE = re.compile(
    r"(?:[0-9]{2,4}\*[0-9]{2,4}|xxxx[0-9]{3,4}|\*[0-9]{4})"
    r"|(?:" + CURRENCY_TOKEN_PATTERN + r")"
    r"|(?:[0-9]+(?:[,.'][0-9]+)*)"
    r"|(?:[A-Za-z\u0621-\u064A\u064B-\u065F]+)"
    r"|(?:\S)",
    re.IGNORECASE,
)
NUMBER_RE = re.compile(r"[0-9]+(?:[,.'][0-9]+)*")
BALANCE_HINT_RE = re.compile(
    r"(?:available\s+balance|avail\s+bal(?:ance)?|balance|bal\.?|"
    r"الرصيد|رصيدك|رصيد|الرصيد\s+المتاح)",
    re.IGNORECASE,
)
AMOUNT_HINT_RE = re.compile(
    r"(?:amount|purchase|transaction|debited|credited|withdrawal|deposit|cashback|"
    r"refund|payment|billed|بمبلغ|بقيمة|شراء|خصم|سحب|ايداع|إيداع|تحويل|دفع|تسديد)",
    re.IGNORECASE,
)


def parse_number(value):
    cleaned = value.replace("'", "").replace("’", "").replace(" ", "")
    if "," in cleaned and "." in cleaned:
        if cleaned.rfind(".") > cleaned.rfind(","):
            cleaned = cleaned.replace(",", "")
        else:
            cleaned = cleaned.replace(".", "").replace(",", ".")
    elif "," in cleaned:
        parts = cleaned.split(",")
        cleaned = parts[0] + "." + parts[1] if len(parts) == 2 and len(parts[1]) <= 2 else cleaned.replace(",", "")
    return float(cleaned)


def number_spans(text, target):
    matches = []
    for match in NUMBER_RE.finditer(text):
        try:
            if abs(parse_number(match.group()) - float(target)) < 0.000001:
                matches.append((match.start(), match.end()))
        except ValueError:
            continue
    return matches


def literal_span(text, value):
    if not value:
        return None
    parts = [re.escape(part) for part in str(value).split()]
    if not parts:
        return None
    match = re.search(r"\s+".join(parts), text, re.IGNORECASE)
    return (match.start(), match.end()) if match else None


def select_balance_span(text, value):
    candidates = number_spans(text, value)
    if not candidates:
        return None
    nearby = []
    for hint in BALANCE_HINT_RE.finditer(text):
        for candidate in candidates:
            if hint.end() <= candidate[0] <= hint.end() + 64:
                nearby.append((candidate[0] - hint.end(), candidate))
            elif candidate[1] <= hint.start() and hint.start() - candidate[1] <= 64:
                nearby.append((hint.start() - candidate[1], candidate))
    if nearby:
        nearby.sort()
        return nearby[0][1]
    return candidates[-1] if len(candidates) == 1 else None


def select_amount_span(text, value, balance_span):
    candidates = [span for span in number_spans(text, value) if span != balance_span]
    if not candidates:
        return None
    scored = []
    for candidate in candidates:
        window_start = max(0, candidate[0] - 64)
        context = text[window_start:candidate[1] + 8]
        hint_count = len(AMOUNT_HINT_RE.findall(context))
        scored.append((hint_count, -candidate[0], candidate))
    scored.sort(reverse=True)
    if len(scored) == 1 or scored[0][:2] != scored[1][:2]:
        return scored[0][2]
    return None


def select_currency_span(text, amount_span, expected_currency):
    if not amount_span or not expected_currency:
        return None
    normalized_chars = []
    source_positions = []
    for index, char in enumerate(text):
        if '\u064B' <= char <= '\u065F' or char == '\u0670':
            continue
        normalized_chars.append(char)
        source_positions.append(index)
    normalized_text = ''.join(normalized_chars)
    currency_pattern = re.compile(CURRENCY_TOKEN_PATTERN, re.IGNORECASE)
    nearby = []
    for match in currency_pattern.finditer(normalized_text):
        start = source_positions[match.start()]
        end = source_positions[match.end() - 1] + 1
        while end < len(text) and ('\u064B' <= text[end] <= '\u065F' or text[end] == '\u0670'):
            end += 1
        distance = min(abs(start - amount_span[1]), abs(amount_span[0] - end))
        if distance <= 8:
            nearby.append((distance, start, end))
    if not nearby:
        return None
    nearby.sort()
    return nearby[0][1:]


def build_entities(text, expected):
    entities = []
    unresolved = []

    balance = select_balance_span(text, expected.get("balance")) if expected.get("balance") is not None else None
    amount = select_amount_span(text, expected.get("amount"), balance) if expected.get("amount") is not None else None
    merchant = literal_span(text, expected.get("merchantOrParty"))
    account = literal_span(text, expected.get("accountMask"))
    currency = select_currency_span(text, amount, expected.get("currency"))

    fields = (("AMT", amount), ("CURR", currency), ("MERCHANT", merchant), ("ACCT", account), ("BAL", balance))
    for label, span in fields:
        if span is None:
            if expected.get({"AMT": "amount", "CURR": "currency", "MERCHANT": "merchantOrParty", "ACCT": "accountMask", "BAL": "balance"}[label]) is not None:
                unresolved.append(label)
            continue
        entities.append({"label": label, "start": span[0], "end": span[1], "text": text[span[0]:span[1]]})

    entities.sort(key=lambda entity: (entity["start"], -(entity["end"] - entity["start"])))
    non_overlapping = []
    previous_end = -1
    for entity in entities:
        if entity["start"] < previous_end:
            unresolved.append(entity["label"] + "_OVERLAP")
            continue
        non_overlapping.append(entity)
        previous_end = entity["end"]
    return non_overlapping, sorted(set(unresolved))


def tag_tokens(text, entities):
    token_matches = list(TOKEN_RE.finditer(text))
    tokens = [match.group() for match in token_matches]
    tags = ["O"] * len(tokens)

    for entity in entities:
        token_indexes = [
            index for index, match in enumerate(token_matches)
            if match.start() >= entity["start"] and match.end() <= entity["end"]
        ]
        if not token_indexes:
            continue
        for offset, index in enumerate(token_indexes):
            tags[index] = ("B-" if offset == 0 else "I-") + entity["label"]
    return tokens, tags


def build():
    with SOURCE_PATH.open("r", encoding="utf-8") as handle:
        suite = json.load(handle)

    examples = []
    label_counts = {}
    unresolved_cases = []
    for case in suite["testCases"]:
        expected = case["expected"]
        if not expected.get("isValidTransaction"):
            continue
        entities, unresolved = build_entities(case["body"], expected)
        tokens, tags = tag_tokens(case["body"], entities)
        for tag in tags:
            if tag != "O":
                label_counts[tag] = label_counts.get(tag, 0) + 1
        if unresolved:
            unresolved_cases.append({"id": case["id"], "unresolved": unresolved})
        examples.append({
            "id": case["id"],
            "sourceCategory": case["category"],
            "text": case["body"],
            "tokens": tokens,
            "tags": tags,
            "entities": entities,
            "unresolved": unresolved,
        })

    artifact = {
        "metadata": {
            "source": SOURCE_PATH.relative_to(ROOT).as_posix(),
            "sourceSha256": hashlib.sha256(SOURCE_PATH.read_bytes()).hexdigest(),
            "builderSha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            "labelOrigin": "legacy_heuristic_drafts_from_development_regression",
            "humanReviewed": False,
            "independentEvaluationEligible": False,
            "knownLimit": "Preserves legacy alignment heuristics; BIO label repair and independent entity evaluation remain separate tasks",
            "sourceCaseCount": len(suite["testCases"]),
            "includedValidTransactionCount": len(examples),
            "excludedInvalidTransactionCount": len(suite["testCases"]) - len(examples),
            "tagScheme": "BIO",
            "entityLabels": ["AMT", "CURR", "MERCHANT", "ACCT", "BAL"],
            "labelCounts": label_counts,
            "examplesWithUnresolvedGoldFields": len(unresolved_cases),
            "unresolvedCases": unresolved_cases,
        },
        "examples": examples,
    }
    write_immutable(OUTPUT_PATH, json.dumps(artifact, ensure_ascii=False, indent=2) + "\n")
    print(f"Saved {len(examples)} BIO examples to {OUTPUT_PATH}")
    print(f"Heuristic examples with unresolved expected fields: {len(unresolved_cases)}")
    print("Label counts:", json.dumps(label_counts, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    build()
