"""Single approved word-only follow-up on frozen old plus authored weak training data."""
import argparse
from collections import Counter, defaultdict
from copy import deepcopy
import json
import math
import platform
import warnings

from src.python.research.sms_semantics import CONTRACT, CONTRACT_PATH, SmsSemanticsModel
from training.transactions import semantics_ab as base
from training.corpus import coverage
from training.corpus.semantics import json_text
from training.corpus_io import ROOT, DATASET, sha256, write_immutable, snapshot_report_inputs

PROTOCOL_PATH = ROOT / "config/experiments/sms_semantics_followup_v1.json"
PROTOCOL = json.loads(PROTOCOL_PATH.read_text(encoding="utf-8"))
RUN = PROTOCOL["runId"]
REPORT = base.AREA / (RUN + ".json")
COHORT = base.AREA / (RUN + "_cohort.json")
ATTEMPT = base.AREA / (RUN + "_attempt.json")
FAILURE = base.AREA / (RUN + "_failure.json")
MODEL = ROOT / ("data/models/" + RUN + "_word_candidate.json")


def select_cohort(old, batch, sources, blocks):
    blocked_groups = {row["authoringGroupId"] for row in batch if blocks[row["recordId"]]}
    selected = deepcopy(old)
    selected.update(runId=RUN, scope="Approved adaptive weak research selection; original admission flags unchanged",
                    sourceViews=[{"artifact": DATASET.relative_to(ROOT).as_posix(), "indexStart": 0, "recordCount": len(sources)},
                                 {"artifact": coverage.BATCH.relative_to(ROOT).as_posix(), "indexStart": len(sources), "recordCount": len(batch)}],
                    indexConvention="sourceIndex addresses this concatenated source view only; originIndex/sourceArtifact identify immutable originals")
    for name, field in base.FIELDS.items():
        for row in selected["training"][name]:
            row.update(weightGroup=row["sourceExpressionId"], sourceArtifact=DATASET.relative_to(ROOT).as_posix(), originIndex=row["sourceIndex"])
        added = []
        for index, row in enumerate(batch):
            fields = row["annotations"]
            if row["authoringGroupId"] in blocked_groups or fields.get(field, {}).get("value") not in CONTRACT["heads"][name].values():
                continue
            if name == "direction" and fields["transactionStatus"]["value"] != "completed":
                continue
            added.append({"recordId": row["recordId"], "sourceIndex": len(sources) + index, "textSha256": row["textSha256"],
                          "sourceExpressionId": row["sourceExpressionId"], "leakageGroupId": row["authoringGroupId"],
                          "weightGroup": row["authoringGroupId"], "target": fields[field]["value"],
                          "sourceArtifact": coverage.BATCH.relative_to(ROOT).as_posix(), "originIndex": index})
        sizes = Counter(row["weightGroup"] for row in added)
        for row in added:
            row["weight"] = 1 / sizes[row["weightGroup"]]
        selected["training"][name].extend(added)
    return selected


def validate_selection(selected, old, batch, sources, blocks):
    if selected.get("productionAdmissionGranted") is not False or selected["validation"] != old["validation"]:
        raise ValueError("Research selection cannot grant admission or alter validation")
    expected = select_cohort(old, batch, sources, blocks)
    if selected != expected:
        raise ValueError("Selection changed approved source IDs, targets, groups, weights or exclusions")
    for name, rows in selected["training"].items():
        if len({row["recordId"] for row in rows}) != len(rows) or dict(Counter(row["target"] for row in rows)) != PROTOCOL["trainingCounts"][name]:
            raise ValueError("Approved training coverage/classes changed")
        if len(selected["validation"][name]) != PROTOCOL["validationCounts"][name]:
            raise ValueError("Approved validation count changed")
        if {row["leakageGroupId"] for row in rows} & {row["leakageGroupId"] for row in selected["validation"][name]}:
            raise ValueError("Research groups crossed the frozen validation boundary")
        weights = defaultdict(float)
        for row in rows:
            if type(row["sourceIndex"]) is not int or type(row["originIndex"]) is not int:
                raise ValueError("Source offsets must remain integer indices")
            if type(row["weight"]) not in (int, float) or not math.isfinite(row["weight"]) or row["weight"] <= 0:
                raise ValueError("Invalid research weight")
            weights[row["weightGroup"]] += row["weight"]
        if any(abs(weight - 1) > 1e-12 for weight in weights.values()):
            raise ValueError("Authoring/expression group weight differs from one")


