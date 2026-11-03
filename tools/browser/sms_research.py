"""Embed the frozen research export for opt-in local comparison; never train."""
import hashlib
import json


def build_sms_research(root):
    report_path = root / "data/reports/transactions/sms_semantics_followup_v1.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    model_path = "data/models/sms_semantics_followup_v1_word_candidate.json"
    runtime_path = "data/models/sms_semantics_ab_v1_browser_runtime.js"
    def checked(relative, expected):
        raw = (root / relative).read_bytes()
        if hashlib.sha256(raw).hexdigest() != expected:
            raise ValueError("Research tester asset differs from frozen evaluation: " + relative)
        return raw.decode("utf-8")
    model = checked(model_path, report["outputSha256"][model_path])
    runtime = checked(runtime_path, report["inputSha256"][runtime_path])
    for relative, expected in report["exportParity"]["browserSourceSha256"].items():
        checked(relative, expected)
    context_report = json.loads((root / "data/reports/transactions/sms_completion_context_v1.json").read_text(encoding="utf-8"))
    context_model_path = "data/models/sms_completion_context_v1_candidate.json"
    context_runtime_path = "data/models/sms_completion_context_v1_browser_runtime.js"
    context_model = checked(context_model_path, context_report["outputSha256"][context_model_path])
    context_runtime = checked(context_runtime_path, context_report["outputSha256"][context_runtime_path])
    for relative, expected in context_report["exportParity"]["browserSourceSha256"].items():
        checked(relative, expected)
    ui_path = "tools/browser/sms_research.js"
    ui = (root / ui_path).read_text(encoding="utf-8")
    assets = {model_path: report["outputSha256"][model_path], runtime_path: report["inputSha256"][runtime_path],
              ui_path: hashlib.sha256((root / ui_path).read_bytes()).hexdigest()}
    assets.update(context_report["outputSha256"])
    markup = '''
  <details class="assessment-details sms-research-panel" id="smsResearchPanel" ontoggle="toggleSmsResearch()">
    <summary><span>Try the trained model</span><span class="quiet-label">Optional research</span></summary>
    <p class="help-text">This experimental model was trained with synthetic messages. It predicts transaction wording and money flow; it does not decide whether to record a transaction.</p>
    <label class="quiet-label" for="smsResearchModelSelect">Research model</label>
    <select id="smsResearchModelSelect" onchange="changeSmsResearchModel()" aria-describedby="smsResearchModelNote">
      <option value="word">Word reference</option>
      <option value="context">Word sequences · experimental</option>
    </select>
    <p class="help-text" id="smsResearchModelNote">The word-sequence candidate has known false acceptances, including an OTP. Compare it manually; it is not ready for automatic recording.</p>
    <div class="sms-research-predictions" aria-live="polite">
      <div><span class="quiet-label">Model prediction</span><p id="smsResearchTransaction">Open to compare</p></div>
      <div><span class="quiet-label">Money flow</span><p id="smsResearchDirection">—</p></div>
    </div>
    <table class="result-table" aria-label="Existing message-only checks">
      <tbody>
        <tr><th scope="row">Amount · existing extractor</th><td id="smsResearchAmount">—</td></tr>
        <tr><th scope="row">Recording · message-only check</th><td id="smsResearchTracking">—</td></tr>
      </tbody>
    </table>
    <p class="help-text" id="smsResearchNote">Ownership confirmations are shown in their own panel. These checks remain separate from the model prediction.</p>
    <details class="json-details"><summary>Model details</summary>
      <p class="help-text">Decision scores are not confidence percentages. This is a small development experiment, not a real-world accuracy estimate.</p>
      <pre id="smsResearchOutput">{}</pre>
    </details>
  </details>'''
    safe_model = json.dumps(json.loads(model), ensure_ascii=False).replace("<", "\\u003c").replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")
    safe_context = json.dumps(json.loads(context_model), ensure_ascii=False).replace("<", "\\u003c").replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")
    script = runtime + "\nconst SmsCompletionContextResearch = (() => {\n" + context_runtime + "\nreturn SmsSemanticsResearch;\n})();\n"
    script += "const SMS_RESEARCH_MODEL = " + safe_model + ";\nconst SMS_CONTEXT_MODEL = " + safe_context + ";\nconst SMS_RESEARCH_ASSETS = " + json.dumps(assets) + ";\n" + ui
    return markup, script
