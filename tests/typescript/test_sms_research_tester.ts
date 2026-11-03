/** Real built-page handlers and frozen research scorer; no fitting or promotion. */
import assert from 'node:assert/strict';
import crypto from 'node:crypto';
import fs from 'node:fs';
import vm from 'node:vm';
import { SmsSemanticsModel } from '../../src/typescript/research/SmsSemantics.ts';
import { SmsCompletionContextModel } from '../../src/typescript/research/SmsCompletionContext.ts';

const root = new URL('../../', import.meta.url);
const html = fs.readFileSync(new URL('tools/browser/tester.html', root), 'utf8');
const script = html.match(/<script>([\s\S]*?)<\/script>/)?.[1];
assert.ok(script);
assert.match(html, /id="smsResearchPanel" ontoggle="toggleSmsResearch\(\)"/);
assert.ok(!html.match(/id="smsResearchPanel"[^>]*\bopen\b/), 'comparison starts collapsed');
assert.ok(html.includes('Decision scores are not confidence percentages'));
const model = JSON.parse(fs.readFileSync(new URL('data/models/sms_semantics_followup_v1_word_candidate.json', root), 'utf8'));
const direct = new SmsSemanticsModel(model);
const contextModel = JSON.parse(fs.readFileSync(new URL('data/models/sms_completion_context_v1_candidate.json', root), 'utf8'));
const directContext = new SmsCompletionContextModel(contextModel);
function page() {
  const elements: Record<string, any> = {};
  const document = { addEventListener() {}, getElementById(id: string) {
    return elements[id] ??= { value: '', checked: false, open: false, innerText: '', style: {}, disabled: false };
  } };
  const context = vm.createContext({ performance, document });
  vm.runInContext(script!, context);
  vm.runInContext(`updateMerchantSms = function() {};
    var researchCalls = 0;
    var originalResearchPredict = SmsSemanticsResearch.SmsSemanticsModel.prototype.predict;
    SmsSemanticsResearch.SmsSemanticsModel.prototype.predict = function(text) {
      researchCalls++; return originalResearchPredict.call(this, text);
    };`, context);
  return { elements, run(code: string): any { return vm.runInContext(code, context); } };
}
const p = page();
assert.deepEqual(JSON.parse(p.run('JSON.stringify(SMS_RESEARCH_MODEL)')), model);
for (const [relative, expected] of Object.entries(p.run('SMS_RESEARCH_ASSETS'))) {
  assert.equal(crypto.createHash('sha256').update(fs.readFileSync(new URL(relative, root))).digest('hex'), expected);
}
function input(text: string) {
  p.run(`document.getElementById('bodyInput').value = ${JSON.stringify(text)}; runAnalysis();`);
}
const cases = [
  'تم سحب ١٩٫٥٠ دينار نقداً من حسابك بنجاح.',
  'Your account was credited JOD 35.00. Transfer received from another person.',
  'Your login OTP is 223344. Do not share it.',
  'اكتمل دفع فاتورتك من المحفظة. افتح الكشف لعرض التفاصيل.',
  'JOD 20.00 debited. Transfer to LOCAL PERSON completed.',
  'Internal transfer of JOD 12.00 between your own accounts completed.'
];
input(cases[0]);
assert.equal(p.run('researchCalls'), 0, 'closed panel performs no research inference');
assert.equal(p.run('smsResearchCandidate'), null, 'research model initializes lazily');
const before = p.elements.jsonOutput.innerText;
p.run("document.getElementById('smsResearchPanel').open = true; toggleSmsResearch();");
assert.equal(p.run('researchCalls'), 1);
assert.equal(p.elements.jsonOutput.innerText, before, 'opening comparison preserves legacy result');
const rows = [];
for (const text of cases) {
  input(text);
  const result = JSON.parse(p.elements.smsResearchOutput.innerText);
  const expected = direct.predict(text).heads;
  assert.deepEqual(result.completion, { prediction: expected.completion.prediction, score: expected.completion.score });
  assert.deepEqual(result.direction, expected.completion.prediction === 'completed' ?
    { prediction: expected.direction.prediction, score: expected.direction.score } : null);
  assert.equal(p.elements.smsResearchDirection.innerText, result.direction ?
    (result.direction.prediction === 'incoming' ? 'Incoming' : 'Outgoing') : 'Not applicable');
  const actualAssessment = p.run(`analyzeDetailed({text:${JSON.stringify(text)},sender:'',isContact:false})`);
  assert.deepEqual(result.existingMessageOnlyAssessment, JSON.parse(JSON.stringify(actualAssessment)));
  const oldResult = p.run(`MasroofRuntime.MasroofEngine.analyze({body:${JSON.stringify(text)},sender:'',isContact:false})`);
  assert.deepEqual(JSON.parse(p.elements.jsonOutput.innerText), JSON.parse(JSON.stringify(oldResult)));
  rows.push({ text, displayed: result });
}
input(cases[4]);
const rawBefore = p.elements.smsResearchOutput.innerText;
p.run("confirmOwnership('other_person')");
assert.equal(p.elements.smsResearchOutput.innerText, rawBefore, 'ownership confirmation cannot alter text-only model or message-only assessment');
const rawCompletion = JSON.parse(rawBefore).completion;
p.run("document.getElementById('senderInput').value='Changed sender'; document.getElementById('isContactInput').checked=true; runAnalysis();");
assert.deepEqual(JSON.parse(p.elements.smsResearchOutput.innerText).completion, rawCompletion, 'text model has no sender/contact registry');
input('');
assert.equal(p.elements.smsResearchOutput.innerText, '{}');
assert.equal(p.elements.smsResearchDirection.innerText, '—');
assert.equal(p.elements.smsResearchAmount.innerText, '—');
p.run("document.getElementById('smsResearchPanel').open=false; toggleSmsResearch();");
const calls = p.run('researchCalls');
input(cases[1]);
assert.equal(p.run('researchCalls'), calls);
assert.equal(p.elements.smsResearchOutput.innerText, '{}', 'closed edits clear stale results');
p.run("document.getElementById('smsResearchPanel').open=true; toggleSmsResearch();");
const reopened = direct.predict(cases[1]).heads.completion;
assert.deepEqual(JSON.parse(p.elements.smsResearchOutput.innerText).completion,
  { prediction: reopened.prediction, score: reopened.score });
