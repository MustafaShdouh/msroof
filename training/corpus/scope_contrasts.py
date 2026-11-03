"""Build and validate weak scope contrasts; no model imports, inference or admission."""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import re

from src.python.research.sms_semantics import normalize
from src.python.research.merchant_category import normalize_name
from training.corpus.semantics import BUSINESSES, RESERVATION, FAMILIES, reservation_forms
from training.corpus_io import ROOT, sha256

SOURCE = ROOT / "data/annotations/sms_scope_v1/scenarios.txt"
OUTPUT = ROOT / "data/training/authored_sms_scope_v1/messages.jsonl"
MANIFEST = ROOT / "data/annotations/sms_scope_v1/manifest.json"
REPORT = ROOT / "data/reports/transactions/sms_scope_v1_preparation.json"
THEMES = {"personal_claim": (1, 1), "question_request": (1, 1), "pending_settled": (1, 0),
          "negated_failure": (0, 1), "illustrative_scope": (1, 0), "party_scope": (0, 1)}
STATES = dict(C="completed", N="non_transaction", U="uncertain")
SEED = "sms-scope-v1-2026-10-28"


def key(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def unmark(marked):
    text, spans, offset = "", [], 0
    for match in re.finditer(r"\{\{(event|context|scope):([^{}]+)\}\}", marked):
        text += marked[offset:match.start()]
        start = len(text)
        text += match[2]
        spans.append(dict(kind={"event": "eventMention", "context": "messageContext", "scope": "scopeQualifier"}[match[1]], start=start, end=len(text), text=match[2]))
        offset = match.end()
    text += marked[offset:]
    if "{{" in text or "}}" in text or not spans or not any(s["kind"] == "messageContext" for s in spans):
        raise ValueError("Malformed or incomplete manual evidence markup")
    if any(text[s["start"]:s["end"]] != s["text"] for s in spans):
        raise ValueError("Invalid code-point evidence")
    return text, spans


def parse(source):
    groups, current = [], None
    for line in source.splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        if line.startswith("@ "):
            _, identifier, theme = line.split()
            if theme not in THEMES or any(g["id"] == identifier for g in groups):
                raise ValueError("Unknown theme or duplicate family")
            current = dict(id=identifier, theme=theme, cases=[])
            groups.append(current)
            continue
        match = re.fullmatch(r"([CNU]) (ar|en) (.+)", line)
        if current is None or not match:
            raise ValueError("Malformed case")
        text, spans = unmark(match[3])
        current["cases"].append(dict(language=match[2], target=STATES[match[1]], text=text, evidence=spans))
    if len(groups) != 24 or Counter(g["theme"] for g in groups) != {t: 4 for t in THEMES}:
        raise ValueError("Expected four families per theme")
    for group in groups:
        if len(group["cases"]) != 8:
            raise ValueError("Expected four bilingual semantic states")
        for i in range(0, 8, 2):
            ar, en = group["cases"][i:i+2]
            if (ar["language"], en["language"]) != ("ar", "en") or ar["target"] != en["target"]:
                raise ValueError("Translation/state pair mismatch")
        if Counter(r["target"] for r in group["cases"])["uncertain"] != 2:
            raise ValueError("Each family must retain its ambiguity pair")
    return groups


def contained(value):
    if isinstance(value, dict):
        for k, v in value.items():
            if k in ("text", "body", "message", "ar", "en") and isinstance(v, str):
                yield v
            elif isinstance(v, (dict, list)):
                yield from contained(v)
    elif isinstance(value, list):
        for v in value:
            yield from contained(v)


def comparison_inputs():
    paths = set()
    for directory in (ROOT / "data/training", ROOT / "tests/fixtures"):
        paths.update(p for p in directory.rglob("*") if p.suffix in (".json", ".jsonl") and p != OUTPUT)
    paths.add(ROOT / ".local-backups/sms_research_manual_v1/cases.json")
    # Only extant sanitized/diagnostic inputs; no private original SMS export.
    texts = []
    for path in sorted(paths):
        raw = path.read_text(encoding="utf-8-sig")
        obj = [json.loads(line) for line in raw.splitlines() if line.strip()] if path.suffix == ".jsonl" else json.loads(raw)
        texts.extend(contained(obj))
    return sorted(paths), texts


def build():
    groups = parse(SOURCE.read_text(encoding="utf-8"))
    assignments = {}
    for theme, (dev, reserved) in THEMES.items():
        ordered = sorted((g for g in groups if g["theme"] == theme), key=lambda g: key(SEED + ":" + g["id"]))
        for i, group in enumerate(ordered):
            assignments[group["id"]] = "development" if i < dev else "reserved_diagnostic" if i < dev + reserved else "proposed_training"
    rows = []
    for group in groups:
        for i, case in enumerate(group["cases"]):
            rows.append(dict(recordId=f"scope-v1-{group['id']}-{i//2+1}-{case['language']}", authoringGroupId="scope-v1-" + group["id"],
                semanticState=i//2+1, theme=group["theme"], fold=assignments[group["id"]], **case,
                textSha256=key(case["text"]), labelState="weak", reviewer="assistant", origin="assistant_authored_scope_contrast",
                ownershipInferred=False, binaryScoringAllowed=case["target"] != "uncertain",
                trainingEligible=False, independentEvaluationEligible=False, modelFittingAllowed=False))
    paths, old = comparison_inputs()
    old_exact, old_normal, old_proxy = {key(t) for t in old}, {normalize(t) for t in old}, {normalize_name(normalize(t)) for t in old}
    forms = reservation_forms([json.loads(line) for line in BUSINESSES.read_text(encoding="utf-8").splitlines() if line.strip()],
        json.loads(RESERVATION.read_text(encoding="utf-8"))["businessAssignments"], json.loads(FAMILIES.read_text(encoding="utf-8"))["families"])
    seen = defaultdict(set)
    collisions = []
    for row in rows:
        normal, proxy = normalize(row["text"]), normalize_name(normalize(row["text"]))
        seen[proxy].add(row["authoringGroupId"])
        blockers = []
        if row["textSha256"] in old_exact: blockers.append("old_exact")
        if normal in old_normal: blockers.append("old_normalized")
        if proxy in old_proxy: blockers.append("old_numeric_punctuation_proxy")
        for form in forms:
            if " " + form + " " in " " + normalize_name(row["text"]) + " ": blockers.append("protected_merchant_alias")
        if blockers: collisions.append(dict(recordId=row["recordId"], blockers=sorted(set(blockers))))
    cross = [sorted(v) for v in seen.values() if len(v) > 1]
    if collisions or cross or len({r["textSha256"] for r in rows}) != 192:
        raise ValueError("Overlap blockers: " + json.dumps(dict(old=collisions, crossFamily=cross)))
    manifest = dict(version="1.0.0", sourceSha256=sha256(SOURCE), seed=SEED, allocation="Within each theme, sort SHA256(seed+':'+familyId); first quota to development, next quota reserved, rest proposed training",
        themeQuotas={t: dict(development=d, reserved=r) for t, (d, r) in THEMES.items()}, assignments=assignments,
        families=[dict(id=g["id"], theme=g["theme"], records=8, fold=assignments[g["id"]]) for g in groups],
        labelReview="Same assistant reviewed all bilingual states before model inference; not human gold or independent review",
        spanOffsets="Unicode code points, half-open; eventMention does not assert factual completion inside quotes",
        uncertainPolicy="Retain uncertain rows; exclude from binary fitting/scoring; no default negative",
        ownershipPolicy="Not labeled or inferred; completed transfers can still require ownership review",
        evaluationPlan=dict(unit="whole authoring family including four states and both languages", counts="TP/TN/FP/FN and abstentions per fold/language/theme; paired-state consistency; uncertain cases separate",
            reservedUsage="No inference until a future fixed experiment protocol explicitly authorizes it; never training or tuning", threshold="No threshold selection on this data is authorized", modelFittingAllowed=False),
        trainingEligible=False, independentEvaluationEligible=False, modelFittingAllowed=False)
    report = dict(runId="sms_scope_v1_preparation", rows=len(rows), familyCounts=dict(Counter(assignments.values())), foldCounts=dict(Counter(r["fold"] for r in rows)),
        targetCounts=dict(Counter(r["target"] for r in rows)), languageCounts=dict(Counter(r["language"] for r in rows)),
        foldTargetCounts={f: dict(Counter(r["target"] for r in rows if r["fold"] == f)) for f in set(assignments.values())},
        checkedTextOccurrences=len(old), checkedPaths={p.relative_to(ROOT).as_posix(): sha256(p) for p in paths},
        sourceSha256=sha256(SOURCE), producerSha256=sha256(Path(__file__)), exactNormalizedNumericProxyBlockers=collisions, crossFamilyProxyBlockers=cross,
        protectedMerchantInference=False, modelInference=False, modelFitted=False,
        limits=["Authored families are provenance groups, not proven semantic independence; broad themes and short financial phrases cross folds.",
                "Old normalized/punctuation-number proxies are bounded checks, not proof of source/template independence.",
                "Batch informed by exposed failures and same assistant author/reviewer. Reserved means prospective synthetic diagnostics only.",
                "Fictional shop-name minimal pairs deliberately test scope within a family; no merchant registry or real-world store evidence."])
    outputs = {OUTPUT: "".join(json.dumps(r, ensure_ascii=False, separators=(",", ":")) + "\n" for r in rows),
        MANIFEST: json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", REPORT: json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n"}
    return rows, outputs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    rows, outputs = build()
    for path, content in outputs.items():
        if path.exists():
            if path.read_bytes() != content.encode("utf-8"): raise ValueError("Frozen output differs: " + str(path))
        elif args.check:
            raise ValueError("Missing output: " + str(path))
        else:
            with path.open("x", encoding="utf-8", newline="\n") as handle: handle.write(content)
    print(json.dumps(dict(records=len(rows), folds=dict(Counter(r["fold"] for r in rows)), labels=dict(Counter(r["target"] for r in rows)))))


if __name__ == "__main__":
    main()
