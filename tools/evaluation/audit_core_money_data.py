"""R2 data-only inventory: never fit, predict, relabel, or admit records."""
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path

from training.corpus_io import ROOT, sha256, write_immutable, load_development_split
from training.transactions.factorization_protocol import prepare_view
from src.python.research.sms_semantics import normalize

PREFIX=ROOT/"data/reports/behavior/core_money_r2"


def duplicate_inventory(rows,normalizer=lambda text:text,fields=("status","context","event")):
    groups=defaultdict(list)
    for row in rows:groups[normalizer(row["text"])].append(row)
    duplicate=[]
    for text,items in groups.items():
        if len(items)<2:continue
        targets={f:sorted({str(r.get(f)) for r in items}) for f in fields}
        duplicate.append(dict(inputSha256=hashlib.sha256(text.encode()).hexdigest(),recordIds=[r["recordId"] for r in items],
            sourceGroups=sorted({r["group"] for r in items}),targets=targets,
            conflictingFields=[f for f,values in targets.items() if len(values)>1]))
    return dict(uniqueInputs=len(groups),duplicateGroups=len(duplicate),rowsInDuplicateGroups=sum(len(r["recordIds"]) for r in duplicate),
        conflictingGroups=sum(bool(r["conflictingFields"]) for r in duplicate),
        crossSourceGroupDuplicates=sum(len(r["sourceGroups"])>1 for r in duplicate),groups=duplicate)


def spans_valid(text,spans):
    return all(type(s.get("start")) is int and type(s.get("end")) is int and
               0<=s["start"]<s["end"]<=len(text) and text[s["start"]:s["end"]]==s.get("text") for s in spans)


