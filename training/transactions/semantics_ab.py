"""One approved weak-SMS word/character trial; immutable outputs, no promotion."""
import argparse
from collections import Counter, defaultdict
import json
import math
import platform
import re
import subprocess
import warnings

from src.python.research.sms_semantics import CONTRACT, CONTRACT_PATH, SmsSemanticsModel, features
from training.corpus.propagation import build as proposal_build, PLAN, PROPOSAL
from training.corpus.validation_semantics import build as review_build, MANIFEST as VALIDATION_MANIFEST, REVIEWED
from training.corpus.semantics import json_text, digest
from training.corpus_io import ROOT, DATASET, sha256, write_immutable, snapshot_report_inputs
from tools.node_runtime import node_executable

RUN = "sms_semantics_ab_v1"
AREA = ROOT / "data/reports/transactions"
REPORT = AREA / (RUN + ".json")
COHORT = AREA / (RUN + "_cohort.json")
ATTEMPT = AREA / (RUN + "_attempt.json")
FAILURE = AREA / (RUN + "_failure.json")
MODELS = {arm: ROOT / f"data/models/{RUN}_{arm}_candidate.json" for arm in CONTRACT["arms"]}
BROWSER = ROOT / f"data/models/{RUN}_browser_runtime.js"
CONTROLS = ROOT / "tests/fixtures/sms_semantics_feature_cases.json"
PROBE = ROOT / "tools/evaluation/probe_sms_semantics.ts"
FIELDS = {"completion": "transactionStatus", "direction": "direction"}


def checked_outputs(outputs):
    for path, content in outputs.items():
        if not path.exists() or path.read_bytes() != content.encode("utf-8"):
            raise ValueError("Bound research input missing/stale: " + path.name)


def cohorts():
    if sha256(PLAN) != CONTRACT["cohorts"]["proposalManifestSha256"] or sha256(VALIDATION_MANIFEST) != CONTRACT["cohorts"]["validationManifestSha256"]:
        raise ValueError("Research cohort manifests differ from approved bindings")
    proposals, _, _, outputs = proposal_build()
    checked_outputs(outputs)
    reviewed, _, outputs = review_build()
    checked_outputs(outputs)
    training, validation = {}, {}
    for name, field in FIELDS.items():
        training[name] = [{"recordId": row["recordId"], "sourceIndex": row["sourceIndex"],
                           "textSha256": row["textSha256"], "sourceExpressionId": row["sourceExpressionId"],
                           "leakageGroupId": row["leakageGroupId"], "target": row["candidateTargets"][field]["value"],
                           "weight": row["candidateTargets"][field]["proposedTrainingWeight"]}
                          for row in proposals if row["outcome"] == "candidate" and field in row["candidateTargets"]]
        validation[name] = [{"recordId": row["recordId"], "sourceIndex": row["sourceIndex"],
                             "textSha256": row["textSha256"], "sourceExpressionId": row["sourceExpressionId"],
                             "leakageGroupId": row["leakageGroupId"], "target": row["annotations"][field]["value"]}
                            for row in reviewed if not row["admissionBlockers"] and field in row["annotations"]
                            and row["annotations"][field]["value"] in CONTRACT["heads"][name].values()
                            and (name != "direction" or row["annotations"]["transactionStatus"]["value"] == "completed")]
        if len(training[name]) != CONTRACT["cohorts"]["training" + name.title()] or len(validation[name]) != CONTRACT["cohorts"]["validation" + name.title()]:
            raise ValueError("Approved research cohort count changed")
        if {row["leakageGroupId"] for row in training[name]} & {row["leakageGroupId"] for row in validation[name]}:
            raise ValueError("Research cohort crosses a frozen group")
        if {row["target"] for row in training[name]} != set(CONTRACT["heads"][name].values()):
            raise ValueError("Required training classes absent")
        weights = defaultdict(float)
        for row in training[name]:
            weights[row["sourceExpressionId"]] += row["weight"]
        if any(abs(weight - 1) > 1e-12 for weight in weights.values()):
            raise ValueError("Expression weight differs from one")
    return {"runId": RUN, "scope": "Owner-approved isolated weak research selection; canonical flags unchanged",
            "training": training, "validation": validation, "productionAdmissionGranted": False}


def vocabulary(texts, arm):
    counts = Counter()
    for text in texts:
        counts.update(features(text, arm))
    return sorted(feature for feature, count in counts.items() if count >= CONTRACT["fit"]["minimumDocumentFrequency"])


