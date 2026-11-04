"""Read-only source audit with private record output and text-free public counts.

No inference, data admission, guessed Gemini lineage, or modification of source SMS.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from difflib import SequenceMatcher
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from src.python.preprocessing import normalize_financial_numbers
from training.corpus_io import historical_path, ARCHIVES

MANIFEST = "data/sources/transactions/seed_audit_manifest.json"
PRIVATE = "data/private/sms_provenance/seed_audit.json"
REPORT = "data/reports/real_sms_provenance_audit.json"
READABLE = "data/reports/REAL_SMS_PROVENANCE_AUDIT.md"
CORPORA = {
    "legacy_transaction_data": "data/training/dataset_expanded.json",
    "bio_training": "data/training/bio_training_data.json",
    "frozen_regression": "tests/fixtures/test_suite_cases.json",
    "frozen_adversarial": "tests/fixtures/qa_adversarial_cases.json",
}


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKC", normalize_financial_numbers(value))).strip().casefold()


def number_masked(value):
    # Keep financial/status wording and party names. This is NOT a true template ID.
    return re.sub(r"\d+(?:[.,:/-]\d+)*", "<NUM>", canonical(value))


def blocks(text):
    result, start, start_line, cursor = [], None, None, 0
    lines = text.splitlines(keepends=True)
    for line_number, line in enumerate(lines, 1):
        if line.strip():
            if start is None:
                start, start_line = cursor, line_number
        elif start is not None:
            end = cursor
            while end > start and text[end - 1] in "\r\n":
                end -= 1
            result.append({"startChar": start, "endChar": end, "startLine": start_line,
                           "endLine": line_number - 1, "text": text[start:end]})
            start = None
        cursor += len(line)
    if start is not None:
        end = len(text)
        while end > start and text[end - 1] in "\r\n":
            end -= 1
        result.append({"startChar": start, "endChar": end, "startLine": start_line,
                       "endLine": len(lines), "text": text[start:end]})
    return result


def verified_blocks(source, text, source_hash, copy_hash):
    if source_hash != source["sha256"] or copy_hash != source["sha256"]:
        raise ValueError("Attested source/copy hash changed; explicit source review is required")
    chunks = blocks(text)
    if len(chunks) != source["expectedBlocks"]:
        raise ValueError("Reviewed source block count changed")
    return chunks


def compare_csv(csv_rows, records):
    fields = ("text", "label", "provider", "type", "expected_amount", "expected_merchant")
    exact, equivalent, newline_rows = len(csv_rows) == len(records), len(csv_rows) == len(records), 0
    for row, item in zip(csv_rows, records):
        for field in fields:
            expected = "" if item[field] is None else str(item[field])
            actual = row[field]
            if actual != expected:
                exact = False
                if field == "text" and actual.replace("\r\n", "\n") == expected.replace("\r\n", "\n"):
                    newline_rows += 1
                else:
                    equivalent = False
    return {"exactFieldEquality": exact, "equalAfterTextLineEndingNormalization": equivalent, "textLineEndingDifferenceRows": newline_rows}


def proxy_partition_overlap(rows):
    report = {}
    for key in ("normalized", "masked"):
        groups = defaultdict(list)
        for row in rows:
            groups[row["index"][key]].append(row["reference"])
        crossed = [refs for refs in groups.values() if {ref["currentPartition"] for ref in refs} == {"train", "validation"}]
        report[key] = {"crossPartitionGroups": len(crossed), "rowsInThoseGroups": sum(map(len, crossed)),
                       "groupsAcrossProviderMetadata": sum(len({x.get("providerMetadata") for x in refs}) > 1 for refs in crossed),
                       "groupsWithConflictingExistingLabels": sum(len({x.get("existingLabel") for x in refs}) > 1 for refs in crossed),
                       "rowsByPartition": dict(sorted(Counter(x["currentPartition"] for refs in crossed for x in refs).items()))}
    return report


def sanitize_draft(text):
    """Conservative drafts for these seeds, never certified anonymization."""
    candidates = []

    def mark(pattern, kind, group=0, flags=re.I):
        for match in re.finditer(pattern, text, flags):
            candidates.append((*match.span(group), kind))

    mark(r"\d{2,4}\*\d{2,4}|xxxx\d{3,4}|\*\d{4}", "ACCOUNT")
    mark(r"(?:ending\s+(?:with\s+|in\s+)?|المنتهي(?:ة)?\s*ب[ـ\s]*)[x*]*(\d{3,4})", "ACCOUNT", 1)
    mark(r"(?<![\d.])\d{1,2}[/-]\d{1,2}(?:[/-]\d{2,4})?(?![\d.])", "DATE")
    mark(r"\b\d{1,2}:\d{2}(?::\d{2})?\b", "TIME")
    mark(r"(?:ref(?:erence)?\s*#?\s*)(\d+)", "REFERENCE", 1)
    mark(r"(?:one\s+time\s+password\s*:|otp\s+is|enter\s+the\s+code)\s*(\d+)", "OTP", 1)
    mark(r"^\s*(\d+)\s+هو\s+رمز", "OTP", 1)
    mark(r"(?<!\w)(?:\+|00)?\d{7,15}(?!\w)", "IDENTIFIER")
    mark(r"\b(?=[A-Za-z0-9]{8,}\b)(?=[A-Za-z0-9]*[A-Za-z])(?=[A-Za-z0-9]*\d)[A-Za-z0-9]+\b", "TOKEN")
    mark(r"^\s*([A-Za-z0-9]{8,})\s*$", "TOKEN", 1, re.M)
    if re.search(r"cliq|كليك|transfer", text, re.I):
        # Seed counterparties are uppercase Latin text; currency/routing acronyms stay.
        safe = {"JO", "JOD", "USD", "EUR", "GBP", "OTP", "ATM", "REF"}
        for match in re.finditer(r"\b[A-Z]{2,}(?:[ \t]+[A-Z]{2,})*\b", text):
            if not all(word in safe for word in match.group().split()):
                candidates.append((*match.span(), "PERSON"))
    selected = []
    for start, end, kind in sorted(candidates, key=lambda x: (x[0], -(x[1] - x[0]))):
        if not selected or start >= selected[-1][1]:
            selected.append((start, end, kind))
    output, replacements, cursor, output_length = [], [], 0, 0
    identities, counts = {}, Counter()
    for start, end, kind in selected:
        original = text[start:end]
        if (kind, original) not in identities:
            counts[kind] += 1
            identities[kind, original] = f"[{kind}_{counts[kind]}]"
        placeholder = identities[kind, original]
        prefix = text[cursor:start]
        output.append(prefix + placeholder)
        output_length += len(prefix)
        replacements.append({"sourceStart": start, "sourceEnd": end, "sanitizedStart": output_length,
                             "sanitizedEnd": output_length + len(placeholder), "kind": kind, "placeholder": placeholder})
        output_length += len(placeholder)
        cursor = end
    output.append(text[cursor:])
    return "".join(output), replacements


def indexed(text):
    masked = number_masked(text)
    return {"text": text, "normalized": canonical(text), "masked": masked,
            "tokens": re.findall(r"\w+|[^\w\s]", masked)}


def overlap(seed, candidate, policy):
    for key, method, evidence in (("text", "exact_text", "observed_content_overlap"),
                                  ("normalized", "normalized_text", "observed_content_overlap"),
                                  ("masked", "number_masked", "inferred_template_candidate")):
        if seed[key] == candidate[key]:
            return {"method": method, "evidence": evidence, "confirmedParentId": None}
    left, right = set(seed["tokens"]), set(candidate["tokens"])
    shared, union = len(left & right), len(left | right)
    if shared < policy["minimumSharedTokens"] or not union:
        return None
    jaccard = shared / union
    if jaccard < policy["minimumTokenJaccard"]:
        return None
    ratio = SequenceMatcher(None, seed["tokens"], candidate["tokens"], autojunk=False).ratio()
    if ratio < policy["minimumTokenSequenceRatio"]:
        return None
    return {"method": "similarity_candidate", "evidence": "inferred_template_candidate",
            "tokenJaccard": round(jaccard, 4), "tokenSequenceRatio": round(ratio, 4), "confirmedParentId": None}


def load_rows(payload):
    if isinstance(payload, list):
        return payload
    return payload["testCases"] if "testCases" in payload else payload["examples"]


def protected_hashes(root):
    paths = list((root / "DATA_YOU_WANT").glob("*.txt")) + list((root / "data/raw").glob("*.txt"))
    paths += list((root / "data/models").glob("*.json"))
    paths += [root / path for path in ("data/training/dataset_expanded.json", "data/training/dataset_expanded.csv",
              "data/training/bio_training_data.json", "data/training/splits/transaction_direction_split.json",
              "data/training/splits/category_brand_split.json", "tests/fixtures/test_corpus_manifest.json",
              "tests/fixtures/test_suite_cases.json", "tests/fixtures/qa_adversarial_cases.json")]
    result = {}
    for path in sorted(paths):
        relative = path.relative_to(root).as_posix()
        if not path.exists():
            path = historical_path(relative, root)
        result[relative] = digest(path.read_bytes())
    for directory in ARCHIVES:
        manifest_path = root / directory / "manifest.json"
        if not manifest_path.exists():
            continue
        result[directory + "/manifest.json"] = digest(manifest_path.read_bytes())
        for relative, expected in json.loads(manifest_path.read_text(encoding="utf-8"))["filesSha256"].items():
            archive = (root / directory).resolve()
            path = (archive / relative).resolve()
            if not path.is_relative_to(archive) or digest(path.read_bytes()) != expected:
                raise ValueError("Historical archive integrity failed: " + relative)
            result[directory + "/" + relative] = digest(path.read_bytes())
    return result


def build_audit(root=ROOT):
    manifest = json.loads((root / MANIFEST).read_text(encoding="utf-8"))
    inputs = {}

    def read(relative):
        # The v1 audit describes historical exposure, including its original
        # tool hashes. Retain its exact evidence after working-copy retirement.
        archived = set(CORPORA.values()) | {
            "training/audit_sms_provenance.py", "training/build_bio_training_set.py",
            "training/expand_dataset.py", "data/training/dataset_expanded.csv",
            "data/training/splits/transaction_direction_split.json",
        }
        path = historical_path(relative, root) if relative in archived else root / relative
        if not path.exists():
            # Cleanup retired the duplicate raw files. Use the original only
            # when its exact bytes match the source manifest's recorded copy.
            source = next((row for row in manifest["sources"] if row["rawCopy"] == relative), None)
            if source is None:
                raise FileNotFoundError(path)
            raw = (root / source["path"]).read_bytes()
            if digest(raw) != source["sha256"]:
                raise ValueError("Original no longer matches retired raw copy: " + relative)
        else:
            raw = path.read_bytes()
        inputs[relative] = digest(raw)
        return raw.decode("utf-8-sig")

    read(MANIFEST)
    read("training/audit_sms_provenance.py")
    read("training/build_bio_training_set.py")
    read("config/contracts/sms_provenance_record.json")
    attestation = json.loads(read(manifest["sourceAttestation"]))["localRawProvenance"]
    history = json.loads(read("data/sources/transactions/generation_history.json"))
    reproduction = history["currentGeneratorReproduction"]
    read(reproduction["generatorPath"])
    read(reproduction["datasetPath"])
    if inputs[reproduction["generatorPath"]] != reproduction["generatorSha256"] or inputs[reproduction["datasetPath"]] != reproduction["datasetSha256"]:
        raise ValueError("Current artifacts no longer match the recorded generator reproduction evidence")
    copies = {row["original"]: row for row in attestation["verifiedOriginalCopies"]}
    for source in manifest["sources"]:
        if (source["path"] not in copies or copies[source["path"]]["sha256"] != source["sha256"]
                or copies[source["path"]]["existingRawCopy"] != source["rawCopy"]):
            raise ValueError("Seed manifest does not match the user provenance account")
    split = json.loads(read("data/training/splits/transaction_direction_split.json"))
    partitions = {i: fold for fold, field in (("train", "trainIndices"), ("validation", "validationIndices")) for i in split[field]}
    corpora = {}
    for role, path in CORPORA.items():
        rows = load_rows(json.loads(read(path)))
        corpora[role] = [{"reference": {"path": path, "rowIndex": i, "recordId": row.get("id"),
                                     "existingLabel": row.get("label"), "providerMetadata": row.get("provider"),
                                     "currentPartition": partitions.get(i) if role == "legacy_transaction_data" else None},
                          "index": indexed(row.get("text", row.get("body", "")))} for i, row in enumerate(rows)]
    partition_indices = split["trainIndices"] + split["validationIndices"]
    row_count = len(corpora["legacy_transaction_data"])
    if (len(partition_indices) != row_count or set(partition_indices) != set(range(row_count))
            or split["datasetSha256"] != inputs[CORPORA["legacy_transaction_data"]]):
        raise ValueError("Current split does not identify this complete dataset")
    originals = {row["rawCopy"] for row in manifest["sources"]}
    for path in sorted((root / "data/raw").glob("*.txt")):
        relative = path.relative_to(root).as_posix()
        if relative in originals:
            continue  # Known byte copies are not extra independent seeds/corpus rows.
        corpora["unresolved_raw:" + path.stem] = [
            {"reference": {"path": relative, "block": i, "startLine": block["startLine"], "endLine": block["endLine"]},
             "index": indexed(block["text"])} for i, block in enumerate(blocks(read(relative)), 1)]
    source_reports, records, stats = [], [], {}
    observations = {(x["sourceId"], x["block"]): x for x in manifest["observations"]}
    for source in manifest["sources"]:
        text = read(source["path"])
        read(source["rawCopy"])
        chunks = verified_blocks(source, text, inputs[source["path"]], inputs[source["rawCopy"]])
        source_reports.append({"sourceId": source["id"], "blocks": len(chunks), "rawCopyByteIdentical": True})
        for i, chunk in enumerate(chunks, 1):
            record_id = f"{source['id']}-{i:03d}"
            source_index = indexed(chunk["text"])
            links = []
            for corpus, candidates in corpora.items():
                for candidate in candidates:
                    evidence = overlap(source_index, candidate["index"], manifest["similarityCandidatePolicy"])
                    if evidence:
                        links.append({"corpus": corpus, **candidate["reference"], **evidence})
            draft, replacements = sanitize_draft(chunk["text"])
            observation = observations.get((source["id"], i), {})
            records.append({"schemaVersion": "1.0.0", "id": record_id, "sourceId": source["id"], "sourcePath": source["path"],
                            "sourceLocator": {key: chunk[key] for key in ("startChar", "endChar", "startLine", "endLine")},
                            "textSha256": digest(chunk["text"].encode("utf-8")),
                            "normalizedSha256": digest(source_index["normalized"].encode("utf-8")),
                            "templateProxyId": "numeric-proxy-" + digest(source_index["masked"].encode("utf-8")),
                            "verifiedTemplateFamilyId": None, "parentRecordIds": None,
                            "origin": "user_attested_real_seed", "originVerification": "user_statement_not_bank_authentication",
                            "sender": None, "receivedAt": None, "collectionDate": None, "labels": None,
                            "scriptPresence": {"arabic": bool(re.search(r"[\u0621-\u064a]", chunk["text"])),
                                               "latin": bool(re.search(r"[A-Za-z]", chunk["text"]))},
                            "trainingEligible": False, "evaluationEligible": False,
                            "exposure": "user_reported_gemini_seed_development_exposed",
                            "sanitizedTextDraft": draft, "sanitizationReviewStatus": "assistant_draft_human_review_required",
                            "redactions": replacements, "qualityFlags": observation.get("flags", []),
                            "qualityNote": observation.get("note"), "exposureLinks": links})
    for corpus in corpora:
        links = [(record["id"], link) for record in records for link in record["exposureLinks"] if link["corpus"] == corpus]
        stats[corpus] = {"recordsScanned": len(corpora[corpus]), "seedBlocksWithAnyCandidate": len({seed for seed, _ in links}),
                         "seedBlocksWithObservedTextOverlap": len({seed for seed, link in links if link["evidence"] == "observed_content_overlap"}),
                         "linksByStrongestMethod": dict(sorted(Counter(link["method"] for _, link in links).items())),
                         "distinctMatchedCorpusRecords": len({(link.get("rowIndex"), link.get("block")) for _, link in links})}
    publication = manifest["previouslyPublishedFixtureEvidence"]
    if inputs[publication["fixturePath"]] != publication["fixtureSha256"]:
        raise ValueError("Fixture differs from the recorded historical publication evidence; review the evidence/version")
    # BIO explicitly takes fixture IDs/text; verify this artifact relation separately from guessed Gemini ancestry.
    fixture_text = {row["reference"]["recordId"]: row["index"]["text"] for row in corpora["frozen_regression"]}
    bio_verified = sum(fixture_text.get(row["reference"]["recordId"]) == row["index"]["text"] for row in corpora["bio_training"])
    csv_rows = list(csv.DictReader(read("data/training/dataset_expanded.csv").splitlines(keepends=True)))
    expanded = load_rows(json.loads(read(CORPORA["legacy_transaction_data"])))
    csv_projection = compare_csv(csv_rows, expanded)
    businesses = [json.loads(line) for line in read("data/annotations/businesses_200.jsonl").splitlines() if line.strip()]
    category_split = json.loads(read("data/training/splits/category_brand_split.json"))
    mention_counts, mention_seeds = Counter(), defaultdict(set)
    def words(text):
        return tuple(re.findall(r"[^\W_]+", re.sub(r"[\u064b-\u065f\u0670]", "", canonical(text))))
    for record in records:
        source = next(row for row in manifest["sources"] if row["id"] == record["sourceId"])
        locator = record["sourceLocator"]
        text = (root / source["path"]).read_bytes().decode("utf-8-sig")[locator["startChar"]:locator["endChar"]]
        tokens, mentions = words(text), []
        for business in businesses:
            forms = [words(name) for name in [business["name"]] + business["aliases"]]
            if any(form and any(tokens[i:i + len(form)] == form for i in range(len(tokens) - len(form) + 1)) for form in forms):
                fold = category_split["businessAssignments"][business["businessId"]]
                mentions.append({"businessId": business["businessId"], "fold": fold, "evidence": "lexical_mention_not_identity_proof"})
                mention_counts[fold] += 1
                mention_seeds[fold].add(record["id"])
        record["businessMentionCandidates"] = mentions
    summary = {"auditVersion": manifest["auditVersion"], "scope": "Source/content exposure audit only; no model inference, admission, or independent evaluation",
               "sourceFiles": source_reports, "seedBlockCount": len(records),
               "sourceAuthentication": "user_attested_not_independently_authenticated", "independentEvaluationEligibleCount": 0,
               "trainingAdmittedCount": 0, "confirmedGeminiParentEdges": 0,
               "unresolvedOtherRawBlockCount": sum(len(rows) for role, rows in corpora.items() if role.startswith("unresolved_raw:")),
               "scriptCoverage": {"arabicScriptPresent": sum(row["scriptPresence"]["arabic"] for row in records),
                                  "latinOnly": sum(row["scriptPresence"]["latin"] and not row["scriptPresence"]["arabic"] for row in records),
                                  "interpretation": "Script probes, not reviewed language or performance labels"},
               "currentTrainingSplitProxyOverlap": proxy_partition_overlap(corpora["legacy_transaction_data"]),
               "corpora": stats, "bioRowsVerifiedAsFixtureCopies": bio_verified,
               "previouslyPublishedFixtureExposure": {"commit": publication["commit"], "path": publication["fixturePath"],
                                                      "gitBlobSha1": publication["gitBlobSha1"],
                                                      "seedBlocksWithObservedTextOverlap": stats["frozen_regression"]["seedBlocksWithObservedTextOverlap"],
                                                      "currentFixtureMatchesHistoricalBlobEvidence": True,
                                                      "currentRemoteVisibilityOrRevisionChecked": False},
               "bioRowsScanned": len(corpora["bio_training"]), "csvProjection": csv_projection,
               "generationHistory": {"historicalAiReportedRows": history["userSuppliedHistoricalAccount"]["reportedGeneratedRows"],
                                     "currentRows": len(expanded), "currentGeneratorReproductionEvidenceMatchesHashes": True,
                                     "perRecordGeminiParentsConfirmed": False},
               "categoryBusinessMentionCandidates": {fold: {"mentions": mention_counts[fold], "seedBlocks": len(mention_seeds[fold])} for fold in ("train", "validation", "test")},
               "qualityFlagCounts": dict(sorted(Counter(flag for record in records for flag in record["qualityFlags"]).items())),
               "sanitization": {"draftCount": len(records), "humanReviewedCount": 0, "allDraftsPrivate": True},
               "limits": ["File blocks are not authenticated SMS packet boundaries.", "Exact/normalized overlap establishes content reuse, not historical parentage.",
                          "Number masking/similarity are candidate evidence only; unmatched rows do not prove independence.",
                          "Current train/validation normalized duplicates cross provider metadata; provider-local grouping is not content isolation.",
                          "The previously pushed fixture snapshot embeds original-seed text; ignoring raw/private files does not remove those historical copies. Versioned sanitization and separately authorized remote-history remediation are needed.",
                          "Other raw files have unresolved origins. A user-pasted historical AI account supplies no per-row Gemini ancestry.",
                          "Sanitized drafts are private and unadmitted; no new labels or public message text.",
                          "The existing merchant final-test reservation remains separate and unevaluated."]}
    private = {"auditVersion": manifest["auditVersion"], "sourceManifest": MANIFEST,
               "inputSha256": dict(sorted(inputs.items())), "records": records,
               "unresolvedRawSources": [{"role": role, "blocks": len(rows), "origin": "unresolved", "trainingAdmitted": False,
                                         "evaluationEligible": False} for role, rows in corpora.items() if role.startswith("unresolved_raw:")],
               "verifiedArtifactLineage": {"builder": "training/build_bio_training_set.py", "source": CORPORA["frozen_regression"],
                                           "derived": CORPORA["bio_training"], "verifiedIdAndTextPairs": bio_verified},
               "lineageRule": "Text equality and proxy similarity are exposure evidence, not confirmed Gemini parent links."}
    return private, summary


def readable(summary):
    lines = ["# Real SMS source audit", "", "Read-only audit of user-attested seed files. No bank authentication or independent accuracy claim.", "",
             f"Located **{summary['seedBlockCount']} message blocks**; no new messages admitted for training or independent evaluation.", "",
             "| Source | Message blocks | Raw copy identical |", "| --- | ---: | --- |"]
    lines += [f"| {row['sourceId']} | {row['blocks']} | yes |" for row in summary["sourceFiles"]]
    lines += ["", "| Corpus | Records scanned | Seeds with observed text overlap | Seeds with any candidate |", "| --- | ---: | ---: | ---: |"]
    lines += [f"| {name} | {row['recordsScanned']} | {row['seedBlocksWithObservedTextOverlap']} | {row['seedBlocksWithAnyCandidate']} |" for name, row in summary["corpora"].items()]
    lines += ["", f"BIO rows verified as exact fixture copies by ID and text: {summary['bioRowsVerifiedAsFixtureCopies']}/{summary['bioRowsScanned']}.",
              "", f"Privacy finding: **{summary['previouslyPublishedFixtureExposure']['seedBlocksWithObservedTextOverlap']} seed blocks match text in a fixture included in the previously pushed snapshot**. Raw-file ignore rules do not protect embedded copies. Prepare a sanitized version and preserve the historical baseline privately; remote-history changes require separate authorization. Current repository visibility was not checked.",
              f"Training CSV equals the JSON's reduced fields after CRLF/LF normalization: {summary['csvProjection']['equalAfterTextLineEndingNormalization']}. Text rows differing only in line endings: {summary['csvProjection']['textLineEndingDifferenceRows']}.", "",
              f"Historical AI account: {summary['generationHistory']['historicalAiReportedRows']} rows; current generator/data: {summary['generationHistory']['currentRows']} rows, reproducible in memory. The historical artifact is unavailable.", "",
              f"Other raw blocks with unresolved origins: {summary['unresolvedOtherRawBlockCount']}. Seed blocks containing Arabic script: {summary['scriptCoverage']['arabicScriptPresent']} (script presence only, not accuracy).", "",
              f"Observed normalized-text duplication across current training/validation: **{summary['currentTrainingSplitProxyOverlap']['normalized']['crossPartitionGroups']} groups / {summary['currentTrainingSplitProxyOverlap']['normalized']['rowsInThoseGroups']} rows**, across provider metadata. No existing-label conflicts in these groups: {summary['currentTrainingSplitProxyOverlap']['normalized']['groupsWithConflictingExistingLabels'] == 0}.", "",
              f"Current training/validation numeric-mask proxy overlap: {summary['currentTrainingSplitProxyOverlap']['masked']['crossPartitionGroups']} groups across {summary['currentTrainingSplitProxyOverlap']['masked']['rowsInThoseGroups']} rows. These are candidates, not verified source families; assignments remain unchanged.", "",
              "Confirmed Gemini parent edges: **0**. Similarity scores are matching heuristics, not certainty probabilities.", "",
              "Record locators, redaction drafts, and candidate links are stored only under ignored `data/private/sms_provenance/`.",
              "No public report contains message text, party names, account values, dates, codes, or per-message content hashes.", "", "Limits:", ""]
    lines += [f"- {limit}" for limit in summary["limits"]]
    lines += ["", "Next: review/supplement origin evidence and sanitized drafts; acquire fresh unexposed families before independent evaluation.", ""]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Recompute in memory and check saved artifacts without writing")
    args = parser.parse_args()
    if "/data/private/" not in (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines():
        raise ValueError("Private audit output must be ignored before writing")
    before = protected_hashes(ROOT)
    private, summary = build_audit()
    outputs = {PRIVATE: json.dumps(private, ensure_ascii=False, indent=2) + "\n",
               REPORT: json.dumps(summary, ensure_ascii=False, indent=2) + "\n", READABLE: readable(summary)}
    for relative, content in outputs.items():
        path = ROOT / relative
        if args.check:
            if not path.is_file() or path.read_text(encoding="utf-8") != content:
                raise ValueError("Audit artifact missing or stale: " + relative)
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
    if protected_hashes(ROOT) != before:
        raise ValueError("Protected source/model/fixture inputs changed during audit")
    print(f"SMS provenance audit: {summary['seedBlockCount']} seed blocks; 0 independent/admitted records; private links and text-free summary {'checked' if args.check else 'saved'}. Protected inputs unchanged.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
