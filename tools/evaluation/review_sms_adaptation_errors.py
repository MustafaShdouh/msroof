"""Review saved adaptation mistakes and literal training coverage, without inference."""
from collections import Counter
import json
from pathlib import Path

from training.transactions.completion_adaptation import prepare, read, REPORT, PROTOCOL, ROOT
from training.transactions.completion_encoder import digest

OUTPUT = ROOT / "data/reports/transactions/sms_completion_adaptation_v1_error_review.json"
REASONS = {
    "synthetic-v1-1665": ("posted_deposit", "The text states that funds have been credited as an ATM deposit. This is a completion label, not ownership proof."),
    "synthetic-v1-0289": ("question", "A question about finishing a transaction does not report a completed account movement."),
    "foreign-purchase-en": ("settled_foreign_purchase", "The text explicitly states a debited USD purchase and distinguishes its JOD available balance."),
    "probe-example-context-completed-ar": ("credit_context", "The text reports salary landing and funds becoming available; the alert wording is not an example introduction."),
    "probe-approval-state-completed-ar": ("negation_scope", "The debit is finished; no longer pending negates the pending state, not the completed payment."),
    "qualified-merchant-en": ("party_scope", "Teaching Example is inside the merchant field after at, not an instruction that the message is a teaching example."),
    "qualified-merchant-ar": ("party_scope", "The quoted shop name follows لدى; its educational wording does not negate the stated debit."),
    "scope-v1-wage-receipt-1-ar": ("credit_context", "Posted work pay and withdrawable funds explicitly describe completed credit; no amount is required for completion."),
    "scope-v1-wage-receipt-1-en": ("credit_context", "Booked work payment and withdrawable funds describe completed credit; recording can still require missing fields."),
}
REFS = ("word", "context", "encoder")


def prediction(score):
    return "completed" if score > 0 else "non_transaction"


def review():
    protocol, training, cohorts, _ = prepare()
    report = read(REPORT)
    if digest(PROTOCOL) != report["binding"]["protocolSha256"] or digest(ROOT / "training/transactions/completion_adaptation.py") != report["binding"]["producerSha256"]:
        raise ValueError("Original experiment bindings changed")
    if report["reservedInferred"] or report["reservedScoredRecordIds"]:
        raise ValueError("This review must not silently include reserved results")
    errors, transitions = [], {}
    for name, raw_rows in cohorts.items():
        saved = report["evaluations"][name]["rows"]
        if [r["recordId"] for r in raw_rows] != [r["recordId"] for r in saved]:
            raise ValueError("Cohort alignment changed")
        changes = {ref: dict(fixes=[], regressions=[]) for ref in REFS}
        for raw, saved_row in zip(raw_rows, saved):
            if raw["target"] not in ("completed", "non_transaction"):
                continue
            choices = {key: prediction(saved_row[key]) for key in (*REFS, "candidate")}
            correct = {key: value == raw["target"] for key, value in choices.items()}
            for ref in REFS:
                if correct["candidate"] and not correct[ref]: changes[ref]["fixes"].append(raw["recordId"])
                if not correct["candidate"] and correct[ref]: changes[ref]["regressions"].append(raw["recordId"])
            if not correct["candidate"]:
                group, rationale = REASONS[raw["recordId"]]
                errors.append(dict(cohort=name, recordId=raw["recordId"], text=raw["text"], target=raw["target"],
                    errorType="false_completion" if choices["candidate"] == "completed" else "missed_completion",
                    pattern=group, labelReview=dict(reviewer="assistant", state="weak", retained=True, rationale=rationale),
                    scores={key: saved_row[key] for key in (*REFS, "candidate")}, predictions=choices,
                    referencesCorrect=[ref for ref in REFS if correct[ref]], allModelsWrong=not any(correct.values())))
        transitions[name] = changes
    if {r["recordId"] for r in errors} != set(REASONS) or len(errors) != 9:
        raise ValueError("Review case inventory changed")
    queries = {
        "literal_question_mark": lambda r: "?" in r["text"] or "؟" in r["text"],
        "literal_USD": lambda r: "usd" in r["text"].lower(),
        "literal_English_wage": lambda r: "wage" in r["text"].lower(),
        "new_party_scope": lambda r: r["recordId"].startswith("scope-v1-") and any(g in r["group"] for g in ("shop-reminder", "cafe-test", "bookshop-pending", "vendor-cancel")),
    }
    coverage = {}
    for name, query in queries.items():
        matches = [r for r in training if query(r)]
        coverage[name] = dict(records=len(matches), groups=len({r["group"] for r in matches}),
            targetCounts=dict(Counter(r["target"] for r in matches)), recordIds=[r["recordId"] for r in matches],
            interpretation="Literal query only, not an event-coverage or semantic-similarity annotation")
    result = dict(runId="sms_completion_adaptation_v1_error_review", fitting=False, newInference=False, reservedInferred=False,
        inputSha256={REPORT.relative_to(ROOT).as_posix(): digest(REPORT), PROTOCOL.relative_to(ROOT).as_posix(): digest(PROTOCOL),
            Path(__file__).relative_to(ROOT).as_posix(): digest(Path(__file__))},
        errorCounts=dict(Counter(r["errorType"] for r in errors)), patternCounts=dict(Counter(r["pattern"] for r in errors)),
        allModelsWrong=[r["recordId"] for r in errors if r["allModelsWrong"]], errors=errors, transitions=transitions,
        trainingLiteralCoverage=coverage, labelsChanged=0,
        limits=["All labels remain same-assistant weak, not human gold. Review is not independent validation.",
                "Scores have different scales across models and are not calibrated confidence; do not compare their magnitudes as certainty.",
                "No threshold or ensemble search, new predictions, attribution inference, or reserved access occurred.",
                "The experiment changed training data and representation; no single cause of errors is established.",
                "Training literal query absence does not establish absence of semantic equivalents or prove root cause."])
    content = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if OUTPUT.exists():
        if OUTPUT.read_bytes() != content.encode("utf-8"): raise ValueError("Frozen review changed")
    else:
        with OUTPUT.open("x", encoding="utf-8", newline="\n") as handle: handle.write(content)
    print(json.dumps(dict(errors=result["errorCounts"], allModelsWrong=result["allModelsWrong"],
        frozenReferenceChanges={k:{c:len(v) for c,v in t["encoder"].items()} for k,t in transitions.items()},
        literalCoverage={k:v["records"] for k,v in coverage.items()})))


if __name__ == "__main__":
    review()
