"""Record-bound full source review; exact lossless packets, no model inference."""
import argparse
from collections import defaultdict
import difflib
import json
from pathlib import Path
import re

from training.corpus import factorization_pilot as pilot
from training.corpus import factorization_supplement as supplement
from training.transactions.completion_adaptation import prepare, ROOT

DIRECTORY = pilot.DIRECTORY
QUEUE = DIRECTORY / "remaining_queue.json"
LOG = DIRECTORY / "source_review_log.jsonl"
ANNOTATIONS = DIRECTORY / "full_annotations.jsonl"
AUDIT = ROOT / "data/reports/transactions/sms_factorization_v1_full.json"


def queue():
    _, training, _, _ = prepare()
    previous = [json.loads(line) for path in (pilot.ANNOTATIONS, supplement.ANNOTATIONS) for line in path.read_text(encoding="utf-8").splitlines()]
    seen = {r["recordId"] for r in previous}
    groups = defaultdict(list)
    for row in training:
        if row["recordId"] not in seen:
            groups[row["group"]].append(row)
    packets = []
    for group, rows in sorted(groups.items(), key=lambda item: (not item[0].startswith("literal-"), item[0])):
        # Every record appears once; never infer a family label from its representative.
        for start in range(0, len(rows), 50):
            packets.append(dict(packetId=f"source-{len(packets)+1:03d}", group=group, rows=rows[start:start+50]))
    result = dict(version="1.0.0", trainingRows=1158, previousRows=36, remainingRows=1122, packets=packets,
        previousSha256={p.relative_to(ROOT).as_posix():pilot.digest(p) for p in (pilot.ANNOTATIONS, supplement.ANNOTATIONS)},
        trainingViewSha256=pilot.read(pilot.PROTOCOL)["cohort"]["trainingViewSha256"],
        modelPredictionsUsed=False, modelFittingAllowed=False)
    if sum(len(p["rows"]) for p in packets) != 1122:
        raise ValueError("Unexpected remaining review coverage")
    return result


def display(packet):
    """Print base plus token-offset replacements that round-trip every raw string."""
    base = packet["rows"][0]["text"]
    tokens = re.findall(r"\S+\s*|\s+", base)
    print(json.dumps(dict(packetId=packet["packetId"], group=packet["group"], rows=len(packet["rows"]), baseTokens=list(enumerate(tokens))), ensure_ascii=False))
    shapes = defaultdict(list)
    for row in packet["rows"]:
        other = re.findall(r"\S+\s*|\s+", row["text"])
        edits = [(a,b,"".join(other[c:d])) for tag,a,b,c,d in difflib.SequenceMatcher(None,tokens,other,autojunk=False).get_opcodes() if tag!="equal"]
        rebuilt = tokens[:]
        for a,b,value in reversed(edits): rebuilt[a:b] = [value]
        if "".join(rebuilt) != row["text"]:
            raise ValueError("Review view is not lossless")
        shapes[tuple((a,b) for a,b,_ in edits)].append([row["recordId"],*[v for _,_,v in edits]])
    for shape, rows in shapes.items():
        print(json.dumps(dict(replaceTokenRanges=shape, records=rows), ensure_ascii=False, separators=(",",":")))


def record_review(packet_id, context, event_state, context_quote, event_quote, note, hold=None):
    if AUDIT.exists(): raise ValueError("Full review is frozen")
    frozen = pilot.read(QUEUE)
    if frozen != queue(): raise ValueError("Source review queue changed")
    packet = next(p for p in frozen["packets"] if p["packetId"] == packet_id)
    entries = [] if not LOG.exists() else [json.loads(l) for l in LOG.read_text(encoding="utf-8").splitlines()]
    if any(e["packetId"] == packet_id for e in entries): raise ValueError("Packet already reviewed")
    contract = pilot.read(pilot.CONTRACT)
    reviewed = []
    for row in packet["rows"]:
        # Mechanical evidence binding after explicit manual source review, not label inference.
        review = dict(recordId=row["recordId"], context=context, eventState=event_state,
            contextQuote=row["text"] if context_quote == "<whole_message>" else context_quote,
            eventQuote=row["text"] if event_quote == "<whole_message>" else event_quote, note=note)
        if hold: review.update(reviewState="hold", holdReasons=[hold])
        annotation = pilot.validate_review(row, review, contract)
        reviewed.append(annotation)
    entry = dict(packetId=packet_id, packetSha256=pilot.hashed(json.dumps(packet,ensure_ascii=False,sort_keys=True,separators=(",",":"))),
        reviewMethod="Assistant inspected every record via exact base/replacement view; explicit row-list assignment only; no defaults for unseen rows or automatic family propagation",
        annotations=reviewed)
    with LOG.open("a",encoding="utf-8",newline="\n") as handle: handle.write(json.dumps(entry,ensure_ascii=False,separators=(",",":"))+"\n")
    print(packet_id,len(reviewed),context,event_state)


