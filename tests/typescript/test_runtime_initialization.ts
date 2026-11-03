/** Characterize existing startup; toy weights are test controls, not a trained model. */
import assert from 'node:assert/strict';
import fs from 'node:fs';
import crypto from 'node:crypto';
import { MasroofEngine } from '../../src/typescript/MasroofEngine.ts';

const root=new URL('../../',import.meta.url);
const policy=JSON.parse(fs.readFileSync(new URL('config/contracts/core_validation_preflight_v1.json',root),'utf8'));
const raw=fs.readFileSync(new URL(policy.runtime.modelPath,root));
assert.equal(crypto.createHash('sha256').update(raw).digest('hex'),policy.runtime.modelSha256);
const structural={text:'17.250 was debited from your account.'};
const fallback={text:'unclassified-token'};
const without=MasroofEngine.analyzeDetailed(fallback);
assert.equal(without.transactionStatus,'non_transaction');
assert.equal(MasroofEngine.analyzeDetailed(structural).trackingDecision,'include',
  'a structural success does not establish that the fallback was initialized');
// This deliberately empty toy feature table is not admissible as production weights.
MasroofEngine.init({metadata:{intercept_tx:20,intercept_credit:0},features:{}} as any);
const withToy=MasroofEngine.analyzeDetailed(fallback);
assert.equal(withToy.transactionStatus,'uncertain');
assert.equal(withToy.trackingDecision,'review');
assert.notDeepEqual(withToy,without,'missing initialization changes the available financial-candidate fallback');
MasroofEngine.init({} as any); // Existing init accepts it; the later scorer cannot use it.
assert.throws(()=>MasroofEngine.analyzeDetailed(fallback));
MasroofEngine.init(JSON.parse(raw.toString('utf8')));
assert.equal(MasroofEngine.analyzeDetailed(structural).amount,17.25);
assert.equal(MasroofEngine.analyzeDetailed(structural).currencyResolution,'default_missing');
assert.doesNotThrow(()=>MasroofEngine.analyzeDetailed(fallback));
const match=new RegExp('(?<=a)(b)','d').exec('ab');
assert.deepEqual(match?.indices?.[1],[1,2]);
assert.equal([...('ab ab').matchAll(/b/g)].length,2);
console.log('Runtime initialization: pinned weights, structural-versus-fallback startup and current invalid-init behavior characterized; no engine behavior changed.');