def build():
    used=set()
    def read(relative):
        path=ROOT/relative;used.add(path)
        raw=path.read_text(encoding="utf-8")
        return [json.loads(l) for l in raw.splitlines() if l.strip()] if path.suffix==".jsonl" else json.loads(raw)
    rows,summary,cohorts,_=prepare_view()
    parent=read("config/experiments/sms_factorization_comparison_v2.json")
    used.update(ROOT/p for p in parent["frozenInputs"])
    raw=duplicate_inventory(rows);normalized=duplicate_inventory(rows,normalize)
    blocked=set()
    for inventory in (raw,normalized):
        for group in inventory["groups"]:
            if group["conflictingFields"]:blocked.update(group["recordIds"])
    # Cross-family duplicate relations must remain connected in any future split.
    parent_groups={r["group"]:r["group"] for r in rows}
    def find(x):
        while parent_groups[x]!=x:x=parent_groups[x]
        return x
    for group in normalized["groups"]:
        names=group["sourceGroups"]
        for other in names[1:]:parent_groups[find(other)]=find(names[0])
    components=defaultdict(list)
    for group in parent_groups:components[find(group)].append(group)
    connected=[sorted(v) for v in components.values() if len(v)>1]
    overlaps=[]
    index=defaultdict(list)
    for row in rows:index[normalize(row["text"])].append(row["recordId"])
    for name,items in cohorts.items():
        for row in items:
            matches=index.get(normalize(row["text"]),[])
            if matches:overlaps.append(dict(cohort=name,recordId=row["recordId"],trainingRecordIds=matches))

    legacy=read("data/training/sanitized_v1/transactions.json")
    split=read("data/training/splits/transaction_direction_sanitized_v1.json")
    load_development_split(legacy)
    legacy_inventory=dict(rows=len(legacy),labelOrigins=dict(Counter(r.get("labelOrigin","unspecified") for r in legacy)),
        origins=dict(Counter(r.get("origin","unspecified") for r in legacy)),
        directionClaims=dict(Counter(str(r.get("type")) for r in legacy)),
        amountClaims=sum(r.get("expected_amount") is not None for r in legacy),
        amountSourceSpans=0,directionSourceSpans=0,
        interpretation="Generator/legacy claims, not span-reviewed primary amount/direction truth. All rows synthetic development; neither type nor realistic provider metadata authenticates a message.")
    assignments={i:fold for fold in ("train","validation") for i in split[fold+"Indices"]}
    oldforms=defaultdict(list)
    for i,row in enumerate(legacy):oldforms[normalize(row["text"])].append(i)
    cross=[ids for ids in oldforms.values() if len({assignments[i] for i in ids})>1]
    legacy_inventory["normalizedCrossFoldGroups"]=len(cross)
    legacy_inventory["normalizedCrossFoldRows"]=sum(map(len,cross))

    bio=read("data/training/sanitized_v2/bio_training_data.json")
    biosplit=read("data/training/splits/bio_sanitized_v2.json")
    assert biosplit["datasetSha256"]==sha256(ROOT/"data/training/sanitized_v2/bio_training_data.json")
    partitions=[set(biosplit[f+"Ids"]) for f in ("train","validation","quarantined")]
    assert not any(a&b for i,a in enumerate(partitions) for b in partitions[i+1:])
    assert set.union(*partitions)=={r["id"] for r in bio["examples"]}
    bio_rows=[];span_errors=[]
    for r in bio["examples"]:
        entities=r["entities"]
        if not spans_valid(r["text"],entities):span_errors.append(r["id"])
        fold=next(f for f in ("train","validation","quarantined") if r["id"] in biosplit[f+"Ids"])
        bio_rows.append(dict(recordId=r["id"],fold=fold,textSha256=hashlib.sha256(r["text"].encode()).hexdigest(),
            amountSpans=sum(s["label"]=="AMT" for s in entities),currencySpans=sum(s["label"]=="CURR" for s in entities),
            directionClaim=r.get("expectedFields",{}).get("type"),directionClaimOrigin="inherited synthetic fixture field, not a reviewed direction evidence span",
            annotationComplete=r["annotationComplete"],unresolved=r["unresolved"],humanReviewed=r["humanReviewed"],
            reviewCandidate=fold=="train" and r["annotationComplete"] and not r["unresolved"] and r["id"] not in span_errors))
    authored=read("data/training/authored_sms_v1/messages.jsonl")
    authored_rows=[]
    for row in authored:
        assert row["textSha256"]==hashlib.sha256(row["text"].encode()).hexdigest()
        claims={};issues=[]
        for field in ("amount","currency","direction"):
            label=row["annotations"].get(field)
            if label is None:claims[field]=None;continue
            evidence=label.get("evidence",[])
            spans=[s for s in evidence if s.get("kind")=="text_span"]
            valid=spans_valid(row["text"],spans)
            if not valid:issues.append(field)
            claims[field]=dict(value=label.get("value"),state=label["state"],origin=label.get("origin"),sourceSpans=len(spans),validSourceSpans=valid)
        amount=claims["amount"];direction=claims["direction"]
        completed=row["annotations"]["transactionStatus"]["value"]=="completed"
        authored_rows.append(dict(recordId=row["recordId"],group=row["authoringGroupId"],fold=row["fold"],claims=claims,invalidFields=issues,
            amountReviewCandidate=completed and row["fold"]=="proposed_training" and bool(amount and type(amount["value"]) in (int,float) and amount["value"]>0 and amount["sourceSpans"] and amount["validSourceSpans"]),
            directionReviewCandidate=completed and row["fold"]=="proposed_training" and bool(direction and direction["value"] in ("incoming","outgoing") and direction["sourceSpans"] and direction["validSourceSpans"]),
            reviewCandidate=row["fold"]=="proposed_training" and not issues,
            trainingEligible=row["trainingEligible"],independentEvaluationEligible=row["independentEvaluationEligible"]))
    propagation=read("data/annotations/sms_semantics_v1/propagation_proposal_v1.jsonl")
    proposed_directions=[r for r in propagation if "direction" in r.get("candidateTargets",{})]
    provenance=read("data/reports/real_sms_provenance_audit.json")
    scope=read("data/training/authored_sms_scope_v1/messages.jsonl")
    context=read("data/training/authored_sms_context_v1/scenarios.json")
    fixture=read("tests/fixtures/core_money_v1.json")
    manifest=dict(schemaVersion="1.0.0",purpose="Review selection and split constraints only; not an admitted training set",
        trainingEligible=False,modelFittingAllowed=False,independentEvaluationEligible=False,
        statusReviewCandidates=[dict(recordId=r["recordId"],group=r["group"],textSha256=hashlib.sha256(r["text"].encode()).hexdigest(),blockedByConflict=r["recordId"] in blocked) for r in rows],
        conflictBlockedIds=sorted(blocked),existingHeldIds=summary["heldRecordIds"],
        connectedSourceGroups=connected,bioReviewCandidates=[r["recordId"] for r in bio_rows if r["reviewCandidate"]],
        authoredReviewCandidates=[r["recordId"] for r in authored_rows if r["reviewCandidate"]],
        authoredAmountReviewCandidates=[r["recordId"] for r in authored_rows if r["amountReviewCandidate"]],
        authoredDirectionReviewCandidates=[r["recordId"] for r in authored_rows if r["directionReviewCandidate"]],
        excludedDevelopmentFixtureIds=[r["id"] for r in fixture["cases"]],
        admissionRules=["Only existing proposed-training/train memberships may enter review; validation/quarantine/reserved never become training by this audit.",
                        "Block any conflicting normalized input; keep each source/translation/duplicate-connected component in one future fold.",
                        "Do not infer amount or direction truth from a status label, BIO merchant span, model score or default currency.",
                        "Future fitting requires task-specific source review, provenance, content preflight, protected-identity checks and explicit protocol approval."])
    report=dict(schemaVersion="1.0.0",trainingRows=len(rows),trainingViewSha256=summary["trainingViewSha256"],rawDuplicates=raw,normalizedDuplicates=normalized,
        duplicateConnectedComponents=connected,diagnosticOverlaps=overlaps,legacyInventory=legacy_inventory,
        bioInventory=dict(rows=len(bio_rows),foldCounts=dict(Counter(r["fold"] for r in bio_rows)),invalidSpanRecordIds=span_errors,
            origin=bio["metadata"]["labelOrigin"],records=bio_rows),
        authoredInventory=dict(rows=len(authored_rows),records=authored_rows),
        propagationInventory=dict(rows=len(propagation),proposedDirectionRows=len(proposed_directions),amountTargets=sum("amount" in r.get("candidateTargets",{}) for r in propagation),
            interpretation="Guarded weak propagation proposals; no automatic admission or independently reviewed direction ground truth."),
        contextAndScopeInventory=dict(contextGroups=len(context["groups"]),scopeRows=len(scope),
            interpretation="Status/context/event evidence does not supply general amount/direction annotations. Keep original family/fold memberships; do not parse numbers into gold labels."),
        developmentFixtureInventory=dict(records=len(fixture["cases"]),pendingPolicies=len(fixture["pendingPolicyCases"]),trainingEligible=False,independentEvaluationEligible=False),
        originalSourceInventory={k:provenance[k] for k in ("seedBlockCount","sourceAuthentication","independentEvaluationEligibleCount","trainingAdmittedCount","confirmedGeminiParentEdges","unresolvedOtherRawBlockCount")},
        modelTraining=False,newInference=False,labelsChanged=0,reservedInferred=False,
        inputs={p.relative_to(ROOT).as_posix():sha256(p) for p in sorted(used|{Path(__file__)})},
        limitations=["Duplicate/conflict checks operate on exact text and existing number-masking normalization, not semantic equivalence.",
            "Evidence-span integrity is syntactic; it does not certify that a value is the correct event amount or direction.",
            "Amount/direction inventories overlap in ancestry; counts must not be pooled as independent receipts.",
            "Assistant-weak/synthetic labels and exposed originals are not independent real-world evaluation.",
            "No record is admitted, reweighted, relabeled, moved between folds or deduplicated by this audit."])
    return report,manifest


if __name__=="__main__":
    report,manifest=build()
    for suffix,data in (("_audit.json",report),("_review_manifest.json",manifest)):
        write_immutable(Path(str(PREFIX)+suffix),json.dumps(data,ensure_ascii=False,indent=2)+"\n")
    print(json.dumps(dict(rows=report["trainingRows"],rawConflicts=report["rawDuplicates"]["conflictingGroups"],normalizedConflicts=report["normalizedDuplicates"]["conflictingGroups"],normalizedDuplicateGroups=report["normalizedDuplicates"]["duplicateGroups"],connectedGroups=report["duplicateConnectedComponents"],bio=report["bioInventory"]["foldCounts"],authored=report["authoredInventory"]["rows"])))
