"""Fixed matched-data comparison; two training arms, research-only evaluation."""
from collections import Counter
from fractions import Fraction
import hashlib
import importlib.metadata
import json
from pathlib import Path
import time

from training.transactions import factorization_protocol as view
from training.transactions import completion_adaptation as old
from training.transactions import completion_encoder as encoder
from src.python.research.sms_semantics import normalize

ROOT=view.ROOT
RUN="sms_auxiliary_status_v1"
PROTOCOL=ROOT/"config/experiments"/(RUN+".json")
CACHE=ROOT/".local-backups"/RUN
AREA=ROOT/"data/reports/transactions"
MASTER,REPORT,FAILURE=(AREA/(RUN+s+".json") for s in ("_attempt","","_failure"))
REFERENCES=("word","word_sequences","frozen_encoder","binary_adapted")
MODELS=("direct_status","factorized",*REFERENCES)
LABELS=("completed","non_transaction","uncertain")


def write_new(path,data):
    with path.open("x",encoding="utf-8",newline="\n") as f:
        json.dump(data,f,ensure_ascii=False,indent=2); f.write("\n")


def protocol():
    p=old.read(PROTOCOL)
    if p["trainingRunsAuthorized"]!=1 or not p["ownerApproval"]:
        raise ValueError("Explicit one-run approval required")
    for relative,expected in p["frozenInputs"].items():
        if encoder.digest(ROOT/relative)!=expected: raise ValueError("Frozen input changed: "+relative)
    rows,summary,evaluations,reserved=view.prepare_view()
    if summary!=old.read(ROOT/p["cohort"]["path"]): raise ValueError("Cohort manifest differs")
    if summary["trainingViewSha256"]!=p["cohort"]["trainingViewSha256"]: raise ValueError("View hash differs")
    from training.evaluation.content_preflight import preflight
    preflight(rows,[dict(r,cohort=name) for name,rs in evaluations.items() for r in rs],old.read(ROOT/p["evaluation"]["contract"]))
    p["arms"]=[dict(id="direct_status",headParameters=5005,trainableParameters=3553933,**{k+"Classes":v for k,v in p["heads"].items()})]
    return p,rows,evaluations,reserved


def binding():
    return dict(protocolSha256=encoder.digest(PROTOCOL),producerSha256=encoder.digest(Path(__file__)),
        viewProducerSha256=encoder.digest(Path(view.__file__)),environment={n:importlib.metadata.version(n) for n in ("torch","transformers","numpy","safetensors")})


def journal(model,cohort,rows):
    with (CACHE/"inference_journal.jsonl").open("a",encoding="utf-8",newline="\n") as f:
        f.write(json.dumps(dict(model=model,cohort=cohort,intendedRecordIds=[r["recordId"] for r in rows]))+"\n")


