import assert from 'node:assert/strict';
import fs from 'node:fs';
import { scoreLegacyTransactionModel } from '../../src/typescript/LegacyTransactionModel.ts';
const cases = JSON.parse(fs.readFileSync(new URL('../fixtures/legacy_model_score_cases.json', import.meta.url), 'utf8'));
const output = new Float64Array(2);
const results = [];
for (const item of cases) {
  output.fill(999);
  scoreLegacyTransactionModel(item.model, item.tokens, output);
  const expected = [item.transactionLogit, item.incomingLogit].map(value => 1 / (1 + Math.exp(-value)));
  for (let index = 0; index < 2; index++) assert.ok(Math.abs(output[index] - expected[index]) < 1e-14, item.id);
  results.push([...output]);
}
console.log(JSON.stringify(results));
