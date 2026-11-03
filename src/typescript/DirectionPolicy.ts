/** Direction evidence and owner relationship policy; no completion inference. */
import rules from '../../config/contracts/transaction_evidence.json' with { type: 'json' };
import { MONEY, currency, number, maskBalances } from './MoneyCandidates.ts';
import { hasAccountDebit, hasAccountCredit } from './AccountMovement.ts';
import type { DetailedResult, OwnershipOverride } from './DetailedAssessment.ts';
const RX: Record<string,RegExp>=Object.fromEntries(Object.entries(rules.patterns).map(([k,v])=>[k,new RegExp(v,'i')]));
const PAIRED = rules.pairedMovement.templates.map(template => new RegExp(template
  .replaceAll('{money}', '(?:' + currency + '\\s*' + number + '|' + number + '\\s*' + currency + ')')
  .replaceAll('{account}', rules.pairedMovement.account), 'i'));
const PAIRED_REJECT = new RegExp(rules.pairedMovement.reject, 'i');
const TRANSFER_PURPOSE = new RegExp(rules.patterns.transferPurpose, 'gi');

function pairedMovement(text: string, amount: number | null, negative: string[]): boolean {
  // Strict templates cannot cross sentence punctuation except an account abbreviation.
  if (negative.length || PAIRED_REJECT.test(text) || amount === null || [...maskBalances(text).matchAll(MONEY)].length !== 1) return false;
  const working = maskBalances(text);
  return PAIRED.some(pattern => {
    const match = pattern.exec(working);
    if (!match || match[1].toLowerCase() === match[2].toLowerCase()) return false;
    const remaining = working.slice(0, match.index) + ' '.repeat(match[0].length) + working.slice(match.index + match[0].length);
    return !RX.financial.test(remaining) && !RX.completion.test(remaining) && !RX.postedDebit.test(remaining) &&
      !RX.postedCredit.test(remaining) && !hasAccountDebit(remaining) && !hasAccountCredit(remaining);
  });
}

function ownerPosting(part: string, key: string): boolean {
  const match = RX[key].exec(part);
  return !!match && RX.postedOwnerSuffix.test(part.slice(match.index + match[0].length));
}

function transferContent(semantic: string): string {
  if (!RX.transferPurpose.test(semantic)) return semantic;
  if (RX.own.test(semantic) || RX.otherPerson.test(semantic) || RX.explicitTransfer.test(semantic) ||
      PAIRED.some(pattern => pattern.test(semantic))) return semantic;
  if (RX.salaryPurpose.test(semantic) && (!hasAccountCredit(semantic) || hasAccountDebit(semantic))) return semantic;
  return semantic.replace(TRANSFER_PURPOSE, '');
}

export function initialDirection(text: string,relevant: string[]): [DetailedResult['direction'],DetailedResult['transferRelationship']] {
  const semantic=relevant.join(' ');
  let incoming = relevant.some(part => RX.incoming.test(part) ||
    (RX.transfer.test(part) && RX.transferOwnerRecipient.test(part)));
  let outgoing = relevant.some(part => (RX.outgoing.test(part) ||
    (RX.transfer.test(part) && RX.transferOwnerSource.test(part))) && !RX.returnMovement.test(part));
  const postedIn = relevant.some(part => ownerPosting(part, 'postedCredit') || hasAccountCredit(part));
  const postedOut = relevant.some(part => ownerPosting(part, 'postedDebit') || hasAccountDebit(part));
  if (postedIn || postedOut) { incoming = postedIn; outgoing = postedOut; }
  let direction: DetailedResult['direction'] = incoming === outgoing || RX.directionDenied.test(text) ? 'uncertain' : (incoming ? 'incoming' : 'outgoing');
  let relation: DetailedResult['transferRelationship'] = 'not_transfer';
  if (RX.transfer.test(transferContent(semantic))) relation = RX.own.test(semantic) ? 'own_accounts' : (RX.otherPerson.test(semantic) ? 'other_person' : 'unknown');
  if (relation === 'own_accounts') direction = 'not_applicable';
  return [direction,relation];
}

export function resolveRelationship(text: string,semantic: string,amount: number | null,negative: string[],direction: DetailedResult['direction'],relation: DetailedResult['transferRelationship'],ownershipOverride?: OwnershipOverride): [DetailedResult['direction'],DetailedResult['transferRelationship']] {
  if (relation === 'not_transfer' && pairedMovement(text, amount, negative)) {
    relation = RX.own.test(semantic) ? 'own_accounts' : (RX.otherPerson.test(semantic) ? 'other_person' : 'unknown');
    direction = relation === 'own_accounts' ? 'not_applicable' : 'uncertain';
  }
  // Confirmation supplies relationship only; extraction above remains body-derived.
  if (ownershipOverride) {
    relation = ownershipOverride.relationship;
    if (ownershipOverride.uncertainDirection || direction === 'not_applicable') direction = 'uncertain';
    if (relation === 'own_accounts') direction = 'not_applicable';
  }
  return [direction,relation];
}

export function recordingDecision(status: DetailedResult['transactionStatus'],amount: number | null,direction: DetailedResult['direction'],relation: DetailedResult['transferRelationship']): DetailedResult['trackingDecision'] {
  let decision: DetailedResult['trackingDecision'] = 'review';
  if (status === 'completed') {
    if (relation === 'own_accounts') decision = 'exclude';
    else if (amount !== null && direction !== 'uncertain' && relation !== 'unknown') decision = 'include';
  }
  return decision;
}
