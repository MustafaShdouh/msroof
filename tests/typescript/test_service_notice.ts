/** Semantic guard checks, including full-result parity with the built tester. */
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';
import { fileURLToPath } from 'node:url';
import { MasroofEngine } from '../../src/typescript/MasroofEngine.ts';
import { isServiceNotice, SERVICE_NOTICE_REASON } from '../../src/typescript/ServiceNotice.ts';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const read = (name: string) => JSON.parse(fs.readFileSync(path.join(root, name), 'utf8'));
MasroofEngine.init(read('data/models/masroof_model.json'));
const html = fs.readFileSync(path.join(root, 'tools/browser/tester.html'), 'utf8');
const script = html.match(/<script>([\s\S]*?)<\/script>/)?.[1];
assert.ok(script);
const browser = vm.createContext({ performance, document: { addEventListener() {} } });
vm.runInContext(script, browser);
const outputs = [];
for (const testCase of read('tests/fixtures/service_notice_cases.json').cases) {
  const notice = isServiceNotice(testCase.body);
  assert.equal(notice, testCase.isServiceNotice, testCase.id);
  assert.equal(browser.isServiceNotice(testCase.body), notice, `Browser guard: ${testCase.id}`);
  const result = MasroofEngine.analyze({ sender: 'SERVICE', body: testCase.body });
  if (notice) {
    assert.deepEqual(result, { isValidTransaction: false, confidence: 0, reason: SERVICE_NOTICE_REASON, data: null }, testCase.id);
  }
  if ('isValidTransaction' in testCase) {
    assert.equal(result.isValidTransaction, testCase.isValidTransaction, testCase.id);
  }
  // Full-result comparison for every new scenario, not just decision parity.
  assert.equal(JSON.stringify(browser.analyze('SERVICE', testCase.body, false).result), JSON.stringify(result), `Browser result: ${testCase.id}`);
  outputs.push({ id: testCase.id, notice, result });
}
console.log(JSON.stringify(outputs));
