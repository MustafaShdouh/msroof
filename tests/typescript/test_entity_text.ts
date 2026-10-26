import assert from 'node:assert/strict';
import fs from 'node:fs';
import { MasroofEngine } from '../../src/typescript/MasroofEngine.ts';
const cases = JSON.parse(fs.readFileSync(new URL('../fixtures/entity_text_cases.json', import.meta.url), 'utf8')).cases;
MasroofEngine.init(JSON.parse(fs.readFileSync(new URL('../../data/models/masroof_model.json', import.meta.url), 'utf8')));
const outputs = [];
for (const item of cases) {
  const result = MasroofEngine.analyze({ sender: 'SERVICE', body: item.text });
  assert.equal(result.isValidTransaction, true, item.id);
  assert.equal(result.data?.merchantOrParty, item.name, item.id);
  assert.ok(item.text.includes(result.data!.merchantOrParty!), item.id);
  outputs.push(result);
}
MasroofEngine.loadUserOverlay('{"__proto__":1}');
assert.equal(MasroofEngine.classifyCategory('__proto__', '').category, 'Dining & Food Delivery');
MasroofEngine.applyCorrection('NORMAL', 'constructor' as any);
assert.equal(MasroofEngine.exportUserOverlay().normal, undefined);
MasroofEngine.loadUserOverlay('{}');
console.log(JSON.stringify(outputs));
