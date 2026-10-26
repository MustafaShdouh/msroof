/** Research features/predictions only; no production or category model loading. */
import fs from 'node:fs';
import { ContextBioModel, contextFeatures } from '../../src/typescript/BioContext.ts';
const input = JSON.parse(fs.readFileSync(0, 'utf8'));
const features = input.examples.map((tokens: string[]) => contextFeatures(tokens));
const model = input.model ? new ContextBioModel(input.model) : null;
const predictions = model ? input.examples.map((tokens: string[]) => model.predict(tokens)) : null;
console.log(JSON.stringify({ features, predictions }));
