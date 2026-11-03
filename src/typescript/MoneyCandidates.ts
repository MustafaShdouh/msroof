/** Source-linked monetary candidates; original primary amount policy retained. */
import rules from '../../config/contracts/transaction_evidence.json' with { type: 'json' };
import { EntityText } from './EntityText.ts';
import { ALIASES, moneyCurrency, moneyNumber, bareAmount } from './MoneySyntax.ts';
import { bareAccountSpans } from './AccountMovement.ts';
export const currency = moneyCurrency;
export const number = moneyNumber;
const RX: Record<string, RegExp> = Object.fromEntries(Object.entries(rules.patterns).map(([k,v]) => [k,new RegExp(v,'i')]));
interface Extracted { amount: number | null; currency: string; originalAmount?: number | null; originalCurrency?: string | null; }
type Resolution = 'explicit' | 'default_missing' | 'default_ambiguous' | 'not_applicable';
export const MONEY = new RegExp('(' + currency + ')\\s*(' + number + ')|(' + number + ')\\s*(' + currency + ')', 'gdi');
const PRIMARY = new RegExp(rules.patterns.explicitPrimary + '(?:' + MONEY.source + ')','gdi');
const RECEIVER = new RegExp(rules.patterns.amountReceiverAnchor + '(?:' + MONEY.source + ')','gdi');
const CURRENCY = new RegExp(currency, 'gi');
const balanceNumber = '(?:' + currency + '\\s*)?[+-]?' + number;
const BALANCE = new RegExp('(?:' + rules.patterns.balance + ')' + rules.patterns.balanceJoin
  + balanceNumber + '(?:(\\s*)(' + currency + '))?', 'gi');
const BALANCE_SUFFIX = new RegExp(balanceNumber + '(?:\\s*' + currency + ')?' + rules.patterns.balanceSuffix, 'gi');
const FOLLOWING_AMOUNT = new RegExp('^(\\s*)' + number);
const SOURCE_LINE_BREAK = /[\r\n]|\\[nr]/;
const UNMARKED = new RegExp('(?:' + rules.patterns.amountAnchor + ')(' + number + ')', 'gdi');
const BARE_PRIMARY = new RegExp(rules.patterns.explicitPrimary + bareAmount,'gdi');
const BARE_LIST = new RegExp(rules.unmarkedAccountAmount.list,'i');
const RECEIVER_ID = new RegExp('^(?:'+rules.unmarkedAccountAmount.receiverIdentifierPrefix+')$','i');
function barePrimarySpans(text: string) {
  return [...text.matchAll(BARE_PRIMARY)].map(m=>({start:m.indices![1][0],end:m.indices![1][1],contextStart:m.index!,
    resolution:(m[2]?'default_ambiguous':'default_missing') as Resolution}));
}
interface Candidate {value: number;currency: string|null;role: string;start: number;end: number;text: string;currencyResolution?: Resolution;}

export function maskBalances(text: string, onExcluded?: (start: number,end: number) => void, source?: EntityText): string {
  // Prefixes win: in "20 JOD الرصيد 100 JOD", only 100 is a balance.
  const blank = (start: number, end: number) => {
    onExcluded?.(start,end);
    return ' '.repeat(end-start);
  };
  const working = text.replace(BALANCE,(match: string, gap: string | undefined, unit: string | undefined, start: number) => {
    const end = start + match.length;
    if (source && gap && unit) {
      const currencyStart = end - unit.length;
      const gapStart = currencyStart - gap.length;
      if (SOURCE_LINE_BREAK.test(source.exact(gapStart,currencyStart) ?? '')) {
        const following = FOLLOWING_AMOUNT.exec(text.slice(end));
        if (following && !SOURCE_LINE_BREAK.test(source.exact(end,end+following[1].length) ?? '')) {
          // The currency starts the amount on the next source line.
          return blank(start,gapStart) + text.slice(gapStart,end);
        }
      }
    }
    return blank(start,end);
  });
  return working.replace(BALANCE_SUFFIX,(match: string, start: number) => blank(start,start+match.length));
}


