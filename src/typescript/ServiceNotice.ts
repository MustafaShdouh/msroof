/** Narrow semantic guard; the shared grammar contains no institution names. */
import rules from '../../config/contracts/service_notice.json' with { type: 'json' };

const SERVICE = new RegExp(rules.servicePattern, 'i');
const AVAILABILITY = new RegExp(rules.availabilityPattern, 'i');
const COMPLETION = new RegExp(rules.completionPattern, 'i');
const DIACRITICS = /[\u064B-\u065F\u0670]/g;

export const SERVICE_NOTICE_REASON = rules.reason;

export function isServiceNotice(body: string): boolean {
  const text = body.replace(DIACRITICS, '');
  // A receipt can carry a separate maintenance reminder. Let normal inference
  // handle messages that also contain explicit completed-payment wording.
  return SERVICE.test(text) && AVAILABILITY.test(text) && !COMPLETION.test(text);
}