def prepare():
    for relative, expected in PROTOCOL["frozenInputs"].items():
        if sha256(ROOT / relative) != expected:
            raise ValueError("Approved input changed: " + relative)
    original_report = json.loads(base.REPORT.read_text(encoding="utf-8"))
    for relative, expected in original_report["inputSha256"].items():
        if sha256(ROOT / relative) != expected:
            raise ValueError("Original A/B source binding changed: " + relative)
    old = base.cohorts()
    if base.COHORT.read_bytes() != json_text(old).encode("utf-8"):
        raise ValueError("Original measured cohort changed")
    batch, audit = coverage.build()
    if coverage.REPORT.read_bytes() != json_text(audit).encode("utf-8"):
        raise ValueError("Authored batch quarantine report changed")
    sources = json.loads(DATASET.read_text(encoding="utf-8"))
    blocks = audit["authoredBatch"]["blockersByRecord"]
    selected = select_cohort(old, batch, sources, blocks)
    validate_selection(selected, old, batch, sources, blocks)
    return selected, sources + batch, original_report, audit


def fit(selected, sources):
    import numpy as np
    from sklearn.exceptions import ConvergenceWarning
    from sklearn.linear_model import LogisticRegression
    settings, heads, checks = CONTRACT["fit"], {}, {}
    for name, rows in selected["training"].items():
        texts = [sources[row["sourceIndex"]]["text"] for row in rows]
        words = base.vocabulary(texts, "word")
        if not words:
            raise ValueError("Empty training vocabulary")
        matrix = base.matrix(texts, "word", words)
        labels = [int(row["target"] == CONTRACT["heads"][name]["positive"]) for row in rows]
        estimator = LogisticRegression(solver=settings["solver"], C=settings["C"], l1_ratio=settings["l1Ratio"],
                                       dual=settings["dual"], fit_intercept=settings["fitIntercept"], intercept_scaling=settings["interceptScaling"],
                                       tol=settings["tolerance"], max_iter=settings["maxIterations"], random_state=settings["seed"], class_weight=None)
        with warnings.catch_warnings():
            warnings.simplefilter("error", ConvergenceWarning)
            estimator.fit(matrix, labels, sample_weight=np.asarray([row["weight"] for row in rows], dtype=np.float64))
        heads[name] = {"labels": CONTRACT["heads"][name], "vocabulary": words, "weights": estimator.coef_[0].tolist(), "intercept": float(estimator.intercept_[0])}
        checks[name] = {"iterations": int(estimator.n_iter_[0]), "featureCount": len(words), "scores": estimator.decision_function(matrix).tolist()}
    model = {"contractVersion": CONTRACT["contractVersion"], "arm": "word", "heads": heads,
             "metadata": {"runId": RUN, "contractSha256": sha256(CONTRACT_PATH), "protocolSha256": sha256(PROTOCOL_PATH),
                          "cohortSha256": sha256(COHORT), "fitSettings": settings, "productionIntegrated": False}}
    scorer = SmsSemanticsModel(model)
    for name, rows in selected["training"].items():
        reference = checks[name].pop("scores")
        exported = [scorer.predict(sources[row["sourceIndex"]]["text"])["heads"][name]["score"] for row in rows]
        gap = max(abs(x - y) for x, y in zip(reference, exported))
        if gap > CONTRACT["scoreTolerance"] or any((x > 0) != (y > 0) for x, y in zip(reference, exported)):
            raise ValueError("Export differs from fitted decision function")
        checks[name]["maximumSklearnExportScoreGap"] = gap
    model["metadata"]["fitAudit"] = checks
    return model


def compare(old, new):
    result = {}
    for name, before in old["arms"]["word"]["heads"].items():
        after = new["word"]["heads"][name]
        if set(before["byExpression"]) != set(after["byExpression"]):
            raise ValueError("Validation expressions changed between experiments")
        changes = []
        for expression, previous in before["byExpression"].items():
            current = after["byExpression"][expression]
            if previous["recordId"] != current["recordId"] or previous["target"] != current["target"]:
                raise ValueError("Validation identity or truth changed")
            if previous["prediction"] != current["prediction"]:
                changes.append({"expression": expression, "recordId": current["recordId"], "target": current["target"],
                                "previousPrediction": previous["prediction"], "currentPrediction": current["prediction"]})
        result[name] = {"before": before["raw"], "after": after["raw"], "changedPredictions": changes}
    return result


def input_hashes(old, audit):
    hashes = {**old["inputSha256"], **audit["inputSha256"]}
    for path in (PROTOCOL_PATH, COHORT, base.REPORT, coverage.REPORT, base.BROWSER,
                 ROOT / "training/transactions/semantics_followup.py", ROOT / "tests/python/test_sms_semantics_followup.py"):
        hashes[path.relative_to(ROOT).as_posix()] = sha256(path)
    return hashes


