/** Exact additive transaction and direction model contract. */

export const TRANSACTION_DIRECTION_CONTRACT_VERSION = '1.0.0';
export const TRANSACTION_DIRECTION_FEATURE_ENCODING = 'unigrams_then_adjacent_bigrams';

export interface ScoreHead {
  intercept: number;
  threshold?: number;
  incomeThreshold?: number;
  weights: Record<string, number>;
}

export interface TransactionDirectionModel {
  contractVersion: string;
  preprocessingVersion?: string;
  featureEncoding: string;
  transaction: ScoreHead;
  direction: ScoreHead;
}

export interface TransactionDirectionResult {
  transactionLogit: number;
  transactionProbability: number;
  isTransaction: boolean;
  directionLogit: number;
  incomeProbability: number;
  type: 'EXPENSE' | 'INCOME';
}

function finiteNumber(value: unknown): value is number {
  return typeof value === 'number' && Number.isFinite(value);
}

export function validateTransactionDirectionModel(model: unknown): model is TransactionDirectionModel {
  if (!model || typeof model !== 'object') return false;
  const candidate = model as TransactionDirectionModel;
  if (candidate.contractVersion !== TRANSACTION_DIRECTION_CONTRACT_VERSION || candidate.featureEncoding !== TRANSACTION_DIRECTION_FEATURE_ENCODING) return false;
  const heads: Array<[ScoreHead, 'threshold' | 'incomeThreshold']> = [
    [candidate.transaction, 'threshold'],
    [candidate.direction, 'incomeThreshold'],
  ];
  for (const [head, thresholdName] of heads) {
    if (!head || !finiteNumber(head.intercept) || !finiteNumber(head[thresholdName])) return false;
    const threshold = head[thresholdName] as number;
    if (threshold <= 0 || threshold >= 1 || !head.weights || typeof head.weights !== 'object') return false;
    for (const key of Object.keys(head.weights)) {
      if (!finiteNumber(head.weights[key])) return false;
    }
  }
  return true;
}

export function sigmoid(logit: number): number {
  if (logit >= 0) return 1 / (1 + Math.exp(-logit));
  const expLogit = Math.exp(logit);
  return expLogit / (1 + expLogit);
}

export function scoreHead(head: ScoreHead, features: readonly string[]): [number, number] {
  let logit = head.intercept;
  for (let index = 0; index < features.length; index++) {
    const feature = features[index];
    if (Object.prototype.hasOwnProperty.call(head.weights, feature)) logit += head.weights[feature];
  }
  return [logit, sigmoid(logit)];
}

export function evaluateTransactionDirectionModel(model: TransactionDirectionModel, features: readonly string[]): TransactionDirectionResult {
  if (!validateTransactionDirectionModel(model)) throw new Error('Invalid transaction-direction model');
  const [transactionLogit, transactionProbability] = scoreHead(model.transaction, features);
  const [directionLogit, incomeProbability] = scoreHead(model.direction, features);
  return {
    transactionLogit,
    transactionProbability,
    isTransaction: transactionProbability >= (model.transaction.threshold as number),
    directionLogit,
    incomeProbability,
    type: incomeProbability >= (model.direction.incomeThreshold as number) ? 'INCOME' : 'EXPENSE',
  };
}
