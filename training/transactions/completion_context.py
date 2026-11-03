"""One fixed completion fit; old direction and all earlier research remain frozen."""
import argparse
from collections import Counter
from copy import deepcopy
import json
import platform
import subprocess
import warnings

from src.python.research.sms_completion_context import CONTRACT, CONTRACT_PATH, SmsCompletionContextModel, features
from src.python.research.sms_semantics import CONTRACT as BASE, SmsSemanticsModel, normalize
from training.transactions import semantics_followup as previous
from training.corpus import coverage
from training.corpus.semantics import json_text
from training.corpus_io import ROOT, sha256, write_immutable, snapshot_report_inputs
from tools.node_runtime import node_executable

RUN = "sms_completion_context_v1"
PROTOCOL = ROOT / f"config/experiments/{RUN}.json"
BATCH = ROOT / "data/training/authored_sms_context_v1/scenarios.json"
MANUAL = ROOT / ".local-backups/sms_research_manual_v1/cases.json"
MODEL = ROOT / f"data/models/{RUN}_candidate.json"
BROWSER = ROOT / f"data/models/{RUN}_browser_runtime.js"
AREA = ROOT / "data/reports/transactions"
REPORT, ATTEMPT, FAILURE = (AREA / f"{RUN}{suffix}.json" for suffix in ("", "_attempt", "_failure"))
PROBE = ROOT / "tools/evaluation/probe_sms_completion_context.ts"


def node(arguments, payload=None):
    result = subprocess.run([node_executable(), str(PROBE), *arguments], input=None if payload is None else json_text(payload),
                            capture_output=True, text=True, encoding="utf-8", cwd=ROOT)
    if result.returncode:
        raise ValueError(result.stderr)
    return result.stdout


def expand_batch(document):
    if document.get("version") != "1.0.0" or document.get("trainingEligible") is not False or document.get("independentEvaluationEligible") is not False:
        raise ValueError("Authored provenance/admission flags changed")
    rows, groups = [], set()
    for group in document["groups"]:
        if group["id"] in groups or group["fold"] not in ("research_training", "authored_probe"):
            raise ValueError("Duplicate group or unsupported fold")
        groups.add(group["id"])
        for target in ("completed", "non_transaction"):
            if set(group[target]) != {"ar", "en"}:
                raise ValueError("Each contrast needs both languages")
            for language, text in group[target].items():
                if not isinstance(text, str) or not text.strip():
                    raise ValueError("Empty authored message")
                rows.append({"recordId": group["id"] + "-" + target + "-" + language,
                             "authoringGroupId": group["id"], "language": language, "text": text,
                             "target": target, "fold": group["fold"], "weight": 0.25,
                             "trainingEligible": False, "independentEvaluationEligible": False})
    if Counter(row["fold"] for row in rows) != {"research_training": 48, "authored_probe": 24}:
        raise ValueError("Frozen 12 training / 6 probe scenario groups changed")
    return rows


def prepare():
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    for relative, expected in protocol["frozenInputs"].items():
        if sha256(ROOT / relative) != expected:
            raise ValueError("Frozen context input changed: " + relative)
    selected, sources, _, _ = previous.prepare()
    old_report = json.loads(previous.REPORT.read_text(encoding="utf-8"))
    for relative, expected in {**old_report["inputSha256"], **old_report["outputSha256"]}.items():
        if sha256(ROOT / relative) != expected:
            raise ValueError("Frozen follow-up source changed: " + relative)
    rows = expand_batch(json.loads(BATCH.read_text(encoding="utf-8")))
    manual = json.loads(MANUAL.read_text(encoding="utf-8"))
    if len(manual["cases"]) != 24 or manual["trainingEligible"] is not False or manual["independentEvaluationEligible"] is not False:
        raise ValueError("Manual diagnostic source/flags changed")
    texts = [row["text"] for row in sources] + [row["text"] for row in manual["cases"]]
    for path in coverage.CONTROLS:
        texts.extend(coverage.contained_texts(json.loads(path.read_text(encoding="utf-8"))))
    businesses = [json.loads(line) for line in coverage.BUSINESSES.read_text(encoding="utf-8").splitlines() if line.strip()]
    forms = coverage.reservation_forms(businesses, json.loads(coverage.RESERVATION.read_text(encoding="utf-8"))["businessAssignments"],
                                       json.loads(coverage.FAMILIES.read_text(encoding="utf-8"))["families"])
    blocks = coverage.overlap_blocks(rows, texts, forms)
    if any(blocks.values()) or len({normalize(row["text"]) for row in rows}) != len(rows):
        raise ValueError("New contrast has a normalized/proxy/protected overlap; stop before fitting: " + str({k: v for k, v in blocks.items() if v}))
    training = [{**row, "text": sources[row["sourceIndex"]]["text"]} for row in selected["training"]["completion"]]
    training += [row for row in rows if row["fold"] == "research_training"]
    validation = [{**row, "text": sources[row["sourceIndex"]]["text"]} for row in selected["validation"]["completion"]]
    probe = [row for row in rows if row["fold"] == "authored_probe"]
    diagnostics = [{"recordId": row["id"], "text": row["text"], "target": row["expected"]["transactionStatus"]} for row in manual["cases"]]
    controls = json.loads(previous.base.CONTROLS.read_text(encoding="utf-8"))["cases"]
    return protocol, selected, sources, training, {"oldExposedValidation": validation, "authoredProbe": probe, "exposedManual": diagnostics}, controls, blocks


