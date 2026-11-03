/** Verify the real page displays the detailed API, including unresolved fields. */
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';

const root = new URL('../../', import.meta.url);
const html = fs.readFileSync(new URL('tools/browser/tester.html', root), 'utf8');
const script = html.match(/<script>([\s\S]*?)<\/script>/)?.[1];
assert.ok(script);
const markup = html.slice(0,html.indexOf('<script>'));
const idList = [...markup.matchAll(/\bid="([^"]+)"/g)].map(m=>m[1]);
const ids = new Set(idList);
assert.equal(ids.size,idList.length,'rendered HTML has no duplicate IDs');
assert.ok(markup.indexOf('id="primaryAssessment"') < markup.indexOf('id="legacyPanel"'));
assert.match(markup, /<details class="assessment-details" id="legacyPanel">/);
assert.match(markup,/Message-only assessment/);
assert.match(markup,/The message-only result above and legacy comparison stay unchanged/);
assert.ok(script.replace(/\r\n/g,'\n').includes(fs.readFileSync(new URL('tools/browser/assessment_view.js',root),'utf8').replace(/\r\n/g,'\n').trim()));

const elements: Record<string,any> = {};
const context = vm.createContext({performance, document:{addEventListener(){},getElementById(id: string){
  assert.ok(ids.has(id),'handler targets a real HTML element: '+id);
  return elements[id] ??= {value:'',checked:false,open:false,innerText:'',style:{},disabled:false};
}}});
const run = (code: string): any=>vm.runInContext(code,context);
vm.runInContext(script,context);
run('updateMerchantSms = function() {};');
function input(text: string, contact=false) {
  run(`document.getElementById('bodyInput').value=${JSON.stringify(text)};
    document.getElementById('senderInput').value='Saved contact';
    document.getElementById('isContactInput').checked=${contact}; runAnalysis();`);
}
const cases = [
  {text:'17.250 was debited from your account.',decision:'include',currency:'JOD · default (currency missing)'},
  {text:'أُضيف ١٧٫٢٥٠ إلى حسابك.',decision:'include',currency:'JOD · default (currency missing)'},
  {text:'Your account was charged 17 pounds.',decision:'include',currency:'JOD · default (currency ambiguous)'},
  {text:'USD 17.250 was debited from your account.',decision:'include',currency:'USD · explicit in message'},
  {text:'Your account was debited JOD 0.001.',decision:'include'},
  {text:'Your account was debited JOD 1,250.375.',decision:'include'},
  {text:'Your account was credited.',decision:'review'},
  {text:'JOD 20.00 debited. Transfer to LOCAL PERSON completed.',decision:'review'},
  {text:'Transfer of JOD 20 between your own accounts completed.',decision:'exclude'},
  {text:'Your account 1234 was debited from your account.',decision:'review'},
  {text:'Whether 17 was credited to your account is not confirmed.',decision:'review'},
  {text:'Your login OTP is 223344. Do not share it.',decision:'exclude'},
  {text:'تم رفض عملية الشراء بقيمة ١٧ دينار.',decision:'exclude'}
];
const directions: Record<string,string> = {incoming:'Incoming',outgoing:'Outgoing',uncertain:'Direction unresolved',not_applicable:'Not applicable'};
const ownership: Record<string,string> = {not_transfer:'Not a transfer',own_accounts:'My own accounts',other_person:'Another person',unknown:'Ownership unresolved',not_applicable:'Not applicable'};
for(const c of cases) {
  input(c.text,true); // Contact metadata must not accidentally show the legacy rejection.
  const actual=JSON.parse(elements.detailedOutput.innerText);
  const direct=JSON.parse(run(`JSON.stringify(analyzeDetailed({text:${JSON.stringify(c.text)},sender:'Saved contact',isContact:true}))`));
  assert.deepEqual(actual,direct);
  assert.equal(actual.trackingDecision,c.decision,c.text);
  assert.equal(elements.detailedDecision.innerText,{include:'Include',review:'Review required',exclude:'Exclude'}[c.decision]);
  assert.equal(elements.primaryAmount.innerText,actual.amount===null ? (actual.transactionStatus==='non_transaction'?'Not applicable':'Unresolved') : String(actual.amount));
  assert.equal(elements.primaryDirection.innerText,directions[actual.direction]);
  assert.equal(elements.primaryOwnership.innerText,ownership[actual.transferRelationship]);
  assert.ok(elements.primaryReasons.innerText);
  assert.match(elements.primaryLatency.innerText,/^[0-9.]+ ms$/);
  if(c.currency)assert.equal(elements.primaryCurrency.innerText,c.currency);
  if(actual.transactionStatus==='non_transaction')assert.equal(elements.primaryCurrency.innerText,'Not applicable');
}
input(cases[7].text);
const messageOnly=elements.detailedOutput.innerText;
const legacy=elements.jsonOutput.innerText;
run("confirmOwnership('other_person')");
assert.equal(JSON.parse(elements.ownershipOutput.innerText).assessment.trackingDecision,'include');
assert.equal(elements.detailedOutput.innerText,messageOnly,'confirmation stays separate from message-only result');
assert.equal(elements.jsonOutput.innerText,legacy,'legacy API remains independent');
run("confirmOwnership('own_accounts')");
assert.equal(JSON.parse(elements.ownershipOutput.innerText).assessment.trackingDecision,'exclude');
assert.equal(elements.detailedOutput.innerText,messageOnly);

input('');
assert.equal(elements.detailedDecision.innerText,'Ready');
for(const id of ['primaryAmount','primaryCurrency','primaryDirection','primaryOwnership','primaryStatus','primaryLatency'])assert.equal(elements[id].innerText,'—');
assert.equal(elements.detailedOutput.innerText,'{}');
assert.equal(elements.jsonOutput.innerText,'{}');
assert.equal(elements.ownershipOutput.innerText,'{}');

run("analyze = function(){throw new Error('compatibility unavailable')};");
input(cases[0].text);
assert.equal(elements.detailedDecision.innerText,'Include','legacy failure cannot replace the primary assessment');
assert.equal(elements.primaryAmount.innerText,'17.25');
assert.equal(elements.fieldAmount.innerText,'--','failed legacy comparison cannot leave a stale amount');
assert.match(elements.decisionTitle.innerText,/unavailable/);
assert.match(JSON.parse(elements.jsonOutput.innerText).error,/compatibility unavailable/);
console.log('Primary tester: detailed decisions, amounts/defaults, metadata, resets, ownership separation and legacy failure isolation passed.');
