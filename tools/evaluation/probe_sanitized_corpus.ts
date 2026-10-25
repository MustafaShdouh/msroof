// Diagnostic only: report legacy behavior; a zero process exit is not acceptance.
import fs from 'node:fs';
import { MasroofEngine } from '../../src/typescript/MasroofEngine.ts';

const modelPath = new URL('../../data/models/masroof_model.json', import.meta.url);
MasroofEngine.init(JSON.parse(fs.readFileSync(modelPath, 'utf8')));
const cases = JSON.parse(fs.readFileSync(0, 'utf8')).cases;
const result = { cases: 0, classificationCorrect: 0, falsePositive: 0, falseNegative: 0,
  entityMismatches: 0, failures: [] as Array<{caseId: string; field: string; kind?: string}> };
function norm(value: unknown): string | null {
  return value === null || value === undefined ? null : String(value).replace(/[\u064b-\u065f\u0670]/g, '').replace(/\s+/g, ' ').trim().toLowerCase();
}
function currency(value: unknown) {
  const normalized = norm(value);
  return normalized === '$' ? 'usd' : normalized === '€' ? 'eur' : normalized === '£' ? 'gbp' : normalized;
}
for (const item of cases) {
  result.cases++;
  const actual = MasroofEngine.analyze({ sender: item.sender, body: item.body });
  const expected = item.expected;
  if (actual.isValidTransaction !== expected.isValidTransaction) {
    const kind = actual.isValidTransaction ? 'falsePositive' : 'falseNegative';
    result[kind]++;
    result.failures.push({ caseId: item.id, field: 'classification', kind });
    continue;
  }
  result.classificationCorrect++;
  if (!expected.isValidTransaction) continue;
  const data = actual.data as unknown as Record<string, unknown> | null;
  for (const field of ['type', 'amount', 'currency', 'merchantOrParty', 'accountMask', 'balance']) {
    const wanted = expected[field];
    if (wanted === null || wanted === undefined) continue;
    const got = data?.[field];
    let ok: boolean;
    if (field === 'amount' || field === 'balance') ok = typeof got === 'number' && Math.abs(wanted - got) < .001;
    else if (field === 'currency') ok = currency(wanted) === currency(got);
    else {
      const a = norm(wanted)!; const b = norm(got);
      ok = b !== null && (a === b || ((field === 'merchantOrParty' || field === 'accountMask') && (a.includes(b) || b.includes(a))));
    }
    if (!ok) {
      result.entityMismatches++;
      result.failures.push({ caseId: item.id, field });
    }
  }
}
process.stdout.write(JSON.stringify(result));
