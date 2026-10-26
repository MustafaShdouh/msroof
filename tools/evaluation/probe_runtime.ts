/** Read-only model/runtime probes; no merchant final-fold loading or fitting. */
import fs from 'node:fs';
import vm from 'node:vm';
import { MasroofEngine } from '../../src/typescript/MasroofEngine.ts';

const root = new URL('../../', import.meta.url);
MasroofEngine.init(JSON.parse(fs.readFileSync(new URL('data/models/masroof_model.json', root), 'utf8')));
const html = fs.readFileSync(new URL('tools/browser/tester.html', root), 'utf8');
const script = html.match(/<script>([\s\S]*?)<\/script>/)?.[1];
if (!script) throw new Error('Built tester script missing');
const browser = vm.createContext({ performance, document: { addEventListener() {} } });
vm.runInContext(script, browser);
const inputs = JSON.parse(fs.readFileSync(0, 'utf8'));
function capture(fn: () => unknown) {
  try { return { result: fn() }; }
  catch (error) { return { error: error instanceof Error ? error.name : 'RuntimeError' }; }
}
const typescript = inputs.cases.map((row: any) => ({ id: row.id, ...capture(() => MasroofEngine.analyze({
  sender: row.input.sender ?? '', body: row.input.text, isContact: row.input.isContact ?? false,
})) }));
const web = inputs.cases.map((row: any) => ({ id: row.id, ...capture(() =>
  browser.analyze(row.input.sender ?? '', row.input.text, row.input.isContact ?? false).result) }));
const categories = inputs.categoryProbes.map((row: any) => ({ id: row.id,
  typescript: capture(() => MasroofEngine.classifyCategory(null, row.text)),
  browser: capture(() => browser.classifyCategory(null, row.text)),
}));
process.stdout.write(JSON.stringify({ typescript, browser: web, categories,
  bundleSources: vm.runInContext('MasroofRuntime.sourceSha256', browser),
  bundledModelMatchesSource: JSON.stringify(vm.runInContext('MODEL', browser)) === JSON.stringify(JSON.parse(fs.readFileSync(new URL('data/models/masroof_model.json', root), 'utf8'))),
}));
