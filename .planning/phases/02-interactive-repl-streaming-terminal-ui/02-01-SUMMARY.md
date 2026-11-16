---
phase: 02-interactive-repl-streaming-terminal-ui
plan: 01
subsystem: ui
tags: [rich, live-markdown, stream-renderer, stdin-piping, one-shot-cli]

requires: [01-01, 01-02, 01-03]
provides:
  - RichStreamRenderer with live markdown updates, pygments code syntax highlighting, and transient status spinner
  - Terminal capability detection respecting NO_COLOR, TERM=dumb, and COLORTERM=truecolor
  - CLI one-shot execution via `-c` / `--command` and bare positional queries
  - Unix stdin pipe ingestion bounded defensively to 512KB with truncation warning
affects: [02-02, 02-03, phase-3]

actuals:
  tokens: 4100
  tasks: 2
  commits: 2

tech-stack:
  added: [prompt-toolkit, pygments]
  patterns: [Rich Live stream rendering with Pygments code highlighting, DefaultCommandGroup pattern for bare positional queries]

key-files:
  created:
    - src/aishell/ui/__init__.py
    - src/aishell/ui/renderer.py
    - tests/test_ui_renderer.py
    - tests/test_cli_oneshot.py
  modified:
    - pyproject.toml
    - src/aishell/cli.py

key-decisions:
  - "D-05: Real-time Markdown token streaming using Rich Live and Markdown rendering with Pygments syntax highlighting"
  - "D-06: Transient status spinner that cleanly clears without visual artifacts or orphaned blank lines when tokens start arriving"
  - "D-07: Automatic terminal capability detection (is_tty, color_system, NO_COLOR, TERM=dumb) with clean non-interactive degradation"
  - "D-08: Dual one-shot CLI execution: both aishell -c '<prompt>' and bare positional aishell '<prompt>'"
  - "D-09: Unix stdin piping support (cat log.txt | aishell 'diagnose') reading non-TTY stdin"
  - "T-02-01: Stdin pipe bounded defensively to 512KB maximum with user truncation warning"

patterns-established:
  - "DefaultCommandGroup subclassing TyperGroup to dispatch non-option arguments to ask command"
  - "RichStreamRenderer supporting explicit Console injection and capability-aware fallback"

requirements-completed: [REPL-03, REPL-05]

coverage:
  - id: D1
    description: "End-to-end streaming terminal renderer with Live Markdown and status spinner"
    requirement: "REPL-03"
    verification:
      - kind: unit
        ref: "tests/test_ui_renderer.py"
        status: pass
    human_judgment: false
  - id: D2
    description: "CLI one-shot execution and Unix stdin pipe ingestion"
    requirement: "REPL-05"
    verification:
      - kind: unit
        ref: "tests/test_cli_oneshot.py"
        status: pass
    human_judgment: false

duration: 5min
completed: 2026-11-16
status: complete
---

# Phase 2 Plan 1: Terminal UI Streaming Renderer & One-Shot CLI Pipeline Summary

**Live streaming terminal Markdown renderer, transient status spinner, terminal capability degradation, and CLI one-shot / stdin pipe execution implemented and tested.**

## Performance

- **Duration:** 5 min
- **Started:** 2026-11-16T17:33:00Z
- **Completed:** 2026-11-16T17:38:00Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments

- Added `prompt-toolkit>=3.0.50,<4.0.0` and `pygments>=2.19.0,<3.0.0` dependencies to `pyproject.toml`.
- Implemented `RichStreamRenderer` and `detect_terminal_capabilities` in `src/aishell/ui/renderer.py` supporting live streaming token accumulation, Pygments code syntax highlighting, and transient thinking spinners without visual residue.
- Subclassed `TyperGroup` in `src/aishell/cli.py` with `DefaultCommandGroup` allowing bare positional queries (`aishell "query"`) and `-c "query"`.
- Implemented piped stdin ingestion in `src/aishell/cli.py` capped to 512KB with warning banners.
- Added 13 new unit tests across `tests/test_ui_renderer.py` and `tests/test_cli_oneshot.py` (total 40 passing tests).

## Task Commits

1. **Task 1: Terminal UI streaming renderer and capability detection** - `4c52fc7` (feat)
2. **Task 2: CLI one-shot execution and stdin pipe ingestion** - `a1a6c07` (feat)