def record_individual_reviews(specification):
    """Bind explicitly written per-record decisions; no semantic defaults or inference."""
    if AUDIT.exists(): raise ValueError("Full review is frozen")
    frozen = pilot.read(QUEUE)
    if frozen != queue(): raise ValueError("Source review queue changed")
    existing = [] if not LOG.exists() else [json.loads(l) for l in LOG.read_text(encoding="utf-8").splitlines()]
    done = {r["packetId"] for r in existing}
    contract = pilot.read(pilot.CONTRACT)
    decisions = {}
    context_codes = dict(F="financial_notice",K="known_other",P="personal_conversation",Q="question_or_request",I="instruction_or_example",U="unknown")
    event_codes = dict(C="completed",N="not_completed",Z="no_event",U="unknown")
    for line in specification.splitlines():
        if not line.strip() or line.startswith("#"): continue
        record_id, context, event, cq, eq, note = line.split("|",5)
        if record_id in decisions: raise ValueError("Duplicate explicit decision")
        decisions[record_id] = dict(recordId=record_id,context=context_codes[context],eventState=event_codes[event],contextQuote=cq,eventQuote=eq,note=note)
    covered = set()
    new_entries = []
    for packet in frozen["packets"]:
        ids = {r["recordId"] for r in packet["rows"]}
        if not ids & decisions.keys(): continue
        if packet["packetId"] in done or not ids <= decisions.keys(): raise ValueError("Partial/already reviewed packet")
        annotations=[]
        for row in packet["rows"]:
            review = dict(decisions[row["recordId"]])
            for field in ("contextQuote","eventQuote"):
                if review[field] == "<whole_message>": review[field] = row["text"]
            annotations.append(pilot.validate_review(row,review,contract))
        covered.update(ids)
        new_entries.append(dict(packetId=packet["packetId"],packetSha256=pilot.hashed(json.dumps(packet,ensure_ascii=False,sort_keys=True,separators=(",",":"))),
            reviewMethod="Explicit individual source-text decisions, separately reviewed in each language; no counterpart/family propagation",annotations=annotations))
    if covered != decisions.keys(): raise ValueError("Unknown or unassigned record decision")
    with LOG.open("a",encoding="utf-8",newline="\n") as handle:
        for entry in new_entries: handle.write(json.dumps(entry,ensure_ascii=False,separators=(",",":"))+"\n")
    print("Recorded",len(covered),"individual decisions")


