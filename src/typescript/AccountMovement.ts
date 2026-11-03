/** Cash effects on an owned account; context/negation belong to the assessor. */
import rules from '../../config/contracts/transaction_evidence.json' with { type: 'json' };
import { moneyCurrency, moneyNumber, bareAmount } from './MoneySyntax.ts';

const money = '(?:' + moneyCurrency + '\\s*' + moneyNumber + '|' + moneyNumber + '\\s*' + moneyCurrency + '|' + bareAmount + ')';
function compileEffect(templates: string[]): RegExp {
  return new RegExp(templates.map(p => '(?:' + p.replaceAll('{money}', money)
    .replaceAll('{owner}', rules.accountMovement.owner) + ')').join('|'), 'i');
}
const DEBIT = compileEffect(rules.accountMovement.debitTemplates);
const CREDIT = compileEffect(rules.accountMovement.creditTemplates);
const SPAN_PATTERNS = [new RegExp(DEBIT.source,'gdi'),new RegExp(CREDIT.source,'gdi')];

export function hasAccountDebit(text: string): boolean { return DEBIT.test(text); }
export function hasAccountCredit(text: string): boolean { return CREDIT.test(text); }

export function bareAccountSpans(text: string) {
  const spans: {start: number;end: number;contextStart: number;resolution: 'default_missing'|'default_ambiguous'}[]=[];
  for (const pattern of SPAN_PATTERNS) {
    for (const match of text.matchAll(pattern)) {
      for (let group=1;group<match.length;group+=2) if (match[group]!==undefined) {
        const [start,end]=match.indices![group];
        spans.push({start,end,contextStart:match.index!,resolution:match[group+1]?'default_ambiguous':'default_missing'});
      }
    }
  }
  return spans;
}
