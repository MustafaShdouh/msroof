/** Isolated research scorer; never used by the deployed SMS extractor. */
import { normalizeBioToken } from './BioNormalization.ts';
import { normalizeFinancialNumbers } from '../Preprocessing.ts';

export const CONTEXT_TAGS = ['O', 'B-AMT', 'I-AMT', 'B-CURR', 'I-CURR', 'B-MERCHANT', 'I-MERCHANT', 'B-ACCT', 'I-ACCT', 'B-BAL', 'I-BAL'];
export const FEATURE_CONTRACT = 'bio-context-1.0.0';

function tokenParts(raw: string): [string, string[]] {
  const value = normalizeBioToken(normalizeFinancialNumbers(raw));
  const digits = (value.match(/[0-9]/g) || []).length;
  if (digits && /^[0-9*x]+$/.test(value) && /[*x]/.test(value)) {
    return ['<MASK>', ['mask', `digits:${Math.min(digits, 8)}`]];
  }
  if (/^[0-9]+(?:[.,'’][0-9]+)*$/.test(value)) {
    const shape = ['number', `digits:${Math.min(digits, 8)}`];
    const final = /[.,]([0-9]+)$/.exec(value);
    shape.push(final ? `fraction:${Math.min(final[1].length, 4)}` : (/^[0-9]+$/.test(value) ? 'integer' : 'grouped'));
    return ['<NUMBER>', shape];
  }
  if (/^[a-z\u0621-\u064a]+$/.test(value)) return [value, ['word']];
  return [value, [value && !/[\p{L}\p{N}]/u.test(value) ? 'punct' : 'mixed']];
}

export function contextFeatures(tokens: readonly string[]): string[][] {
  const parts = tokens.map(tokenParts);
  return parts.map(([word, shape], index) => {
    const features = ['bias', `w0=${word}`, ...shape.map(item => `s0=${item}`)];
    for (const offset of [-2, -1, 1, 2]) {
      const at = index + offset;
      const neighbor = at >= 0 && at < parts.length ? parts[at][0] : (at < 0 ? '<BOS>' : '<EOS>');
      features.push(`w${offset}=${neighbor}`);
    }
    for (const offset of [-1, 1]) {
      const at = index + offset;
      const shapes = at >= 0 && at < parts.length ? parts[at][1] : [at < 0 ? 'BOS' : 'EOS'];
      for (const item of shapes) features.push(`s${offset}=${item}`);
    }
    return features;
  });
}

interface ContextExport {
  version: string;
  featureContract: string;
  tags: string[];
  featureIndex: Record<string, number>;
  emissionWeights: number[];
  transitionWeights: number[];
}

export class ContextBioModel {
  private readonly featureIndex: Record<string, number>;
  private readonly emission: Float32Array;
  private readonly transition: Float32Array;

  constructor(model: ContextExport) {
    if (!model || model.version !== '2.0.0' || model.featureContract !== FEATURE_CONTRACT || JSON.stringify(model.tags) !== JSON.stringify(CONTEXT_TAGS)) {
      throw new Error('Unsupported context BIO model contract');
    }
    const index = model.featureIndex;
    if (!index || typeof index !== 'object' || Array.isArray(index)) throw new Error('Invalid feature index');
    const values = Object.values(index);
    if (values.some(value => !Number.isInteger(value) || value < 0 || value >= values.length) || new Set(values).size !== values.length) {
      throw new Error('Feature indexes must be contiguous');
    }
    if (!Array.isArray(model.emissionWeights) || !Array.isArray(model.transitionWeights) ||
        model.emissionWeights.length !== values.length * CONTEXT_TAGS.length || model.transitionWeights.length !== CONTEXT_TAGS.length ** 2) {
      throw new Error('Context BIO weight dimensions mismatch');
    }
    for (const array of [model.emissionWeights, model.transitionWeights]) {
      if (array.some(value => typeof value !== 'number' || !Number.isFinite(value) || !Number.isFinite(Math.fround(value)))) {
        throw new Error('Context BIO weights must fit finite float32');
      }
    }
    this.featureIndex = Object.assign(Object.create(null), index);
    this.emission = new Float32Array(model.emissionWeights);
    this.transition = new Float32Array(model.transitionWeights);
  }

  predict(tokens: readonly string[]): number[] {
    const result: number[] = [];
    const count = CONTEXT_TAGS.length;
    const scores = new Float32Array(count);
    let previous: number | null = null;
    for (const features of contextFeatures(tokens)) {
      scores.fill(0);
      for (const feature of features) {
        const index = this.featureIndex[feature];
        if (index !== undefined) {
          for (let tag = 0; tag < count; tag++) scores[tag] += this.emission[index * count + tag];
        }
      }
      if (previous !== null) {
        for (let tag = 0; tag < count; tag++) scores[tag] += this.transition[previous * count + tag];
      }
      let best = 0;
      for (let tag = 1; tag < count; tag++) {
        const legal = tag % 2 === 1 || previous === tag - 1 || previous === tag;
        if (legal && scores[tag] > scores[best]) best = tag;
      }
      result.push(best);
      previous = best;
    }
    return result;
  }
}