class Arm:
    def __init__(self,p,arm):
        import torch
        from transformers import AutoModel,AutoTokenizer
        self.torch=torch
        self.name=arm
        self.spec=next(a for a in p["arms"] if a["id"]==arm)
        self.classes={field:self.spec[field+"Classes"] for field in ("status","context","event") if field+"Classes" in self.spec}
        self.tokenizer=AutoTokenizer.from_pretrained(old.MODEL_DIR,local_files_only=True,trust_remote_code=False)
        self.backbone=AutoModel.from_pretrained(old.MODEL_DIR,local_files_only=True,trust_remote_code=False,dtype=torch.float32).cpu().eval()
        self.heads={field:torch.nn.Linear(384,len(classes)).cpu().eval() for field,classes in self.classes.items()}
        with torch.no_grad():
            for head in self.heads.values(): head.weight.zero_(); head.bias.zero_()
        for name,parameter in self.backbone.named_parameters(): parameter.requires_grad_(old.selected(name))
        self.encoder_parameters=[p for p in self.backbone.parameters() if p.requires_grad]
        self.head_parameters=[p for head in self.heads.values() for p in head.parameters()]
        if sum(x.numel() for x in self.encoder_parameters)!=3548928 or sum(x.numel() for x in self.head_parameters)!=self.spec["headParameters"]:
            raise ValueError("Trainable parameter selection differs")
        self.alphas={field:torch.tensor([float(Fraction(p["training"]["classReweighting"]["heads"][field]["factorRationals"][label])) for label in classes],dtype=torch.float32) for field,classes in self.classes.items()}

    def vectors(self,rows):
        tokens=self.tokenizer([normalize(r["text"]) for r in rows],padding=True,truncation=False,return_tensors="pt")
        if tokens["input_ids"].shape[1]>128: raise ValueError("No truncation: token overflow")
        hidden=self.backbone(**tokens).last_hidden_state
        mask=tokens["attention_mask"].unsqueeze(-1).expand(hidden.size()).float()
        return (hidden*mask).sum(1)/mask.sum(1).clamp(min=1e-9)

    def logits(self,rows):
        vectors=self.vectors(rows)
        return {field:head(vectors) for field,head in self.heads.items()}

    def predict(self,rows,cohort):
        result=[]
        with self.torch.inference_mode():
            for start in range(0,len(rows),16):
                batch=rows[start:start+16]
                journal(self.name,cohort,batch)
                logits=self.logits(batch)
                if any(not self.torch.isfinite(x).all() for x in logits.values()): raise ValueError("Nonfinite inference")
                for j in range(len(batch)):
                    labels={field:self.classes[field][int(values[j].argmax())] for field,values in logits.items()}
                    status=labels["status"] if self.name=="direct_status" else view.compose_status(labels["context"],labels["event"])
                    result.append(dict(status=status,labels=labels,logits={field:x[j].tolist() for field,x in logits.items()}))
        return result

    def delta(self):
        tensors={"backbone."+name:p.detach().contiguous() for name,p in self.backbone.named_parameters() if old.selected(name)}
        for field,head in self.heads.items():
            tensors.update({"head."+field+"."+name:p.detach().contiguous() for name,p in head.named_parameters()})
        return tensors

    def restore(self,path):
        from safetensors.torch import load_file
        tensors=load_file(str(path))
        if set(tensors)!=set(self.delta()): raise ValueError("Delta tensor set differs")
        with self.torch.no_grad():
            for name,param in self.backbone.named_parameters():
                if old.selected(name): param.copy_(tensors["backbone."+name])
            for field,head in self.heads.items():
                for name,param in head.named_parameters(): param.copy_(tensors["head."+field+"."+name])


def setup(p):
    import os,random,numpy,torch
    os.environ.update(HF_HUB_OFFLINE="1",TRANSFORMERS_OFFLINE="1",TOKENIZERS_PARALLELISM="false")
    random.seed(p["training"]["seed"]); numpy.random.seed(p["training"]["seed"]); torch.manual_seed(p["training"]["seed"])
    torch.set_num_threads(2); torch.use_deterministic_algorithms(True)
    if encoder.digest(old.MODEL_DIR/"model.safetensors")!=p["architecture"]["baseSafetensorsSha256"]: raise ValueError("Base weights differ")
    for name,entry in old.read(encoder.CACHE/"preflight.json")["assets"].items():
        if encoder.digest(old.MODEL_DIR/name)!=entry["sha256"]: raise ValueError("Tokenizer asset differs")


def row_losses(arm,logits,batch):
    torch=arm.torch
    values={}
    for field,classes in arm.classes.items():
        labels=torch.tensor([classes.index(r[field]) for r in batch],dtype=torch.long)
        values[field]=torch.nn.functional.cross_entropy(logits[field],labels,weight=arm.alphas[field],reduction="none")
    from training.transactions.auxiliary_status_protocol import combine_losses
    return combine_losses(values)