def vocabulary(texts):
    counts = Counter(feature for text in texts for feature in features(text))
    return sorted(feature for feature, count in counts.items() if count >= CONTRACT["minimumDocumentFrequency"])


def matrix(texts, words):
    import numpy as np
    from scipy.sparse import csr_matrix
    indices = {word: index for index, word in enumerate(words)}
    positions, offsets = [], [0]
    for text in texts:
        positions.extend(sorted(indices[x] for x in features(text) if x in indices))
        offsets.append(len(positions))
    return csr_matrix((np.ones(len(positions), dtype=np.float64), positions, offsets), shape=(len(texts), len(words)), dtype=np.float64)


def fit(training, old_model, hashes):
    import numpy as np
    from sklearn.exceptions import ConvergenceWarning
    from sklearn.linear_model import LogisticRegression
    settings = BASE["fit"]
    texts = [row["text"] for row in training]
    words = vocabulary(texts)
    x = matrix(texts, words)
    estimator = LogisticRegression(solver=settings["solver"], C=settings["C"], l1_ratio=settings["l1Ratio"], dual=settings["dual"],
                                   fit_intercept=settings["fitIntercept"], intercept_scaling=settings["interceptScaling"],
                                   tol=settings["tolerance"], max_iter=settings["maxIterations"], random_state=settings["seed"], class_weight=None)
    with warnings.catch_warnings():
        warnings.simplefilter("error", ConvergenceWarning)
        estimator.fit(x, [int(row["target"] == "completed") for row in training], sample_weight=np.asarray([row["weight"] for row in training], dtype=np.float64))
    model = {"kind": "completion_context", "contractVersion": CONTRACT["contractVersion"],
             "heads": {"completion": {"labels": BASE["heads"]["completion"], "vocabulary": words,
                                      "weights": estimator.coef_[0].tolist(), "intercept": float(estimator.intercept_[0])},
                       "direction": deepcopy(old_model["heads"]["direction"])},
             "metadata": {"runId": RUN, "directionReferenceSha256": sha256(previous.MODEL), "inputSha256": hashes,
                          "fitCalls": 1, "fitSettings": settings, "productionIntegrated": False}}
    scorer = SmsCompletionContextModel(model)
    expected = estimator.decision_function(x).tolist()
    actual = [scorer.predict(text)["heads"]["completion"]["score"] for text in texts]
    gap = max(abs(a - b) for a, b in zip(expected, actual))
    if gap > BASE["scoreTolerance"] or any((a > 0) != (b > 0) for a, b in zip(expected, actual)):
        raise ValueError("Context flat export differs from estimator")
    model["metadata"]["fitAudit"] = {"iterations": int(estimator.n_iter_[0]), "featureCount": len(words), "maximumSklearnExportScoreGap": gap}
    return model


def evaluate(rows, old, new):
    outputs = []
    for row in rows:
        outputs.append({"recordId": row["recordId"], "target": row["target"],
                        "baseline": old.predict(row["text"])["heads"]["completion"],
                        "candidate": new.predict(row["text"])["heads"]["completion"]})
    definite = [row for row in outputs if row["target"] in BASE["heads"]["completion"].values()]
    counts = {key: previous.base.confusion(definite, [row[key]["prediction"] for row in definite], "completed") for key in ("baseline", "candidate")}
    return {**counts, "uncertainNotBinaryScored": len(outputs) - len(definite), "rows": outputs}


