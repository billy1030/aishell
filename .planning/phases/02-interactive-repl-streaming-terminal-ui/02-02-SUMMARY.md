---
phase: 02-interactive-repl-streaming-terminal-ui
plan: 02
subsystem: ui
tags: [prompt-toolkit, history, sqlite, banner, prompt-formatting]

requires: [02-01]
provides:
  - SQLiteHistory adapting prompt_toolkit.history.History to query and persist to history.db
  - Dynamic path contraction for working directories (`~/project`)
  - Compact prompt formatting `aishell [~/dir] (model) > ` with styled tokens
  - Startup banner displaying system metadata, active model/provider, and shortcut hints
affects: [02-03]

actuals:
  tokens: 3500
  tasks: 2
  commits: 2

tech-stack:
  added: [prompt_toolkit.history, distro]
  patterns: [SQLiteHistory prompt_toolkit adapter, Table/Panel Rich startup banner, Styled prompt tokens]

key-files:
  created:
    - src/aishell/ui/history.py
    - src/aishell/ui/banner.py
    - tests/test_ui_history.py
    - tests/test_ui_banner.py
  modified:
    - src/aishell/ui/__init__.py

key-decisions:
  - "D-01: Compact single-line prompt layout with contracted working directory and active model info: aishell [~/project] (ollama) >"
  - "D-04: Up/Down arrow navigation and reverse history search (Ctrl+R) backed by SQLite audit database (history.db)"
  - "D-11: Custom prompt_toolkit History adapter querying and storing directly to SQLite without duplicate disk files"
  - "D-13: Startup banner with system metadata summary (OS distro, Python, active AI provider/model, shortcut hints)"

patterns-established:
  - "SQLiteHistory implementing load_history_strings (recent items first) and store_string"
  - "format_prompt returning styled prompt_toolkit token lists alongside format_prompt_string"

requirements-completed: [REPL-01, REPL-02]

coverage:
  - id: D1
    description: "End-to-end prompt_toolkit SQLite history adapter with reverse search"
    requirement: "REPL-02"
    verification:
      - kind: unit
        ref: "tests/test_ui_history.py"
        status: pass
    human_judgment: false
  - id: D2
    description: "Startup banner and compact status prompt formatting"
    requirement: "REPL-01"
    verification:
      - kind: unit
        ref: "tests/test_ui_banner.py"
        status: pass
    human_judgment: false

duration: 4min
completed: 2026-11-16
status: complete
---

# Phase 2 Plan 2: SQLite REPL History Adapter & Status Banner Summary

**prompt_toolkit SQLite history adapter with reverse search (`Ctrl+R`), path contraction, styled compact prompt, and startup banner implemented and verified.**

## Performance

- **Duration:** 4 min
- **Started:** 2026-11-16T17:38:00Z
- **Completed:** 2026-11-16T17:42:00Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments

- Implemented `SQLiteHistory` in `src/aishell/ui/history.py` directly connecting prompt_toolkit with `HistoryManager` and SQLite `command_history` without redundant disk files.
- Built `contract_path`, `format_prompt`, and `format_prompt_string` in `src/aishell/ui/banner.py` rendering `aishell [~/project] (ollama) > ` with home directory contraction.
- Built `render_banner` in `src/aishell/ui/banner.py` displaying Linux OS distro (via `distro`), Python version, AI provider/model, and shortcut hints.
- Added 9 unit tests across `tests/test_ui_history.py` and `tests/test_ui_banner.py` (total 49 passing tests).

## Task Commits

1. **Task 1: SQLite history adapter for prompt_toolkit** - `62dc829` (feat)
2. **Task 2: Startup banner and compact prompt formatting** - `85ec401` (feat)
