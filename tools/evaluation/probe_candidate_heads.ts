import fs from 'node:fs';
import { evaluateTransactionDirectionModel, validateTransactionDirectionModel } from '../../src/typescript/research/TransactionDirection.ts';
const input = JSON.parse(fs.readFileSync(0, 'utf8'));
if (!validateTransactionDirectionModel(input.model)) throw new Error('Invalid candidate');
process.stdout.write(JSON.stringify(input.features.map((features: string[]) => evaluateTransactionDirectionModel(input.model, features))));