def train(name):
    import torch
    from safetensors.torch import save_file,load_file
    p,rows,evaluations,reserved=protocol()
    setup(p)
    path=CACHE/name
    path.mkdir(exist_ok=True)
    attempt=path/"attempt.json"
    if attempt.exists() or (path/"final.safetensors").exists(): raise ValueError("Arm already attempted; no retry")
    if old.read(MASTER)["binding"]!=binding(): raise ValueError("Experiment start binding differs")
    arm=Arm(p,name)
    lengths=[len(arm.tokenizer(normalize(r["text"]),truncation=False)["input_ids"]) for r in rows+[r for group in evaluations.values() for r in group]+reserved]
    if max(lengths)>128: raise ValueError("Token overflow")
    initial=old.tensor_hashes(arm.backbone)
    generator=torch.Generator(device="cpu").manual_seed(p["training"]["seed"])
    orders=[torch.randperm(len(rows),generator=generator).tolist() for _ in range(3)]
    if name=="direct_status":
        reference=old.read(ROOT/".local-backups/sms_factorization_comparison_v2/direct_status/attempt.json")
        if reference["trainingRecordIds"]!=[r["recordId"] for r in rows]: raise ValueError("Training IDs differ")
        if reference["initialEncoderHashes"]!=initial or reference["epochOrders"]!=orders: raise ValueError("Matched initial state/order differs")
    if any(torch.count_nonzero(x) for x in arm.head_parameters): raise ValueError("Heads not zero initialized")
    settings=p["training"]
    optimizer=torch.optim.AdamW([dict(params=arm.encoder_parameters,lr=settings["encoderLearningRate"]),dict(params=arm.head_parameters,lr=settings["headLearningRate"])],
        betas=tuple(settings["betas"]),eps=settings["epsilon"],weight_decay=settings["weightDecay"],foreach=False,fused=False,amsgrad=False)
    if {id(x) for g in optimizer.param_groups for x in g["params"]}!={id(x) for x in arm.encoder_parameters+arm.head_parameters}: raise ValueError("Optimizer parameter mismatch")
    write_new(attempt,dict(arm=name,binding=binding(),initialEncoderHashes=initial,epochOrders=orders,
        trainingRecordIds=[r["recordId"] for r in rows],classes=arm.classes,zeroHeads=True,maximumTokenizerLength=max(lengths),started=time.monotonic()))
    losses=[]; steps=0
    for epoch,order in enumerate(orders):
        weighted_sum=0.0
        for start in range(0,len(rows),8):
            batch=[rows[i] for i in order[start:start+8]]
            optimizer.zero_grad(set_to_none=True)
            item_loss=row_losses(arm,arm.logits(batch),batch)
            weight=torch.tensor([r["weight"] for r in batch],dtype=torch.float32)
            weighted=(item_loss*weight).sum()
            loss=weighted*(len(rows)/(129*len(batch)))
            if not torch.isfinite(loss): raise ValueError("Nonfinite loss")
            loss.backward()
            params=arm.encoder_parameters+arm.head_parameters
            if any(x.grad is None or not torch.isfinite(x.grad).all() for x in params): raise ValueError("Invalid trainable gradient")
            if any(x.grad is not None for n,x in arm.backbone.named_parameters() if not old.selected(n)): raise ValueError("Frozen gradient")
            torch.nn.utils.clip_grad_norm_(params,1.0,error_if_nonfinite=True)
            optimizer.step()
            if any(not torch.isfinite(x).all() for x in params): raise ValueError("Nonfinite weights")
            weighted_sum+=float(weighted.detach()); steps+=1
        losses.append(weighted_sum/129)
        print(json.dumps(dict(arm=name,epoch=epoch+1,steps=steps,trainingLoss=losses[-1])),flush=True)
    if steps!=444: raise ValueError("Incomplete prescribed run")
    final_hashes=old.tensor_hashes(arm.backbone)
    if any(final_hashes[n]!=sha for n,sha in initial.items() if not old.selected(n)): raise ValueError("Frozen tensors changed")
    checkpoint=path/"final.safetensors"
    save_file(arm.delta(),str(checkpoint),metadata=dict(arm=name,baseSha256=p["architecture"]["baseSafetensorsSha256"]))
    sentinels=rows[:8]
    expected=arm.predict(sentinels,"training_sentinels")
    import gc
    del optimizer,arm
    gc.collect()
    restored=Arm(p,name); restored.restore(checkpoint)
    if restored.predict(sentinels,"training_sentinels_reload")!=expected: raise ValueError("Reload logits differ")
    write_new(path/"result.json",dict(arm=name,binding=binding(),optimizerSteps=steps,trainingLosses=losses,finalEncoderHashes=final_hashes,
        frozenParametersUnchanged=True,reloadExact=True,checkpointSha256=encoder.digest(checkpoint),checkpointBytes=checkpoint.stat().st_size,
        ended=time.monotonic(),trainableParameters=restored.spec["trainableParameters"]))


def metrics(rows,model):
    matrix={truth:{pred:0 for pred in LABELS} for truth in LABELS}
    for row in rows: matrix[row["target"]][row["outputs"][model]["status"]]+=1
    return dict(matrix=matrix,correct=sum(matrix[c][c] for c in LABELS),total=len(rows),
        falseCompleted=matrix["non_transaction"]["completed"],unnecessaryUncertain=matrix["non_transaction"]["uncertain"],
        missedCompleted=matrix["completed"]["non_transaction"]+matrix["completed"]["uncertain"],
        wrongCertainty=matrix["uncertain"]["completed"]+matrix["uncertain"]["non_transaction"])


