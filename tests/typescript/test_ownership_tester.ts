/** Exercise the built page's real handlers; no training inputs or model changes. */
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';

const root = new URL('../../', import.meta.url);
const html = fs.readFileSync(new URL('tools/browser/tester.html', root), 'utf8');
const script = html.match(/<script>([\s\S]*?)<\/script>/)?.[1];
assert.ok(script, 'built tester script is present');
assert.ok(script.replace(/\r\n/g, '\n').includes(fs.readFileSync(new URL('tools/browser/ownership_tester.js', root), 'utf8').replace(/\r\n/g, '\n').trim()), 'ownership source is embedded');
for (const [id, handler] of [['ownershipOwn', "confirmOwnership('own_accounts')"],
  ['ownershipOther', "confirmOwnership('other_person')"], ['ownershipUnknown', "confirmOwnership('unknown')"],
  ['ownershipClear', 'clearOwnershipConfirmation()'], ['ownershipNewMessage', 'startNewOwnershipMessage()']]) {
  assert.ok(html.includes(`id="${id}"`) && html.includes(`onclick="${handler}"`), 'click control is wired: ' + id);
}
function page() {
  const elements: Record<string, any> = {};
  const document = { addEventListener() {}, getElementById(id: string) {
    return elements[id] ??= { value: '', checked: false, innerText: '', style: {}, disabled: false };
  } };
  const context = vm.createContext({ performance, document });
  vm.runInContext(script!, context);
  // This test isolates ownership from the separate merchant research panel.
  vm.runInContext('updateMerchantSms = function() {};', context);
  return { elements, context, run(code: string) { return vm.runInContext(code, context); } };
}
const p = page();
const text = 'JOD 20.00 debited. Transfer to LOCAL PERSON completed.';
function input(body = text) {
  p.run(`document.getElementById('bodyInput').value = ${JSON.stringify(body)};
    document.getElementById('senderInput').value = 'Local test'; runAnalysis();`);
}
function response() { return JSON.parse(p.elements.ownershipOutput.innerText); }
function current() { return p.elements.jsonOutput.innerText; }
function check(status: string, decision: string) {
  const result = response();
  assert.equal(result.contextStatus, status);
  assert.equal(result.assessment.trackingDecision, decision);
  const request = p.run('ownershipRequest()');
  const direct = p.run('MasroofRuntime.MasroofEngine.analyzeWithOwnership(ownershipRequest())');
  assert.deepEqual(result, JSON.parse(JSON.stringify(direct)), 'displayed response equals the canonical API');
  if (request.ownershipContext) {
    assert.equal(request.ownershipContext.text, request.message.text);
    assert.equal(request.ownershipContext.messageId, request.messageId);
    assert.equal(request.ownershipContext.ownerScopeId, request.ownerScopeId);
  }
}
input();
check('absent', 'review');
const original = current();
p.run("confirmOwnership('other_person')");
check('applied', 'include');
assert.equal(p.elements.ownershipOther.ariaPressed, 'true');
assert.equal(current(), original, 'confirmation does not change legacy output');
p.run("confirmOwnership('own_accounts')");
check('applied', 'exclude');
assert.equal(p.elements.ownershipOwn.ariaPressed, 'true');
assert.equal(p.elements.ownershipOther.ariaPressed, 'false');
p.run("confirmOwnership('unknown')");
check('unresolved', 'review');
p.run('clearOwnershipConfirmation()');
check('absent', 'review');
assert.equal(p.elements.ownershipClear.disabled, true);

