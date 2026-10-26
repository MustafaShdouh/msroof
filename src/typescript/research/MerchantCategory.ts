/** Standalone research scorer. This is not part of MasroofEngine.analyze. */
import { normalizeFinancialNumbers } from '../Preprocessing.ts';

export const MERCHANT_CATEGORY_CONTRACT = 'merchant-name-category-1.0.0';
export function normalizeMerchantName(text: string): string {
    if (typeof text !== 'string') throw new Error('Merchant name must be text');
    return normalizeFinancialNumbers(text.normalize('NFKC')).toLowerCase()
        .replace(/[\u064b-\u065f\u0670\u0640]/g, '')
        .replace(/[^a-z0-9\u00c0-\u024f\u0621-\u064a]+/g, ' ').trim();
}
export function merchantNameFeatures(text: string): string[] {
    const name = normalizeMerchantName(text);
    if (!name) return [];
    const features = new Set(name.split(' ').map(word => 'w:' + word));
    const padded = '^' + name + '$';
    for (const size of [3, 4, 5]) for (let i = 0; i <= padded.length - size; i++)
        features.add('c' + size + ':' + padded.slice(i, i + size));
    return [...features].sort();
}
export type MerchantCategoryModel = {
    contractVersion: string; classes: string[]; features: string[]; weights: number[];
    bias: number[]; classBusinessSupport: number[];
    abstention: { minScore: number; minMargin: number; minKnownFeatureFraction: number; minClassBusinesses: number };
};
export function loadMerchantCategoryModel(model: MerchantCategoryModel) {
    if (model.contractVersion !== MERCHANT_CATEGORY_CONTRACT) throw new Error('Unsupported merchant category contract');
    if (!Array.isArray(model.classes) || !model.classes.length || model.classes.some(x => typeof x !== 'string' || !x) || new Set(model.classes).size !== model.classes.length) throw new Error('Invalid classes');
    if (!Array.isArray(model.features) || model.features.some(x => typeof x !== 'string' || !x) || model.features.some((x, i) => i > 0 && x <= model.features[i - 1])) throw new Error('Invalid features');
    for (const [key, size] of [['weights', model.features.length * model.classes.length], ['bias', model.classes.length], ['classBusinessSupport', model.classes.length]] as const) {
        if (!Array.isArray(model[key]) || model[key].length !== size || model[key].some(x => typeof x !== 'number' || !Number.isFinite(x))) throw new Error('Invalid ' + key);
    }
    if (model.classBusinessSupport.some(x => !Number.isInteger(x) || x < 1)) throw new Error('Invalid business support');
    for (const key of ['minScore', 'minMargin', 'minKnownFeatureFraction'] as const) {
        const value = model.abstention[key];
        if (typeof value !== 'number' || !Number.isFinite(value) || value < 0 || value > 1) throw new Error('Invalid abstention threshold');
    }
    if (!Number.isInteger(model.abstention.minClassBusinesses) || model.abstention.minClassBusinesses < 1) throw new Error('Invalid minimum class support');
    return { model, index: new Map(model.features.map((feature, i) => [feature, i])) };
}
export function predictMerchantCategory(loaded: ReturnType<typeof loadMerchantCategoryModel>, text: string) {
    const { model, index } = loaded, features = merchantNameFeatures(text);
    const known = features.filter(feature => index.has(feature)).map(feature => index.get(feature)!);
    const fraction = features.length ? known.length / features.length : 0;
    const logits = [...model.bias], scale = known.length ? 1 / Math.sqrt(known.length) : 0;
    for (const feature of known) for (let c = 0; c < logits.length; c++) logits[c] += model.weights[feature * logits.length + c] * scale;
    const maximum = Math.max(...logits), exp = logits.map(value => Math.exp(value - maximum));
    const total = exp.reduce((a, b) => a + b, 0), scores = exp.map(value => value / total);
    const order = scores.map((_, i) => i).sort((a, b) => scores[b] - scores[a] || a - b), top = order[0];
    const margin = scores[top] - (scores.length > 1 ? scores[order[1]] : 0), policy = model.abstention;
    const reason = !features.length ? 'no_features' : !known.length || fraction < policy.minKnownFeatureFraction ? 'insufficient_feature_evidence' :
        model.classBusinessSupport[top] < policy.minClassBusinesses ? 'insufficient_class_support' :
        scores[top] < policy.minScore ? 'low_model_score' : margin < policy.minMargin ? 'small_margin' : 'accepted';
    return { category: reason === 'accepted' ? model.classes[top] : null, topClass: model.classes[top],
        uncalibratedModelScore: scores[top], margin, knownFeatureFraction: fraction, reason, logits, scores };
}
