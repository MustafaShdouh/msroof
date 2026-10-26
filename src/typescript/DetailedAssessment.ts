/** Canonical contract assessment; metadata and classifier scores cannot prove settlement. */
import rules from '../../config/contracts/transaction_evidence.json' with { type: 'json' };
import { EntityText } from './EntityText.ts';
import { isAuthorizationRequest } from './AuthorizationRequest.ts';
import { isServiceNotice } from './ServiceNotice.ts';

export interface DetailedInput { text: string; sender?: string | null; isContact?: boolean; receivedAt?: string | null; }
export interface DetailedResult {
  contractVersion: '1.0.0'; transactionStatus: 'completed' | 'non_transaction' | 'uncertain';
  trackingDecision: 'include' | 'exclude' | 'review'; reasonCodes: string[];
  amount: number | null; currency: string | null;
  currencyResolution: 'explicit' | 'default_missing' | 'default_ambiguous' | 'not_applicable';
  direction: 'incoming' | 'outgoing' | 'uncertain' | 'not_applicable';
  transferRelationship: 'not_transfer' | 'own_accounts' | 'other_person' | 'unknown' | 'not_applicable';
  merchantOrCounterparty: string | null; expenseCategory: string | null;
  categoryStatus: 'assigned' | 'uncertain' | 'not_applicable';
}
interface Extracted {
  amount: number | null; currency: string; merchantOrParty: string | null;
  originalAmount?: number | null; originalCurrency?: string | null;
}
const RX: Record<string, RegExp> = Object.fromEntries(Object.entries(rules.patterns).map(([key, value]) => [key, new RegExp(value, 'i')]));
const PURPOSE = Object.entries(rules.purpose).map(([label, value]) => ({ label, pattern: new RegExp(value, 'i') }));
const ALIASES: Record<string, string> = Object.fromEntries(Object.entries(rules.currencyAliases).map(([key, value]) => [key.toUpperCase(), value]));
function escape(value: string) { return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'); }
const currency = '(?<![A-Za-z\\u0621-\\u064A])(?:' + Object.keys(ALIASES).sort((a, b) => b.length - a.length).map(escape).join('|') + ')(?![A-Za-z\\u0621-\\u064A])';
const number = "(?<![0-9*.,'’])" + rules.number + '(?![0-9]|[.,][0-9])';
const MONEY = new RegExp('(' + currency + ')\\s*(' + number + ')|(' + number + ')\\s*(' + currency + ')', 'gi');
const CURRENCY = new RegExp(currency, 'gi');
const balanceValue = '(?:' + currency + '\\s*)?[+-]?' + number + '(?:\\s*' + currency + ')?';
const BALANCE = new RegExp('(?:' + rules.patterns.balance + ')' + rules.patterns.balanceJoin + balanceValue, 'gi');
const BALANCE_SUFFIX = new RegExp(balanceValue + rules.patterns.balanceSuffix, 'gi');
const UNMARKED = new RegExp('(?:' + rules.patterns.amountAnchor + ')(' + number + ')', 'gi');

function maskBalances(text: string): string {
  // Prefixes win: in "20 JOD الرصيد 100 JOD", only 100 is a balance.
  return text.replace(BALANCE, match => ' '.repeat(match.length))
    .replace(BALANCE_SUFFIX, match => ' '.repeat(match.length));
}

function nonTransaction(reasons: string[]): DetailedResult {
  return { contractVersion: '1.0.0', transactionStatus: 'non_transaction', trackingDecision: 'exclude',
    reasonCodes: [...new Set(reasons)].sort(), amount: null, currency: null, currencyResolution: 'not_applicable',
    direction: 'not_applicable', transferRelationship: 'not_applicable', merchantOrCounterparty: null,
    expenseCategory: null, categoryStatus: 'not_applicable' };
}

function amounts(text: string, extracted: Extracted, parseNumber: (value: string) => number | null): [number | null, string, DetailedResult['currencyResolution']] {
  let working = maskBalances(text);
  for (const key of ['date', 'identifier']) working = working.replace(new RegExp(rules.patterns[key], 'gi'), match => ' '.repeat(match.length));
  const pairs: [number, string][] = [];
  for (const match of working.matchAll(MONEY)) {
    const value = parseNumber(match[2] || match[3]);
    const unit = ALIASES[(match[1] || match[4]).toUpperCase()];
    if (value !== null && Number.isFinite(value) && value > 0) pairs.push([value, unit]);
  }
  const units = new Set(pairs.map(pair => pair[1]));
  if (!units.size) for (const match of working.matchAll(CURRENCY)) units.add(ALIASES[match[0].toUpperCase()]);
  const explicit = units.size === 1;
  const resolution = explicit ? 'explicit' : (units.size || RX.ambiguousCurrency.test(working) ? 'default_ambiguous' : 'default_missing');
  const unit = explicit ? [...units][0] : 'JOD';
  if (RX.amountAlternatives.test(working)) return [null, unit, resolution];
  if (pairs.length === 1) return [pairs[0][0], unit, resolution];
  if (pairs.length > 1) {
    const expected = [[extracted.amount, extracted.currency], [extracted.originalAmount, extracted.originalCurrency]];
    if (pairs.length === 2 && extracted.originalAmount && RX.fx.test(text) &&
        pairs.every(pair => expected.some(value => value[0] === pair[0] && value[1] === pair[1])) &&
        expected.every(value => pairs.some(pair => value[0] === pair[0] && value[1] === pair[1]))) {
      return [extracted.amount, extracted.currency, 'explicit'];
    }
    return [null, unit, resolution];
  }
  const candidates: number[] = [];
  for (const match of working.matchAll(UNMARKED)) {
    const value = parseNumber(match[1]);
    if (value !== null && Number.isFinite(value) && value > 0) candidates.push(value);
  }
  return [candidates.length === 1 ? candidates[0] : null, unit, resolution];
}

function exactParty(raw: string): string | null {
  const source = new EntityText(raw);
  for (const key of ['partyLabelAnchor', 'partyAnchor']) {
    for (const anchor of source.text.matchAll(new RegExp(rules.patterns[key], 'gi'))) {
      const start = anchor.index! + anchor[0].length;
      const match = RX.partyValue.exec(source.text.slice(start));
      if (!match) continue;
      const candidate = match[1].replace(/[ .;,]+$/, '');
      if (!candidate || RX.partyReject.test(candidate) || RX.partyAccountRole.test(candidate)) continue;
      const chosen = source.exact(start, start + candidate.length);
      if (chosen && !RX.alignedLocation.test(chosen)) return chosen;
    }
  }
  return null;
}

function completedClause(clause: string, allowPurchase: boolean): boolean {
  if (RX.completionDenied.test(clause) || RX.reportedSpeech.test(clause)) return false;
  const purchase = allowPurchase && RX.purchaseEvidence.test(clause) && !RX.purchaseUnsettled.test(clause) &&
    !RX.purchaseConditional.test(clause) && !RX.deferred.test(clause) && !RX.declined.test(clause) && !RX.chat.test(clause);
  return RX.completion.test(clause) || purchase;
}

export function assess(input: DetailedInput, extract: (body: string, type: 'INCOME' | 'EXPENSE') => Extracted,
  parseNumber: (value: string) => number | null, financialCandidate: (text: string) => boolean): DetailedResult {
  const raw = input?.text;
  if (typeof raw !== 'string' || !raw.trim()) return nonTransaction(['empty_or_malformed']);
  const text = new EntityText(raw).text;
  const clauses = text.split(RX.sentence).filter(part => part.trim());
  const allowPurchase = !RX.purchaseQualification.test(text);
  const hasCompletion = clauses.some(clause => completedClause(clause, allowPurchase));
  const completed: string[] = [], negative: string[] = [], relevant: string[] = [];
  for (const clause of clauses) {
    const complete = completedClause(clause, allowPurchase);
    const reasons: string[] = [];
    if (RX.chat.test(clause) || RX.reportedSpeech.test(clause)) reasons.push('personal_conversation');
    if (isAuthorizationRequest(clause) || RX.otpRequest.test(clause) || (RX.otp.test(clause) && !hasCompletion)) reasons.push('otp_or_authorization');
    if (RX.declined.test(clause)) reasons.push('declined_or_failed');
    if (RX.deferred.test(clause) || RX.completionDenied.test(clause) || RX.purchaseConditional.test(clause)) reasons.push('pending_or_requested');
    if (RX.promotion.test(clause) || (RX.serviceScope.test(clause) && isServiceNotice(clause))) reasons.push('promotion_or_administration');
    if (complete) completed.push(clause);
    negative.push(...reasons);
    if (!reasons.length) relevant.push(clause);
  }
  const conflicts = !!completed.length && negative.some(reason => reason !== 'promotion_or_administration');
  if (!completed.length && negative.length) return nonTransaction(negative);
  if (!completed.length && RX.balanceInquiry.test(text)) return nonTransaction(['balance_only']);
  if (!completed.length && !RX.financial.test(text)) {
    if (RX.balance.test(text)) return nonTransaction(['balance_only']);
    if (!financialCandidate(text)) return nonTransaction(['personal_conversation']);
  }
  let status: DetailedResult['transactionStatus'] = completed.length && !conflicts ? 'completed' : 'uncertain';
  const semantic = relevant.join(' ');
  const incoming = relevant.some(part => RX.incoming.test(part) ||
    (RX.transfer.test(part) && RX.transferOwnerRecipient.test(part)));
  const outgoing = relevant.some(part => (RX.outgoing.test(part) ||
    (RX.transfer.test(part) && RX.transferOwnerSource.test(part))) && !RX.returnMovement.test(part));
  let direction: DetailedResult['direction'] = incoming === outgoing || RX.directionDenied.test(text) ? 'uncertain' : (incoming ? 'incoming' : 'outgoing');
  let relation: DetailedResult['transferRelationship'] = 'not_transfer';
  if (RX.transfer.test(semantic)) relation = RX.own.test(semantic) ? 'own_accounts' : (RX.otherPerson.test(semantic) ? 'other_person' : 'unknown');
  if (relation === 'own_accounts') direction = 'not_applicable';
  const extracted = extract(raw, direction === 'incoming' ? 'INCOME' : 'EXPENSE');
  let [amount, unit, resolution] = amounts(text, extracted, parseNumber);
  if (completed.filter(part => [...maskBalances(part).matchAll(MONEY)].length > 0).length > 1) {
    status = 'uncertain'; amount = null;
  }
  let decision: DetailedResult['trackingDecision'] = 'review';
  if (status === 'completed') {
    if (relation === 'own_accounts') decision = 'exclude';
    else if (amount !== null && direction !== 'uncertain' && relation !== 'unknown') decision = 'include';
  }
  const purpose = decision === 'include' && direction === 'outgoing' ? PURPOSE.filter(item => item.pattern.test(semantic)).map(item => item.label) : [];
  const label = purpose.length === 1 ? purpose[0] : null;
  const categoryStatus = decision === 'include' && direction === 'outgoing' ? (label ? 'assigned' : 'uncertain') : 'not_applicable';
  const reasons = [status === 'completed' ? 'completed_transaction' : 'completion_unresolved'];
  if (amount === null) reasons.push('amount_unresolved');
  if (direction === 'uncertain') reasons.push('direction_unresolved');
  if (relation === 'unknown') reasons.push('transfer_ownership_unresolved');
  if (relation === 'own_accounts') reasons.push('own_account_transfer');
  if (categoryStatus === 'uncertain') reasons.push('category_unresolved');
  return { contractVersion: '1.0.0', transactionStatus: status, trackingDecision: decision, reasonCodes: reasons.sort(),
    amount, currency: unit, currencyResolution: resolution, direction, transferRelationship: relation,
    merchantOrCounterparty: relation === 'own_accounts' ? null : exactParty(raw), expenseCategory: label, categoryStatus };
}
