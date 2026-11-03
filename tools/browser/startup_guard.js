// Tester boundary only. A startup failure is not a transaction assessment.
var testerStartup = { ready: false, errorCode: 'not_initialized', message: 'Engine not ready.' };

function checkTesterFeatures() {
  if (typeof String.prototype.matchAll !== 'function' || typeof String.prototype.replaceAll !== 'function' ||
      typeof Object.fromEntries !== 'function' || typeof Array.from !== 'function' || typeof Number.isFinite !== 'function') {
    throw new Error('Required JavaScript features are unavailable. Open the tester in a supported modern browser.');
  }
  var match = new RegExp('(?<=a)(b)', 'd').exec('ab');
  if (!match || !match.indices || match.indices[1][0] !== 1 || match.indices[1][1] !== 2 ||
      Array.from('ab'.matchAll(new RegExp('b', 'g'))).length !== 1) {
    throw new Error('Required regular-expression features are unavailable.');
  }
}

function validateTesterModel(model) {
  if (!model || typeof model !== 'object' || !model.metadata || !model.features || Array.isArray(model.features)) {
    throw new Error('Model weights are missing or malformed. Rebuild the tester from the pinned model.');
  }
  if (!Number.isFinite(model.metadata.intercept_tx) || !Number.isFinite(model.metadata.intercept_credit)) {
    throw new Error('Model intercepts must be finite numbers.');
  }
  var keys = Object.keys(model.features);
  if (!keys.length || keys.some(function(key) {
    var feature = model.features[key];
    return !key || !Array.isArray(feature) || feature.length !== 3 || feature.some(function(value) {
      return typeof value !== 'number' || !Number.isFinite(value);
    });
  })) throw new Error('Model features must contain finite weight triples.');
}

function initializeTesterRuntime(bundleSource, model) {
  testerStartup = { ready: false, errorCode: 'runtime_features', message: 'Engine not ready.' };
  try {
    checkTesterFeatures();
    testerStartup.errorCode = 'invalid_model';
    validateTesterModel(model);
    testerStartup.errorCode = 'runtime_load';
    // Compile only after feature checks, so unsupported core regex syntax is caught.
    var runtime = new Function(bundleSource + '\nreturn MasroofRuntime;')();
    var engine = runtime && runtime.MasroofEngine;
    if (!engine || typeof engine.init !== 'function' || typeof engine.analyzeDetailed !== 'function' ||
        typeof engine.analyzeWithOwnership !== 'function' || typeof engine.analyze !== 'function') {
      throw new Error('The core runtime could not be loaded. Rebuild the tester.');
    }
    testerStartup.errorCode = 'initialization_failed';
    engine.init(model);
    testerStartup = { ready: true, errorCode: null, message: 'Engine ready.' };
    return runtime;
  } catch (error) {
    testerStartup.message = String(error.message || error);
    return null;
  }
}

function requireTesterReady() {
  if (!testerStartup.ready) throw new Error('Engine not ready: ' + testerStartup.message);
}

function renderTesterNotReady() {
  renderPrimaryAssessment(null);
  var message = 'Engine not ready. No message was analyzed. ' + testerStartup.message;
  var banner = document.getElementById('startupStatus');
  banner.hidden = false;
  banner.innerText = message;
  document.getElementById('detailedDecision').innerText = 'Engine not ready';
  document.getElementById('primaryReasons').innerText = message;
  var error = { startupStatus: 'not_ready', errorCode: testerStartup.errorCode, message: testerStartup.message };
  document.getElementById('detailedOutput').innerText = JSON.stringify(error, null, 2);
  renderLegacyComparison(null);
  document.getElementById('decisionTitle').innerText = 'Engine not ready';
  document.getElementById('jsonOutput').innerText = JSON.stringify(error, null, 2);
  ownershipState.context = null;
  ownershipState.fresh = true;
  ['ownershipOwn', 'ownershipOther', 'ownershipUnknown', 'ownershipClear'].forEach(function(id) {
    var button = document.getElementById(id);
    button.disabled = true;
    button.ariaPressed = 'false';
    button.className = '';
  });
  document.getElementById('ownershipOutput').innerText = '{}';
  document.getElementById('ownershipSummary').innerText = 'Engine not ready. No ownership assessment.';
  document.getElementById('ownershipStatus').innerText = 'No confirmation';
  if (typeof resetSmsResearch === 'function') resetSmsResearch('Engine not ready');
  document.getElementById('merchantSmsResult').textContent = 'Engine not ready. No message assessment.';
}
