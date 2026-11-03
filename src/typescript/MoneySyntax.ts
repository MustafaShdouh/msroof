/** Shared monetary lexical grammar; no event or selection policy. */
import rules from '../../config/contracts/transaction_evidence.json' with { type: 'json' };
export const ALIASES: Record<string,string> = Object.fromEntries(Object.entries(rules.currencyAliases).map(([key,value])=>[key.toUpperCase(),value]));
function escape(value: string) { return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'); }
export const moneyCurrency = '(?<![A-Za-z\\u0621-\\u064A])(?:' + Object.keys(ALIASES).sort((a,b)=>b.length-a.length).map(escape).join('|') + ')(?![A-Za-z\\u0621-\\u064A])';
export const moneyNumber = "(?<![0-9*.,'’])" + rules.number + '(?![0-9]|[.,][0-9])';

// Captures only the unmarked number and its optional ambiguous unit.
export const bareAmount = rules.unmarkedAccountAmount.prefix + '(' + rules.unmarkedAccountAmount.positive + rules.number + ')'
  + '(?:\\s+(' + rules.patterns.ambiguousCurrency + '))?' + rules.unmarkedAccountAmount.tail;