p.run("smsResearchCandidate.predict=function(){throw new Error('research unavailable')}; runAnalysis();");
assert.equal(p.elements.smsResearchTransaction.innerText, 'Comparison unavailable');
assert.doesNotThrow(() => JSON.parse(p.elements.jsonOutput.innerText), 'research failure cannot break current output');
const fresh = page();
assert.equal(fresh.run('smsResearchCandidate'), null);
assert.equal(fresh.elements.smsResearchPanel?.open ?? false, false);
// The new candidate is a selectable research comparison; the reference stays default.
assert.match(html, /<option value="word">Word reference<\/option>/);
assert.match(html, /known false acceptances, including an OTP/);
const compare = page();
const contextRows = [];
compare.run(`document.getElementById('smsResearchModelSelect').value='context'; changeSmsResearchModel();`);
assert.equal(compare.run('smsResearchCandidate'), null, 'closed selection stays lazy');
for (const text of cases) {
  compare.run(`document.getElementById('bodyInput').value=${JSON.stringify(text)}; runAnalysis();
    document.getElementById('smsResearchPanel').open=true; toggleSmsResearch();`);
  const output = JSON.parse(compare.elements.smsResearchOutput.innerText);
  const expected = directContext.predict(text).heads;
  assert.equal(output.candidate, contextModel.metadata.runId);
  assert.deepEqual(output.completion, { prediction: expected.completion.prediction, score: expected.completion.score });
  assert.deepEqual(output.direction, expected.completion.prediction === 'completed' ?
    { prediction: expected.direction.prediction, score: expected.direction.score } : null);
  const baselineDirection = direct.predict(text).heads.direction;
  assert.deepEqual(expected.direction, baselineDirection, 'context model must retain direction exactly');
  contextRows.push({ text, displayed: output });
}
const legacyBeforeSwitch = compare.elements.jsonOutput.innerText;
compare.run("document.getElementById('smsResearchModelSelect').value='word'; changeSmsResearchModel();");
assert.equal(JSON.parse(compare.elements.smsResearchOutput.innerText).candidate, model.metadata.runId);
assert.equal(compare.elements.jsonOutput.innerText, legacyBeforeSwitch, 'switching model preserves the active engine output');
compare.run("document.getElementById('bodyInput').value=''; runAnalysis();");
assert.equal(compare.elements.smsResearchOutput.innerText, '{}');
process.stdout.write(JSON.stringify({ rows, contextRows, assetChecks: true, optInChecks: true }));
