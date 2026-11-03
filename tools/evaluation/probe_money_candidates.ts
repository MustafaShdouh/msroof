/** Candidate evidence only; stdin source strings, no learned model. */
import fs from 'node:fs';
import { EntityText } from '../../src/typescript/EntityText.ts';
import { collectCandidates } from '../../src/typescript/MoneyCandidates.ts';
import { MasroofEngine } from '../../src/typescript/MasroofEngine.ts';
const texts=JSON.parse(fs.readFileSync(0,'utf8'));
process.stdout.write(JSON.stringify(texts.map((text: string)=>collectCandidates(new EntityText(text),value=>MasroofEngine.parseNumber(value)))));
