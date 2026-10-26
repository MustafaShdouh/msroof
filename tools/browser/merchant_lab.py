"""Bundle the shared TypeScript scorer and trained exports into the offline tester."""
import hashlib
import json
import subprocess


def build_merchant_lab(root):
    report_path = root / "data/reports/merchant_category_research_jordan_data_v3.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    models = {}
    for variant, item in report["variants"].items():
        path = root / item["modelPath"]
        if hashlib.sha256(path.read_bytes()).hexdigest() != item["modelSha256"]:
            raise ValueError("Candidate model/report hash mismatch")
        models[variant] = json.loads(path.read_text(encoding="utf-8"))
    # Strip types using Node's bundled parser; no independent browser scorer copy.
    transpile = """import fs from 'node:fs'; import {stripTypeScriptTypes} from 'node:module';
const source=fs.readFileSync(process.argv[1],'utf8').replace(/^import .*;\\r?\\n/gm,'');
process.stdout.write(stripTypeScriptTypes(source).replace(/^export /gm,''));"""
    process = subprocess.run([r"C:\Program Files\nodejs\node.exe", "--input-type=module", "-e", transpile,
                              str(root / "src/typescript/MerchantCategory.ts")],
                             capture_output=True, text=True, encoding="utf-8", check=True)
    script = "const MerchantResearch = (() => {\n" + process.stdout + "\nreturn {loadMerchantCategoryModel,predictMerchantCategory};})();\n"
    summary = {key: {"human": item["validation"]["humanLabelsOnly"],
                     "combined": item["validation"]["combinedResearchLabels"],
                     "businessCount": item["businessCount"], "viewCount": item["viewCount"]}
               for key, item in report["variants"].items()}
    payload = {"models": models, "summary": summary, "selected": report["selectedResearchVariant"],
               "reportPath": report_path.relative_to(root).as_posix()}
    script += "const MERCHANT_LAB_DATA = " + json.dumps(payload, ensure_ascii=False).replace('<', '\\u003c') + ";\n"
    script += (root / "tools/browser/merchant_lab.js").read_text(encoding="utf-8")
    markup = '''
  <details class="merchant-lab">
    <summary>Merchant category research <span class="quiet-label">Experimental</span></summary>
    <div class="merchant-content">
    <p class="help-text">Try a shop or service name. This predicts a merchant default;
    a specific purchase, installment or refund can need more context.</p>
    <div class="merchant-controls">
    <div class="merchant-field"><label for="merchantVariant">Research model</label>
    <select id="merchantVariant" onchange="runMerchantLab();runAnalysis()">
      <option value="baseline">Canonical names (selected baseline)</option>
      <option value="aliases">Observed Arabic / English aliases</option>
      <option value="augmented">Aliases + bounded spelling variations</option>
    </select></div>
    <div class="merchant-field"><label for="merchantNameInput">Shop or service name</label>
    <input id="merchantNameInput" type="text" dir="auto" placeholder="Enter an Arabic or English name"
      oninput="runMerchantLab()"></div>
    </div>
    <div class="merchant-examples"><span>Training examples</span>
      <button onclick="setMerchantExample('مطعم هاشم')">مطعم هاشم</button>
      <button onclick="setMerchantExample('شركة الكهرباء الأردنية')">شركة الكهرباء الأردنية</button>
      <button onclick="setMerchantExample('Netflix')">Netflix</button>
    </div>
    <div class="merchant-results">
      <div><h3>Name prediction</h3><pre id="merchantNameResult"></pre></div>
      <div><h3>From the message above</h3><pre id="merchantSmsResult"></pre></div>
    </div>
    <details class="research-notes"><summary>Research notes &amp; validation</summary>
    <p>Training round 3 includes broader grocery, hospital and fuel-provider examples.
    The examples above are from training and are not accuracy tests.</p>
    <p id="merchantMetrics"></p>
    <p>Model scores are uncalibrated, not a percentage chance of being correct.
    Cash Withdrawals, Installments and Fees are not trained here. Results do not change
    the existing SMS engine category shown above. Final test set remains unevaluated.</p>
    </details>
    </div>
  </details>'''
    return markup, script