def matrix(texts, arm, words):
    import numpy as np
    from scipy.sparse import csr_matrix
    lookup = {word: index for index, word in enumerate(words)}
    indices, indptr = [], [0]
    for text in texts:
        indices.extend(sorted(lookup[word] for word in features(text, arm) if word in lookup))
        indptr.append(len(indices))
    if max(len(indices), len(words), len(texts)) >= 2 ** 31:
        raise ValueError("liblinear sparse capacity exceeded")
    return csr_matrix((np.ones(len(indices), dtype=np.float64), np.asarray(indices, dtype=np.int32), np.asarray(indptr, dtype=np.int32)),
                      shape=(len(texts), len(words)))


def fit_arm(arm, cohort, sources):
    import numpy as np
    from sklearn.exceptions import ConvergenceWarning
    from sklearn.linear_model import LogisticRegression
    settings, heads, audits = CONTRACT["fit"], {}, {}
    for name, rows in cohort["training"].items():
        texts = [sources[row["sourceIndex"]]["text"] for row in rows]
        words = vocabulary(texts, arm)
        if not words:
            raise ValueError("No supported training vocabulary")
        x = matrix(texts, arm, words)
        labels = [int(row["target"] == CONTRACT["heads"][name]["positive"]) for row in rows]
        solver = LogisticRegression(solver=settings["solver"], C=settings["C"], l1_ratio=settings["l1Ratio"],
                                    dual=settings["dual"], fit_intercept=settings["fitIntercept"],
                                    intercept_scaling=settings["interceptScaling"], tol=settings["tolerance"],
                                    max_iter=settings["maxIterations"], random_state=settings["seed"], class_weight=None)
        with warnings.catch_warnings():
            warnings.simplefilter("error", ConvergenceWarning)
            solver.fit(x, labels, sample_weight=np.asarray([row["weight"] for row in rows], dtype=np.float64))
        heads[name] = {"labels": CONTRACT["heads"][name], "vocabulary": words,
                       "weights": solver.coef_[0].tolist(), "intercept": float(solver.intercept_[0])}
        audits[name] = {"iterations": int(solver.n_iter_[0]), "featureCount": len(words),
                        "sklearnTrainingScores": solver.decision_function(x).tolist()}
    model = {"contractVersion": CONTRACT["contractVersion"], "arm": arm, "heads": heads,
             "metadata": {"runId": RUN, "contractSha256": sha256(CONTRACT_PATH), "cohortSha256": sha256(COHORT),
                          "fitSettings": settings, "productionIntegrated": False}}
    scorer = SmsSemanticsModel(model)
    for name, rows in cohort["training"].items():
        reference = audits[name].pop("sklearnTrainingScores")
        exported = [scorer.predict(sources[row["sourceIndex"]]["text"])["heads"][name]["score"] for row in rows]
        gap = max(abs(x - y) for x, y in zip(reference, exported))
        if gap > CONTRACT["scoreTolerance"] or any((x > 0) != (y > 0) for x, y in zip(reference, exported)):
            raise ValueError("Export differs from fitted training decision function")
        audits[name]["maximumSklearnExportScoreGap"] = gap
    model["metadata"]["fitAudit"] = audits
    return model


def node(arguments, payload=None):
    process = subprocess.run([node_executable(), str(PROBE), *arguments],
                             input=None if payload is None else json_text(payload), capture_output=True,
                             text=True, encoding="utf-8", cwd=ROOT)
    if process.returncode:
        raise ValueError(process.stderr.strip())
    return process.stdout


def verify_parity(models, texts, browser):
    other = json.loads(node([], {"models": models, "texts": texts, "browserRuntime": browser}))
    if len(other["rows"]) != len(models):
        raise ValueError("Runtime probe dropped a model")
    maximum = 0.0
    for model, outputs in zip(models, other["rows"]):
        if outputs["arm"] != model["arm"] or any(len(outputs[key]) != len(texts) for key in ("typescript", "browser")):
            raise ValueError("Runtime probe changed arm/record order")
        scorer = SmsSemanticsModel(model)
        for index, text in enumerate(texts):
            reference = scorer.predict(text)
            for key in ("typescript", "browser"):
                actual = outputs[key][index]
                if reference["normalized"] != actual["normalized"] or reference["features"] != actual["features"] or set(actual["heads"]) != set(reference["heads"]):
                    raise ValueError("Feature/preprocessing parity failed")
                for name, expected in reference["heads"].items():
                    received = actual["heads"][name]
                    gap = abs(expected["score"] - received["score"])
                    maximum = max(maximum, gap)
                    if not math.isfinite(received["score"]) or gap > CONTRACT["scoreTolerance"] or expected["activeIndices"] != received["activeIndices"] or expected["prediction"] != received["prediction"]:
                        raise ValueError("Exported vector/score/head parity failed")
    return {"textsPerArm": len(texts), "arms": len(models), "headsPerArm": 2,
            "typescriptAndBrowser": True, "maximumScoreGap": maximum,
            "browserSourceSha256": other["sourceSha256"], "scope": "Actual stripped browser-compatible source in Node VM; no interactive UI or Hermes claim"}