// Exact edits, including whitespace and numeral script, revoke rather than reuse confirmation.
for (const changed of [text + ' ', text.replace('20.00', '21.00'), text.replace('20.00', '٢٠٫٠٠'), '']) {
  input();
  p.run("confirmOwnership('other_person')");
  const previousId = p.run('ownershipRequest().messageId');
  input(changed);
  assert.equal(p.run('ownershipState.context'), null);
  assert.notEqual(p.run('ownershipRequest().messageId'), previousId);
  assert.equal(p.elements.ownershipOther.ariaPressed, 'false');
  if (changed) assert.equal(response().contextStatus, 'absent');
  else {
    assert.equal(p.elements.ownershipOutput.innerText, '{}');
    assert.equal(p.elements.ownershipOwn.disabled, true);
    p.run("confirmOwnership('other_person')");
    assert.equal(p.run('ownershipState.context'), null);
  }
}
input();
p.run("confirmOwnership('other_person')");
input(text + ' ');
input();
check('absent', 'review'); // Reverting an edit must not restore a confirmation.
for (const change of ["document.getElementById('senderInput').value = 'Other sender'",
  "document.getElementById('isContactInput').checked = true"]) {
  p.run("confirmOwnership('other_person')");
  p.run(change + '; runAnalysis()');
  check('absent', 'review');
}
p.run("confirmOwnership('other_person')");
const oldId = p.run('ownershipRequest().messageId');
p.run('startNewOwnershipMessage()');
check('absent', 'review');
assert.notEqual(p.run('ownershipRequest().messageId'), oldId, 'identical body can be a new record');

// Loading the same sample twice also represents different records.
p.run("loadPreset('cliq_out'); confirmOwnership('own_accounts')");
const presetId = p.run('ownershipRequest().messageId');
p.run("loadPreset('cliq_out')");
assert.equal(response().contextStatus, 'absent');
assert.notEqual(p.run('ownershipRequest().messageId'), presetId);
p.run("loadPreset('internal_transfer')");
check('absent', 'review');
assert.equal(response().assessment.transferRelationship, 'unknown');
p.run("confirmOwnership('own_accounts')");
check('applied', 'exclude');
p.run("confirmOwnership('other_person')");
check('applied', 'review');
assert.equal(response().assessment.direction, 'uncertain');

input('تم استلام دفعة كليك بمبلغ ١٢٫٣٧٥ دينار إلى محفظتك من LOCAL PERSON.');
p.run("confirmOwnership('other_person')");
check('applied', 'include');
assert.equal(response().assessment.direction, 'incoming');
assert.equal(response().assessment.amount, 12.375);
const pairedExamples = JSON.parse(fs.readFileSync(new URL('tests/fixtures/paired_movement_cases.json', root), 'utf8')).cases;
for (const id of ['arabic_failed', 'arabic_conditional', 'arabic_separate', 'arabic_same_identifier']) {
  input(pairedExamples.find((row: any) => row.id === id).text);
  check('absent', id === 'arabic_conditional' ? 'exclude' : 'review');
  p.run("confirmOwnership('own_accounts')");
  check('not_applicable', id === 'arabic_conditional' ? 'exclude' : 'review');
}
input('تم إضافة المبلغ 7.333 دينار إلى الحساب *1111، إذا احتجت مساعدة اتصل بالدعم.');
check('absent', 'include');
assert.equal(response().assessment.direction, 'incoming');
input('Transfer of JOD 75.00 between your own accounts completed.');
p.run("confirmOwnership('other_person')");
check('conflict', 'review');
assert.match(p.elements.ownershipStatus.innerText, /conflicts/);
input('Your OTP for transfer JOD 20.00 is 481763.');
p.run("confirmOwnership('other_person')");
check('not_applicable', 'exclude');
assert.match(p.elements.ownershipStatus.innerText, /not a transaction/);
input('Card purchase completed for JOD 20.00.');
p.run("confirmOwnership('own_accounts')");
check('not_applicable', 'include');
assert.match(p.elements.ownershipStatus.innerText, /not a recognized transfer/);
// A fresh page has no confirmation to reload; no storage API is provided by the harness.
const fresh = page();
assert.equal(fresh.run('ownershipState.context'), null);
assert.equal(fresh.run('ownershipState.serial'), 0);
console.log('Ownership tester: choices, binding, resets, Arabic, conflicts and negative controls passed.');
