/** Experimental tagger only; never invokes merchant category final-fold models. */
import fs from 'node:fs';
import { MasroofEngine } from '../../src/typescript/MasroofEngine.ts';
import { normalizeBioToken } from '../../src/typescript/research/BioNormalization.ts';
const input = JSON.parse(fs.readFileSync(0, 'utf8'));
if (!MasroofEngine.loadSequenceTaggerModel(input.model)) throw new Error('BIO model rejected');
const predictions = input.examples.map((tokens: string[]) => {
  const normalized = tokens.map(normalizeBioToken);
  const output = new Uint8Array(tokens.length);
  if (MasroofEngine.tagNormalizedTokens(normalized, output) !== tokens.length) throw new Error('BIO output incomplete');
  return [...output];
});
MasroofEngine.clearSequenceTaggerModel();
console.log(JSON.stringify(predictions));
