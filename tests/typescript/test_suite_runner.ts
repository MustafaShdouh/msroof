import { MasroofEngine } from '../../src/typescript/MasroofEngine.ts';
import type { MasroofResult } from '../../src/typescript/MasroofEngine.ts';
import fs from 'fs';
import path from 'path';

const ROOT = process.cwd();

interface TestCase {
  id: string;
  category: string;
  provider: string;
  sender: string;
  description: string;
  body: string;
  expected: {
    isValidTransaction: boolean;
    type?: 'EXPENSE' | 'INCOME';
    amount?: number | null;
    currency?: string;
    accountMask?: string | null;
    account_mask?: string | null;
    merchantOrParty?: string | null;
    merchant_or_party?: string | null;
    balance?: number | null;
  };
}

function normalizeStr(s: any): string | null {
  if (s === null || s === undefined) return null;
  return String(s)
    .replace(/[\u064B-\u065F\u0670]/g, '')
    .replace(/\s+/g, ' ')
    .trim()
    .toLowerCase();
}

function normalizeCurr(c: any): string | null {
  const s = normalizeStr(c);
  if (s === '$') return 'usd';
  if (s === '€') return 'eur';
  if (s === '£') return 'gbp';
  return s;
}

function isClose(a: number | null, b: number | null): boolean {
  if (a === null || b === null) return a === b;
  return Math.abs(a - b) < 0.001;
}

