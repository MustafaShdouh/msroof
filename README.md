# Masroof

Offline Arabic/English transaction parsing for Jordanian bank and wallet messages. Development is suspended as of 2026-11-04. This prototype is prepared for teammate evaluation.

Start with the [teammate handover](docs/TEAMMATE_HANDOFF.md) for setup, API examples, architecture, product decisions and limits.

## Quick start

Open [the standalone tester](tools/browser/tester.html), or verify runtime behavior:

~~~powershell
python verify_runtime.py
~~~

The portable check requires Python 3.14 and Node.js 24. Inference uses standard Python. The engine combines rules, regex extraction and a small learned scorer. Categories are incomplete. Independent accuracy, production/mobile readiness and an advantage over a simpler parser remain unestablished.

## Layout

| Directory | Purpose |
| --- | --- |
| src/python, src/typescript | Runtime implementations and isolated research modules |
| config/contracts | Shared behavior and data contracts |
| data/models/masroof_model.json | Active weights |
| tools/browser | Tester source, builder and generated page |
| tests | Runtime and research safeguards |
| training | Offline data preparation, training and evaluation |
| data/reports, docs | Historical evidence and specifications |

## Get the repository

~~~powershell
git clone https://github.com/MustafaShdouh/msroof.git
cd msroof
python verify_runtime.py
~~~

Read the teammate handover before changing engine behavior. Runtime source, tests, training code, sanitized development data and historical reports are retained in this repository. Private original messages, local environments and AI working notes are ignored.

## Full source verification

For maintainers with the complete private research inputs:

~~~powershell
python -m pip install -r config/requirements-dev.txt
python -X utf8 run_all_tests.py
~~~

The full runner includes historical research checks requiring private checksum-bound snapshots and original messages. Those inputs are excluded from GitHub. The portable check runs without them.

The last complete gate passed 359 Python tests, 14 TypeScript suites and 226 frozen cases. These are development conformance results.

Rebuild the tester after source edits:

~~~powershell
python tools/browser/build_tester_ui.py
~~~

[Architecture](docs/ARCHITECTURE.md) and [readiness](docs/CORE_MONEY_READINESS.md) describe the implementation and evidence. The [roadmap](docs/CORE_MONEY_ROADMAP.md) records historical work and open tasks. Development is currently suspended.
