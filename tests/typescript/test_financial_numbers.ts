/** Numeric equivalence checks for TypeScript and the optional built browser. */
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';
import { fileURLToPath } from 'node:url';
import { MasroofEngine } from '../../src/typescript/MasroofEngine.ts';
import { normalizeFinancialNumbers } from '../../src/typescript/Preprocessing.ts';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const read = (relative: string) => JSON.parse(fs.readFileSync(path.join(root, relative), 'utf8'));
const vectors = read('tests/fixtures/financial_number_cases.json');
MasroofEngine.init(read('data/models/masroof_model.json'));
const html = fs.readFileSync(path.join(root, 'tools/browser/tester.html'), 'utf8');
const script = html.match(/<script>([\s\S]*?)<\/script>/)?.[1];
assert.ok(script, 'Build the optional browser tester before running its contract checks');
const browser = vm.createContext({ performance, document: { addEventListener() {} } });
vm.runInContext(script, browser);
for (const testCase of vectors) {
  assert.equal(normalizeFinancialNumbers(testCase.raw), testCase.normalized, testCase.id);
  assert.equal(browser.normalizeFinancialNumbers(testCase.raw), testCase.normalized, `Browser: ${testCase.id}`);
  if ('value' in testCase) {
    assert.ok(Math.abs(MasroofEngine.parseNumber(testCase.raw)! - testCase.value) < 1e-12, testCase.id);
    assert.ok(Math.abs(browser.parseNumber(testCase.raw) - testCase.value) < 1e-12, `Browser: ${testCase.id}`);
  }
}
let equivalentCases = 0;
for (const name of ['test_suite_cases.json', 'qa_adversarial_cases.json']) {
  const payload = read(`tests/fixtures/sanitized_v1/${name}`);
  for (const testCase of Array.isArray(payload) ? payload : payload.testCases) {
    const baseline = MasroofEngine.analyze({ sender: testCase.sender, body: testCase.body });
    const browserBaseline = browser.analyze(testCase.sender, testCase.body, false).result;
    for (const [digits, separators] of [['٠١٢٣٤٥٦٧٨٩', false], ['۰۱۲۳۴۵۶۷۸۹', false], ['٠١٢٣٤٥٦٧٨٩', true]] as const) {
      let body = testCase.body.replace(/[0-9]/g, (digit: string) => digits[Number(digit)]);
      if (separators) body = body.replace(/\./g, '٫').replace(/,/g, '٬');
      const expected = structuredClone(baseline);
      const expectedBrowser = JSON.parse(JSON.stringify(browserBaseline));
      for (const output of [expected, expectedBrowser]) {
        if (typeof output.data?.merchantOrParty === 'string') {
          output.data.merchantOrParty = output.data.merchantOrParty.replace(/[0-9]/g, (digit: string) => digits[Number(digit)]);
          if (separators) output.data.merchantOrParty = output.data.merchantOrParty.replace(/\./g, '٫').replace(/,/g, '٬');
        }
      }
      assert.deepEqual(MasroofEngine.analyze({ sender: testCase.sender, body }), expected, testCase.id);
      assert.equal(JSON.stringify(browser.analyze(testCase.sender, body, false).result), JSON.stringify(expectedBrowser), `Browser: ${testCase.id}`);
      equivalentCases++;
    }
  }
}
for (const sender of ['+٩٦٢٧٩١٢٣٤٥٦٧', '٠٧٩١٢٣٤٥٦٧', '+۹۶۲۷۹۱۲۳۴۵۶۷']) {
  const result = MasroofEngine.analyze({ sender, body: 'تم شراء بقيمة ١٢٫٥٠ دينار لدى مطعم' });
  assert.equal(result.isValidTransaction, false);
  assert.equal(result.reason, 'Personal sender (phone number)');
  assert.equal(browser.analyze(sender, 'تم شراء بقيمة ١٢٫٥٠ دينار لدى مطعم', false).result.reason, 'Personal sender (phone number)');
}
console.log(`TypeScript and optional browser financial numbers passed: ${vectors.length} vectors, ${equivalentCases} full-result equivalence cases each, 3 sender guards each.`);