function runTypeScriptSuite(filePath: string = path.join(ROOT, 'tests', 'fixtures', 'sanitized_v1', 'test_suite_cases.json')) {
  const model = JSON.parse(fs.readFileSync(path.join(ROOT, 'data', 'models', 'masroof_model.json'), 'utf-8'));
  MasroofEngine.init(model);

  const rawData = JSON.parse(fs.readFileSync(filePath, 'utf-8'));
  const testCases: TestCase[] = Array.isArray(rawData) ? rawData : rawData.testCases;

  let tp = 0;
  let tn = 0;
  let fp = 0;
  let fn = 0;

  const categoryStats: Record<string, { total: number; correct: number; fp: number; fn: number }> = {};
  const latencies: number[] = [];

  const entityMetrics = {
    type: { match: 0, total: 0 },
    amount: { match: 0, total: 0 },
    currency: { match: 0, total: 0 },
    merchant: { match: 0, total: 0 },
    accountMask: { match: 0, total: 0 },
    balance: { match: 0, total: 0 },
  };

  const mismatches: any[] = [];

  for (const tc of testCases) {
    const { id, category, sender, body, expected } = tc;

    if (!categoryStats[category]) {
      categoryStats[category] = { total: 0, correct: 0, fp: 0, fn: 0 };
    }
    categoryStats[category].total += 1;

    const t0 = process.hrtime.bigint();
    const res: MasroofResult = MasroofEngine.analyze({ sender, body });
    const t1 = process.hrtime.bigint();

    const latencyMs = Number(t1 - t0) / 1_000_000.0;
    latencies.push(latencyMs);

    const expValid = expected.isValidTransaction;
    const predValid = res.isValidTransaction;

    if (expValid && predValid) {
      tp += 1;
      categoryStats[category].correct += 1;
    } else if (!expValid && !predValid) {
      tn += 1;
      categoryStats[category].correct += 1;
    } else if (!expValid && predValid) {
      fp += 1;
      categoryStats[category].fp += 1;
      mismatches.push({
        id,
        category,
        type: 'FALSE_POSITIVE',
        predicted: res,
        expected,
      });
    } else if (expValid && !predValid) {
      fn += 1;
      categoryStats[category].fn += 1;
      mismatches.push({
        id,
        category,
        type: 'FALSE_NEGATIVE',
        predicted: res,
        expected,
        body,
      });
    }

    if (expValid) {
      const predData = res.data || ({} as any);

      // Type
      if (expected.type) {
        entityMetrics.type.total += 1;
        if (predData.type === expected.type) {
          entityMetrics.type.match += 1;
        } else {
          mismatches.push({
            id,
            category,
            field: 'type',
            predicted: predData.type,
            expected: expected.type,
          });
        }
      }

      // Amount
      if (expected.amount !== undefined && expected.amount !== null) {
        entityMetrics.amount.total += 1;
        if (isClose(predData.amount, expected.amount)) {
          entityMetrics.amount.match += 1;
        } else {
          mismatches.push({
            id,
            category,
            field: 'amount',
            predicted: predData.amount,
            expected: expected.amount,
          });
        }
      }

      // Currency
      if (expected.currency) {
        entityMetrics.currency.total += 1;
        if (normalizeCurr(predData.currency) === normalizeCurr(expected.currency)) {
          entityMetrics.currency.match += 1;
        } else {
          mismatches.push({
            id,
            category,
            field: 'currency',
            predicted: predData.currency,
            expected: expected.currency,
          });
        }
      }

      // Merchant
      const expParty = expected.merchantOrParty !== undefined && expected.merchantOrParty !== null
        ? expected.merchantOrParty
        : expected.merchant_or_party;
      if (expParty !== undefined && expParty !== null) {
        entityMetrics.merchant.total += 1;
        const pM = normalizeStr(predData.merchantOrParty);
        const eM = normalizeStr(expParty);
        if (pM && (pM === eM || eM.includes(pM) || pM.includes(eM))) {
          entityMetrics.merchant.match += 1;
        } else {
          mismatches.push({
            id,
            category,
            field: 'merchantOrParty',
            predicted: predData.merchantOrParty,
            expected: expParty,
          });
        }
      }

      // Account Mask
      const expMask = expected.accountMask !== undefined && expected.accountMask !== null
        ? expected.accountMask
        : expected.account_mask;
      if (expMask !== undefined && expMask !== null) {
        entityMetrics.accountMask.total += 1;
        const pA = normalizeStr(predData.accountMask);
        const eA = normalizeStr(expMask);
        if (pA && (pA === eA || eA.includes(pA) || pA.includes(eA))) {
          entityMetrics.accountMask.match += 1;
        } else {
          mismatches.push({
            id,
            category,
            field: 'accountMask',
            predicted: predData.accountMask,
            expected: expMask,
          });
        }
      }

      // Balance
      if (expected.balance !== undefined && expected.balance !== null) {
        entityMetrics.balance.total += 1;
        if (isClose(predData.balance, expected.balance)) {
          entityMetrics.balance.match += 1;
        } else {
          mismatches.push({
            id,
            category,
            field: 'balance',
            predicted: predData.balance,
            expected: expected.balance,
          });
        }
      }
    }
  }

  latencies.sort((a, b) => a - b);
  const total = testCases.length;
  const meanLat = latencies.reduce((a, b) => a + b, 0) / latencies.length;
  const medianLat = latencies[Math.floor(latencies.length / 2)];
  const p95Lat = latencies[Math.floor(latencies.length * 0.95)];
  const p99Lat = latencies[Math.floor(latencies.length * 0.99)];
  const minLat = latencies[0];
  const maxLat = latencies[latencies.length - 1];

  const accuracy = (tp + tn) / total;
  const precision = tp + fp > 0 ? tp / (tp + fp) : 0;
  const recall = tp + fn > 0 ? tp / (tp + fn) : 0;
  const f1 = precision + recall > 0 ? (2 * precision * recall) / (precision + recall) : 0;

  console.log('======================================================');
  console.log('         MASROOF TYPESCRIPT ENGINE TEST REPORT        ');
  console.log('======================================================');
  console.log(`Total Test Cases: ${total}`);
  console.log(`Classification Accuracy: ${(accuracy * 100).toFixed(2)}% (F1: ${(f1 * 100).toFixed(2)}%)`);
  console.log(`True Positives: ${tp} | True Negatives: ${tn}`);
  console.log(`FALSE POSITIVES: ${fp} (CRITICAL)`);
  console.log(`FALSE NEGATIVES: ${fn}`);
  console.log('\n--- Latency Performance ---');
  console.log(`  mean    : ${meanLat.toFixed(4)} ms`);
  console.log(`  median  : ${medianLat.toFixed(4)} ms`);
  console.log(`  p95     : ${p95Lat.toFixed(4)} ms`);
  console.log(`  p99     : ${p99Lat.toFixed(4)} ms`);
  console.log(`  min     : ${minLat.toFixed(4)} ms`);
  console.log(`  max     : ${maxLat.toFixed(4)} ms`);

  console.log('\n--- Entity Extraction Accuracy ---');
  for (const [k, v] of Object.entries(entityMetrics)) {
    const acc = v.total > 0 ? ((v.match / v.total) * 100).toFixed(2) : '100.00';
    console.log(`  ${k.padEnd(15)}: ${v.match}/${v.total} (${acc}%)`);
  }

  console.log('\n--- Category Breakdown ---');
  for (const cat of Object.keys(categoryStats).sort()) {
    const stats = categoryStats[cat];
    const acc = ((stats.correct / stats.total) * 100).toFixed(1);
    console.log(`  ${cat.padEnd(35)}: ${stats.correct}/${stats.total} (${acc}%) | FP: ${stats.fp} | FN: ${stats.fn}`);
  }

  console.log(`\nTotal Mismatches / Imperfections: ${mismatches.length}`);
  if (mismatches.length > 0) {
    console.log('\nTop Mismatches Details:');
    for (const m of mismatches.slice(0, 15)) {
      console.log(`  [${m.type || m.field}] ID: ${m.id} (Cat: ${m.category || 'N/A'})`);
      console.log(`    Expected: ${JSON.stringify(m.expected)}`);
      console.log(`    Got:      ${JSON.stringify(m.predicted)}`);
    }
    process.exitCode = 1;
  }
}

runTypeScriptSuite(process.argv[2] || path.join(ROOT, 'tests', 'fixtures', 'sanitized_v1', 'test_suite_cases.json'));
