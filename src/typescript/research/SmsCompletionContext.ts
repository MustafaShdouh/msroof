/** Research-only short word sequences; no semantic keyword rules or threshold tuning. */
import contextContract from '../../../config/contracts/sms_completion_context.json' with { type: 'json' };
import contract from '../../../config/contracts/sms_semantics_model.json' with { type: 'json' };
import { normalize, features as wordFeatures, codePointCompare } from './SmsSemantics.ts';

export function contextFeatures(text: string): string[] {
  const words = normalize(text).match(/[\p{L}\p{N}_]+/gu) ?? [];
  const result = new Set<string>();
  contextContract.lengths.forEach((size, order) => {
    for (let i = 0; i <= words.length - size; i++) result.add(contextContract.prefixes[order] + words.slice(i, i + size).join(' '));
  });
  return [...result].sort(codePointCompare);
}

export function validateContextModel(model: any): void {
  if (!model || model.contractVersion !== contextContract.contractVersion || model.kind !== 'completion_context' || !model.heads ||
      JSON.stringify(Object.keys(model.heads).sort()) !== JSON.stringify(Object.keys(contract.heads).sort())) throw new Error('Invalid context model kind/version/heads');
  for (const [name, head] of Object.entries(model.heads) as [string, any][]) {
    const prefixes = name === 'completion' ? contextContract.prefixes : ['w|'];
    if (!Array.isArray(head.vocabulary) || head.vocabulary.some((x: any) => typeof x !== 'string' || !prefixes.some(p => x.startsWith(p))) ||
        head.vocabulary.some((x: string, i: number) => i > 0 && codePointCompare(head.vocabulary[i - 1], x) >= 0)) throw new Error('Invalid context vocabulary/order/encoding');
    if (!Array.isArray(head.weights) || head.weights.length !== head.vocabulary.length || head.weights.some((x: any) => typeof x !== 'number' || !Number.isFinite(x)) ||
        typeof head.intercept !== 'number' || !Number.isFinite(head.intercept)) throw new Error('Invalid context flat weights/intercept');
    const labels = (contract.heads as any)[name];
    if (!head.labels || Object.keys(head.labels).length !== 2 || head.labels.positive !== labels.positive || head.labels.negative !== labels.negative) throw new Error('Invalid context head labels');
  }
}

export class SmsCompletionContextModel {
  model: any;
  indices: Record<string, Map<string, number>>;
  constructor(model: any) {
    validateContextModel(model);
    this.model = model;
    this.indices = Object.fromEntries(Object.entries(model.heads).map(([name, head]: [string, any]) =>
      [name, new Map(head.vocabulary.map((word: string, index: number) => [word, index]))]));
  }
  predict(text: string): any {
    const emitted: Record<string, string[]> = { completion: contextFeatures(text), direction: wordFeatures(text, 'word') };
    const heads: Record<string, any> = {};
    for (const [name, head] of Object.entries(this.model.heads) as [string, any][]) {
      const lookup = this.indices[name];
      const active = emitted[name].filter(x => lookup.has(x)).map(x => lookup.get(x)!).sort((a, b) => a - b);
      let score = head.intercept;
      for (const index of active) score += head.weights[index];
      if (!Number.isFinite(score)) throw new Error('Non-finite context score');
      heads[name] = { activeIndices: active, score, prediction: head.labels[score > 0 ? 'positive' : 'negative'] };
    }
    return { normalized: normalize(text), features: emitted, heads };
  }
}
