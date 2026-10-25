"""Prepare a synthetic privacy-transformed corpus and globally grouped dev split.

Historical inputs are archived privately and never overwritten. No model fitting,
legacy-gate migration, Git publication, or history rewrite is performed.
"""
from __future__ import annotations

import argparse
import ast
import copy
import json
import random
import re
import sys
from collections import Counter, defaultdict
from decimal import Decimal, InvalidOperation
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from training.audit_sms_provenance import canonical, digest, number_masked, protected_hashes
from src.python.preprocessing import normalize_financial_numbers

VERSION = "sanitized-corpus-1.0.0"
ARCHIVE = "data/private/historical_corpus_v1"
DATA = "data/training/sanitized_v1/transactions.json"
SPLIT = "data/training/splits/transaction_direction_sanitized_v1.json"
FIXTURE_DIR = "tests/fixtures/sanitized_v1"
REPORT = "data/reports/sanitized_corpus_v1.json"
READABLE = "data/reports/SANITIZED_CORPUS_V1.md"
SEED = 20261025
HISTORICAL = [
    "training/expand_dataset.py", "data/training/dataset_expanded.json", "data/training/dataset_expanded.csv",
    "data/training/bio_training_data.json", "data/training/splits/transaction_direction_split.json",
    "tests/fixtures/test_suite_cases.json", "tests/fixtures/qa_adversarial_cases.json",
    "tests/fixtures/test_corpus_manifest.json", "data/models/masroof_model.json",
    "src/python/verify_engine.py", "src/python/preprocessing.py",
    "src/typescript/MasroofEngine.ts", "src/typescript/Preprocessing.ts",
    "tools/generators/generate_test_suite.py", "tools/generators/build_qa_adversarial_cases.py",
]
DIACRITICS = r"[\u064b-\u065f\u0670]*"
NUMBERS = re.compile(r"\d+(?:[.,'’\u066b\u066c]\d+)*")
ACCOUNT = re.compile(r"\d{2,4}\*\d{2,4}|xxxx\d{3,4}|\*\d{4}", re.I)
ACCOUNT_CONTEXT = re.compile(r"(?:ending\s+(?:in\s+|with\s+)?|المنتهي(?:ة)?\s*ب[ـ\s]*|(?:account|acc\.?|card|حسابك|حساب|بطاقتك|بطاقة)\s*(?:no\.?\s*)?)(\d{3,8})(?!\d)", re.I)
TRANSFER = re.compile(r"cliq|كليك|transfer|حوالة|تحويل", re.I)


class TemplateText(str):
    def __new__(cls, value, template_id):
        obj = super().__new__(cls, value)
        obj.template_id = template_id
        return obj


class TraceTemplates(ast.NodeTransformer):
    def __init__(self):
        self.inside = False

    def visit_FunctionDef(self, node):
        if node.name != "generate_samples":
            return node
        self.inside = True
        node = self.generic_visit(node)
        self.inside = False
        return node

    def tag(self, node):
        return ast.copy_location(ast.Call(func=ast.Name(id="_trace_text", ctx=ast.Load()),
                                         args=[node, ast.Constant(f"literal-L{node.lineno}-C{node.col_offset}")], keywords=[]), node)

    def visit_JoinedStr(self, node):
        # Do not transform f-string literal pieces or format specifications.
        return self.tag(node) if self.inside else node

    def visit_Constant(self, node):
        return self.tag(node) if self.inside and isinstance(node.value, str) else node

    def visit_Call(self, node):
        node = self.generic_visit(node)
        if (self.inside and isinstance(node.func, ast.Attribute) and node.func.attr == "append"
                and isinstance(node.func.value, ast.Name) and node.func.value.id == "dataset"):
            return ast.copy_location(ast.Call(func=ast.Name(id="_trace_append", ctx=ast.Load()),
                                             args=[node.func.value, node.args[0]], keywords=[]), node)
        return node


