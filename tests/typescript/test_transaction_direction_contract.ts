import fs from 'fs';
import path from 'path';
import { PREPROCESSING_CONTRACT_VERSION, preprocessMessage, tokenizeFeatures } from '../../src/typescript/Preprocessing.ts';
import { evaluateTransactionDirectionModel, TRANSACTION_DIRECTION_CONTRACT_VERSION } from '../../src/typescript/TransactionDirection.ts';

const fixtureRoot = path.join(process.cwd(), 'tests', 'fixtures');
const contract = JSON.parse(fs.readFileSync(path.join(fixtureRoot, 'transaction_direction_contract.json'), 'utf-8'));
const vectors = JSON.parse(fs.readFileSync(path.join(fixtureRoot, 'transaction_direction_score_cases.json'), 'utf-8'));
if (contract.contractVersion !== TRANSACTION_DIRECTION_CONTRACT_VERSION || contract.preprocessingVersion !== PREPROCESSING_CONTRACT_VERSION) {
  throw new Error('Transaction-direction contract version mismatch');
}

const failures: string[] = [];
for (const testCase of vectors.cases) {
  const result = evaluateTransactionDirectionModel(vectors.model, tokenizeFeatures(preprocessMessage(testCase.raw)));
  for (const field of ['transactionLogit', 'transactionProbability', 'directionLogit', 'incomeProbability']) {
    if (Math.abs(result[field] - testCase[field]) > 1e-12) failures.push(`${testCase.id}:${field}`);
  }
  for (const field of ['isTransaction', 'type']) {
    if (result[field] !== testCase[field]) failures.push(`${testCase.id}:${field}`);
  }
}
if (failures.length > 0) throw new Error(`TypeScript transaction-direction contract failures: ${failures.join(', ')}`);
console.log(`TypeScript transaction-direction contract passed: ${vectors.cases.length} vectors.`);
