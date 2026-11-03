"""Review existing training-designated uncertainty separately from the frozen cohort."""
import argparse
from collections import Counter
import json
from pathlib import Path

from training.corpus import factorization_pilot as pilot
from training.corpus import factorization_full as full
from training.transactions.completion_encoder import read as source_read

REVIEWS = pilot.DIRECTORY / "uncertainty_reviews.tsv"
ANNOTATIONS = pilot.DIRECTORY / "uncertainty_annotations.jsonl"
REPORT = pilot.ROOT / "data/reports/transactions/sms_factorization_v1_uncertainty.json"
SOURCES = ("data/training/authored_sms_v1/messages.jsonl","data/training/authored_sms_scope_v1/messages.jsonl")


def build():
    original, full_report, outputs = full.build()
    for path, content in outputs.items():
        if path.read_bytes()!=content.encode("utf-8"): raise ValueError("Frozen full-cohort annotations changed")
    old = source_read(SOURCES[0])
    scope = source_read(SOURCES[1])
    selected = [dict(recordId=r["recordId"],text=r["text"],group=r["authoringGroupId"],target="uncertain",sourceArtifact=SOURCES[0]) for r in old
        if r["fold"]=="proposed_training" and r["annotations"]["transactionStatus"]["value"]=="uncertain"]
    selected += [dict(recordId=r["recordId"],text=r["text"],group=r["authoringGroupId"],target=r["target"],sourceArtifact=SOURCES[1]) for r in scope
        if r["fold"]=="proposed_training" and r["target"]=="uncertain"]
    if len(selected)!=36 or {r["recordId"] for r in selected}&{r["recordId"] for r in original}:
        raise ValueError("Uncertainty slice is not separate and exactly 36 training-designated rows")
    contexts=dict(F="financial_notice",K="known_other",P="personal_conversation",Q="question_or_request",I="instruction_or_example",U="unknown")
    events=dict(C="completed",N="not_completed",Z="no_event",U="unknown")
    decisions={}
    for line in REVIEWS.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.startswith("#"): continue
        fields=line.split("|")
        if len(fields) not in (6,7): raise ValueError("Invalid manual review row")
        rid,context,event,cq,eq,note=fields[:6]
        if rid in decisions: raise ValueError("Duplicate review")
        value=dict(recordId=rid,context=contexts[context],eventState=events[event],contextQuote=cq,eventQuote=eq,note=note)
        if len(fields)==7: value.update(reviewState="hold",holdReasons=[fields[6]])
        decisions[rid]=value
    if set(decisions)!={r["recordId"] for r in selected}: raise ValueError("Manual coverage differs from source slice")
    contract=pilot.read(pilot.CONTRACT)
    annotations=[]
    for row in selected:
        annotation=pilot.validate_review(row,decisions[row["recordId"]],contract)
        annotation.update(sourceFold="proposed_training_uncertainty_appendix",sourceArtifact=row["sourceArtifact"],selectedInFrozen1158=False,
            trainingWeightAssigned=False)
        annotations.append(annotation)
    combined=original+annotations
    nonheld=[r for r in combined if r["reviewState"]=="reviewed_weak"]
    context_counts=Counter(r["messageContext"]["value"] for r in nonheld)
    report=dict(runId="sms_factorization_v1_uncertainty",appendixRows=36,appendixReviewStates=dict(Counter(r["reviewState"] for r in annotations)),
        appendixContexts=dict(Counter(r["messageContext"]["value"] for r in annotations if r["reviewState"]=="reviewed_weak")),
        appendixEvents=dict(Counter(r["describedEventState"]["value"] for r in annotations if r["reviewState"]=="reviewed_weak")),
        appendixHeldIds=[r["recordId"] for r in annotations if r["reviewState"]=="hold"],
        combinedAnnotatedRows=len(combined),combinedNonheldRows=len(nonheld),combinedHeldRows=len(combined)-len(nonheld),
        combinedGroupCount=len({r["authoringGroupId"] for r in combined}),
        combinedNonheldContexts=dict(context_counts),combinedNonheldEvents=dict(Counter(r["describedEventState"]["value"] for r in nonheld)),
        unknownContextSourceGroups=sorted({r["authoringGroupId"] for r in nonheld if r["messageContext"]["value"]=="unknown"}),
        missingObservedContextClasses=[k for k in contract["contextLabels"] if not context_counts[k]],
        original1158CohortChanged=False,originalCompletionLabelsChanged=False,modelFitted=False,modelInference=False,reservedInferred=False,
        newTrainingViewAuthorized=False,weightsAssigned=False,
        inputSha256={p.relative_to(pilot.ROOT).as_posix():pilot.digest(p) for p in (REVIEWS,pilot.CONTRACT,full.QUEUE,full.LOG,full.ANNOTATIONS,full.AUDIT,
            *(pilot.ROOT/s for s in SOURCES),Path(__file__),Path(full.__file__),Path(pilot.__file__))},
        limits=["The 36 rows were already proposed-training source messages with uncertain overall status; no diagnostic/reserved message was selected.",
                "This appendix does not silently enlarge the frozen 1158-row view or assign it binary targets or training weights.",
                "Unknown context is reviewed when the source explicitly withholds its frame, unlike a held annotator interpretation of an ambiguous cost fragment.",
                "Pension-forward excerpts supply no underlying credit clause; no_event describes visible text, not an invented outcome of an unseen message.",
                "Debit/cancellation conflicts remain held because event focus/chronology cannot be resolved.",
                "Observed class support is small, same-assistant synthetic evidence, not independent reliability. Future protocol must define weights, class set, hold masks and gates.",
                "Adding uncertainty rows to existing groups requires recomputing group-normalized weights in a new view; never append them with the old per-row weights."])
    outputs={ANNOTATIONS:"".join(json.dumps(r,ensure_ascii=False,separators=(",",":"))+"\n" for r in annotations),REPORT:json.dumps(report,ensure_ascii=False,sort_keys=True,indent=2)+"\n"}
    return annotations,report,outputs


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check",action="store_true")
    args=parser.parse_args()
    _,report,outputs=build()
    for path,content in outputs.items():
        if path.exists():
            if path.read_bytes()!=content.encode("utf-8"): raise ValueError("Frozen uncertainty review changed")
        elif args.check: raise ValueError("Missing uncertainty review")
        else:
            with path.open("x",encoding="utf-8",newline="\n") as handle: handle.write(content)
    print(json.dumps({k:report[k] for k in ("appendixReviewStates","combinedAnnotatedRows","combinedNonheldRows","combinedHeldRows","combinedNonheldContexts","missingObservedContextClasses")}))


if __name__=="__main__": main()
