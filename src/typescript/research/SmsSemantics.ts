/** Isolated research feature/export contract; never used by the active engine. */
import contract from '../../../config/contracts/sms_semantics_model.json' with { type: 'json' };
import { normalizeFinancialNumbers } from '../Preprocessing.ts';

export function codePointCompare(left: string, right: string): number {
  const a = Array.from(left), b = Array.from(right);
  for (let index = 0; index < Math.min(a.length, b.length); index++) {
    const difference = a[index].codePointAt(0)! - b[index].codePointAt(0)!;
    if (difference) return difference;
  }
  return a.length - b.length;
}

export function normalize(text: string): string {
  if (typeof text !== 'string') throw new TypeError('text must be a string');
  let value = normalizeFinancialNumbers(text.normalize('NFC')).replace(/\\n/g, '\n').replace(/\r/g, '');
  if (value.startsWith('JO\n')) value = value.slice(3);
  value = value.replace(/[\u064b-\u065f\u0670]/g, '').replace(/[A-Z]/g, char => char.toLowerCase());
  return value.replace(new RegExp(contract.numericPattern, 'g'), ' num ')
    .replace(new RegExp(contract.whitespacePattern, 'g'), ' ').replace(/^ +| +$/g, '');
}

export function features(text: string, arm: string): string[] {
  if (!contract.arms.includes(arm)) throw new Error('Unsupported research arm');
  const value = normalize(text);
  const result = new Set((value.match(/[\p{L}\p{N}_]+/gu) ?? []).map(word => 'w|' + word));
  if (arm === 'word_char') {
    const chars = Array.from(value);
    for (const length of [3, 4, 5]) {
      for (let index = 0; index <= chars.length - length; index++) result.add(`c${length}|` + chars.slice(index, index + length).join(''));
    }
  }
  return [...result].sort(codePointCompare);
}

export function validateModel(model: any): void {
  if (!model || model.contractVersion !== contract.contractVersion || !contract.arms.includes(model.arm) ||
      !model.heads || JSON.stringify(Object.keys(model.heads).sort()) !== JSON.stringify(Object.keys(contract.heads).sort())) throw new Error('Invalid research model/version/arm/heads');
  for (const [name, head] of Object.entries(model.heads) as [string, any][]) {
    if (!Array.isArray(head.vocabulary) || head.vocabulary.some((word: any) => typeof word !== 'string') ||
        head.vocabulary.some((word: string, index: number) => index > 0 && codePointCompare(head.vocabulary[index - 1], word) >= 0)) throw new Error('Invalid vocabulary order/duplicates');
    const prefixes = model.arm === 'word' ? ['w|'] : ['w|', 'c3|', 'c4|', 'c5|'];
    if (head.vocabulary.some((word: string) => !prefixes.some(prefix => word.startsWith(prefix)))) throw new Error('Feature encoding does not match arm');
    if (!Array.isArray(head.weights) || head.weights.length !== head.vocabulary.length || head.weights.some((weight: any) => typeof weight !== 'number' || !Number.isFinite(weight)) ||
        typeof head.intercept !== 'number' || !Number.isFinite(head.intercept)) throw new Error('Invalid flat weights/intercept');
    const labels = (contract.heads as any)[name];
    if (!head.labels || Object.keys(head.labels).length !== 2 || head.labels.positive !== labels.positive || head.labels.negative !== labels.negative) throw new Error('Invalid head labels');
  }
}

export class SmsSemanticsModel {
  model: any;
  indices: Record<string, Map<string, number>>;
  constructor(model: any) {
    validateModel(model);
    this.model = model;
    this.indices = Object.fromEntries(Object.entries(model.heads).map(([name, head]: [string, any]) =>
      [name, new Map(head.vocabulary.map((word: string, index: number) => [word, index]))]));
  }
  predict(text: string): any {
    const emitted = features(text, this.model.arm);
    const heads: Record<string, any> = {};
    for (const [name, head] of Object.entries(this.model.heads) as [string, any][]) {
      const lookup = this.indices[name];
      const active = emitted.filter(word => lookup.has(word)).map(word => lookup.get(word)!).sort((a, b) => a - b);
      let score = head.intercept;
      for (const index of active) score += head.weights[index];
      if (!Number.isFinite(score)) throw new Error('Non-finite accumulated score');
      heads[name] = { activeIndices: active, score, prediction: head.labels[score > 0 ? 'positive' : 'negative'] };
    }
    return { normalized: normalize(text), features: emitted, heads };
  }
}