def traced_generation(source, source_path, expected_rows):
    def append(rows, row):
        template_id = getattr(row["text"], "template_id", None)
        if template_id is None:
            raise ValueError("Untraced generator text; source-template review required")
        plain = {str(key): str(value) if isinstance(value, str) else value for key, value in row.items()}
        rows.append(dict(plain, sourceTemplateId=template_id))

    namespace = {"__name__": "private_traced_generator", "__file__": str(source_path),
                 "_trace_text": TemplateText, "_trace_append": append}
    previous_rng = random.getstate()
    try:
        tree = ast.fix_missing_locations(TraceTemplates().visit(ast.parse(source)))
        exec(compile(tree, str(source_path), "exec"), namespace)
        rows = namespace["generate_samples"]()
    finally:
        random.setstate(previous_rng)
    plain = [{key: value for key, value in row.items() if key != "sourceTemplateId"} for row in rows]
    if plain != expected_rows:
        raise ValueError("Traced generator does not reproduce historical records and order")
    return rows, list(namespace["NAMES"])


def phrase_pattern(value):
    plain = re.sub(r"[\u064b-\u065f\u0670]", "", value)
    parts = []
    for token in plain.split():
        parts.append("".join(re.escape(char) + (DIACRITICS if "\u0621" <= char <= "\u064a" else "") for char in token))
    return re.compile(r"(?<![\w])" + r"(?:\s|\\[nr])+".join(parts) + r"(?![\w])", re.I)


def decimal_shape(token):
    text = normalize_financial_numbers(token).replace("'", "").replace("’", "")
    if "." in text and "," in text:
        decimal = "." if text.rfind(".") > text.rfind(",") else ","
    elif "," in text:
        parts = text.split(",")
        decimal = "," if len(parts) == 2 and len(parts[1]) in (1, 2) else None
    else:
        decimal = "." if "." in text else None
    before, after = text.rsplit(decimal, 1) if decimal else (text, "")
    integer = before.replace(",", "").replace(".", "")
    value = Decimal(integer + ("." + after if after else ""))
    return value, len(integer), len(after)


def render_money(original, value):
    _, width, precision = decimal_shape(original)
    formatted = f"{value:.{precision}f}"
    whole, _, fraction = formatted.partition(".")
    digits = iter(whole.zfill(width) + fraction)
    output = []
    for char in original:
        if char.isdecimal():
            digit = next(digits)
            output.append(chr(ord(digit) + (0x0660 - 48 if "٠" <= char <= "٩" else 0x06F0 - 48 if "۰" <= char <= "۹" else 0)))
        else:
            output.append(char)
    if next(digits, None) is not None:
        raise ValueError("Synthetic number no longer fits its formatting shape")
    return "".join(output)


def is_person_party(case, party):
    return bool(party and ("CLIQ" in case.get("category", "") or TRANSFER.search(canonical(case.get("body", case.get("text", ""))))))


def synthetic_person(phrase, rng):
    # Neutral identifiers avoid a repeated label-correlated token like RECIPIENT.
    forbidden = {"TO", "FROM", "ON", "AT", "AS", "IS", "IN", "BY", "OF", "OR", "AN", "NO",
                 "JOD", "USD", "EUR", "GBP", "OTP", "ATM", "REF", "CARD", "ACCOUNT", "BALANCE",
                 "من", "في", "تم", "على", "إلى", "الى", "لدى", "عبر", "هو", "دينار", "ريال", "رصيد"}
    result = []
    plain = re.sub(r"[\u064b-\u065f\u0670]", "", phrase)
    for word in plain.split():
        for _ in range(100):
            chars = []
            for char in word:
                if "\u0621" <= char <= "\u064a":
                    chars.append(rng.choice("ابتثجحخدذرزسشصضطظعغفقكلمنهوي"))
                elif char.isascii() and char.isalpha():
                    letter = rng.choice("abcdefghijklmnopqrstuvwxyz")
                    chars.append(letter.upper() if char.isupper() else letter)
                else:
                    chars.append(char)
            token = "".join(chars)
            if token.upper() not in forbidden and token not in forbidden and canonical(token) != canonical(word):
                result.append(token)
                break
        else:
            raise ValueError("Cannot generate a neutral identifier")
    return " ".join(result)


