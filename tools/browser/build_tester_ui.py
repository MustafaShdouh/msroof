import json
import subprocess
from pathlib import Path
from merchant_lab import build_merchant_lab

def build():
    root = Path(__file__).resolve().parents[2]
    with (root / "data" / "models" / "masroof_model.json").open("r", encoding="utf-8") as f:
        model_json_str = f.read()

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
    <button onclick="loadPreset('internal_transfer')">Own-account transfer</button>
    <button onclick="loadPreset('trap_otp')">Verification code</button>
    <button onclick="loadPreset('declined')">Declined</button>
    <button onclick="loadPreset('chat_noise')">Personal message</button>
    <button onclick="loadPreset('gibberish')">Unrecognized text</button>
        </div>
      </details>
    </section>

    <section class="panel analysis-panel" aria-labelledby="analysisHeading">
      <div class="panel-heading"><h2 id="analysisHeading">Analysis</h2><span class="quiet-label">Engine output</span></div>
  <details class="assessment-details">
    <summary><span>Detailed assessment comparison</span><span class="decision-badge" id="detailedDecision">Ready</span></summary>
    <p class="help-text">Include is eligible for recording. Review requires inspection. This view compares the new assessment with the current engine below.</p>
    <pre id="detailedOutput">{}</pre>
  </details>
  <div class="result-heading"><h3>Current output</h3><span class="quiet-label">Legacy caller</span></div>
  <table class="result-table" aria-label="Current engine result">
    <tbody>
    <tr class="status-row"><th scope="row">Status</th><td id="decisionTitle">Ready</td></tr>
    <tr><th scope="row">Model score</th><td id="confidenceVal">--</td></tr>
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
  <details class="json-details"><summary>Raw response <span class="quiet-label">JSON</span></summary><pre id="jsonOutput">{}</pre></details>
    </section>
    </div>
  __MERCHANT_LAB_MARKUP__
  </main>
  <footer class="page-footer"><span>Masroof · Jordan SMS engine</span><span>Arabic &amp; English · Offline</span></footer>
  </div>
  <script>
    const MODEL = __MODEL_DATA__;
    __ENGINE_BUNDLE__
    MasroofRuntime.MasroofEngine.init(MODEL);

    const PRESETS = __TESTER_PRESETS__;

    function loadPreset(key) {
      var p = PRESETS[key];
      if (p) {
        document.getElementById('senderInput').value = p.sender;
        document.getElementById('bodyInput').value = p.body;
        document.getElementById('isContactInput').checked = false;
        runAnalysis();
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
      var started = performance.now();
      var result = MasroofRuntime.MasroofEngine.analyze({ sender: sender, body: body, isContact: isContact });
      return { result: result, latency: performance.now() - started };
    }

    function analyzeDetailed(input) {
      return MasroofRuntime.MasroofEngine.analyzeDetailed(input);
    }

    function runAnalysis() {
      var sender = document.getElementById('senderInput').value;
      var body = document.getElementById('bodyInput').value;
      var isContact = document.getElementById('isContactInput').checked;

      if (!body.trim()) {
        document.getElementById('detailedDecision').innerText = 'Ready';
        document.getElementById('detailedDecision').style.color = '#68716a';
        document.getElementById('detailedDecision').style.backgroundColor = '#f3f5f1';
        document.getElementById('detailedOutput').innerText = '{}';
        updateMerchantSms(null);
        document.getElementById('decisionTitle').innerText = "Ready (Type text or click preset)";
        document.getElementById('decisionTitle').style.color = "#626b65";
        document.getElementById('confidenceVal').innerText = "--";
        document.getElementById('fieldCategory').innerText = "--";
        document.getElementById('fieldDirection').innerText = "--";
        document.getElementById('fieldAmount').innerText = "--";
        document.getElementById('fieldOrigAmount').innerText = "--";
        document.getElementById('fieldRate').innerText = "--";
        document.getElementById('fieldParty').innerText = "--";
        document.getElementById('fieldAccount').innerText = "--";
        document.getElementById('fieldBalance').innerText = "--";
        document.getElementById('jsonOutput').innerText = "{}";
        document.getElementById('latencyBadge').innerText = "0 ms";
        return;
      }

      var detailed = analyzeDetailed({ sender: sender, text: body, isContact: isContact });
      document.getElementById('detailedDecision').innerText = detailed.trackingDecision === 'review' ? 'Review required' :
        (detailed.trackingDecision === 'include' ? 'Include' : 'Exclude');
      document.getElementById('detailedDecision').style.color = detailed.trackingDecision === 'review' ? '#846434' :
        (detailed.trackingDecision === 'include' ? '#35634c' : '#68716a');
      document.getElementById('detailedDecision').style.backgroundColor = detailed.trackingDecision === 'review' ? '#f5efe3' :
        (detailed.trackingDecision === 'include' ? '#edf1e9' : '#f3f5f1');
      document.getElementById('detailedOutput').innerText = JSON.stringify(detailed, null, 2);
      var analysis = analyze(sender, body, isContact);
      var result = analysis.result;
      updateMerchantSms(result);
      var latency = analysis.latency;

      document.getElementById('latencyBadge').innerText = latency.toFixed(3) + " ms";
      document.getElementById('confidenceVal').innerText = result.confidence;

      var title = document.getElementById('decisionTitle');

      if (result.isValidTransaction) {
        title.innerText = "VALID TRANSACTION";
        title.style.color = "#35634c";

        var d = result.data;
        document.getElementById('fieldCategory').innerText = d.category ? (d.category + " (" + Math.round(d.categoryConfidence * 100) + "%)") : "--";
        document.getElementById('fieldDirection').innerText = d.type + " (" + d.direction + ")";
        document.getElementById('fieldAmount').innerText = d.amount + " " + d.currency;
        document.getElementById('fieldOrigAmount').innerText = (d.originalAmount && d.originalCurrency) ? (d.originalAmount + " " + d.originalCurrency) : "None (Single Currency)";
        document.getElementById('fieldRate').innerText = d.exchangeRate ? ("1 " + d.originalCurrency + " = " + d.exchangeRate + " " + d.currency) : "None";
        document.getElementById('fieldParty').innerText = d.merchantOrParty || "None";
        document.getElementById('fieldAccount').innerText = d.accountMask || "None";
        document.getElementById('fieldBalance').innerText = d.balance !== null ? (d.balance + " " + d.currency) : "None";
      } else {
        title.innerText = "REJECTED (" + (result.reason || "Invalid") + ")";
        title.style.color = "#984b47";

        document.getElementById('fieldCategory').innerText = "--";
        document.getElementById('fieldDirection').innerText = "--";
        document.getElementById('fieldAmount').innerText = "--";
        document.getElementById('fieldOrigAmount').innerText = "--";
        document.getElementById('fieldRate').innerText = "--";
        document.getElementById('fieldParty').innerText = "--";
        document.getElementById('fieldAccount').innerText = "--";
        document.getElementById('fieldBalance').innerText = "--";
      }

      document.getElementById('jsonOutput').innerText = JSON.stringify(result, null, 2);
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
    bundle = subprocess.run([r"C:\Program Files\nodejs\node.exe", str(root / "tools/browser/bundle_engine.mjs")],
                            capture_output=True, text=True, encoding="utf-8", check=True)
    final_html = final_html.replace("__ENGINE_BUNDLE__", bundle.stdout)
    markup, script = build_merchant_lab(root)
    final_html = final_html.replace("__MERCHANT_LAB_MARKUP__", markup).replace("__MERCHANT_LAB_SCRIPT__", script)

    final_html = "\n".join(line.rstrip() for line in final_html.splitlines()) + "\n"

    workspace_path = Path(__file__).resolve().with_name("tester.html")
    with workspace_path.open("w", encoding="utf-8") as f:
        f.write(final_html)
    print(f"Saved workspace tester: {workspace_path}")

if __name__ == "__main__":
    build()