def run(check=False):
    import numpy, scipy, sklearn
    selected, sources, old, audit = prepare()
    if check:
        if COHORT.read_bytes() != json_text(selected).encode("utf-8"):
            raise ValueError("Follow-up cohort missing/stale")
    else:
        if any(path.exists() for path in (ATTEMPT, REPORT, FAILURE, MODEL)):
            raise ValueError("Follow-up already attempted; use --check, never refit")
        write_immutable(COHORT, json_text(selected))
    hashes = input_hashes(old, audit)
    environment = {"python": platform.python_version(), "numpy": numpy.__version__, "scipy": scipy.__version__, "sklearn": sklearn.__version__}
    attempt = {"runId": RUN, "ownerApproval": PROTOCOL["ownerApproval"], "fitCallsAuthorized": 2, "inputSha256": hashes, "environment": environment}
    if check:
        if ATTEMPT.read_bytes() != json_text(attempt).encode("utf-8"):
            raise ValueError("Follow-up sources/cohort/environment changed")
        model = json.loads(MODEL.read_text(encoding="utf-8"))
    else:
        snapshot_report_inputs(RUN, hashes)
        write_immutable(ATTEMPT, json_text(attempt))
        model = fit(selected, sources)
        write_immutable(MODEL, json_text(model))
    metadata = model["metadata"]
    if metadata["runId"] != RUN or model["arm"] != "word" or metadata["contractSha256"] != sha256(CONTRACT_PATH) or metadata["protocolSha256"] != sha256(PROTOCOL_PATH) or metadata["cohortSha256"] != sha256(COHORT) or metadata["fitSettings"] != CONTRACT["fit"] or metadata["productionIntegrated"] is not False:
        raise ValueError("Model binding differs from approved follow-up")
    texts = [sources[row["sourceIndex"]]["text"] for fold in ("training", "validation") for row in selected[fold]["completion"]]
    texts += [row["text"] for row in json.loads(base.CONTROLS.read_text(encoding="utf-8"))["cases"]]
    parity = base.verify_parity([model], texts, base.BROWSER.read_text(encoding="utf-8"))
    # Only after fixed export parity, compute the previously exposed validation metrics.
    evaluated = base.evaluate([model], selected, sources)
    support = {}
    for name, rows in selected["training"].items():
        support[name] = {"rows": len(rows), "targets": dict(Counter(row["target"] for row in rows)),
                         "weightGroups": len({row["weightGroup"] for row in rows}), "totalWeight": math.fsum(row["weight"] for row in rows),
                         "originalRows": sum(row["sourceArtifact"] == DATASET.relative_to(ROOT).as_posix() for row in rows),
                         "authoredRows": sum(row["sourceArtifact"] == coverage.BATCH.relative_to(ROOT).as_posix() for row in rows)}
    report = {"runId": RUN, "scope": PROTOCOL["evaluationStatus"], "inputSha256": hashes, "environment": environment,
              "fitCalls": 2, "trainingSupport": support, "validationSupport": {name: len(rows) for name, rows in selected["validation"].items()},
              "exportParity": parity, "candidate": evaluated["word"], "comparisonToPriorWord": compare(old, evaluated),
              "unchangedStructuralBaseline": old["unchangedStructuralBaseline"],
              "outputSha256": {MODEL.relative_to(ROOT).as_posix(): sha256(MODEL)},
              "productionIntegrated": False, "canonicalAdmissionFlagsChanged": False, "reservedMerchantFinalInferred": False,
              "limits": ["Adaptive gap filling was informed by an exposed development failure; these scores cannot establish independent accuracy.",
                         "Only 18 weak validation representatives, four completed; authored messages are not verified bank formats or genuine received SMS.",
                         "Unknown ownership and uncertain settlement are not learned by these binary heads. No guard integration or promotion.",
                         "The structural baseline is copied unchanged from the hash-bound prior run, whose source/model inputs are verified unchanged.",
                         "The frozen 226-case active-engine check is separate; neither the candidate nor authored data replaces it."]}
    content = json_text(report)
    if check:
        if REPORT.read_bytes() != content.encode("utf-8"):
            raise ValueError("Saved follow-up differs; no automatic overwrite or refit")
    else:
        write_immutable(REPORT, content)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    try:
        report = run(args.check)
    except Exception as error:
        if not args.check and ATTEMPT.exists() and not REPORT.exists() and not FAILURE.exists():
            write_immutable(FAILURE, json_text({"runId": RUN, "error": str(error), "refitAllowed": False}))
        raise
    print(json_text({"runId": RUN, "trainingSupport": report["trainingSupport"], "exportParity": report["exportParity"],
                     "comparison": report["comparisonToPriorWord"], "productionIntegrated": False}))


if __name__ == "__main__":
    main()