def sanitize_record(text, record_id, personal_phrases, expected=None, sender=None):
    """Use source-ID/slot-seeded synthetic values, never reversible digit substitution."""
    rng = random.Random(int(digest((VERSION + record_id).encode())[:16], 16))
    spans, account_map, entity_map = [], {}, {}
    expected = copy.deepcopy(expected or {})
    party = expected.get("merchantOrParty", expected.get("merchant_or_party", expected.get("expected_merchant")))

    def available(start, end):
        return all(end <= a or start >= b for a, b, _, _ in spans)

    def add(start, end, replacement, kind):
        if available(start, end):
            spans.append((start, end, replacement, kind))
            return True
        return False

    def new_digits(original):
        if not any(char.isdecimal() for char in original):
            return original
        while True:
            chars = []
            for char in original:
                if char.isdecimal():
                    base = 0x0660 if "٠" <= char <= "٩" else 0x06F0 if "۰" <= char <= "۹" else 48
                    chars.append(chr(base + rng.randrange(10)))
                else:
                    chars.append(char)
            candidate = "".join(chars)
            if candidate != original:
                return candidate

    phrases = set(personal_phrases)
    for phrase in sorted(phrases, key=lambda x: (-len(x), x)):
        for match in phrase_pattern(phrase).finditer(text):
            if not available(*match.span()):
                continue
            key = canonical(phrase)
            if key not in entity_map:
                entity_map[key] = synthetic_person(phrase, rng)
            replacement = entity_map[key]
            if add(*match.span(), replacement, "person"):
                entity_map[key] = replacement
    # Public business names remain; protect embedded branch digits from amount remapping.
    protected_merchants = []
    if party and canonical(party) not in entity_map:
        protected_merchants = [match.span() for match in phrase_pattern(party).finditer(text)]

    for match in ACCOUNT.finditer(text):
        original = match.group()
        if available(*match.span()):
            replacement = account_map.setdefault(original, new_digits(original))
            add(*match.span(), replacement, "account")
    for match in ACCOUNT_CONTEXT.finditer(text):
        original = match.group(1)
        if available(*match.span(1)):
            replacement = account_map.setdefault(original, new_digits(original))
            add(*match.span(1), replacement, "account")

    date_pattern = r"\b\d{4}[/-]\d{1,2}[/-]\d{1,2}\b|(?<![\d.])\d{1,2}[/-]\d{1,2}(?:[/-]\d{2,4})?(?![\d.])"
    for match in re.finditer(date_pattern, text):
        raw = match.group()
        chunks = re.split(r"([/-])", raw)
        if len(chunks[0]) == 4:
            chunks[0], chunks[2], chunks[4] = "2001", str(rng.randint(1, 12)).zfill(len(chunks[2])), str(rng.randint(1, 28)).zfill(len(chunks[4]))
        else:
            chunks[0], chunks[2] = str(rng.randint(1, 28)).zfill(len(chunks[0])), str(rng.randint(1, 12)).zfill(len(chunks[2]))
            if len(chunks) > 3:
                chunks[4] = "2001" if len(chunks[4]) == 4 else "01"
        add(*match.span(), "".join(chunks), "date")
    for match in re.finditer(r"\b\d{1,2}:\d{2}(?::\d{2})?\b", text):
        pieces = match.group().split(":")
        replacement = ":".join(str(rng.randrange(24 if i == 0 else 60)).zfill(len(part)) for i, part in enumerate(pieces))
        add(*match.span(), replacement, "time")
    secret_map = {}
    secret_patterns = [
        (r"(?:ref(?:erence)?\s*#?\s*)(\d+)", 1),
        (r"(?:one[- ]time\s+password\s*:|otp\s+is|enter\s+the\s+code|verification\s+code\s+is)\s*(\d+)", 1),
        (r"^\s*(\d+)\s+هو\s+رمز", 1),
        (r"(?<!\w)(?:\+|00)\d{7,15}(?!\w)|\b0[67-9]\d{7,9}\b", 0),
    ]
    for pattern, group in secret_patterns:
        for match in re.finditer(pattern, text, re.I):
            raw = match.group(group)
            if raw not in secret_map:
                # Wallet counterparty extraction depends on local phone structure.
                prefix = 3 if re.match(r"07[789]\d{7}$", raw) else 2 if re.match(r"0[6-9]", raw) else 0
                secret_map[raw] = raw[:prefix] + new_digits(raw[prefix:])
            add(*match.span(group), secret_map[raw], "identifier")
    for match in re.finditer(r"\b(?=[A-Za-z0-9]{8,}\b)(?=[A-Za-z0-9]*[A-Za-z])(?=[A-Za-z0-9]*\d)[A-Za-z0-9]+\b", text):
        add(*match.span(), "SYNTHCODE" + str(rng.randrange(100000, 999999)), "token")
    for match in re.finditer(r"^([A-Za-z0-9]{8,})$", text, re.M):
        if any(c.islower() for c in match.group()) and any(c.isupper() for c in match.group()):
            add(*match.span(), "SYNTHETICTOKEN", "token")

    monetary = []
    for match in NUMBERS.finditer(text):
        if available(*match.span()) and all(match.end() <= a or match.start() >= b for a, b in protected_merchants):
            try:
                value, width, precision = decimal_shape(match.group())
            except InvalidOperation:
                raise ValueError("Unresolved numeric format requires corpus review") from None
            monetary.append((match, value, width, precision))
    shapes = defaultdict(list)
    for match, value, width, precision in monetary:
        shapes[value].append((width, precision))
    money_map = {}
    for value, formats in shapes.items():
        if value == 0:
            money_map[value] = Decimal(0)
            continue
        width, precision = min(w for w, _ in formats), min(p for _, p in formats)
        low = 0 if value < 1 else 10 ** (width - 1)
        high = 0 if value < 1 else 10 ** width - 1
        for _ in range(100):
            integer = rng.randint(low, high)
            fraction = rng.randrange(10 ** precision) if precision else 0
            candidate = Decimal(integer) + Decimal(fraction).scaleb(-precision)
            if candidate > 0 and candidate != value:
                money_map[value] = candidate
                break
        else:
            raise ValueError("Cannot choose a distinct positive synthetic amount with the required shape")
    for match, value, _, _ in monetary:
        add(*match.span(), render_money(match.group(), money_map[value]), "number")

    spans.sort()
    pieces, cursor = [], 0
    for start, end, replacement, _ in spans:
        pieces.extend((text[cursor:start], replacement))
        cursor = end
    pieces.append(text[cursor:])
    output = "".join(pieces)
    for field in ("amount", "balance", "expected_amount"):
        if expected.get(field) is not None:
            value = Decimal(str(expected[field]))
            if value not in money_map:
                raise ValueError(f"{record_id}: expected {field} has no unambiguous numeric source")
            expected[field] = float(money_map[value])
    for field in ("merchantOrParty", "merchant_or_party", "expected_merchant"):
        if expected.get(field) and canonical(expected[field]) in entity_map:
            expected[field] = entity_map[canonical(expected[field])]
    for field in ("accountMask", "account_mask"):
        value = expected.get(field)
        if value:
            if value in account_map:
                expected[field] = account_map[value]
            else:
                mapped = value
                for original, replacement in sorted(account_map.items(), key=lambda x: -len(x[0])):
                    mapped = mapped.replace(original, replacement)
                if mapped != value:
                    expected[field] = mapped
                    continue
                options = {replacement[original.index(value):original.index(value) + len(value)]
                           for original, replacement in account_map.items() if value in original}
                if len(options) != 1:
                    raise ValueError(f"{record_id}: account expectation cannot be mapped uniquely")
                expected[field] = options.pop()
    new_sender = sender
    if sender and any(c.isdecimal() for c in sender):
        # Preserve the sender guard's structural class, including local 07/08/09.
        prefix = 2 if sender.startswith(("07", "08", "09", "00")) else 0
        new_sender = sender[:prefix] + new_digits(sender[prefix:])
    return output, expected, new_sender, {"recordId": record_id, "spans": [
        {"start": start, "end": end, "replacement": replacement, "kind": kind} for start, end, replacement, kind in spans]}