def confusion(rows, predicted, positive):
    counts = Counter()
    for row, value in zip(rows, predicted):
        actual = row["target"] == positive
        counts[(actual, value == positive)] += 1
    return {"count": len(rows), "truePositive": counts[True, True], "trueNegative": counts[False, False],
            "falsePositive": counts[False, True], "falseNegative": counts[True, False],
            "correct": counts[True, True] + counts[False, False]}


def script_slice(text):
    arabic, english = bool(re.search(r"[\u0621-\u064a]", text)), bool(re.search(r"[A-Za-z]", text))
    return "mixed" if arabic and english else "arabic" if arabic else "english" if english else "other"


def evaluate(models, cohort, sources):
    outputs = {}
    for model in models:
        scorer, heads = SmsSemanticsModel(model), {}
        for name, rows in cohort["validation"].items():
            predictions = [scorer.predict(sources[row["sourceIndex"]]["text"])["heads"][name] for row in rows]
            labels = [row["prediction"] for row in predictions]
            positive = CONTRACT["heads"][name]["positive"]
            slices = {}
            for script in ("arabic", "english", "mixed", "arabicContaining"):
                indices = [i for i, row in enumerate(rows) if (bool(re.search(r"[\u0621-\u064a]", sources[row["sourceIndex"]]["text"])) if script == "arabicContaining" else script_slice(sources[row["sourceIndex"]]["text"]) == script)]
                slices[script] = confusion([rows[i] for i in indices], [labels[i] for i in indices], positive)
            by_expression = {row["sourceExpressionId"]: {"recordId": row["recordId"], "target": row["target"],
                            "prediction": prediction["prediction"], "score": prediction["score"],
                            "script": script_slice(sources[row["sourceIndex"]]["text"])} for row, prediction in zip(rows, predictions)}
            heads[name] = {"raw": confusion(rows, labels, positive), "scriptSlices": slices, "byExpression": by_expression}
        rows = cohort["validation"]["direction"]
        joint = sum(scorer.predict(sources[row["sourceIndex"]]["text"])["heads"]["completion"]["prediction"] == "completed" and
                    scorer.predict(sources[row["sourceIndex"]]["text"])["heads"]["direction"]["prediction"] == row["target"] for row in rows)
        outputs[model["arm"]] = {"heads": heads, "jointCompletedAndCorrectDirection": {"correct": joint, "count": len(rows)},
                                 "candidateBytes": len(json_text(model).encode("utf-8")), "fitAudit": model["metadata"]["fitAudit"]}
    return outputs


def structural_baseline(cohort, sources, reviewed):
    from src.python.engine import MasroofEngine
    engine = MasroofEngine()
    truth = {row["recordId"]: row["annotations"] for row in reviewed}
    results, counts = [], Counter()
    for row in cohort["validation"]["completion"]:
        actual = engine.predict_detailed({"text": sources[row["sourceIndex"]]["text"]})
        expected = truth[row["recordId"]]
        checked = [key for key in ("transactionStatus", "trackingDecision", "amount", "currency", "currencyResolution", "direction", "transferRelationship", "merchantOrCounterparty", "expenseCategory", "categoryStatus") if key in expected]
        mismatches = [key for key in checked if actual[key] != expected[key]["value"]]
        counts[actual["trackingDecision"]] += 1
        results.append({"recordId": row["recordId"], "assessment": actual, "mismatchFields": mismatches})
    return {"scope": "Unchanged active detailed assessment, reported separately; candidates are not wired into its guards",
            "trackingCounts": dict(counts), "fullyMatchingWeakReviews": sum(not row["mismatchFields"] for row in results), "rows": results}


def input_hashes():
    paths = [CONTRACT_PATH, PLAN, PROPOSAL, VALIDATION_MANIFEST, REVIEWED, DATASET, COHORT, CONTROLS, PROBE,
             ROOT / "src/python/research/sms_semantics.py", ROOT / "src/typescript/research/SmsSemantics.ts",
             ROOT / "src/typescript/Preprocessing.ts", ROOT / "training/transactions/semantics_ab.py",
             ROOT / "tests/python/test_sms_semantics_model.py", ROOT / "tools/node_runtime.py", ROOT / "training/corpus_io.py",
             ROOT / "data/models/masroof_model.json"]
    paths += sorted((ROOT / "src/python").glob("*.py"))
    paths += [ROOT / ("config/contracts/" + name + ".json") for name in ("transaction_evidence", "entity_text", "service_notice", "authorization_request", "transaction_behavior")]
    return {path.relative_to(ROOT).as_posix(): sha256(path) for path in paths}


