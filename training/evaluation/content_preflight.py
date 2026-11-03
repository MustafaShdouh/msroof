"""Content exposure and diagnostic reason checks; no learned model dependency."""
import hashlib
from src.python.research.sms_semantics import normalize


def sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def preflight(training, diagnostics, contract):
    """Reject unacknowledged training overlap; exceptions bind exact provenance.

    Diagnostics have cohort/recordId/text/target. Output contains metadata only.
    Text disjointness is not evidence of family or real-world independence.
    """
    train_ids, raw, normalized = set(), {}, {}
    for row in training:
        rid, text = row["recordId"], row["text"]
        if rid in train_ids or not text.strip() or not normalize(text):
            raise ValueError("Duplicate training ID or empty training text")
        train_ids.add(rid)
        raw.setdefault(sha(text), set()).add(rid)
        normalized.setdefault(sha(normalize(text)), set()).add(rid)
    exceptions = contract["inSampleControls"]
    reasons = contract["uncertaintyReasons"]
    seen, used = set(), set()
    result = []
    for row in diagnostics:
        key = row["cohort"] + "/" + row["recordId"]
        if row["target"] not in ("completed", "non_transaction", "uncertain"):
            raise ValueError("Unknown diagnostic target: " + key)
        if key in seen or not row["text"].strip() or not normalize(row["text"]):
            raise ValueError("Duplicate diagnostic key or empty diagnostic text")
        seen.add(key)
        text_hash = sha(row["text"])
        exact = sorted(raw.get(text_hash, ()))
        equivalent = sorted(normalized.get(sha(normalize(row["text"])), ()))
        overlap = sorted(set(exact) | set(equivalent))
        exception = exceptions.get(key)
        if exception is not None:
            if (exception["textSha256"] != text_hash or
                    exception["trainingRecordIds"] != overlap or not overlap or
                    not exception["rationale"].strip()):
                raise ValueError("Stale or mismatched in-sample control binding: " + key)
            used.add(key)
        elif overlap or row["recordId"] in train_ids:
            raise ValueError("Unacknowledged training/diagnostic overlap: " + key)
        reason = reasons.get(key)
        if row["target"] == "uncertain":
            if reason not in contract["reasonDefinitions"]:
                raise ValueError("Missing or invalid uncertainty reason: " + key)
        elif reason is not None:
            raise ValueError("Uncertainty reason attached to definite truth: " + key)
        result.append(dict(cohort=row["cohort"], recordId=row["recordId"],
            textSha256=text_hash, normalizedTextSha256=sha(normalize(row["text"])),
            target=row["target"], role="in_sample_conformance" if exception else "text_disjoint_exposed_diagnostic",
            exactTrainingRecordIds=exact, normalizedTrainingRecordIds=equivalent,
            uncertaintyReason=reason, independentEvaluationEligible=False))
    if used != set(exceptions) or set(reasons) - seen:
        raise ValueError("Unused exposure exception or uncertainty metadata")
    return result
