/** Canonical contract assessment; metadata and classifier scores cannot prove settlement. */
import rules from '../../config/contracts/transaction_evidence.json' with { type: 'json' };
import { EntityText } from './EntityText.ts';
import { maskBalances, amounts, hasMovementAmount } from './MoneyCandidates.ts';
import { initialDirection, resolveRelationship, recordingDecision } from './DirectionPolicy.ts';
import { isAuthorizationRequest } from './AuthorizationRequest.ts';
import { isServiceNotice } from './ServiceNotice.ts';
import { hasAccountDebit, hasAccountCredit } from './AccountMovement.ts';

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
export interface OwnershipOverride {
  relationship: 'own_accounts' | 'other_person' | 'unknown'; uncertainDirection: boolean;
}
interface Extracted {
  amount: number | null; currency: string; merchantOrParty: string | null;
  originalAmount?: number | null; originalCurrency?: string | null;
}
const RX: Record<string, RegExp> = Object.fromEntries(Object.entries(rules.patterns).map(([key, value]) => [key, new RegExp(value, 'i')]));
const NONCASH_POSTING = new RegExp(rules.patterns.nonCashPosting, 'gi');
const RESOLVED_PENDING = new RegExp(rules.patterns.resolvedPending, 'gi');
const PURPOSE = Object.entries(rules.purpose).map(([label, value]) => ({ label, pattern: new RegExp(value, 'i') }));
function nonTransaction(reasons: string[]): DetailedResult {
  return { contractVersion: '1.0.0', transactionStatus: 'non_transaction', trackingDecision: 'exclude',
    reasonCodes: [...new Set(reasons)].sort(), amount: null, currency: null, currencyResolution: 'not_applicable',
    direction: 'not_applicable', transferRelationship: 'not_applicable', merchantOrCounterparty: null,
    expenseCategory: null, categoryStatus: 'not_applicable' };
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

function completionEvidence(clause: string): boolean {
  return RX.completion.test(clause) || RX.postedDebit.test(clause) || RX.postedCredit.test(clause) ||
    hasAccountDebit(clause) || hasAccountCredit(clause);
}

function conditionalClause(clause: string): boolean {
  return RX.conditionalStart.test(clause) && completionEvidence(clause);
}


function personalContext(clause: string): boolean {
  return RX.chat.test(clause) || RX.personalFrame.test(clause) || RX.reportedSpeech.test(clause) || RX.evidenceInquiry.test(clause);
}

function pendingClause(clause: string): boolean {
  return RX.deferred.test(clause.replace(RESOLVED_PENDING, ''));
}

function completedClause(clause: string, allowPurchase: boolean): boolean {
  if (conditionalClause(clause) || RX.completionDenied.test(clause) || personalContext(clause) || RX.outcomeUnknown.test(clause)) return false;
  // Strip only the noncash posting phrase; keep independent cash evidence.
  if (RX.nonCashPosting.test(clause)) clause = clause.replace(NONCASH_POSTING, '');
  if (RX.resolvedPending.test(clause)) clause = clause.replace(RESOLVED_PENDING, '');
  const purchase = allowPurchase && RX.purchaseEvidence.test(clause) && !RX.purchaseUnsettled.test(clause) &&
    !RX.purchaseConditional.test(clause) && !RX.deferred.test(clause) && !RX.declined.test(clause) && !RX.chat.test(clause);
  return completionEvidence(clause) || purchase;
}


function unresolvedCompletion(clauses: string[]): boolean {
  let noncashSeen = false, financialContext = false, unknown = false, finalUnknown = false;
  for (let clause of clauses) {
    if (personalContext(clause) || RX.otpRequest.test(clause) || RX.promotion.test(clause) || isAuthorizationRequest(clause)) continue;
    if (RX.nonCashPosting.test(clause)) {
      noncashSeen = true;
      clause = clause.replace(NONCASH_POSTING, '');
    }
    financialContext = financialContext || RX.financialOutcomeContext.test(clause) ||
      RX.postedDebit.test(clause) || RX.postedCredit.test(clause) || hasAccountDebit(clause) || hasAccountCredit(clause);
    unknown = unknown || RX.outcomeUnknown.test(clause) || RX.contextUnknown.test(clause);
    finalUnknown = finalUnknown || RX.finalOutcomeUnknown.test(clause);
  }
  if (noncashSeen && !financialContext) return false;
  return unknown || (financialContext && finalUnknown);
}

export function assess(input: DetailedInput, extract: (body: string, type: 'INCOME' | 'EXPENSE') => Extracted,
  parseNumber: (value: string) => number | null, financialCandidate: (text: string) => boolean,
  ownershipOverride?: OwnershipOverride): DetailedResult {
  const raw = input?.text;
  if (typeof raw !== 'string' || !raw.trim()) return nonTransaction(['empty_or_malformed']);
  const source = new EntityText(raw);
  const text = source.text;
  if (!text) return nonTransaction(['empty_or_malformed']);
  // A trailing conditional must not erase a preceding factual receipt.
  const clauses = text.split(RX.sentence).flatMap(sentence => sentence.split(RX.conditionalBoundary)).filter(part => part.trim());
  const allowPurchase = !RX.purchaseQualification.test(text);
  const unresolved = unresolvedCompletion(clauses);
  const hasCompletion = clauses.some(clause => completedClause(clause, allowPurchase));
  const completed: string[] = [], negative: string[] = [], relevant: string[] = [];
  for (const clause of clauses) {
    const complete = completedClause(clause, allowPurchase);
    const reasons: string[] = [];
    if (personalContext(clause)) reasons.push('personal_conversation');
    if (isAuthorizationRequest(clause) || RX.otpRequest.test(clause) || (RX.otp.test(clause) && !hasCompletion)) reasons.push('otp_or_authorization');
    if (RX.declined.test(clause)) reasons.push('declined_or_failed');
    if (conditionalClause(clause) || pendingClause(clause) || RX.completionDenied.test(clause) || RX.purchaseConditional.test(clause)) reasons.push('pending_or_requested');
    if (((RX.nonCashPosting.test(clause) || RX.administration.test(clause)) && !complete) || RX.promotion.test(clause) || (RX.serviceScope.test(clause) && isServiceNotice(clause))) reasons.push('promotion_or_administration');
    if (complete) completed.push(clause);
    negative.push(...reasons);
    if (!reasons.length) relevant.push(clause);
  }
  const conflicts = !!completed.length && negative.some(reason => reason !== 'promotion_or_administration');
  if (!completed.length && negative.length && !unresolved) {
    if (negative.every(reason => reason === 'personal_conversation') && RX.evidenceInquiry.test(text) &&
        !RX.chat.test(text) && !RX.personalFrame.test(text) && RX.balance.test(text) &&
        !RX.financial.test(text) && !clauses.some(part => completionEvidence(part))) return nonTransaction(['balance_only']);
    return nonTransaction(negative);
  }
  if (!completed.length && !unresolved && RX.balanceInquiry.test(text)) return nonTransaction(['balance_only']);
  if (!completed.length && !unresolved && !RX.financial.test(maskBalances(text))) {
    if (RX.balance.test(text)) return nonTransaction(['balance_only']);
    if (!financialCandidate(text)) return nonTransaction(['personal_conversation']);
  }
  let status: DetailedResult['transactionStatus'] = completed.length && !conflicts && !unresolved && !RX.outcomeUnknown.test(text) ? 'completed' : 'uncertain';
  const semantic = relevant.join(' ');
  let [direction,relation]=initialDirection(text,relevant);
  const extracted = extract(raw, direction === 'incoming' ? 'INCOME' : 'EXPENSE');
  let [amount, unit, resolution] = amounts(text, extracted, parseNumber, source,status==='completed');
  if (completed.length > 1 && completed.filter(part => hasMovementAmount(part,parseNumber)).length > 1) {
    status = 'uncertain'; amount = null;
  }
  [direction,relation]=resolveRelationship(text,semantic,amount,negative,direction,relation,ownershipOverride);
  const decision=recordingDecision(status,amount,direction,relation);
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