def run(check=False):
    import numpy, scipy, sklearn
    selected = cohorts()
    content = json_text(selected)
    if check:
        if not COHORT.exists() or COHORT.read_bytes() != content.encode("utf-8"):
            raise ValueError("Frozen research selection missing/stale")
    else:
        if any(path.exists() for path in (ATTEMPT, REPORT, FAILURE, BROWSER, *MODELS.values())):
            raise ValueError("This single trial was already attempted; use --check, never refit")
        write_immutable(COHORT, content)
    hashes = input_hashes()
    environment = {"python": platform.python_version(), "numpy": numpy.__version__, "scipy": scipy.__version__, "sklearn": sklearn.__version__}
    attempt = {"runId": RUN, "ownerApproved": "2026-10-27 sure: isolated fixed weak-SMS A/B", "inputSha256": hashes,
               "environment": environment, "fitCallsAuthorized": 4, "scope": "Immutable start ledger prevents repeated fitting"}
    sources = json.loads(DATASET.read_text(encoding="utf-8"))
    if check:
        if ATTEMPT.read_bytes() != json_text(attempt).encode("utf-8"):
            raise ValueError("Training input/source/environment ledger changed")
        models = [json.loads(MODELS[arm].read_text(encoding="utf-8")) for arm in CONTRACT["arms"]]
        browser = BROWSER.read_text(encoding="utf-8")
    else:
        snapshot_report_inputs(RUN, hashes)
        write_immutable(ATTEMPT, json_text(attempt))
        models = []
        for arm in CONTRACT["arms"]:
            model = fit_arm(arm, selected, sources)
            models.append(model)
            write_immutable(MODELS[arm], json_text(model))
        browser = node(['--bundle'])
        write_immutable(BROWSER, browser)
    for model in models:
        if model["metadata"]["contractSha256"] != sha256(CONTRACT_PATH) or model["metadata"]["cohortSha256"] != sha256(COHORT) or model["metadata"]["fitSettings"] != CONTRACT["fit"] or model["metadata"]["productionIntegrated"] is not False:
            raise ValueError("Candidate is not bound to the approved research settings")
    # Freeze model artifacts and prove vectors/scores/decisions before computing validation metrics.
    indices = [row["sourceIndex"] for row in selected["training"]["completion"]] + [row["sourceIndex"] for row in selected["validation"]["completion"]]
    texts = [sources[index]["text"] for index in indices] + [row["text"] for row in json.loads(CONTROLS.read_text(encoding="utf-8"))["cases"]]
    parity = verify_parity(models, texts, browser)
    for name in CONTRACT["heads"]:
        a, b = [model["heads"][name]["vocabulary"] for model in models]
        if a != [word for word in b if word.startswith("w|")]:
            raise ValueError("A/B word vocabularies differ")
    support = {name: {"rows": len(rows), "targetCounts": dict(Counter(row["target"] for row in rows)),
                       "expressionCounts": dict(Counter({row["sourceExpressionId"]: row["target"] for row in rows}.values()))}
               for name, rows in selected["training"].items()}
    report = {"runId": RUN, "scope": "Single exposed synthetic weak-label development comparison; not independent accuracy",
              "inputSha256": hashes, "environment": environment, "fitCalls": 4, "trainingSupport": support,
              "validationSupport": {name: len(rows) for name, rows in selected["validation"].items()}, "exportParity": parity,
              "arms": evaluate(models, selected, sources),
              "unchangedStructuralBaseline": structural_baseline(selected, sources, review_build()[0]),
              "outputSha256": {path.relative_to(ROOT).as_posix(): sha256(path) for path in (*MODELS.values(), BROWSER)},
              "productionIntegrated": False, "canonicalAdmissionFlagsChanged": False, "reservedMerchantFinalInferred": False,
              "limits": ["Only 18 weak validation representatives, four completed; no precise real-world accuracy/recall or calibrated certainty claim.",
                         "Unknown ownership remains a recording review even when completion/direction are known.",
                         "Raw learned heads are separate from the unchanged structural baseline; no new guarded runtime is evaluated.",
                         "Script/expression slices are exposed synthetic development evidence, not an independent test or promotion decision.",
                         "The 226-case frozen active-engine check is run separately; candidates do not replace that caller."]}
    result = json_text(report)
    if check:
        if REPORT.read_bytes() != result.encode("utf-8"):
            raise ValueError("Saved trial report/model bytes differ; no automatic refit or overwrite")
    else:
        write_immutable(REPORT, result)
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
    print(json_text({"runId": RUN, "exportParity": report["exportParity"],
                     "raw": {arm: {name: head["raw"] for name, head in value["heads"].items()} for arm, value in report["arms"].items()},
                     "productionIntegrated": False}))


if __name__ == "__main__":
    main()
