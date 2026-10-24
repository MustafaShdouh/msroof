/** Diagnostic bridge for the offline Arabic audit; no runtime code changes. */
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { MasroofEngine } from '../../src/typescript/MasroofEngine.ts';
import { preprocessMessage, tokenizeFeatures } from '../../src/typescript/Preprocessing.ts';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const input = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
MasroofEngine.init(JSON.parse(fs.readFileSync(path.join(root, 'data/models/masroof_model.json'), 'utf8')));
const groups: Record<string, unknown> = {};
for (const [name, rawCases] of Object.entries(input.groups)) {
  const cases = rawCases as any[];
  let classificationCorrect = 0, validTransactionCount = 0, coreCorrect = 0;
  const failures: unknown[] = [];
  for (const testCase of cases) {
    const result = MasroofEngine.analyze({ sender: testCase.sender, body: testCase.body });
    const expected = testCase.expected;
    classificationCorrect += Number(result.isValidTransaction === expected.isValidTransaction);
    if (!expected.isValidTransaction) continue;
    validTransactionCount++;
    const data = result.data;
    const correct = result.isValidTransaction && data?.amount != null && Math.abs(data.amount - expected.amount) < 0.001 && data.currency === expected.currency && data.type === expected.type;
    coreCorrect += Number(correct);
    if (!correct) failures.push({ id: testCase.id, accepted: result.isValidTransaction, expectedAmount: expected.amount, actualAmount: data?.amount ?? null, expectedType: expected.type, actualType: data?.type ?? null });
  }
  groups[name] = { caseCount: cases.length, classificationCorrect, validTransactionCount, amountCurrencyDirectionCorrect: coreCorrect, failures };
}
const preprocessing = input.preprocessingInputs.map((raw: string) => { const normalized = preprocessMessage(raw); return { normalized, features: tokenizeFeatures(normalized) }; });
process.stdout.write(JSON.stringify({ groups, preprocessing }));
