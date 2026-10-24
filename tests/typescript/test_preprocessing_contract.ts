import fs from 'fs';
import path from 'path';
import { PREPROCESSING_CONTRACT_VERSION, preprocessMessage, tokenizeFeatures } from '../../src/typescript/Preprocessing.ts';

const fixtureRoot = path.join(process.cwd(), 'tests', 'fixtures');
const contract = JSON.parse(fs.readFileSync(path.join(fixtureRoot, 'preprocessing_contract.json'), 'utf-8'));
const cases = JSON.parse(fs.readFileSync(path.join(fixtureRoot, 'preprocessing_contract_cases.json'), 'utf-8'));

if (contract.version !== PREPROCESSING_CONTRACT_VERSION) {
  throw new Error('Preprocessing contract version mismatch');
}

const failures: string[] = [];
for (const testCase of cases) {
  const normalized = preprocessMessage(testCase.raw);
  const features = tokenizeFeatures(normalized);
  if (normalized !== testCase.normalized || JSON.stringify(features) !== JSON.stringify(testCase.features)) {
    failures.push(testCase.id);
  }
}

if (failures.length > 0) {
  throw new Error(`TypeScript preprocessing contract failures: ${failures.join(', ')}`);
}

console.log(`TypeScript preprocessing contract passed: ${cases.length} vectors.`);
