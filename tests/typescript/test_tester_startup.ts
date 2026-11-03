/** Startup errors must never become SMS exclusions or call unready scorers. */
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';

const root=new URL('../../',import.meta.url);
const html=fs.readFileSync(new URL('tools/browser/tester.html',root),'utf8');
const script=html.match(/<script>([\s\S]*?)<\/script>/)?.[1];
assert.ok(script);
const guard=fs.readFileSync(new URL('tools/browser/startup_guard.js',root),'utf8');
assert.ok(script.replace(/\r\n/g,'\n').includes(guard.replace(/\r\n/g,'\n').trim()));
assert.match(html,/id="startupStatus" role="status"/);
const valid=JSON.parse(fs.readFileSync(new URL('data/models/masroof_model.json',root),'utf8'));
function page(options: {model?: any;before?: string;blockCompilation?: boolean}={}) {
  const elements: Record<string,any>={};
  const callbacks: Function[]=[];
  const context=vm.createContext({performance,__TEST_MODEL:options.model,document:{
    addEventListener(event: string,cb: Function){if(event==='DOMContentLoaded')callbacks.push(cb);},
    getElementById(id: string){return elements[id]??={value:'',checked:false,open:false,innerText:'',textContent:'',style:{}};}
  }},{codeGeneration:{strings:!options.blockCompilation,wasm:false}});
  if(options.before)vm.runInContext(options.before,context);
  const source=Object.hasOwn(options,'model')?script!.replace('const MODEL =','const MODEL = __TEST_MODEL; const UNUSED_MODEL ='):script!;
  vm.runInContext(source,context);
  const run=(code: string):any=>vm.runInContext(code,context);
  callbacks.forEach(cb=>cb());
  return {elements,run};
}
function blocked(p: ReturnType<typeof page>) {
  assert.equal(p.run('testerStartup.ready'),false);
  p.run(`document.getElementById('bodyInput').value='17 was debited from your account.';
    runAnalysis();confirmOwnership('other_person');
    document.getElementById('smsResearchPanel').open=true;toggleSmsResearch();
    setMerchantExample('unit test');`);
  assert.equal(p.elements.detailedDecision.innerText,'Engine not ready');
  assert.equal(p.elements.startupStatus.hidden,false);
  assert.match(p.elements.startupStatus.innerText,/No message was analyzed/);
  assert.equal(p.elements.primaryAmount.innerText,'—');
  assert.equal(p.elements.primaryDirection.innerText,'—');
  const error=JSON.parse(p.elements.detailedOutput.innerText);
  assert.equal(error.startupStatus,'not_ready');
  assert.ok(!Object.hasOwn(error,'transactionStatus')&&!Object.hasOwn(error,'trackingDecision'));
  assert.ok(!Object.hasOwn(JSON.parse(p.elements.jsonOutput.innerText),'isValidTransaction'));
  assert.equal(p.elements.ownershipOwn.disabled,true);
  assert.equal(p.elements.ownershipOutput.innerText,'{}');
  assert.equal(p.run('ownershipState.context'),null);
  assert.equal(p.run('smsResearchCandidate'),null,'no optional SMS scorer created');
  assert.match(p.elements.merchantNameResult.textContent,/No research prediction/);
  assert.throws(()=>p.run("analyzeDetailed({text:'unclassified-token'})"),/Engine not ready/);
  assert.throws(()=>p.run("analyze('','unclassified-token',false)"),/Engine not ready/);
}
for(const model of [null,{}, {metadata:{intercept_tx:0,intercept_credit:0},features:{}},
                    {metadata:{intercept_tx:NaN,intercept_credit:0},features:{x:[1,1,1]}},
                    {metadata:{intercept_tx:0,intercept_credit:0},features:{x:[1,Infinity,1]}}]) {
  const p=page({model});blocked(p);assert.equal(p.run('testerStartup.errorCode'),'invalid_model');
  assert.equal(p.run('MasroofRuntime'),null);
}
for(const before of ["String.prototype.matchAll=undefined", "String.prototype.replaceAll=undefined", "Object.fromEntries=undefined",
  "var NativeRegExp=RegExp;RegExp=function(pattern,flags){if(flags==='d')throw new Error('indices unavailable');return new NativeRegExp(pattern,flags)}"]) {
  const p=page({before});blocked(p);assert.equal(p.run('testerStartup.errorCode'),'runtime_features');
}
const csp=page({blockCompilation:true});blocked(csp);assert.equal(csp.run('testerStartup.errorCode'),'runtime_load');
const ready=page();assert.equal(ready.run('testerStartup.ready'),true);
assert.equal(ready.elements.startupStatus.hidden,true);
assert.equal(ready.elements.detailedDecision.innerText,'Include');
// A post-startup failure must clear old output and confirmation without scoring again.
ready.run(`confirmOwnership('other_person'); var coreCalls=0;
  MasroofRuntime.MasroofEngine.analyzeDetailed=function(){coreCalls++;throw new Error('must not score')};
  MasroofRuntime.MasroofEngine.analyzeWithOwnership=function(){coreCalls++;throw new Error('must not score')};
  MasroofRuntime.MasroofEngine.analyze=function(){coreCalls++;throw new Error('must not score')};
  testerStartup={ready:false,errorCode:'unit_failure',message:'Unit startup failure'};`);
blocked(ready);assert.equal(ready.run('coreCalls'),0);

// Exercise initialization success/throw directly with test-only factory controls.
const controls=vm.createContext({});vm.runInContext(guard,controls);
controls.model=valid;
const fake=`const MasroofRuntime={MasroofEngine:{init(){globalThis.initCalls=(globalThis.initCalls||0)+1},analyzeDetailed(){},analyzeWithOwnership(){},analyze(){}}};`;
controls.bundle=fake;
vm.runInContext('initializeTesterRuntime(bundle,model)',controls);
assert.equal(vm.runInContext('initCalls',controls),1);
controls.bundle=fake.replace('globalThis.initCalls=(globalThis.initCalls||0)+1',"throw new Error('init failed')");
vm.runInContext('initializeTesterRuntime(bundle,model)',controls);
assert.equal(vm.runInContext('testerStartup.errorCode',controls),'initialization_failed');
assert.equal(vm.runInContext('testerStartup.ready',controls),false);
controls.bundle='this is not valid bundle syntax';
vm.runInContext('initializeTesterRuntime(bundle,model)',controls);
assert.equal(vm.runInContext('testerStartup.errorCode',controls),'runtime_load');
console.log('Tester startup: valid init, malformed weights, missing features, blocked compilation, init/load errors and zero inference on failure passed.');