def run(check=False):
    import numpy, scipy, sklearn
    if not check and any(path.exists() for path in (ATTEMPT, REPORT, FAILURE, MODEL, BROWSER)):
        raise ValueError("Context experiment already attempted; --check only, no refit")
    protocol, selected, sources, training, evaluations, controls, blocks = prepare()
    paths = [PROTOCOL, BATCH, MANUAL, previous.REPORT, previous.MODEL, CONTRACT_PATH, PROBE,
             ROOT / "training/transactions/completion_context.py", ROOT / "src/python/research/sms_completion_context.py",
             ROOT / "src/typescript/research/SmsCompletionContext.ts", ROOT / "tests/python/test_sms_completion_context.py"]
    hashes = {path.relative_to(ROOT).as_posix(): sha256(path) for path in paths}
    hashes.update(json.loads(previous.REPORT.read_text(encoding="utf-8"))["inputSha256"])
    environment = {"python": platform.python_version(), "numpy": numpy.__version__, "scipy": scipy.__version__, "sklearn": sklearn.__version__}
    attempt = {"runId": RUN, "ownerApproval": protocol["ownerApproval"], "fitCallsAuthorized": 1, "inputSha256": hashes, "environment": environment}
    old_model = json.loads(previous.MODEL.read_text(encoding="utf-8"))
    if check:
        if ATTEMPT.read_bytes() != json_text(attempt).encode("utf-8"):
            raise ValueError("Context experiment inputs/environment changed")
        model = json.loads(MODEL.read_text(encoding="utf-8"))
        if BROWSER.read_text(encoding="utf-8") != node(["--bundle"]):
            raise ValueError("Context browser source changed")
    else:
        snapshot_report_inputs(RUN, hashes)
        write_immutable(ATTEMPT, json_text(attempt))
        model = fit(training, old_model, hashes)
        write_immutable(MODEL, json_text(model))
        write_immutable(BROWSER, node(["--bundle"]))
    old, new = SmsSemanticsModel(old_model), SmsCompletionContextModel(model)
    if model["heads"]["direction"] != old_model["heads"]["direction"] or model["metadata"]["inputSha256"] != hashes or model["metadata"]["productionIntegrated"] is not False:
        raise ValueError("Frozen direction or model binding changed")
    texts = [row["text"] for row in training] + [row["text"] for rows in evaluations.values() for row in rows] + [row["text"] for row in controls]
    outputs = json.loads(node([], {"model": model, "texts": texts, "browserRuntime": BROWSER.read_text(encoding="utf-8")}))
    if any(len(outputs[key]) != len(texts) for key in ("typescript", "browser")):
        raise ValueError("Parity probe dropped messages")
    for i, text in enumerate(texts):
        expected = new.predict(text)
        if any(outputs[key][i] != expected for key in ("typescript", "browser")):
            raise ValueError("Context Python/TypeScript/browser parity failure")
        if expected["heads"]["direction"] != old.predict(text)["heads"]["direction"]:
            raise ValueError("Frozen direction output changed")
    directions = selected["validation"]["direction"]
    report = {"runId": RUN, "scope": protocol["evaluationStatus"], "inputSha256": hashes, "environment": environment,
              "trainingSupport": {"rows": len(training), "targets": dict(Counter(row["target"] for row in training)),
                                  "oldWeightGroups": 101, "newContrastGroups": 12, "totalWeight": sum(row["weight"] for row in training)},
              "fitCalls": 1, "fitAudit": model["metadata"]["fitAudit"], "overlapBlockers": blocks,
              "evaluations": {name: evaluate(rows, old, new) for name, rows in evaluations.items()},
              "directionReference": {"modelSha256": sha256(previous.MODEL), "headIdentical": True, "allParityOutputsIdentical": True,
                                     "oldValidationCount": len(directions), "oldValidationCorrect": sum(new.predict(sources[row["sourceIndex"]]["text"])["heads"]["direction"]["prediction"] == row["target"] for row in directions)},
              "exportParity": {"texts": len(texts), "exactPythonTypescriptBrowser": True, "maximumScoreGap": 0, "browserSourceSha256": outputs["sourceSha256"]},
              "outputSha256": {path.relative_to(ROOT).as_posix(): sha256(path) for path in (MODEL, BROWSER)},
              "productionIntegrated": False, "canonicalAdmissionFlagsChanged": False, "reservedMerchantFinalInferred": False,
              "limits": protocol["limits"]}
    content = json_text(report)
    if check:
        if REPORT.read_bytes() != content.encode("utf-8"):
            raise ValueError("Context report changed; no overwrite or refit")
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
    print(json_text({"fitCalls": report["fitCalls"], "fitAudit": report["fitAudit"], "exportParity": report["exportParity"],
                     "evaluations": {name: {k: value[k] for k in ("baseline", "candidate", "uncertainNotBinaryScored")} for name, value in report["evaluations"].items()},
                     "directionReference": report["directionReference"]}))


if __name__ == "__main__":
    main()
