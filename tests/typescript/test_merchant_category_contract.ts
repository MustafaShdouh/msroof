import fs from 'node:fs';
import path from 'node:path';
import assert from 'node:assert/strict';
import { fileURLToPath } from 'node:url';
import { normalizeMerchantName, merchantNameFeatures, loadMerchantCategoryModel, predictMerchantCategory } from '../../src/typescript/MerchantCategory.ts';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const fixture = JSON.parse(fs.readFileSync(path.join(root, 'tests/fixtures/merchant_category_contract.json'), 'utf8'));
for (const c of fixture.normalizationCases) assert.equal(normalizeMerchantName(c.raw), c.expected);
assert.deepEqual(merchantNameFeatures(fixture.scoreCase.raw), fixture.scoreCase.expectedFeatures);
const loaded = loadMerchantCategoryModel(fixture.model);
const result = predictMerchantCategory(loaded, fixture.scoreCase.raw);
assert.equal(result.category, fixture.scoreCase.expectedCategory);
result.logits.forEach((value, i) => assert.ok(Math.abs(value - fixture.scoreCase.expectedLogits[i]) < 1e-12));
for (const c of fixture.abstentionCases) {
    const prediction = predictMerchantCategory(loaded, c.raw);
    assert.equal(prediction.category, null);
    assert.equal(prediction.reason, c.reason);
}
for (const patch of [{ weights: [NaN] }, { classBusinessSupport: [true, 3] }, { classes: ['Food', 'Food'] }, { contractVersion: 'unknown' }])
    assert.throws(() => loadMerchantCategoryModel({ ...fixture.model, ...patch }));
const lowSupport = loadMerchantCategoryModel({ ...fixture.model, classBusinessSupport: [1, 3] });
assert.equal(predictMerchantCategory(lowSupport, 'A').reason, 'insufficient_class_support');

if (process.argv.includes('--parity-input')) {
    const input = JSON.parse(fs.readFileSync(0, 'utf8'));
    const output = input.models.map((name: string) => {
        const model = loadMerchantCategoryModel(JSON.parse(fs.readFileSync(path.join(root, name), 'utf8')));
        return input.texts.map((text: string) => ({ normalized: normalizeMerchantName(text), features: merchantNameFeatures(text), prediction: predictMerchantCategory(model, text) }));
    });
    process.stdout.write(JSON.stringify(output));
} else console.log('Merchant category TypeScript contract passed.');
