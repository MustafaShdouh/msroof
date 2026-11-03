/** Build the browser scorer from the exact TypeScript sources and verify it in a VM. */
import fs from 'node:fs';
import vm from 'node:vm';
import crypto from 'node:crypto';
import { stripTypeScriptTypes } from 'node:module';
import { SmsCompletionContextModel } from '../../src/typescript/research/SmsCompletionContext.ts';

const root = new URL('../../', import.meta.url);
const paths = ['src/typescript/Preprocessing.ts', 'src/typescript/research/SmsSemantics.ts', 'src/typescript/research/SmsCompletionContext.ts',
  'config/contracts/sms_semantics_model.json', 'config/contracts/sms_completion_context.json'];
const raw = paths.map(path => fs.readFileSync(new URL(path, root)));
const hashes = Object.fromEntries(paths.map((path, i) => [path, crypto.createHash('sha256').update(raw[i]).digest('hex')]));
const sources = raw.slice(0, 3).map(bytes => stripTypeScriptTypes(bytes.toString('utf8')).replace(/^import .*;[ \t]*$/gm, '').replace(/^export /gm, ''));
// Imported alias has to survive import stripping; both names resolve to identical original word features.
const bundle = `const SmsSemanticsResearch = (() => {\nconst contract = ${raw[3]};\nconst contextContract = ${raw[4]};\n${sources[0]}\n${sources[1]}\nconst wordFeatures = features;\n${sources[2]}\nreturn { SmsSemanticsModel: SmsCompletionContextModel, sourceSha256: ${JSON.stringify(hashes)} };\n})();\n`;
if (process.argv.includes('--bundle')) process.stdout.write(bundle);
else {
  const data = JSON.parse(fs.readFileSync(0, 'utf8'));
  if (data.browserRuntime !== bundle) throw new Error('Context browser bundle differs from source');
  const context = vm.createContext({});
  vm.runInContext(bundle, context);
  const create = vm.runInContext('(model) => new SmsSemanticsResearch.SmsSemanticsModel(model)', context);
  const ts = new SmsCompletionContextModel(data.model), browser = create(data.model);
  process.stdout.write(JSON.stringify({ sourceSha256: hashes,
    typescript: data.texts.map((text: string) => ts.predict(text)), browser: data.texts.map((text: string) => browser.predict(text)) }));
}