export function collectCandidates(source: EntityText, parseNumber: (text: string) => number | null) {
  const exclusions: {role: string;start: number;end: number}[]=[];
  const rawOffset=(index: number) => Array.from(source.source.slice(0,index)).length;
  let working=maskBalances(source.text,(start,end)=>exclusions.push({role:'balance',start:rawOffset(source.starts[start]),end:rawOffset(source.ends[end-1])}),source);
  let accountSpans: ReturnType<typeof bareAccountSpans>=[],primarySpans: ReturnType<typeof barePrimarySpans>=[];
  for (const role of ['date','identifier']) {
    const rx=new RegExp(rules.patterns[role as keyof typeof rules.patterns],'gi');
    // Protect receipt amounts from identifier masking, without primary priority.
    const protectedSpans=role==='identifier' ? [PRIMARY,RECEIVER].flatMap(pattern=>[...working.matchAll(pattern)].map(m=>m.indices![m[2]?2:3])) : [];
    if(role==='identifier'){accountSpans=bareAccountSpans(working);primarySpans=barePrimarySpans(working);}
    const bareProtected=[...accountSpans,...primarySpans];
    const isProtected=(start: number,end: number)=>protectedSpans.some(([a,b])=>start<b && end>a)
      || bareProtected.some(span=>span.contextStart<start && start<=span.start && span.start<end && RECEIVER_ID.test(working.slice(start,span.start)));
    for (const match of working.matchAll(rx)) if (!isProtected(match.index!,match.index!+match[0].length)) exclusions.push({role,start:rawOffset(source.starts[match.index!]),end:rawOffset(source.ends[match.index!+match[0].length-1])});
    working=working.replace(rx,(match,...parts)=>isProtected(parts[parts.length-2],parts[parts.length-2]+match.length)?match:' '.repeat(match.length));
  }
  const candidate=(match: RegExpMatchArray,group: number,unit: string | null,role: string) => {
    const value=parseNumber(match[group]);
    if (value===null || !Number.isFinite(value) || value<=0) return null;
    const [start,end]=match.indices![group];
    const a=source.starts[start],b=source.ends[end-1];
    return {value,currency:unit,role,start:rawOffset(a),end:rawOffset(b),text:source.source.slice(a,b)};
  };
  const monetary: Candidate[]=[];const anchored: Candidate[]=[];const primary: Candidate[]=[];
  for (const match of working.matchAll(MONEY)) {
    const c=candidate(match,match[2]?2:3,ALIASES[(match[1]||match[4]).toUpperCase()],'currency_amount');
    if (c!==null) monetary.push(c);
  }
  for (const match of working.matchAll(UNMARKED)) {
    const c=candidate(match,1,null,'anchored_amount');if(c!==null) anchored.push(c);
  }
  for (const match of working.matchAll(PRIMARY)) {
    const c=candidate(match,match[2]?2:3,ALIASES[(match[1]||match[4]).toUpperCase()],'explicit_primary');
    if(c!==null) primary.push(c);
  }
  for (const [spans,target,role] of [[accountSpans,anchored,'account_amount'],
                                    [primarySpans,primary,'explicit_primary']] as const) {
    for (const span of spans) {
      if(working.slice(span.start,span.end)!==source.text.slice(span.start,span.end))continue;
      const value=parseNumber(working.slice(span.start,span.end));
      if(value===null || !Number.isFinite(value) || value<=0)continue;
      const a=source.starts[span.start],b=source.ends[span.end-1],start=rawOffset(a),end=rawOffset(b);
      if(monetary.some(c=>c.start===start && c.end===end))continue;
      for(let i=target.length-1;i>=0;i--)if(target[i].start===start && target[i].end===end)target.splice(i,1);
      target.push({value,currency:null,role,start,end,text:source.source.slice(a,b),currencyResolution:span.resolution});
    }
  }
  return {working,monetary,anchored,primary,exclusions};
}

