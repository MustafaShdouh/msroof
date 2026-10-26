/** Existing flat-word BIO normalization, separate from whole-message features. */
export const BIO_NORMALIZATION_VERSION = 'bio-word-1.0.0';
const ARABIC_MAP: Record<string, string> = { 'أ': 'ا', 'إ': 'ا', 'آ': 'ا', 'ى': 'ي', 'ة': 'ه', 'ـ': '' };
export function normalizeBioToken(token: string): string {
  return token.toLowerCase().replace(/[\u0610-\u061a\u064b-\u065f\u0670\u06d6-\u06ed]/g, '')
    .replace(/[أإآىةـ]/g, char => ARABIC_MAP[char]);
}
