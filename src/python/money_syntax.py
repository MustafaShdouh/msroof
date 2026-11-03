"""Shared monetary lexical grammar; no candidate selection or event policy."""
import json
from pathlib import Path
import re

RULES = json.loads((Path(__file__).resolve().parents[2]/'config/contracts/transaction_evidence.json').read_text(encoding='utf-8'))
ALIASES = {key.upper(): value for key,value in RULES['currencyAliases'].items()}
currency = r"(?<![A-Za-z\u0621-\u064A])(?:" + '|'.join(re.escape(key) for key in sorted(ALIASES,key=len,reverse=True)) + r")(?![A-Za-z\u0621-\u064A])"
number = r"(?<![0-9*.,'’])" + RULES['number'] + r"(?![0-9]|[.,][0-9])"

# Captures only the unmarked number and its optional ambiguous unit.
BARE_POLICY = RULES['unmarkedAccountAmount']
bare_amount = (BARE_POLICY['prefix'] + '(' + BARE_POLICY['positive'] + RULES['number'] + ')'
               + r'(?:\s+(' + RULES['patterns']['ambiguousCurrency'] + '))?' + BARE_POLICY['tail'])
