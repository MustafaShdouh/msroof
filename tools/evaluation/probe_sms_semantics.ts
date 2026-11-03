/** Run the same research source in TypeScript and an isolated browser-compatible VM. */
import fs from 'node:fs';
import vm from 'node:vm';
import crypto from 'node:crypto';
import { stripTypeScriptTypes } from 'node:module';
import { SmsSemanticsModel } from '../../src/typescript/research/SmsSemantics.ts';

const root = new URL('../../', import.meta.url);
const paths = ['src/typescript/Preprocessing.ts', 'src/typescript/research/SmsSemantics.ts', 'config/contracts/sms_semantics_model.json'];
const sources = paths.map(path => fs.readFileSync(new URL(path, root), 'utf8'));
const hashes = Object.fromEntries(paths.map((path, index) => [path, crypto.createHash('sha256').update(sources[index]).digest('hex')]));
const preprocessing = stripTypeScriptTypes(sources[0]).replace(/^export /gm, '');
const scorer = stripTypeScriptTypes(sources[1]).replace(/^import .*;[ \t]*$/gm, '').replace(/^export /gm, '');
const bundle = `const SmsSemanticsResearch = (() => {\nconst contract = ${JSON.stringify(JSON.parse(sources[2]))};\n${preprocessing}\n${scorer}\nreturn { SmsSemanticsModel, sourceSha256: ${JSON.stringify(hashes)} };\n})();\n`;
if (process.argv.includes('--bundle')) {
  process.stdout.write(bundle);
} else {
  const data = JSON.parse(fs.readFileSync(0, 'utf8'));
  if (data.browserRuntime !== bundle) throw new Error('Browser source does not match current research sources');
  const browser = vm.createContext({});
  vm.runInContext(data.browserRuntime, browser);
  const create = vm.runInContext('(model) => new SmsSemanticsResearch.SmsSemanticsModel(model)', browser);
  const rows = data.models.map((model: any) => {
    const ts = new SmsSemanticsModel(model), web = create(model);
    return { arm: model.arm, typescript: data.texts.map((text: string) => ts.predict(text)),
      browser: data.texts.map((text: string) => web.predict(text)) };
  });
  process.stdout.write(JSON.stringify({ rows, sourceSha256: hashes }));
}
