/** Detailed/legacy comparison only; inputs supplied by the caller, no fitting. */
import fs from 'node:fs';
import vm from 'node:vm';
import { MasroofEngine } from '../../src/typescript/MasroofEngine.ts';

const root = new URL('../../', import.meta.url);
MasroofEngine.init(JSON.parse(fs.readFileSync(new URL('data/models/masroof_model.json', root), 'utf8')));
const html = fs.readFileSync(new URL('tools/browser/tester.html', root), 'utf8');
const script = html.match(/<script>([\s\S]*?)<\/script>/)?.[1];
if (!script) throw new Error('Built tester script missing');
const elements: Record<string, any> = {};
const browser = vm.createContext({ performance, document: { addEventListener() {},
  getElementById(id: string) { return elements[id] ??= { value: '', checked: false, innerText: '', style: {} }; } } });
vm.runInContext(script, browser);
const detailed = vm.runInContext('(input) => MasroofRuntime.MasroofEngine.analyzeDetailed(input)', browser);
const legacy = vm.runInContext('(input) => MasroofRuntime.MasroofEngine.analyze(input)', browser);
const inputData = JSON.parse(fs.readFileSync(0, 'utf8'));
const cases = inputData.cases;
const rows = cases.map((row: any) => {
  const input = { sender: row.input.sender ?? '', body: row.input.text, isContact: row.input.isContact ?? false };
  return { id: row.id, typescript: MasroofEngine.analyzeDetailed(row.input), browser: detailed(row.input),
    legacyTypescript: MasroofEngine.analyze(input), legacyBrowser: legacy(input) };
});
let ui = null;
if (inputData.uiCase) {
  const row = inputData.uiCase;
  for (const [id, value] of Object.entries({ senderInput: row.sender ?? '', bodyInput: row.text })) {
    elements[id] = { value, checked: false, innerText: '', style: {} };
  }
  elements.isContactInput = { checked: row.isContact ?? false };
  // Merchant research is separate; inspect the actual assessment UI handler.
  vm.runInContext('updateMerchantSms = function() {}; runAnalysis();', browser);
  ui = { title: elements.detailedDecision.innerText, assessment: JSON.parse(elements.detailedOutput.innerText) };
}
process.stdout.write(JSON.stringify({ rows, ui, bundleSources: vm.runInContext('MasroofRuntime.sourceSha256', browser) }));
