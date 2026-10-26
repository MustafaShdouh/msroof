"""Recognize pre-completion code requests using the shared bilingual grammar."""
import json
import re
from pathlib import Path

from .preprocessing import normalize_financial_numbers

RULES = json.loads((Path(__file__).resolve().parents[2] / "config/contracts/authorization_request.json").read_text(encoding="utf-8"))
AUTHORIZATION_REQUEST_REASON = RULES["reason"]
PATTERNS = [
    RULES["englishCode"] + RULES["codeValue"] + RULES["englishConnector"] + RULES["englishGoal"],
    r"\bto\s+" + RULES["englishGoal"] + RULES["englishReverseConnector"] + RULES["englishCode"],
    RULES["arabicCode"] + RULES["codeValue"] + RULES["arabicGoal"],
    RULES["arabicGoal"] + RULES["arabicReverseConnector"] + RULES["arabicCode"],
]
REQUESTS = tuple(re.compile(pattern, re.I | re.ASCII) for pattern in PATTERNS)
DIACRITICS = re.compile(r"[\u064B-\u065F\u0670]")


def is_authorization_request(body):
    text = DIACRITICS.sub("", normalize_financial_numbers(body))
    return any(pattern.search(text) for pattern in REQUESTS)
