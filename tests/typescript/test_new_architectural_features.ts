import { MasroofEngine } from '../../src/typescript/MasroofEngine.ts';
import type { MasroofResult } from '../../src/typescript/MasroofEngine.ts';
import fs from 'fs';
import path from 'path';

const model = JSON.parse(fs.readFileSync(path.join(process.cwd(), 'data', 'models', 'masroof_model.json'), 'utf-8'));
MasroofEngine.init(model);

const testCases = [
  // 1. Dual-Currency FX Transactions
  {
    name: "FX: Amazon USD billed JOD",
    sender: "ArabiBank",
    body: "Purchase of USD 50.00 billed as JOD 35.50 on card *1234 at AMAZON. Avail bal JOD 200.",
    exp: {
      isValidTransaction: true,
      amount: 35.50,
      currency: "JOD",
      originalAmount: 50.00,
      originalCurrency: "USD",
      exchangeRate: 0.71,
      merchantOrParty: "AMAZON"
    }
  },
  {
    name: "FX: Steam Games JOD for USD",
    sender: "CapitalBank",
    body: "Billed JOD 14.50 for USD 20.00 purchase on card *1234 at STEAM GAMES. Balance JOD 100.",
    exp: {
      isValidTransaction: true,
      amount: 14.50,
      currency: "JOD",
      originalAmount: 20.00,
      originalCurrency: "USD",
      exchangeRate: 0.725,
      merchantOrParty: "STEAM GAMES"
    }
  },
  {
    name: "FX: Apple Store USD in AED",
    sender: "ENBD",
    body: "Transaction of USD 100.00 (AED 367.50) at APPLE STORE with card *5555.",
    exp: {
      isValidTransaction: true,
      amount: 367.50,
      currency: "AED",
      originalAmount: 100.00,
      originalCurrency: "USD",
      exchangeRate: 3.675,
      merchantOrParty: "APPLE STORE"
    }
  },

  // 2. South Asian & Swiss Number Formatting
  {
    name: "Indian Lakhs: HDFC Bank",
    sender: "HDFCBK",
    body: "Your account *9876 debited by INR 1,50,000.00 on 20-Oct-26 at RELIANCE DIGITAL. Avail bal INR 2,45,000.00",
    exp: {
      isValidTransaction: true,
      amount: 150000.00,
      currency: "INR",
      balance: 245000.00,
      merchantOrParty: "RELIANCE DIGITAL"
    }
  },
  {
    name: "Swiss Apostrophe: UBS",
    sender: "UBS",
    body: "Purchase of CHF 2'450.75 on card *3322 at ROLEX BOUTIQUE. Bal CHF 15'200.00",
    exp: {
      isValidTransaction: true,
      amount: 2450.75,
      currency: "CHF",
      balance: 15200.00,
      merchantOrParty: "ROLEX BOUTIQUE"
    }
  },

  // 3. Anchored Structural Chunker (Prepositions inside proper merchant names)
  {
    name: "Merchant: Farm To Table Cafe",
    sender: "Chase",
    body: "Purchase of $30.00 at FARM TO TABLE CAFE on card ending 1234",
    exp: {
      isValidTransaction: true,
      amount: 30.00,
      currency: "USD",
      merchantOrParty: "FARM TO TABLE CAFE"
    }
  },
  {
    name: "Merchant: Subway At The Mall",
    sender: "WellsFargo",
    body: "Purchase of $12.00 at SUBWAY AT THE MALL on card ending 1234",
    exp: {
      isValidTransaction: true,
      amount: 12.00,
      currency: "USD",
      merchantOrParty: "SUBWAY AT THE MALL"
    }
  },
  {
    name: "Merchant: Door To Door Logistics",
    sender: "BOA",
    body: "Purchase of $50.00 at DOOR TO DOOR LOGISTICS on card ending 1234",
    exp: {
      isValidTransaction: true,
      amount: 50.00,
      currency: "USD",
      merchantOrParty: "DOOR TO DOOR LOGISTICS"
    }
  },
  {
    name: "Merchant: Arabic Restaurant from Home",
    sender: "BankAlEtihad",
    body: "شراء بمبلغ 20 دينار لدى مطعم من البيت بالبطاقة *1234",
    exp: {
      isValidTransaction: true,
      amount: 20.00,
      currency: "JOD",
      merchantOrParty: "مطعم من البيت"
    }
  }
];

console.log("=".repeat(70));
console.log("VERIFYING NEW ARCHITECTURAL CAPABILITIES (TYPESCRIPT ENGINE)");
console.log("=".repeat(70));

