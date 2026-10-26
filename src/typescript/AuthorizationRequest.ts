/** Shared code-request grammar; no institution, sender or merchant names. */
import rules from '../../config/contracts/authorization_request.json' with { type: 'json' };
import { normalizeFinancialNumbers } from './Preprocessing.ts';

export const AUTHORIZATION_REQUEST_REASON = rules.reason;
const REQUESTS = [
  rules.englishCode + rules.codeValue + rules.englishConnector + rules.englishGoal,
  '\\bto\\s+' + rules.englishGoal + rules.englishReverseConnector + rules.englishCode,
  rules.arabicCode + rules.codeValue + rules.arabicGoal,
  rules.arabicGoal + rules.arabicReverseConnector + rules.arabicCode,
].map(pattern => new RegExp(pattern, 'i'));
const DIACRITICS = /[\u064B-\u065F\u0670]/g;

export function isAuthorizationRequest(body: string): boolean {
  const text = normalizeFinancialNumbers(body).replace(DIACRITICS, '');
  for (const pattern of REQUESTS) {
    if (pattern.test(text)) return true;
  }
  return false;
}
