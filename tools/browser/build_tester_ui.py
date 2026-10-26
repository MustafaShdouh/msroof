import json
import subprocess
from pathlib import Path
from merchant_lab import build_merchant_lab

def build():
    root = Path(__file__).resolve().parents[2]
    with (root / "data" / "models" / "masroof_model.json").open("r", encoding="utf-8") as f:
        model_json_str = f.read()

    html_content = r'''<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <title>Masroof ML Tester</title>
</head>
<body style="font-family: monospace; background-color: #fff; color: #000; padding: 15px;">

  <h1 style="color: darkred; margin-bottom: 5px;">Masroof ML Tester</h1>
  <small style="color: #666;">Jordan SMS engine and merchant category experiments</small>
  <hr>

  <div>
    <strong>PRESETS:</strong> <span style="color: gray;">&lt;----- click these if you're too lazy to type</span><br>
    <button onclick="loadPreset('arab_pos')">Arab Bank POS</button>
    <button onclick="loadPreset('cliq_in')">CliQ In</button>
    <button onclick="loadPreset('cliq_out')">CliQ Out</button>
    <button onclick="loadPreset('orange_wallet')">Orange Money</button>
    <button onclick="loadPreset('zain_bill')">Zain Cash</button>
    <button onclick="loadPreset('fx_usd_jod')">FX: USD Billed JOD</button>
    <button onclick="loadPreset('farm_to_table')">Collision: Farm To Table</button>
    <button onclick="loadPreset('balance_inquiry')">Trap: Balance Inquiry</button>
    <button onclick="loadPreset('incomplete_tx')">Trap: No Amount</button>
    <button onclick="loadPreset('internal_transfer')">Trap: Own Account Transfer</button>
    <button onclick="loadPreset('trap_otp')">Trap: OTP</button>
    <button onclick="loadPreset('declined')">Declined</button>
    <button onclick="loadPreset('chat_noise')">Chat Noise</button>
    <button onclick="loadPreset('gibberish')">Gibberish</button>
  </div>

  <br>
  <hr>

  <div>
    <label><strong>Sender:</strong></label><br>
    <input type="text" id="senderInput" value="ArabiBank" style="width: 250px;" oninput="runAnalysis()">
    <span>-----> this is where you put the sender name</span><br>
    <label style="font-size: 13px; color: #333; margin-top: 4px; display: inline-block;">
      <input type="checkbox" id="isContactInput" onchange="runAnalysis()">
      Sender is saved in your iPhone Contacts (e.g., Dad, Mom, Brother)
    </label>
  </div>
  <br>
  <div>
    <label><strong>SMS Body:</strong></label><br>
    <textarea id="bodyInput" rows="6" cols="70" style="vertical-align: top;" oninput="runAnalysis()"></textarea>
    <span style="vertical-align: top; display: inline-block; padding-left: 10px; margin-top: 10px;">-----> paste the actual sms message here</span>
  </div>

  <hr>

  <details>
    <summary><strong>Detailed assessment comparison: <span id="detailedDecision">Ready</span></strong></summary>
    <p>Development comparison. Only an include decision is eligible for recording; review requires inspection.</p>
    <pre id="detailedOutput">{}</pre>
  </details>
  <h3>Legacy output (current caller path) <span style="font-size: 12px; font-weight: normal; color: blue;">-----> compare with the detailed assessment above</span></h3>
  <table border="1" cellpadding="5" cellspacing="0" style="border-collapse: collapse; min-width: 400px;">
    <tr><td style="width: 140px;"><strong>Status:</strong></td><td id="decisionTitle">Ready</td></tr>
    <tr><td><strong>Confidence:</strong></td><td id="confidenceVal">--</td></tr>
    <tr><td><strong>Category:</strong></td><td id="fieldCategory">--</td></tr>
    <tr><td><strong>Direction:</strong></td><td id="fieldDirection">--</td></tr>
    <tr><td><strong>Amount:</strong></td><td id="fieldAmount">--</td></tr>
    <tr><td><strong>Original Amount (FX):</strong></td><td id="fieldOrigAmount">--</td></tr>
    <tr><td><strong>Exchange Rate:</strong></td><td id="fieldRate">--</td></tr>
    <tr><td><strong>Party:</strong></td><td id="fieldParty">--</td></tr>
    <tr><td><strong>Account:</strong></td><td id="fieldAccount">--</td></tr>
    <tr><td><strong>Balance:</strong></td><td id="fieldBalance">--</td></tr>
    <tr><td><strong>Latency:</strong></td><td id="latencyBadge">--</td></tr>
  </table>

  <br>
  <strong>Raw JSON:</strong><br>
  <pre id="jsonOutput" style="background: #f0f0f0; border: 1px solid #aaa; padding: 10px; width: 600px; max-height: 250px; overflow: auto;"></pre>

  __MERCHANT_LAB_MARKUP__
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
        document.getElementById('detailedOutput').innerText = '{}';
        updateMerchantSms(null);
        document.getElementById('decisionTitle').innerText = "Ready (Type text or click preset)";
        document.getElementById('decisionTitle').style.color = "black";
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
        title.style.color = "green";

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
        title.style.color = "red";

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

    final_html = html_content.replace("__MODEL_DATA__", model_json_str)
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
