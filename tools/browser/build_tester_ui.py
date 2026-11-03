import json
import hashlib
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from tools.browser.merchant_lab import build_merchant_lab
from tools.browser.sms_research import build_sms_research
from tools.node_runtime import node_executable

def build():
    root = Path(__file__).resolve().parents[2]
    model_bytes = (root / "data" / "models" / "masroof_model.json").read_bytes()
    policy = json.loads((root / "config/contracts/core_validation_preflight_v1.json").read_text(encoding="utf-8"))
    if hashlib.sha256(model_bytes).hexdigest() != policy["runtime"]["modelSha256"]:
        raise ValueError("Tester weights differ from the pinned model; review the model/version before rebuilding")
    model_json_str = model_bytes.decode("utf-8")

    html_content = r'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Masroof · Message tester</title>
  <style>__TESTER_CSS__</style>
</head>
<body>
  <div class="page-shell">
  <header class="topbar">
    <div class="brand"><span class="brand-mark" aria-hidden="true">m</span><span>Masroof</span></div>
    <span class="environment"><span aria-hidden="true">●</span> Local playground</span>
  </header>

  <main>
    <div class="page-heading">
      <p class="eyebrow">MESSAGE TESTER</p>
      <h1>Test a message.</h1>
      <p>Paste a bank or wallet SMS and see how Masroof reads it.</p>
    </div>

    <div class="workspace-grid">
    <section class="panel message-panel" aria-labelledby="messageHeading">
      <div class="panel-heading"><h2 id="messageHeading">Message</h2><span class="quiet-label">Updates as you type</span></div>
      <div class="field">
        <label for="senderInput">Sender</label>
        <input type="text" id="senderInput" value="ArabiBank" dir="auto" autocomplete="off" oninput="runAnalysis()">
      </div>
      <label class="checkbox-label" for="isContactInput">
        <input type="checkbox" id="isContactInput" onchange="runAnalysis()">
        Sender is a saved contact
      </label>
      <div class="field message-field">
        <label for="bodyInput">SMS message <span class="quiet-label">Arabic or English</span></label>
        <textarea id="bodyInput" rows="8" dir="auto" placeholder="Paste your message here…" spellcheck="false" oninput="runAnalysis()"></textarea>
      </div>
      <details class="sample-library" open>
        <summary>Try a sample <span class="quiet-label">14 examples</span></summary>
        <div class="preset-grid">
    <button onclick="loadPreset('arab_pos')">Card purchase</button>
    <button onclick="loadPreset('cliq_in')">CliQ In</button>
    <button onclick="loadPreset('cliq_out')">CliQ Out</button>
    <button onclick="loadPreset('orange_wallet')">Orange Money</button>
    <button onclick="loadPreset('zain_bill')">Zain Cash</button>
    <button onclick="loadPreset('fx_usd_jod')">Foreign currency</button>
    <button onclick="loadPreset('farm_to_table')">Merchant name</button>
    <button onclick="loadPreset('balance_inquiry')">Balance inquiry</button>
    <button onclick="loadPreset('incomplete_tx')">Missing amount</button>
    <button onclick="loadPreset('internal_transfer')">Paired debit / credit</button>
    <button onclick="loadPreset('trap_otp')">Verification code</button>
    <button onclick="loadPreset('declined')">Declined</button>
    <button onclick="loadPreset('chat_noise')">Personal message</button>
    <button onclick="loadPreset('gibberish')">Unrecognized text</button>
        </div>
      </details>
    </section>

    <section class="panel analysis-panel" aria-labelledby="analysisHeading">
      <div class="panel-heading"><h2 id="analysisHeading">Analysis</h2><span class="quiet-label">Engine output</span></div>
  <p class="help-text" id="startupStatus" role="status">Engine not ready. Waiting for startup checks; no message has been analyzed.</p>
  <div class="result-heading"><h3>Message-only assessment</h3><span class="decision-badge" id="detailedDecision" role="status" aria-live="polite">Ready</span></div>
  <table class="result-table" id="primaryAssessment" aria-label="Primary message assessment">
    <tbody>
    <tr class="status-row"><th scope="row">Completion</th><td id="primaryStatus">—</td></tr>
    <tr class="amount-row"><th scope="row">Amount</th><td id="primaryAmount">—</td></tr>
    <tr><th scope="row">Currency</th><td id="primaryCurrency">—</td></tr>
    <tr><th scope="row">Direction</th><td id="primaryDirection">—</td></tr>
    <tr><th scope="row">Ownership</th><td id="primaryOwnership">—</td></tr>
    <tr><th scope="row">Category</th><td id="primaryCategory">—</td></tr>
    <tr><th scope="row">Why</th><td id="primaryReasons" class="assessment-reasons">Add a message to analyze.</td></tr>
    <tr><th scope="row">Local analysis time</th><td id="primaryLatency">—</td></tr>
    </tbody>
  </table>
  <p class="help-text">Include is eligible for recording. Review needs inspection. Exclude is not recorded. Ownership confirmations are shown separately below.</p>
  <details class="json-details"><summary>Assessment response <span class="quiet-label">JSON</span></summary><pre id="detailedOutput">{}</pre></details>
  <details class="assessment-details ownership-panel" id="ownershipPanel">
    <summary>Try an ownership confirmation <span class="quiet-label">Optional</span></summary>
    <p class="help-text">For this transfer, who owns the other account? Choose only what you know. A name alone does not establish ownership.</p>
    <div class="ownership-choices" role="group" aria-label="Confirm transfer ownership">
      <button type="button" id="ownershipOwn" aria-pressed="false" onclick="confirmOwnership('own_accounts')">My own accounts</button>
      <button type="button" id="ownershipOther" aria-pressed="false" onclick="confirmOwnership('other_person')">Another person</button>
      <button type="button" id="ownershipUnknown" aria-pressed="false" onclick="confirmOwnership('unknown')">I'm not sure</button>
    </div>
    <p class="ownership-summary" id="ownershipSummary" role="status" aria-live="polite">Add a message to try a confirmation.</p>
    <p class="help-text" id="ownershipStatus">No confirmation</p>
    <div class="ownership-actions">
      <button type="button" id="ownershipClear" onclick="clearOwnershipConfirmation()" disabled>Clear confirmation</button>
      <button type="button" id="ownershipNewMessage" onclick="startNewOwnershipMessage()">New message</button>
    </div>
    <p class="help-text">Saved only until you edit the message or sender, load a sample, start a new message, or refresh this page. The message-only result above and legacy comparison stay unchanged.</p>
    <details class="json-details"><summary>Confirmation response <span class="quiet-label">JSON</span></summary><pre id="ownershipOutput">{}</pre></details>
  </details>
  <details class="assessment-details" id="legacyPanel">
    <summary>Legacy comparison <span class="quiet-label">Previous API</span></summary>
    <p class="help-text">Compatibility output from the previous API. Its decisions can differ from the message-only assessment above. Model scores are uncalibrated.</p>
  <table class="result-table" aria-label="Legacy engine comparison">
    <tbody>
    <tr class="status-row"><th scope="row">Status</th><td id="decisionTitle">Ready</td></tr>
    <tr><th scope="row">Raw model score</th><td id="confidenceVal">--</td></tr>
    <tr><th scope="row">Category</th><td id="fieldCategory">--</td></tr>
    <tr><th scope="row">Direction</th><td id="fieldDirection">--</td></tr>
    <tr class="amount-row"><th scope="row">Amount</th><td id="fieldAmount">--</td></tr>
    <tr><th scope="row">Original amount</th><td id="fieldOrigAmount">--</td></tr>
    <tr><th scope="row">Exchange rate</th><td id="fieldRate">--</td></tr>
    <tr><th scope="row">Merchant / party</th><td id="fieldParty" dir="auto">--</td></tr>
    <tr><th scope="row">Account</th><td id="fieldAccount">--</td></tr>
    <tr><th scope="row">Balance</th><td id="fieldBalance">--</td></tr>
    <tr><th scope="row">Processing time</th><td id="latencyBadge">--</td></tr>
    </tbody>
  </table>
  <details class="json-details"><summary>Legacy response <span class="quiet-label">JSON</span></summary><pre id="jsonOutput">{}</pre></details>
  </details>
  __SMS_RESEARCH_MARKUP__
    </section>
    </div>
  __MERCHANT_LAB_MARKUP__
  </main>
  <footer class="page-footer"><span>Masroof · Jordan SMS engine</span><span>Arabic &amp; English · Offline</span></footer>
  </div>
  <script>
    const MODEL = __MODEL_DATA__;
    __STARTUP_SCRIPT__
    var MasroofRuntime = initializeTesterRuntime(__ENGINE_BUNDLE__, MODEL);

    const PRESETS = __TESTER_PRESETS__;
    __ASSESSMENT_SCRIPT__
    __OWNERSHIP_SCRIPT__
    if (!testerStartup.ready) renderTesterNotReady();
    __SMS_RESEARCH_SCRIPT__

    function loadPreset(key) {
      var p = PRESETS[key];
      if (p) {
        document.getElementById('senderInput').value = p.sender;
        document.getElementById('bodyInput').value = p.body;
        document.getElementById('isContactInput').checked = false;
        startNewOwnershipMessage();
      }
    }

    // Compatibility helpers for the optional developer page; inference comes
    // directly from the canonical TypeScript modules in the local bundle.
    function normalizeFinancialNumbers(text) { return MasroofRuntime.preprocessing.normalizeFinancialNumbers(text); }
    function preprocess(text) { return MasroofRuntime.preprocessing.preprocessMessage(text); }
    function tokenize(text) { return MasroofRuntime.preprocessing.tokenizeFeatures(text); }
    function parseNumber(value) { return MasroofRuntime.MasroofEngine.parseNumber(value); }
    function isServiceNotice(text) { return MasroofRuntime.serviceNotice.isServiceNotice(text); }
    function loadUserOverlay(value) { return MasroofRuntime.MasroofEngine.loadUserOverlay(value); }
    function exportUserOverlay() { return MasroofRuntime.MasroofEngine.exportUserOverlay(); }
    function applyCorrection(merchant, category) { return MasroofRuntime.MasroofEngine.applyCorrection(merchant, category); }
    function classifyCategory(merchant, text) { return MasroofRuntime.MasroofEngine.classifyCategory(merchant, text); }
    function analyze(sender, body, isContact) {
      requireTesterReady();
      var started = performance.now();
      var result = MasroofRuntime.MasroofEngine.analyze({ sender: sender, body: body, isContact: isContact });
      return { result: result, latency: performance.now() - started };
    }

    function analyzeDetailed(input) {
      requireTesterReady();
      return MasroofRuntime.MasroofEngine.analyzeDetailed(input);
    }

    function runAnalysis() {
      if (!testerStartup.ready) { renderTesterNotReady(); return; }
      document.getElementById('startupStatus').hidden = true;
      var sender = document.getElementById('senderInput').value;
      var body = document.getElementById('bodyInput').value;
      var isContact = document.getElementById('isContactInput').checked;
      renderOwnership(sender, body, isContact);
      if (!body.trim()) {
        renderPrimaryAssessment(null);
        renderLegacyComparison(null);
        renderSmsResearch(body, null);
        updateMerchantSms(null);
        return;
      }
      var started = performance.now();
      var detailed = analyzeDetailed({ sender: sender, text: body, isContact: isContact });
      renderPrimaryAssessment(detailed, performance.now() - started);
      renderSmsResearch(body, detailed);
      // A compatibility failure cannot suppress the primary assessment.
      try {
        var analysis = analyze(sender, body, isContact);
        renderLegacyComparison(analysis);
        updateMerchantSms(analysis.result);
      } catch (error) {
        renderLegacyComparison(null, String(error.message || error));
        updateMerchantSms(null);
      }
    }

    __MERCHANT_LAB_SCRIPT__
    document.addEventListener("DOMContentLoaded", function() {
      loadPreset('arab_pos');
    });
  </script>
