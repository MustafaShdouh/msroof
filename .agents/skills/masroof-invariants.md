# Masroof Engine Architecture & Development Invariants

1. **Performance SLA**:
   - Mean processing latency must remain under **0.10 ms** in pure JavaScript on the Meta Hermes engine.
   - Minimal memory allocation and zero garbage collection pressure in hot inference paths (prefer flat arrays/primitive loops over allocating temporary closures/objects).

2. **Strict Parity Guarantee**:
   - `MasroofEngine.ts` (TypeScript / React Native runtime), `verify_engine.py` (Python reference/trainer), and `tester.html` (interactive web playground) must maintain 100% mathematical and behavioral parity.
   - Any new feature, formula, or tag must be simultaneously implemented and tested across both engines.

3. **Zero Hardcoding**:
   - No hardcoded bank lists, merchant registries, sender IDs, or switch-cases for specific institutions.
   - All classification and extraction must generalize across Arabic and English financial messages via statistical weights, subwords, or structural linguistic patterns.

4. **Sequential Bite-Sized Implementation**:
   - Implement complex features in small, atomic tasks.
   - Critically evaluate each code chunk for Hermes GC efficiency, scalability, and edge cases before advancing to the next task.

5. **Targeted Code Exploration**: Never dump whole files. Read exact line slices (`StartLine`/`EndLine`).

6. **File-Based Continuation Memory**: Update `.agents/HANDOFF.md` only after a material code change, verified result, user decision, or plan change. It is the single handoff record for a new local model; do not create a duplicate journal.

7. **Command Execution Resilience**: On Windows PowerShell, execute npm/npx packages using `cmd /c npx ...`.