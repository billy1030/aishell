---
phase: 02-interactive-repl-streaming-terminal-ui
plan: 03
subsystem: ui
tags: [repl, prompt-toolkit, multiline, signal-handling, interactive-cli]

requires: [02-01, 02-02]
provides:
  - InteractiveREPL engine with multiline input handling (Enter / Alt+Enter / `\`)
  - Isolated Ctrl+C signal handling preventing generation cancellation from terminating the REPL
  - Clean double Ctrl+C (within 1.5s) and Ctrl+D session exit lifecycle
  - Built-in REPL meta commands (:exit, :quit, /clear, /help)
  - Interactive CLI wiring for bare `aishell` invocation with non-TTY fallback
affects: [03-01]

actuals:
  tokens: 4200
  tasks: 2
  commits: 2

tech-stack:
  added: [prompt_toolkit.shortcuts.PromptSession, prompt_toolkit.key_binding.KeyBindings]
  patterns: [PromptSession event loop, keybinding interception, signal state machine, TTY terminal detection]

key-files:
  created:
    - src/aishell/ui/repl.py
    - tests/test_repl.py
    - tests/test_cli_repl.py
  modified:
    - src/aishell/ui/__init__.py
    - src/aishell/cli.py

key-decisions:
  - "D-02: Multiline submission behavior: standard Enter submits; Alt+Enter or trailing backslash introduces a newline."
  - "D-03: Signal routing: Ctrl+C during active stream cancels token output without killing session; at empty prompt, requires double Ctrl+C within 1.5s (or Ctrl+D) to exit."
  - "D-10: InteractiveREPL built on prompt_toolkit PromptSession integrated with SQLiteHistory and RichStreamRenderer."

patterns-established:
  - "KeyBindings configured with Alt+Enter / Ctrl+J for newline and Enter backslash detection"
  - "is_interactive_terminal helper isolating TTY detection for CLI entrypoint and pipe ingestion"

requirements-completed: [REPL-01, REPL-02, REPL-03, REPL-04, REPL-05]

coverage:
  - id: D1
    description: "InteractiveREPL loop with multiline input and Ctrl+C lifecycle"
    requirement: "REPL-01, REPL-02, REPL-04"
    verification:
      - kind: unit
        ref: "tests/test_repl.py"
        status: pass
    human_judgment: false
  - id: D2
    description: "Bare aishell CLI interactive entrypoint and signal restoration"
    requirement: "REPL-01, REPL-05"
    verification:
      - kind: integration
        ref: "tests/test_cli_repl.py"
        status: pass
    human_judgment: false
---

# Phase 02 Plan 03: Interactive REPL & CLI Wiring Summary

## Accomplishments
1. **InteractiveREPL Implementation**: Built `InteractiveREPL` in `src/aishell/ui/repl.py` uniting `PromptSession`, `SQLiteHistory`, styled prompts (`format_prompt`), and `RichStreamRenderer`.
2. **Multiline Input & Meta-Commands**: Configured `Alt+Enter` and trailing backslash (`\`) newline insertion while preserving standard `Enter` for submission. Added built-in REPL commands (`:exit`, `:quit`, `/clear`, `/help`).
3. **Signal Routing & Cancellation Lifecycle**: Implemented `is_streaming` interrupt isolation where `Ctrl+C` cancels generation immediately without killing the REPL session. Added double `Ctrl+C` within 1.5 seconds (or `Ctrl+D`) for graceful REPL exit.
4. **CLI Entrypoint Integration**: Wired bare `aishell` invocation in `src/aishell/cli.py` to launch `InteractiveREPL.run()` when standard input is an interactive terminal, with helpful usage feedback for non-TTY environments.
5. **Testing & Verification**: 7 tests in `tests/test_repl.py` and 3 tests in `tests/test_cli_repl.py` pass; full test suite of 59 tests passes with zero regressions.