</body>
</html>'''

    final_html = html_content.replace("__TESTER_CSS__", (root / "tools/browser/tester.css").read_text(encoding="utf-8"))
    final_html = final_html.replace("__MODEL_DATA__", model_json_str)
    presets = json.loads((root / "tools/browser/presets.json").read_text(encoding="utf-8"))["presets"]
    final_html = final_html.replace("__TESTER_PRESETS__", json.dumps(presets, ensure_ascii=False))
    bundle = subprocess.run([node_executable(), str(root / "tools/browser/bundle_engine.mjs")],
                            capture_output=True, text=True, encoding="utf-8", check=True)
    # Keep core syntax inside a string until the startup capability checks pass.
    safe_bundle = json.dumps(bundle.stdout, ensure_ascii=False).replace("<", "\\u003c").replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")
    final_html = final_html.replace("__ENGINE_BUNDLE__", safe_bundle)
    final_html = final_html.replace("__STARTUP_SCRIPT__", (root / "tools/browser/startup_guard.js").read_text(encoding="utf-8"))
    final_html = final_html.replace("__ASSESSMENT_SCRIPT__", (root / "tools/browser/assessment_view.js").read_text(encoding="utf-8"))
    final_html = final_html.replace("__OWNERSHIP_SCRIPT__", (root / "tools/browser/ownership_tester.js").read_text(encoding="utf-8"))
    research_markup, research_script = build_sms_research(root)
    final_html = final_html.replace("__SMS_RESEARCH_MARKUP__", research_markup).replace("__SMS_RESEARCH_SCRIPT__", research_script)
    markup, script = build_merchant_lab(root)
    final_html = final_html.replace("__MERCHANT_LAB_MARKUP__", markup).replace("__MERCHANT_LAB_SCRIPT__", script)

    # Unicode separators can occur inside embedded JSON/JS strings. Only split
    # actual file newlines; splitlines() would turn those characters into syntax.
    final_html = "\n".join(line.rstrip() for line in final_html.split("\n")) + "\n"

    workspace_path = Path(__file__).resolve().with_name("tester.html")
    with workspace_path.open("w", encoding="utf-8") as f:
        f.write(final_html)
    print(f"Saved workspace tester: {workspace_path}")

if __name__ == "__main__":
    build()
