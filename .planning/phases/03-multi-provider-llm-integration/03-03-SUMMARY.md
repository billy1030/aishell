---
phase: 03-multi-provider-llm-integration
plan: 03
subsystem: ui-cli
tags: [cli, repl, streaming, error-handling, runtime-switching]

requires: [03-02]
provides:
  - CLI flags (-p/--provider and -m/--model) for one-shot execution and REPL initialization
  - execute_one_shot active streaming from configured or overridden provider
  - InteractiveREPL provider integration with dynamic /provider and /model switching
  - Prompt status indicator showing active provider and model (e.g. [ollama:qwen2.5-coder:7b])
  - Actionable error formatting via render_error with zero raw stack traces
affects: [04-01]

actuals:
  tokens: 4300
  tasks: 2
  commits: 2

tech-stack:
  added: []
  patterns: [CLI argument overrides, dynamic REPL provider switching, async-to-sync streaming bridge]

key-files:
  created:
    - tests/test_cli_provider.py
    - tests/test_repl_provider.py
  modified:
    - src/aishell/cli.py
    - src/aishell/ui/repl.py
    - tests/test_cli_oneshot.py

key-decisions:
  - "D-04: Runtime provider and model switching supported via CLI flags (-p, -m) and REPL meta-commands (/provider, /model)"
  - "D-05: Provider errors intercepted and rendered with actionable guidance hints and zero unhandled python tracebacks"
  - "D-07: Real-time asynchronous token streaming wired end-to-end to RichStreamRenderer for one-shot and REPL queries"

patterns-established:
  - "Async streaming generator bridge using event loop run_until_complete over agen.__anext__()"
  - "REPL prompt status display reflecting provider:model dynamically on every prompt turn"

requirements-completed: [PROV-01, PROV-02, PROV-04]

coverage:
  - id: D1
    description: "CLI provider flags and one-shot active streaming with error guidance"
    requirement: "PROV-01, PROV-02, PROV-04"
    verification:
      - kind: integration
        ref: "tests/test_cli_provider.py"
        status: pass
    human_judgment: false
  - id: D2
    description: "InteractiveREPL provider streaming and /provider, /model switching"
    requirement: "PROV-01, PROV-02, PROV-04"
    verification:
      - kind: integration
        ref: "tests/test_repl_provider.py"
        status: pass
    human_judgment: false
---

# Phase 03 Plan 03: CLI & REPL Multi-Provider Integration Summary

## Accomplishments
1. **CLI Provider & Model Flags**: Added `-p`/`--provider` and `-m`/`--model` options to `aishell` main entrypoint and `ask` command, enabling runtime provider override.
2. **One-Shot Token Streaming**: Wired `execute_one_shot` to resolve the requested provider and stream tokens in real-time to `RichStreamRenderer`.
3. **Actionable Error Interception**: Handled `ProviderError` exceptions (missing API keys, unreachable daemon, rate limits) by outputting clean error guidance without raw stack traces.
4. **InteractiveREPL Live Streaming & Switching**: Replaced the Phase 2 placeholder in `InteractiveREPL` with live provider streaming, added `/provider` and `/model` meta-commands for on-the-fly switching, and updated prompt status to display active provider and model (e.g. `[ollama:qwen2.5-coder:7b]`).
5. **Testing**: 8 tests passing across `tests/test_cli_provider.py` and `tests/test_repl_provider.py`; entire workspace test suite (101 tests) passing cleanly with zero regressions.
