/** Preserve the deployed legacy additive-IDF math; scores are uncalibrated. */
export interface LegacyScoreModel {
  metadata: { intercept_tx: number; intercept_credit: number };
  features: Record<string, [number, number, number]>;
}

// Caller owns the two-element buffer: [transaction score, incoming score].
export function scoreLegacyTransactionModel(model: LegacyScoreModel, tokens: readonly string[], output: Float64Array): void {
  let transaction = model.metadata.intercept_tx;
  let incoming = model.metadata.intercept_credit;
  for (let index = 0; index < tokens.length; index++) {
    const token = tokens[index];
    // Unknown words such as constructor/__proto__ must not resolve to inherited
    // JavaScript object properties and crash inference.
    if (Object.prototype.hasOwnProperty.call(model.features, token)) {
      const feature = model.features[token];
      transaction += feature[1] * feature[0];
      incoming += feature[2] * feature[0];
    }
  }
  output[0] = 1 / (1 + Math.exp(-transaction));
  output[1] = 1 / (1 + Math.exp(-incoming));
}
