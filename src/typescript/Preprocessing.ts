/** Versioned preprocessing shared by Masroof inference and training tests. */

export const PREPROCESSING_CONTRACT_VERSION = '1.1.0';

const ROUTING_PREFIX = /^[A-Z]{2}(\r?\n|\s+)/;
const ARABIC_DIACRITICS = /[\u064B-\u065F\u0670]/g;
const WHITESPACE = /\s+/g;
const LONG_NUMBER = /\b\d{6,}\b/g;
const TOKEN = /[A-Za-z0-9_\u0621-\u064A\u0660-\u0669*\.\-]+/g;

export function normalizeFinancialNumbers(text: string): string {
  return text.replace(/[\u0660-\u0669\u06F0-\u06F9\u066B\u066C]/g, char => {
    const code = char.charCodeAt(0);
    if (code >= 0x0660 && code <= 0x0669) return String(code - 0x0660);
    if (code >= 0x06F0 && code <= 0x06F9) return String(code - 0x06F0);
    return code === 0x066B ? '.' : ',';
  });
}

export function preprocessMessage(text: string): string {
  return normalizeFinancialNumbers(text)
    .replace(/\\n/g, '\n')
    .replace(/\r/g, '')
    .replace(ROUTING_PREFIX, '')
    .replace(ARABIC_DIACRITICS, '')
    .replace(WHITESPACE, ' ')
    .replace(LONG_NUMBER, ' NUM_LONG ')
    .trim()
    .toLowerCase();
}

export function tokenizeFeatures(normalizedText: string): string[] {
  const tokens = normalizedText.match(TOKEN) || [];
  const tokenCount = tokens.length;
  for (let index = 0; index < tokenCount - 1; index++) {
    tokens.push(`${tokens[index]} ${tokens[index + 1]}`);
  }
  return tokens;
}