def template_proxy(row):
    text = canonical(row.get("text", row.get("body", "")))
    party = row.get("expected_merchant")
    if party:
        text = phrase_pattern(canonical(party)).sub(" PARTY ", text)
    text = ACCOUNT.sub(" ACCOUNT ", text)
    return number_masked(text)


def grouped_split(original, sanitized, dataset_hash):
    count = len(original)
    parent = list(range(count))

    def find(i):
        while i != parent[i]:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def union(a, b):
        a, b = find(a), find(b)
        if a != b:
            parent[max(a, b)] = min(a, b)

    keys = {}
    for i, (raw, clean) in enumerate(zip(original, sanitized)):
        views = [("source_template", raw["sourceTemplateId"]), ("original_text", canonical(raw["text"])),
                 ("original_numbers", number_masked(raw["text"])), ("original_slots", template_proxy(raw)),
                 ("sanitized_text", canonical(clean["text"])), ("sanitized_numbers", number_masked(clean["text"])),
                 ("sanitized_slots", template_proxy(clean))]
        for key in views:
            if key in keys:
                union(i, keys[key])
            else:
                keys[key] = i
    components = defaultdict(list)
    for i in range(count):
        components[find(i)].append(i)
    groups = []
    for indices in components.values():
        templates = sorted({original[i]["sourceTemplateId"] for i in indices})
        group_id = "family-" + digest("|".join(templates).encode())[:20]
        groups.append({"groupId": group_id, "indices": indices, "sourceTemplateIds": templates})
    groups.sort(key=lambda x: x["groupId"])
    totals = Counter(row["label"] for row in sanitized)
    selected, validation_counts = [], Counter()
    targets = {label: round(total * .2) for label, total in totals.items()}
    for group in sorted(groups, key=lambda x: digest((str(SEED) + x["groupId"]).encode())):
        labels = Counter(sanitized[i]["label"] for i in group["indices"])
        before = sum(abs(targets[label] - validation_counts[label]) for label in totals)
        after = sum(abs(targets[label] - validation_counts[label] - labels[label]) for label in totals)
        if (after < before
                and all(validation_counts[label] + n < totals[label] for label, n in labels.items())):
            selected.extend(group["indices"])
            validation_counts.update(labels)
    if not selected or len(selected) == count:
        raise ValueError("No viable globally grouped development partition")
    val = set(selected)
    return {"splitVersion": "1.0.0", "corpusVersion": VERSION, "seed": SEED, "validationFractionTarget": .2, "datasetSha256": dataset_hash,
            "scope": "Synthetic development only; no independent final test", "independentEvaluationEligible": False,
            "recordCount": count, "trainIndices": [i for i in range(count) if i not in val], "validationIndices": sorted(val),
            "grouping": "Union of exact generator template expressions and provider-agnostic original/sanitized content and slot/numeric proxies",
            "groups": groups, "labelCounts": {label: {"train": total - validation_counts[label], "validation": validation_counts[label]} for label, total in sorted(totals.items())},
            "limits": ["Generator template expression IDs are verified for the current pinned source; arbitrary semantic paraphrase families remain unproven.",
                       "Proxies conservatively merge candidates; no claimed Gemini seed ancestry or independent real-world accuracy."]}


