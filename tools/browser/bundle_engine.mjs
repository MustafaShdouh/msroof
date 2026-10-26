/** Bundle the local runtime graph with Node's parser; no network/build package. */
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { fileURLToPath } from 'node:url';
import { stripTypeScriptTypes } from 'node:module';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const ids = new Map();
const visiting = new Set();
const statements = [];
const hashes = {};
function load(filename) {
  filename = path.resolve(filename);
  const relative = path.relative(root, filename).replaceAll('\\', '/');
  if (!relative.startsWith('src/typescript/') && !relative.startsWith('config/contracts/')) {
    throw new Error('Only local runtime/contract imports may be bundled: ' + relative);
  }
  if (visiting.has(filename)) throw new Error('Runtime import cycle: ' + relative);
  if (ids.has(filename)) return ids.get(filename);
  const id = ids.size;
  ids.set(filename, id);
  visiting.add(filename);
  const source = fs.readFileSync(filename, 'utf8');
  hashes[relative] = crypto.createHash('sha256').update(source).digest('hex');
  let code;
  if (filename.endsWith('.json')) {
    code = JSON.stringify(JSON.parse(source));
  } else if (filename.endsWith('.ts')) {
    let stripped = stripTypeScriptTypes(source);
    stripped = stripped.replace(/^import\s+(.+?)\s+from\s+['"]([^'"]+)['"](?:\s+with\s*\{[^\n]*\})?;[ \t]*$/gm,
      (_, binding, specifier) => {
        if (!specifier.startsWith('.')) throw new Error('External runtime import unsupported: ' + specifier);
        const dependency = load(path.resolve(path.dirname(filename), specifier));
        if (!/^\{[^}]+\}$/.test(binding) && !/^[A-Za-z_$][\w$]*$/.test(binding)) {
          throw new Error('Unsupported import binding: ' + binding);
        }
        return `const ${binding} = __modules[${dependency}];`;
      });
    const exports = [...stripped.matchAll(/^export\s+(?:const|let|function|class)\s+([A-Za-z_$][\w$]*)/gm)].map(match => match[1]);
    stripped = stripped.replace(/^export /gm, '');
    if (/^\s*(?:import|export)\s/m.test(stripped)) throw new Error('Unsupported module syntax: ' + relative);
    code = `(() => {\n${stripped}\nreturn {${exports.join(',')}};\n})()`;
  } else {
    throw new Error('Unsupported runtime file: ' + relative);
  }
  statements.push(`__modules[${id}] = ${code};`);
  visiting.delete(filename);
  return id;
}
const engine = load(path.join(root, 'src/typescript/MasroofEngine.ts'));
const preprocessing = load(path.join(root, 'src/typescript/Preprocessing.ts'));
const notice = load(path.join(root, 'src/typescript/ServiceNotice.ts'));
process.stdout.write(`const MasroofRuntime = (() => {\nconst __modules = [];\n${statements.join('\n')}\nreturn { ...__modules[${engine}], preprocessing: __modules[${preprocessing}], serviceNotice: __modules[${notice}], sourceSha256: ${JSON.stringify(hashes)} };\n})();\n`);