function standaloneTotal(clause: string): boolean {
  const clean=clause.trim().replace(/[.!?؟;]+$/u,'').trim();
  if(RX.amountSummaryPrefix.test(clean)) {
    for(const pattern of [PRIMARY,BARE_PRIMARY]) {
      for(const match of clean.matchAll(pattern))if(match.index===0 && match[0].length===clean.length)return true;
    }
  }
  return false;
}

export function movementValues(clause: string, parseNumber: (value: string) => number | null): Set<number> {
  if(standaloneTotal(clause))return new Set();
  const evidence=collectCandidates(new EntityText(clause),parseNumber);
  const posted=[...evidence.primary,...evidence.anchored.filter(c=>c.role==='account_amount')];
  const candidates=posted.length?posted:[...evidence.monetary,...evidence.anchored];
  return new Set(candidates.map(c=>c.value));
}

export function hasMovementAmount(clause: string, parseNumber: (value: string) => number | null): boolean {
  if(standaloneTotal(clause))return false;
  if([...maskBalances(clause).matchAll(MONEY)].length)return true;
  const evidence=collectCandidates(new EntityText(clause),parseNumber);
  return evidence.primary.length>0 || evidence.anchored.some(c=>c.role==='account_amount');
}

export function amounts(text: string, extracted: Extracted, parseNumber: (value: string) => number | null , source?: EntityText, allowUnmarked=true): [number | null, string, Resolution] {
  const evidence=collectCandidates(source ?? new EntityText(text),parseNumber);
  const working=evidence.working;
  const pairs: [number,string][]=evidence.monetary.map(c=>[c.value,c.currency!]);
  const units = new Set(pairs.map(pair => pair[1]));
  if (!units.size) for (const match of working.matchAll(CURRENCY)) units.add(ALIASES[match[0].toUpperCase()]);
  const explicit = units.size === 1;
  const resolution = explicit ? 'explicit' : (units.size || RX.ambiguousCurrency.test(working) ? 'default_ambiguous' : 'default_missing');
  const unit = explicit ? [...units][0] : 'JOD';
  const bare=[...evidence.anchored.filter(c=>c.role==='account_amount'),...evidence.primary.filter(c=>c.currency===null)];
  if(bare.length) {
    const resolved=(c: Candidate): [number,string,Resolution]=>[c.value,c.currency||'JOD',c.currency?'explicit':c.currencyResolution!];
    const candidates=new Map<string,Candidate>();
    for(const kind of ['anchored','monetary','primary'] as const)for(const c of evidence[kind])candidates.set(c.start+':'+c.end,c);
    const fallback: [null,string,Resolution]=[null,'JOD',bare.some(c=>c.currencyResolution==='default_ambiguous')?'default_ambiguous':'default_missing'];
    if(!allowUnmarked || RX.amountAlternatives.test(working) || BARE_LIST.test(working))return fallback;
    if(evidence.primary.length===1)return resolved(evidence.primary[0]);
    if(!evidence.primary.length && candidates.size===1)return resolved([...candidates.values()][0]);
    return fallback;
  }
  if (RX.amountAlternatives.test(working)) return [null, unit, resolution];
  if (pairs.length === 1) return [pairs[0][0], unit, resolution];
  if (pairs.length > 1) {
    if (evidence.primary.length===1) {
      const chosen=evidence.primary[0];
      if (pairs.some(pair=>pair[0]===chosen.value && pair[1]===chosen.currency)) return [chosen.value,chosen.currency!,'explicit'];
    }
    const expected = [[extracted.amount, extracted.currency], [extracted.originalAmount, extracted.originalCurrency]];
    if (pairs.length === 2 && extracted.originalAmount && RX.fx.test(text) &&
        pairs.every(pair => expected.some(value => value[0] === pair[0] && value[1] === pair[1])) &&
        expected.every(value => pairs.some(pair => value[0] === pair[0] && value[1] === pair[1]))) {
      return [extracted.amount, extracted.currency, 'explicit'];
    }
    return [null, unit, resolution];
  }
  const candidates=evidence.anchored.map(c=>c.value);
  return [candidates.length === 1 ? candidates[0] : null, unit, resolution];
}