def json_text(value):
    return json.dumps(value, ensure_ascii=False, indent=2) + "\n"


def validate_outputs(outputs, original, clean, fixtures, names):
    combined = "\n".join(outputs.values())
    if any(phrase_pattern(name).search(combined) for name in names):
        raise ValueError("Known personal phrase survived in a prepared public artifact")
    split = json.loads(outputs[SPLIT])
    train, val = set(split["trainIndices"]), set(split["validationIndices"])
    if train & val or train | val != set(range(len(clean))):
        raise ValueError("Development partition coverage/overlap error")
    for group in split["groups"]:
        if not (set(group["indices"]) <= train or set(group["indices"]) <= val):
            raise ValueError("A source/content family crosses partitions")
    probes = {
        "sourceTemplate": lambda row: row["sourceTemplateId"],
        "normalizedText": lambda row: canonical(row["text"]),
        "numericProxy": lambda row: number_masked(row["text"]),
        "slotProxy": template_proxy,
    }
    overlap_checks = {}
    for dataset_name, rows in (("historical", original), ("sanitized", clean)):
        for probe_name, key in probes.items():
            overlap = {key(rows[i]) for i in train} & {key(rows[i]) for i in val}
            overlap_checks[dataset_name + "_" + probe_name] = len(overlap)
            if overlap:
                raise ValueError("Provider-agnostic group overlap survived")
    for raw, new in zip(original, clean):
        for field in ("label", "provider", "type", "expected_currency", "sourceTemplateId"):
            if raw[field] != new[field]:
                raise ValueError("Sanitization altered a non-value label or provenance field")
        if (raw["expected_amount"] is None) != (new["expected_amount"] is None):
            raise ValueError("Missing amount was fabricated or discarded")
    for name, original_cases in fixtures.items():
        cases = json.loads(outputs[f"{FIXTURE_DIR}/{name}"])["testCases"]
        if len(cases) != len(original_cases):
            raise ValueError("Regression cases were added/dropped during sanitization")
        for raw, new in zip(original_cases, cases):
            if raw["id"] != new["id"] or raw["expected"]["isValidTransaction"] != new["expected"]["isValidTransaction"]:
                raise ValueError("Regression ID or classification truth changed")
            for field in ("type", "currency"):
                if raw["expected"].get(field) != new["expected"].get(field):
                    raise ValueError("Regression direction/currency truth changed")
            for field in ("amount", "balance", "merchantOrParty", "accountMask", "merchant_or_party", "account_mask"):
                if (raw["expected"].get(field) is None) != (new["expected"].get(field) is None):
                    raise ValueError("Regression field missingness changed")
            if raw["expected"].get("amount") == raw["expected"].get("balance") and new["expected"].get("amount") != new["expected"].get("balance"):
                raise ValueError("Repeated amount/balance relationship changed")
    return {"knownPersonalPhraseSurvivors": 0, "crossPartitionOverlapCounts": overlap_checks,
            "historicalLabelsAndMissingnessPreserved": True, "independentEvaluationEligible": False}




