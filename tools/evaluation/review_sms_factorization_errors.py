"""Review saved paired decisions; no encoder loading, fitting, or new predictions."""
from collections import Counter
from fractions import Fraction
import hashlib
import json

from training.transactions import factorization_comparison_v2 as trial
from training.transactions.factorization_protocol import compose_status, development_reviews
from src.python.research.sms_semantics import normalize

OUTPUT = trial.AREA / "sms_factorization_comparison_v2_error_review.json"


def transition(target, direct, factorized):
    if direct == target and factorized == target:
        return "both_correct"
    if factorized == target:
        return "fix"
    if direct == target:
        return "regression"
    return "both_wrong"


def unique_counts(rows):
    """Deduplicate exact text; do not silently count quote/manual copies twice."""
    unique = {}
    for row in rows:
        key = row["textSha256"]
        if key in unique:
            assert all(unique[key][k] == row[k] for k in ("target", "direct", "factorized", "transition"))
        unique[key] = row
    return dict(Counter(r["transition"] for r in unique.values()))


def component_substitution(rows):
    """Symbolic use of existing labels, NOT model predictions or attainable scores."""
    return dict(
        rows=len(rows),
        savedStatusCorrect=sum(r["factorized"] == r["target"] for r in rows),
        bothFieldsCorrect=sum(r["context"] == r["goldContext"] and r["event"] == r["goldEvent"] for r in rows),
        wrongFieldButStatusCorrect=sum(
            (r["context"] != r["goldContext"] or r["event"] != r["goldEvent"]) and r["factorized"] == r["target"] for r in rows),
        goldContextOnlyStatusMatches=sum(compose_status(r["goldContext"], r["event"]) == r["target"] for r in rows),
        goldEventOnlyStatusMatches=sum(compose_status(r["context"], r["goldEvent"]) == r["target"] for r in rows),
        interpretation="Label substitution using exposed weak truth; not inference, a deployable correction, or predicted performance.")


def review():
    _, training, cohorts, reserved = trial.protocol()
    report = trial.old.read(trial.REPORT)
    assert report["binding"] == trial.binding()
    assert not report["reservedInferred"] and not report["reservedScoredRecordIds"]
    gold = {r["recordId"]: r for r in development_reviews()}
    all_rows, summaries, components, overlaps = [], {}, [], []
    normalized_training = {}
    for row in training:
        normalized_training.setdefault(normalize(row["text"]), []).append(row)
    for name, raw_rows in cohorts.items():
        saved = report["evaluations"][name]["rows"]
        assert [r["recordId"] for r in raw_rows] == [r["recordId"] for r in saved]
        paired = []
        for raw, row in zip(raw_rows, saved):
            matches = normalized_training.get(normalize(raw["text"]), [])
            if matches:
                overlaps.append(dict(cohort=name, recordId=raw["recordId"],
                    exactTrainingRecordIds=[r["recordId"] for r in matches if r["text"] == raw["text"]],
                    normalizedTrainingRecordIds=[r["recordId"] for r in matches],
                    interpretation="Training-exposed conformance control; not evidence of unseen-text generalization. Frozen scores retained."))
            assert hashlib.sha256(raw["text"].encode("utf-8")).hexdigest() == row["textSha256"]
            assert row["target"] == raw["target"]
            direct = row["outputs"]["direct_status"]["status"]
            factor = row["outputs"]["factorized"]
            item = dict(cohort=name, recordId=row["recordId"], textSha256=row["textSha256"],
                        language=row["language"], target=row["target"], direct=direct,
                        factorized=factor["status"], **factor["labels"],
                        transition=transition(row["target"], direct, factor["status"]))
            paired.append(item)
            if name == "scopeDevelopment":
                label = gold[row["recordId"]]
                component = dict(item, goldContext=label["messageContext"]["value"],
                                 goldEvent=label["describedEventState"]["value"])
                components.append(component)
        summaries[name] = {
            lang: dict(Counter(r["transition"] for r in paired if lang == "all" or r["language"] == lang))
            for lang in ("all", "ar", "en")}
        all_rows.extend(paired)
    assert not {r["recordId"] for r in all_rows} & {r["recordId"] for r in reserved}
    primary = [r for r in all_rows if r["cohort"] != "quoteControls"]
    coverage = {}
    for field in ("context", "event"):
        coverage[field] = {}
        for value in sorted({r[field] for r in training}):
            selected = [r for r in training if r[field] == value]
            coverage[field][value] = dict(records=len(selected), groups=len({r["group"] for r in selected}),
                baseWeight=str(sum((Fraction(1, sum(x["group"] == r["group"] for x in training)) for r in selected), Fraction())))
    errors = [r for r in all_rows if r["transition"] != "both_correct"]
    unknown_rows = [r for r in components if r["target"] == "uncertain"]
    result = dict(runId="sms_factorization_comparison_v2_error_review", fitting=False,
        newModelInference=False, labelsChanged=0, reservedInferred=False, independentAccuracy=False,
        inputs={str(p.relative_to(trial.ROOT)).replace("\\", "/"): trial.encoder.digest(p) for p in (
            trial.REPORT, trial.PROTOCOL, trial.view.DEV_REVIEWS,
            trial.ROOT/"tools/evaluation/review_sms_factorization_errors.py")},
        pairedTransitions=summaries, trainingDiagnosticOverlaps=overlaps, uniquePrimary=unique_counts(primary),
        uniqueIncludingQuoteControls=unique_counts(all_rows), errors=errors,
        componentRows=components, labelSubstitution=component_substitution(components),
        uncertainDevelopment=dict(rows=len(unknown_rows),
            directRetained=sum(r["direct"] == "uncertain" for r in unknown_rows),
            factorizedRetained=sum(r["factorized"] == "uncertain" for r in unknown_rows),
            predictedContextCounts=dict(Counter(r["context"] for r in unknown_rows)),
            predictedEventCounts=dict(Counter(r["event"] for r in unknown_rows))),
        trainingCoverage=coverage,
        limits=["Assistant weak labels and exposed diagnostics; no independent accuracy or causal attribution.",
                "Component truth exists only on 32 development rows; do not invent it for older cohorts.",
                "Four quote-control uncertain targets encode conservative mixed/multisentence scope policy, not solely ambiguous event outcome. Frozen truth retained.",
                "Correct composed status can conceal wrong components; neither substitution score is achievable-performance evidence.",
                "No threshold, ensemble, class-weight, or checkpoint search; no label edits or new example generation."])
    content = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if OUTPUT.exists():
        assert OUTPUT.read_bytes() == content.encode("utf-8"), "Saved review changed"
    else:
        with OUTPUT.open("x", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
    return result


if __name__ == "__main__":
    r = review()
    print(json.dumps({k: r[k] for k in ("uniquePrimary", "uniqueIncludingQuoteControls", "labelSubstitution", "uncertainDevelopment")}))