let allPassed = true;
for (const tc of testCases) {
  const res: MasroofResult = MasroofEngine.analyze({ sender: tc.sender, body: tc.body });
  const exp: any = tc.exp;
  const data: any = res.data || {};

  const errors: string[] = [];
  if (res.isValidTransaction !== exp.isValidTransaction) {
    errors.push(`Valid: got ${res.isValidTransaction} exp ${exp.isValidTransaction}`);
  }
  if (exp.amount !== undefined && data.amount !== exp.amount) {
    errors.push(`Amount: got ${data.amount} exp ${exp.amount}`);
  }
  if (exp.currency !== undefined && data.currency !== exp.currency) {
    errors.push(`Currency: got ${data.currency} exp ${exp.currency}`);
  }
  if (exp.originalAmount !== undefined && data.originalAmount !== exp.originalAmount) {
    errors.push(`OrigAmount: got ${data.originalAmount} exp ${exp.originalAmount}`);
  }
  if (exp.originalCurrency !== undefined && data.originalCurrency !== exp.originalCurrency) {
    errors.push(`OrigCurrency: got ${data.originalCurrency} exp ${exp.originalCurrency}`);
  }
  if (exp.exchangeRate !== undefined && data.exchangeRate !== exp.exchangeRate) {
    errors.push(`ExchangeRate: got ${data.exchangeRate} exp ${exp.exchangeRate}`);
  }
  if (exp.merchantOrParty !== undefined && data.merchantOrParty !== exp.merchantOrParty) {
    errors.push(`Merchant: got '${data.merchantOrParty}' exp '${exp.merchantOrParty}'`);
  }
  if (exp.balance !== undefined && data.balance !== exp.balance) {
    errors.push(`Balance: got ${data.balance} exp ${exp.balance}`);
  }

  if (errors.length === 0) {
    console.log(`  [PASS] ${tc.name}`);
  } else {
    allPassed = false;
    console.log(`  [FAIL] ${tc.name}`);
    for (const err of errors) {
      console.log(`         >>> ${err}`);
    }
  }
}

// Milestone 2: local merchant corrections must be normalized, persistent, and isolated.
MasroofEngine.loadUserOverlay('{}');
const baselineCategory = MasroofEngine.classifyCategory('Starbucks Cafe', 'purchase at Starbucks Cafe');
const baselinePasses = baselineCategory.category === 'Dining & Food Delivery';
console.log(`  [${baselinePasses ? 'PASS' : 'FAIL'}] Overlay baseline classification`);
allPassed = allPassed && baselinePasses;

MasroofEngine.applyCorrection(' STARBUCKS-CAFE ', 'Shopping & Retail');
const correctedCategory = MasroofEngine.classifyCategory('starbucks cafe', 'purchase at Starbucks Cafe');
const correctionPasses = correctedCategory.category === 'Shopping & Retail' && correctedCategory.confidence === 1.0;
console.log(`  [${correctionPasses ? 'PASS' : 'FAIL'}] Overlay correction override`);
allPassed = allPassed && correctionPasses;

const persistedOverlay = JSON.stringify(MasroofEngine.exportUserOverlay());
MasroofEngine.loadUserOverlay('{}');
MasroofEngine.loadUserOverlay(persistedOverlay);
const restoredCategory = MasroofEngine.classifyCategory('STARBUCKS CAFE', 'purchase at Starbucks Cafe');
const persistencePasses = restoredCategory.category === 'Shopping & Retail' && restoredCategory.confidence === 1.0;
console.log(`  [${persistencePasses ? 'PASS' : 'FAIL'}] Overlay export and load`);
allPassed = allPassed && persistencePasses;

const unrelatedCategory = MasroofEngine.classifyCategory('Starbucks Cafe Downtown', 'purchase at Starbucks Cafe Downtown');
const isolationPasses = unrelatedCategory.category === 'Dining & Food Delivery';
console.log(`  [${isolationPasses ? 'PASS' : 'FAIL'}] Overlay merchant isolation`);
allPassed = allPassed && isolationPasses;
MasroofEngine.loadUserOverlay('{}');

// Milestone 3: flat perceptron inference stays isolated from active extraction.
const tagCount = MasroofEngine.BIO_TAGS.length;
const emissionWeights = new Array(4 * tagCount).fill(0);
emissionWeights[0 * tagCount + 5] = 4.0; // coffee -> B-MERCHANT
emissionWeights[1 * tagCount + 6] = 4.0; // house -> I-MERCHANT
emissionWeights[2 * tagCount + 1] = 4.0; // 5.450 -> B-AMT
emissionWeights[3 * tagCount + 3] = 4.0; // jod -> B-CURR
const taggerLoaded = MasroofEngine.loadSequenceTaggerModel({
  version: 'test',
  tagCount,
  featureIndex: { coffee: 0, house: 1, '5.450': 2, jod: 3 },
  emissionWeights,
  transitionWeights: new Array(tagCount * tagCount).fill(0),
  bias: new Array(tagCount).fill(0),
});
const tagOutput = new Uint8Array(4);
const taggedCount = MasroofEngine.tagNormalizedTokens(['coffee', 'house', '5.450', 'jod'], tagOutput);
const taggerPasses = taggerLoaded && taggedCount === 4 &&
  MasroofEngine.sequenceTagLabel(tagOutput[0]) === 'B-MERCHANT' &&
  MasroofEngine.sequenceTagLabel(tagOutput[1]) === 'I-MERCHANT' &&
  MasroofEngine.sequenceTagLabel(tagOutput[2]) === 'B-AMT' &&
  MasroofEngine.sequenceTagLabel(tagOutput[3]) === 'B-CURR';
console.log(`  [${taggerPasses ? 'PASS' : 'FAIL'}] Flat BIO perceptron inference`);
allPassed = allPassed && taggerPasses;
MasroofEngine.clearSequenceTaggerModel();

console.log("\nResult:", allPassed ? "ALL TYPESCRIPT ARCHITECTURAL TESTS PASSED!" : "SOME TESTS FAILED!");
if (!allPassed) {
  process.exit(1);
}