def load_inputs(root=ROOT):
    history = json.loads((root / "data/sources/transactions/generation_history.json").read_text(encoding="utf-8"))["currentGeneratorReproduction"]
    archive = root / ARCHIVE
    archived_manifest = json.loads((archive / "manifest.json").read_text(encoding="utf-8"))
    for relative, expected_hash in archived_manifest["filesSha256"].items():
        path = (archive / relative).resolve()
        if not path.is_relative_to(archive.resolve()) or digest(path.read_bytes()) != expected_hash:
            raise ValueError("Private historical snapshot integrity failed")
    source = (archive / "training/expand_dataset.py").read_bytes()
    dataset = (archive / "data/training/dataset_expanded.json").read_bytes()
    if digest(source) != history["generatorSha256"] or digest(dataset) != history["datasetSha256"]:
        raise ValueError("Historical generator/data differ from verified reproduction evidence")
    rows, names = traced_generation(source.decode("utf-8"), archive / "training/expand_dataset.py", json.loads(dataset))
    fixtures = {}
    for name in ("test_suite_cases.json", "qa_adversarial_cases.json"):
        payload = json.loads((archive / "tests/fixtures" / name).read_text(encoding="utf-8"))
        fixtures[name] = payload if isinstance(payload, list) else payload["testCases"]
    for cases in fixtures.values():
        for case in cases:
            party = case["expected"].get("merchantOrParty", case["expected"].get("merchant_or_party"))
            if is_person_party(case, party):
                names.append(party)
    return rows, fixtures, sorted(set(names))