def cohort_result(raw,outputs):
    rows=[]
    for i,source in enumerate(raw):
        rows.append(dict(recordId=source["recordId"],textSha256=hashlib.sha256(source["text"].encode()).hexdigest(),target=source["target"],
            language=source.get("language") or ("ar" if any("\u0621"<=c<="\u064a" for c in source["text"]) else "en"),
            group=source.get("authoringGroupId"),semanticState=source.get("semanticState"),outputs={m:outputs[m][i] for m in MODELS}))
    pairs={}; groups={}
    for row in rows:
        if row["group"]:
            groups.setdefault(row["group"],[]).append(row)
            state=row["semanticState"] if row["semanticState"] is not None else row["target"]
            pairs.setdefault((row["group"],str(state)),{})[row["language"]]=row
    bilingual=[]
    for (group,state),pair in pairs.items():
        if set(pair)!={"ar","en"}: continue
        bilingual.append(dict(group=group,state=state,recordIds=[pair[l]["recordId"] for l in ("ar","en")],
            models={m:dict(agree=pair["ar"]["outputs"][m]["status"]==pair["en"]["outputs"][m]["status"],
                bothCorrect=all(pair[l]["outputs"][m]["status"]==pair[l]["target"] for l in ("ar","en"))) for m in MODELS}))
    return dict(rows=rows,metrics={lang:{m:metrics([r for r in rows if lang=="all" or r["language"]==lang],m) for m in MODELS} for lang in ("all","ar","en")},
        bilingualConsistency=bilingual,groupConsistency={g:{m:all(r["outputs"][m]["status"]==r["target"] for r in members) for m in MODELS} for g,members in groups.items()})


def gate(cohorts,components=None,require_benefit=True):
    violations=[]; fixes=set()
    for name,data in cohorts.items():
        for lang,values in data["metrics"].items():
            candidate=values["factorized"]
            if candidate["falseCompleted"] or candidate["unnecessaryUncertain"]: violations.append(f"{name}/{lang}: nontransaction not rejected")
            if candidate["wrongCertainty"]: violations.append(f"{name}/{lang}: uncertain truth became decisive")
            if candidate["missedCompleted"]>min(values[m]["missedCompleted"] for m in ("direct_status",*REFERENCES)):
                violations.append(f"{name}/{lang}: completion misses worse than best reference/control")
        for row in data["rows"]:
            direct=row["outputs"]["direct_status"]["status"]==row["target"]
            factor=row["outputs"]["factorized"]["status"]==row["target"]
            if direct and not factor: violations.append(f"{name}/{row['recordId']}: matched-control regression")
            if factor and not direct and name!="quoteControls": fixes.add(row["textSha256"])
    if require_benefit and not fixes: violations.append("No unique primary status improvement versus direct control")
    if components is not None and not components["allExact"]: violations.append("Component development labels not all exact")
    return sorted(set(violations)),len(fixes)


def component_metrics(rows,gold):
    targets={r["recordId"]:r for r in gold}
    result={}; exact=True
    for field,label_field in (("context","messageContext"),("event","describedEventState")):
        vocabulary=old.read(view.pilot.CONTRACT)["contextLabels" if field=="context" else "eventStateLabels"]
        result[field]={}
        for lang in ("all","ar","en"):
            subset=[r for r in rows if lang=="all" or r["language"]==lang]
            matrix={t:{p:0 for p in vocabulary} for t in vocabulary}
            for row in subset:
                truth=targets[row["recordId"]][label_field]["value"]
                pred=row["outputs"]["factorized"]["labels"][field]
                matrix[truth][pred]+=1
                if truth!=pred: exact=False
            result[field][lang]=dict(matrix=matrix,support={k:sum(v.values()) for k,v in matrix.items()},correct=sum(matrix[k][k] for k in vocabulary),total=len(subset))
    result["allExact"]=exact
    return result



