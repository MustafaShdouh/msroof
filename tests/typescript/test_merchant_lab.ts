/** Exercise the built offline page, shared scorer, controls and SMS connection. */
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';
import { fileURLToPath } from 'node:url';
import { loadMerchantCategoryModel, predictMerchantCategory } from '../../src/typescript/MerchantCategory.ts';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const read = (name: string) => JSON.parse(fs.readFileSync(path.join(root, name), 'utf8'));
const html = fs.readFileSync(path.join(root, 'tools/browser/tester.html'), 'utf8');
const elements = new Map<string, any>();
const element = (id: string) => {
  if (!elements.has(id)) elements.set(id, {value: '', textContent: '', innerText: '', checked: false, style: {}});
  return elements.get(id);
};
const ready: Function[] = [];
const browser = vm.createContext({performance, document: {
  getElementById: element,
  addEventListener(event: string, fn: Function) { if (event === 'DOMContentLoaded') ready.push(fn); }
}});
vm.runInContext(html.match(/<script>([\s\S]*?)<\/script>/)![1], browser);
ready.forEach(fn => fn());
assert.equal(element('merchantVariant').value, 'baseline');
assert.match(element('merchantMetrics').textContent, /166 distinct businesses/);
assert.match(element('merchantSmsResult').textContent, /Name:/);

const report = read(vm.runInContext('MERCHANT_LAB_DATA.reportPath', browser));
const plan = read('data/training/splits/category_brand_split.json');
const base = fs.readFileSync(path.join(root, 'data/annotations/businesses_200.jsonl'), 'utf8').trim().split('\n').map(JSON.parse);
const extension = fs.readFileSync(path.join(root, 'data/annotations/merchant_training_extension.jsonl'), 'utf8').trim().split('\n').map(JSON.parse);
const round3 = read('data/sources/businesses/jordan_training_round3.json').businesses;
const texts = [...base.filter((row: any) => plan.businessAssignments[row.businessId] !== 'test'), ...extension, ...round3]
  .flatMap((row: any) => [row.name, ...row.aliases]);
texts.push('', '؟؟؟', '١٢٣ متجر غير معروف', '<img src=x onerror=alert(1)>');
for (const [variant, item] of Object.entries(report.variants) as any) {
  element('merchantVariant').value = variant;
  const loaded = loadMerchantCategoryModel(read(item.modelPath));
  for (const text of texts) {
    const actual = JSON.parse(JSON.stringify(browser.merchantLabPrediction(text)));
    assert.deepEqual(actual, predictMerchantCategory(loaded, text));
  }
  browser.setMerchantExample('Netflix');
  assert.match(element('merchantNameResult').textContent, /Name: Netflix/);
  browser.updateMerchantSms({isValidTransaction: true, data: {type: 'EXPENSE', merchantOrParty: 'Netflix'}});
  assert.equal(element('merchantSmsResult').textContent, element('merchantNameResult').textContent);
}
browser.updateMerchantSms({isValidTransaction: true, data: {type: 'INCOME', merchantOrParty: 'Netflix'}});
assert.match(element('merchantSmsResult').textContent, /Incoming transaction/);
browser.updateMerchantSms({isValidTransaction: true, data: {type: 'EXPENSE', merchantOrParty: null}});
assert.match(element('merchantSmsResult').textContent, /No merchant extracted/);
element('bodyInput').value = '';
browser.runAnalysis();
assert.match(element('merchantSmsResult').textContent, /No accepted transaction/);
assert.equal(report.testInferencePerformed, false);
assert.equal(report.testMetrics, null);
console.log(`Merchant tester passed: three models, ${texts.length} non-test names each, control/SMS/empty/income paths.`);