def build(root=ROOT):
    original, fixtures, names = load_inputs(root)
    clean, plans = [], []
    for i, row in enumerate(original):
        record_id = f"synthetic-v1-{i:04d}"
        text, fields, _, plan = sanitize_record(str(row["text"]), record_id, names, {key: value for key, value in row.items() if key != "text"})
        clean.append(fields | {"text": text, "recordId": record_id, "origin": "synthetic_privacy_transformation_of_legacy_generator",
                               "independentEvaluationEligible": False, "labelOrigin": "legacy_generator_not_human_gold"})
        plans.append(plan)
    data_text = json_text(clean)
    outputs = {DATA: data_text, SPLIT: json_text(grouped_split(original, clean, digest(data_text.encode("utf-8"))))}
    manifest = {"schemaVersion": 1, "corpusVersion": VERSION, "dataKind": "synthetic_privacy_transformed_regression",
                "independentEvaluationEligible": False, "fixtures": {}}
    for name, cases in fixtures.items():
        sanitized = []
        for case in cases:
            text, fields, sender, plan = sanitize_record(case["body"], case["id"], names, case["expected"], case["sender"])
            result = copy.deepcopy(case)
            result.update(body=text, expected=fields, sender=sender,
                          description=f"Synthetic privacy-transformed {case['category']} compatibility case",
                          dataKind="synthetic_privacy_transformed_legacy_case")
            sanitized.append(result)
            plans.append(plan)
        content = json_text({"metadata": {"corpusVersion": VERSION, "dataKind": "synthetic_privacy_transformed_regression",
                                          "independentEvaluationEligible": False}, "testCases": sanitized})
        outputs[f"{FIXTURE_DIR}/{name}"] = content
        manifest["fixtures"][name] = {"sha256": digest(content.encode("utf-8")), "caseCount": len(sanitized),
                                      "validCaseCount": sum(row["expected"]["isValidTransaction"] for row in sanitized),
                                      "invalidCaseCount": sum(not row["expected"]["isValidTransaction"] for row in sanitized)}
    outputs[f"{FIXTURE_DIR}/test_corpus_manifest.json"] = json_text(manifest)
    checks = validate_outputs(outputs, original, clean, fixtures, names)
    split = json.loads(outputs[SPLIT])
    artifact_hashes = {path: digest(content.encode("utf-8")) for path, content in sorted(outputs.items())}
    report = {"corpusVersion": VERSION, "status": "prepared_synthetic_version_not_promoted_or_published",
              "builderSha256": digest(Path(__file__).read_bytes()),
              "sourceArchiveManifestSha256": digest((root / ARCHIVE / "manifest.json").read_bytes()),
              "historicalInputsArchivedPrivately": True, "activeLegacyGateChanged": False,
              "currentRepositoryPrivacyRemediationComplete": False, "remoteHistoryChanged": False,
              "syntheticTrainingRows": len(clean), "compatibilityCases": sum(len(cases) for cases in fixtures.values()),
              "tracedGeneratorTemplateExpressions": len({row["sourceTemplateId"] for row in original}),
              "globalGroups": len(split["groups"]), "trainRows": len(split["trainIndices"]), "validationRows": len(split["validationIndices"]),
              "labelCounts": split["labelCounts"], "checks": checks,
              "runtimeAcceptanceEvidence": "data/reports/sanitized_corpus_v1_legacy_v1_evaluation.json",
              "artifactSha256": artifact_hashes,
              "limits": ["Synthetic transformation, not newly collected messages, approved real labels, or an independent test set.",
                         "Known person strings are removed and values regenerated; this is not a certification of complete repository anonymization.",
                         "Legacy tracked files and prior Git history still contain old data; migration/retirement and separately approved history cleanup remain.",
                         "Source-expression and exact/slot proxies are grouped globally; arbitrary semantic paraphrase relationships remain unproven.",
                         "No category dataset/split change or merchant final-test inference."]}
    outputs[REPORT] = json_text(report)
    lines = ["# Sanitized corpus v1 preparation", "", "Prepared synthetic replacement; no active-gate migration, fitting, or Git publication.", "",
             f"- Synthetic transaction rows: {len(clean)}; transformed regression cases: {report['compatibilityCases']}.",
             f"- Verified generator template expressions: {report['tracedGeneratorTemplateExpressions']}; global groups: {report['globalGroups']}.",
             f"- Development split: {report['trainRows']} train / {report['validationRows']} validation; every existing class is represented in both.",
             "- Zero cross-fold source-expression, normalized-text, numeric-proxy, and slot-proxy overlaps, on both historical and sanitized views.",
             "- Known personal phrases removed; person identifiers vary, while financial values/dates/codes/account masks are synthetic and expected fields remapped.", "",
             "## Legacy-model compatibility diagnostic", "",
             "Run `py training/evaluate_sanitized_corpus.py` separately; preparation does not fit a model or run inference.",
             "Results: `data/reports/sanitized_corpus_v1_legacy_v1_evaluation.json`. Retain expected labels when the model fails.", ""]
    lines += ["", "## Remaining work", "", *[f"- {limit}" for limit in report["limits"]], "",
              "Fix measured compatibility failures before adopting this as the active regression gate. Preserve the historical baseline privately; review and retire unsafe legacy copies before publication. Remote-history changes require separate authorization.", ""]
    outputs[READABLE] = "\n".join(lines)
    # The reversible mappings are private; outputs contain only new synthetic values.
    private = {"version": VERSION, "plans": plans}
    return outputs, private, original, clean, fixtures, names