def evaluate():
    from training.transactions import factorization_comparison_v2 as prior
    from training.evaluation.content_preflight import preflight
    p,training,cohorts,reserved=protocol(); setup(p)
    result=old.read(CACHE/"direct_status/result.json")
    if result["binding"]!=binding() or result["checkpointSha256"]!=encoder.digest(CACHE/"direct_status/final.safetensors"): raise ValueError("Finished checkpoint binding differs")
    original=old.read(prior.REPORT)
    if original["binding"]!=prior.binding(): raise ValueError("Frozen reference binding differs")
    arm=Arm(p,"direct_status");arm.restore(CACHE/"direct_status/final.safetensors")
    evaluations={};proxy={}
    for name,rows in cohorts.items():
        saved=original["evaluations"][name]["rows"]
        if [r["recordId"] for r in rows]!=[r["recordId"] for r in saved]: raise ValueError("Reference IDs differ")
        predictions=arm.predict(rows,name)
        outputs={m:[r["outputs"][m] for r in saved] for m in prior.MODELS}
        outputs["factorized"]=predictions
        proxy[name]=prior.cohort_result(rows,outputs)
        entries=[]
        for raw,reference,prediction in zip(rows,saved,predictions):
            if hashlib.sha256(raw["text"].encode()).hexdigest()!=reference["textSha256"]: raise ValueError("Reference text differs")
            item={**reference,"outputs":{**reference["outputs"],"candidate":prediction}}
            entries.append(item)
        evaluations[name]=dict(rows=entries,metrics={lang:{model:metrics([r for r in entries if lang=="all" or r["language"]==lang],model) for model in ("candidate","direct_status","factorized",*REFERENCES)} for lang in ("all","ar","en")})
    violations,fixes=prior.gate(proxy,components=None)
    metadata=preflight(training,[dict(r,cohort=name) for name,rows in cohorts.items() for r in rows],old.read(ROOT/p["evaluation"]["contract"]))
    bykey={(r["cohort"],r["recordId"]):r for r in metadata}
    slices={}
    for field in ("role","uncertaintyReason"):
        slices[field]={}
        for value in sorted({r[field] for r in metadata if r[field] is not None}):
            selected=[r for name,c in evaluations.items() for r in c["rows"] if bykey[(name,r["recordId"])][field]==value]
            slices[field][value]={lang:{m:metrics([r for r in selected if lang=="all" or r["language"]==lang],m) for m in ("candidate","direct_status")} for lang in ("all","ar","en")}
    exposure=[json.loads(l) for l in (CACHE/"inference_journal.jsonl").read_text().splitlines()]
    if {rid for e in exposure for rid in e["intendedRecordIds"]}&{r["recordId"] for r in reserved}:raise ValueError("Reserved exposure")
    timings=[]
    for _ in range(10):
        start=time.perf_counter();arm.predict(cohorts["oldExposedValidation"][:1],"warm_development");timings.append((time.perf_counter()-start)*1000)
    write_new(REPORT,dict(runId=RUN,binding=binding(),training=result,evaluations=evaluations,componentDevelopment=prior.component_metrics(proxy["scopeDevelopment"]["rows"],view.development_reviews()),savedScoreSlices=slices,metadata=metadata,gateViolations=violations,uniquePrimaryFixes=fixes,developmentGatePassed=not violations,reservedInferred=False,reservedScoredRecordIds=[],warmCpuMilliseconds=timings,independentAccuracy=False,productionIntegrated=False,studentTrained=False))


def run():
    from tools.evaluation.worker_supervision import run_monitored
    if any(p.exists() for p in (MASTER,REPORT,FAILURE)):raise ValueError("Experiment already attempted; no retry")
    p,_,_,_=protocol();CACHE.mkdir(parents=True,exist_ok=True)
    write_new(MASTER,dict(runId=RUN,binding=binding(),ownerApproval=p["ownerApproval"],trainingRunsAuthorized=1))
    monitors={}
    try:
        for name,seconds,call in (("training",480,"train('direct_status')"),("evaluation",240,"evaluate()")):
            code="from training.transactions.auxiliary_status import train,evaluate; "+call
            m=run_monitored(code,CACHE/(name+"_monitor"),seconds,6*1024**3,interval=1,artifact_paths=[CACHE,MASTER,REPORT,FAILURE],artifact_limit_bytes=2*1024**3)
            monitors[name]=m
            if m["exitCode"]!=0 or m["stopReason"] is not None:raise RuntimeError("Worker failed: "+json.dumps(m))
        write_new(CACHE/"supervision.json",dict(workers=monitors,totalWorkerElapsedSeconds=sum(m["elapsedSeconds"] for m in monitors.values())))
    except BaseException as error:
        write_new(FAILURE,dict(error=repr(error),completedMonitors=monitors));raise
    print(json.dumps(dict(completed=True,workers=monitors)))


if __name__=="__main__":run()
