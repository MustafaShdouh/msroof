"""Assemble a proposed matched-data comparison; no fitting or inference."""
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path

from training.transactions.completion_adaptation import prepare, ROOT
from training.corpus import factorization_pilot as pilot
from training.corpus import factorization_full as full
from training.corpus import factorization_uncertainty as uncertainty

DEV_REVIEWS = ROOT / "data/annotations/sms_factorization_eval_v1/development_reviews.tsv"


def compose_status(context, event):
    contract=pilot.read(pilot.CONTRACT)
    if context not in contract["contextLabels"] or event not in contract["eventStateLabels"]:
        raise ValueError("Unrecognized factorized prediction")
    if context=="unknown": return "uncertain"
    if context!="financial_notice": return "non_transaction"
    if event=="completed": return "completed"
    if event=="unknown": return "uncertain"
    return "non_transaction"


def prepare_view():
    _, original, evaluations, reserved=prepare()
    base,_,base_outputs=full.build()
    extra,_,extra_outputs=uncertainty.build()
    for path,content in {**base_outputs,**extra_outputs}.items():
        if path.read_bytes()!=content.encode("utf-8"): raise ValueError("Reviewed annotation source changed")
    sources={r["recordId"]:r for r in original}
    for relative in uncertainty.SOURCES:
        for row in [json.loads(l) for l in (ROOT/relative).read_text(encoding="utf-8").splitlines()]:
            if row["recordId"] not in sources:
                sources[row["recordId"]]=dict(recordId=row["recordId"],text=row["text"],group=row["authoringGroupId"])
    annotations=base+extra
    selected=[a for a in annotations if a["reviewState"]=="reviewed_weak"]
    sizes=Counter(a["authoringGroupId"] for a in selected)
    rows=[]
    for annotation in selected:
        source=sources[annotation["recordId"]]
        if pilot.hashed(source["text"])!=annotation["sourceTextSha256"]:
            raise ValueError("Source text hash differs")
        context,event=annotation["messageContext"]["value"],annotation["describedEventState"]["value"]
        target=annotation["originalCompletionTarget"]
        if compose_status(context,event)!=target:
            raise ValueError("Research composition disagrees with frozen weak target: "+annotation["recordId"])
        rows.append(dict(recordId=source["recordId"],text=source["text"],group=annotation["authoringGroupId"],
            weight=1/sizes[annotation["authoringGroupId"]],status=target,context=context,event=event))
    forbidden={r["recordId"] for group in evaluations.values() for r in group}|{r["recordId"] for r in reserved}
    if {r["recordId"] for r in rows}&forbidden: raise ValueError("Diagnostic record in proposed training")
    if len(rows)!=1177 or len(sizes)!=129: raise ValueError("View coverage changed")
    weights=defaultdict(float)
    for r in rows: weights[r["group"]]+=r["weight"]
    if any(abs(w-1)>1e-12 for w in weights.values()): raise ValueError("Group weight differs")
    encoded=json.dumps(rows,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode("utf-8")
    summary=dict(trainingRows=1177,weightGroups=129,totalWeight=129,heldRowsExcluded=17,
        targets=dict(Counter(r["status"] for r in rows)),contextCounts=dict(Counter(r["context"] for r in rows)),eventCounts=dict(Counter(r["event"] for r in rows)),
        trainingViewSha256=hashlib.sha256(encoded).hexdigest(),heldRecordIds=[a["recordId"] for a in annotations if a["reviewState"]=="hold"],
        rows=[{k:v for k,v in r.items() if k!="text"} | {"textSha256":pilot.hashed(r["text"])} for r in rows],
        trainingEligible=False,independentEvaluationEligible=False,modelFittingAllowed=False)
    return rows,summary,evaluations,reserved


def development_reviews():
    _,_,evaluations,_=prepare()
    rows=evaluations["scopeDevelopment"]
    contexts=dict(F="financial_notice",P="personal_conversation",Q="question_or_request",I="instruction_or_example",U="unknown")
    events=dict(C="completed",N="not_completed",U="unknown")
    reviews={}
    for line in DEV_REVIEWS.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.startswith("#"): continue
        rid,c,e,cq,eq,note=line.split("|",5)
        if rid in reviews: raise ValueError("Duplicate development annotation")
        reviews[rid]=dict(recordId=rid,context=contexts[c],eventState=events[e],contextQuote=cq,eventQuote=eq,note=note)
    if set(reviews)!={r["recordId"] for r in rows}: raise ValueError("Development review does not cover exact existing fold")
    result=[]
    contract=pilot.read(pilot.CONTRACT)
    for row in rows:
        binding={**row,"group":row["authoringGroupId"]}
        annotation=pilot.validate_review(binding,reviews[row["recordId"]],contract)
        annotation.update(sourceFold="development_diagnostic_only",trainingWeightAssigned=False)
        if compose_status(annotation["messageContext"]["value"],annotation["describedEventState"]["value"])!=row["target"]:
            raise ValueError("Development composition differs from unchanged original target")
        result.append(annotation)
    return result