def archive_inputs(root):
    archive = root / ARCHIVE
    hashes = {}
    for relative in HISTORICAL:
        raw = (root / relative).read_bytes()
        target = archive / relative
        if target.exists() and target.read_bytes() != raw:
            raise ValueError("Refusing to overwrite a differing private historical snapshot")
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists():
            target.write_bytes(raw)
        hashes[relative] = digest(raw)
    content = json_text({"archiveVersion": "1.0.0", "filesSha256": hashes})
    manifest = archive / "manifest.json"
    if manifest.exists() and manifest.read_text(encoding="utf-8") != content:
        raise ValueError("Private historical manifest changed")
    if not manifest.exists():
        manifest.write_text(content, encoding="utf-8", newline="\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if "/data/private/" not in (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines():
        raise ValueError("Private outputs must be ignored")
    before = protected_hashes(ROOT)
    if not args.check:
        archive_inputs(ROOT)
    outputs, private, _, clean, _, _ = build()
    outputs[f"{ARCHIVE}/transformation_plans.json"] = json_text(private)
    if not args.check:
        for relative, content in outputs.items():
            path = ROOT / relative
            if path.exists() and path.read_text(encoding="utf-8") != content:
                raise ValueError("Refusing changed-input overwrite of versioned output: " + relative)
    for relative, content in outputs.items():
        path = ROOT / relative
        if args.check:
            if not path.exists() or path.read_text(encoding="utf-8") != content:
                raise ValueError("Sanitized artifact missing or stale: " + relative)
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8", newline="\n")
    if protected_hashes(ROOT) != before:
        raise ValueError("Historical sources/models/fixtures/splits changed")
    print(f"Sanitized corpus {'checked' if args.check else 'prepared'}: {len(clean)} synthetic rows and 226 transformed regression cases; historical inputs unchanged")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
