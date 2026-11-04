# Masroof engine handover

Status as of 2026-11-04. Development is suspended. This is a prototype for teammate evaluation.

## Try it

Open tools/browser/tester.html in a desktop browser. Paste an Arabic or English bank notification. The primary Message-only assessment shows amount, currency, direction, category and the recording decision.

- include means eligible for recording under the current policy.
- review means completion, amount, direction or ownership needs clarification.
- exclude means the message should not be recorded.

The ownership panel can confirm another person or your own accounts. Confirmation applies to that exact message and stays in page memory. Legacy and research panels are developer diagnostics.

## Verify a fresh checkout

Clone the repository and run this from its root, with Python 3.14 and Node.js 24 on PATH:

~~~powershell
python verify_runtime.py
~~~

This compares Python, TypeScript and embedded tester outputs on 54 existing development controls. It uses standard Python and Node, with no training environment or private messages.

## Python entry point

Keep the layout intact so contracts and weights can be found.

~~~python
from src.python.engine import MasroofEngine

engine = MasroofEngine()
result = engine.predict_detailed({
    "text": "Your account was debited JOD 12.750 for a completed purchase."
})
print(result)
~~~

## TypeScript entry point

~~~typescript
import fs from 'node:fs';
import { MasroofEngine } from './src/typescript/MasroofEngine.ts';

MasroofEngine.init(JSON.parse(fs.readFileSync('data/models/masroof_model.json', 'utf8')));
const result = MasroofEngine.analyzeDetailed({
  text: 'Your account was debited JOD 12.750 for a completed purchase.'
});
console.log(result);
~~~

This initialization example uses Node. A mobile host must supply the same JSON through its own asset loader. Target-device integration is unverified.

Use predict_detailed/analyzeDetailed for current behavior. predict/analyze retain compatibility behavior. predict_with_ownership/analyzeWithOwnership provide separate confirmation wrappers. Shared schemas are under config/contracts/.

## Architecture

src/python and src/typescript implement matching pipelines. They normalize number scripts, assess context/completion, extract amount candidates, resolve direction/ownership and return a recording decision. The engine combines shared rules, regex extraction and a small learned scorer. Its weights are data/models/masroof_model.json.

The standalone tester embeds a runtime snapshot. After source changes, rebuild it with python tools/browser/build_tester_ui.py. The training and research directories preserve prior experiments and their evidence.

## Product decisions

- Scope is Jordanian Arabic, English and mixed messages.
- Person-to-person transfers count. Own-account transfers exclude. A counterparty name alone does not prove ownership.
- Missing or ambiguous currency visibly defaults to JOD. Explicit foreign currency is retained.
- Primary amount uses an explicitly stated fee-inclusive posted total or account charge. Unstated sums or conversions are not inferred.
- Exact counterparty text is preserved. Category is optional and can remain unresolved.
- ZAMZAM WATER maps to Water and Electricity by an approved rule. Broader merchant categorization is incomplete.

## Evidence and limits

The source checkout passed 359 Python tests, 14 TypeScript suites and 226 frozen compatibility cases on 2026-11-04 before this handover cleanup. The portable runtime check covers a smaller set. Tests are exposed development evidence. Independent accuracy, production readiness, target-device performance and ML's incremental value remain unestablished.

Text cannot authenticate a bank sender. Zero/signed movement policy and ingestion deduplication need further decisions. Category coverage is limited. There is no evidence that this engine outperforms a simpler regex implementation.

Research dependencies such as PyTorch belong to offline experiments. Runtime inference uses standard Python or TypeScript and JSON.

## Repository contents

The GitHub repository contains the runtime, active and research models, shared contracts, browser tools, tests, training pipelines, sanitized development data, annotations and historical reports. README.md is the starting point. docs/ARCHITECTURE.md maps the implementation, and docs/CORE_MONEY_READINESS.md describes the measured limits.

Private SMS originals, AI working notes, credentials, local environments and experiment caches are ignored. The full research regression runner depends on checksum-bound private historical inputs, so its complete local result cannot be reproduced from a GitHub clone alone. Use python verify_runtime.py for the portable check. Missing historical inputs must not be repaired by modifying old reports.

## Continuation

Run verification and inspect sample results. Decide whether to retain the hybrid engine or compare a simpler parser on fresh labeled messages. Set acceptance criteria before more model work.