def build():
    """Reconcile every explicit decision; never assign a missing record by default."""
    from collections import Counter
    _, training, evaluations, reserved = prepare()
    source = {r["recordId"]:r for r in training}
    frozen = pilot.read(QUEUE)
    if frozen != queue(): raise ValueError("Source queue differs")
    earlier, _, old_outputs = pilot.build()
    added, _, supplement_outputs = supplement.build()
    for path, content in {**old_outputs, **supplement_outputs}.items():
        if path.read_bytes()!=content.encode("utf-8"): raise ValueError("Earlier annotation artifact changed")
    initial = earlier+added
    packets = {p["packetId"]:p for p in frozen["packets"]}
    entries = [json.loads(line) for line in LOG.read_text(encoding="utf-8").splitlines() if line.strip()]
    if len(entries)!=len(packets) or len({e["packetId"] for e in entries})!=len(packets):
        raise ValueError("Every packet requires exactly one explicit review")
    reviewed = list(initial)
    for entry in entries:
        packet = packets[entry["packetId"]]
        if entry["packetSha256"]!=pilot.hashed(json.dumps(packet,ensure_ascii=False,sort_keys=True,separators=(",",":"))):
            raise ValueError("Reviewed source packet changed")
        if [r["recordId"] for r in entry["annotations"]]!=[r["recordId"] for r in packet["rows"]]:
            raise ValueError("Partial/unbound source record review")
        reviewed.extend(entry["annotations"])
    if len(reviewed)!=1158 or len({r["recordId"] for r in reviewed})!=1158 or {r["recordId"] for r in reviewed}!=source.keys():
        raise ValueError("Missing, duplicate or nontraining record annotations")
    contract = pilot.read(pilot.CONTRACT)
    by_id = {r["recordId"]:r for r in reviewed}
    forbidden = {r["recordId"] for group in evaluations.values() for r in group} | {r["recordId"] for r in reserved}
    if source.keys() & forbidden: raise ValueError("Diagnostic record in training annotation view")
    for annotation in reviewed:
        row = source[annotation["recordId"]]
        if annotation["sourceTextSha256"]!=pilot.hashed(row["text"]) or annotation["originalCompletionTarget"]!=row["target"] or annotation["authoringGroupId"]!=row["group"]:
            raise ValueError("Source/legacy target binding changed")
        if annotation["reviewState"] not in contract["reviewStates"] or bool(annotation["holdReasons"])!=(annotation["reviewState"]=="hold"):
            raise ValueError("Hold disposition invalid")
        if annotation["reviewer"]!="assistant" or any(annotation[k] is not False for k in ("trainingEligible","independentEvaluationEligible","modelFittingAllowed")):
            raise ValueError("Weak annotation admission boundary changed")
        for field, vocabulary in (("messageContext",contract["contextLabels"]),("describedEventState",contract["eventStateLabels"])):
            value=annotation[field]
            if value["value"] not in vocabulary or value["state"]!="weak" or not value["evidence"]:
                raise ValueError("Missing weak field/evidence")
            for evidence in value["evidence"]:
                if pilot.span(row["text"],evidence["text"])!=evidence:
                    raise ValueError("Raw source span changed")
    ordered = [by_id[row["recordId"]] for row in training]
    nonheld = [r for r in ordered if r["reviewState"]=="reviewed_weak"]
    held = [r for r in ordered if r["reviewState"]=="hold"]
    groups=defaultdict(list)
    for row in ordered: groups[row["authoringGroupId"]].append(row)
    context_counts=Counter(r["messageContext"]["value"] for r in nonheld)
    event_counts=Counter(r["describedEventState"]["value"] for r in nonheld)
    report=dict(runId="sms_factorization_v1_full",trainingRecords=1158,trainingGroups=129,annotatedRecords=len(ordered),unreviewedRecords=0,
        reviewedWeakRecords=len(nonheld),heldRecords=len(held),heldRecordIds=[r["recordId"] for r in held],
        groupsAllNonheld=sum(all(r["reviewState"]=="reviewed_weak" for r in g) for g in groups.values()),
        groupsWithHolds=[name for name,g in groups.items() if any(r["reviewState"]=="hold" for r in g)],
        nonheldContextCounts=dict(context_counts),nonheldEventCounts=dict(event_counts),
        nonheldOriginalCompletionCounts=dict(Counter(r["originalCompletionTarget"] for r in nonheld)),
        nonheldGroupWeight=sum(row["weight"] for row in training if by_id[row["recordId"]]["reviewState"]=="reviewed_weak"),
        nonheldLanguages=dict(Counter("ar" if re.search(r"[\u0621-\u064a]",source[r["recordId"]]["text"]) else "en" for r in nonheld)),
        absentNonheldContextClasses=[k for k in contract["contextLabels"] if not context_counts[k]],
        absentNonheldEventClasses=[k for k in contract["eventStateLabels"] if not event_counts[k]],
        completionDescribedInNontransaction=sum(r["describedEventState"]["value"]=="completed" and r["originalCompletionTarget"]=="non_transaction" for r in nonheld),
        sourcePackets=len(packets),losslessSourceView="Base whitespace-preserving tokens plus every record's raw replacements; round-trip checked. Individual IDs and source hashes explicitly bound; no unseen-row/family defaults.",
        prior36AnnotationsPreserved=True,canonicalLabelsChanged=0,modelInference=False,modelFitted=False,reservedInferred=False,
        unknownContextClassTrainable=False,trainingReady=False,
        inputSha256={p.relative_to(ROOT).as_posix():pilot.digest(p) for p in (QUEUE,LOG,pilot.CONTRACT,pilot.ANNOTATIONS,supplement.ANNOTATIONS,pilot.AUDIT,supplement.REPORT,Path(__file__),Path(pilot.__file__),Path(supplement.__file__),pilot.PROTOCOL)},
        limits=["Complete review of the selected 1158-row research cohort, not all repository data or independent received SMS.",
                "All labels same-assistant weak; coverage does not demonstrate model accuracy or release readiness.",
                "15 ambiguous cost-fragment holds retain original labels and remain excluded. No unheld unknown-context training examples.",
                "A future fit protocol must specify supported class set, unknown/hold masks, weighting, reference gates and resource budget before fitting."])
    outputs={ANNOTATIONS:"".join(json.dumps(r,ensure_ascii=False,separators=(",",":"))+"\n" for r in ordered),
        AUDIT:json.dumps(report,ensure_ascii=False,sort_keys=True,indent=2)+"\n"}
    return ordered,report,outputs


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--show",nargs="*")
    parser.add_argument("--finalize",action="store_true")
    parser.add_argument("--check",action="store_true")
    args=parser.parse_args()
    value=queue()
    if QUEUE.exists():
        if pilot.read(QUEUE)!=value: raise ValueError("Frozen queue differs")
    else:
        with QUEUE.open("x",encoding="utf-8") as handle: json.dump(value,handle,ensure_ascii=False,indent=2);handle.write("\n")
    if args.finalize or args.check:
        _,report,outputs=build()
        for path,content in outputs.items():
            if path.exists():
                if path.read_bytes()!=content.encode("utf-8"): raise ValueError("Frozen full review changed")
            elif args.check: raise ValueError("Missing full review output")
            else:
                with path.open("x",encoding="utf-8",newline="\n") as handle: handle.write(content)
        print(json.dumps({k:report[k] for k in ("annotatedRecords","unreviewedRecords","reviewedWeakRecords","heldRecords","nonheldContextCounts","nonheldEventCounts","nonheldOriginalCompletionCounts","nonheldGroupWeight")}))
    elif args.show:
        for packet in value["packets"]:
            if packet["packetId"] in args.show: display(packet)
    else:
        for packet in value["packets"]: print(packet["packetId"],packet["group"],len(packet["rows"]))


if __name__=="__main__": main()
