# Phase 2: Interactive REPL & Streaming Terminal UI - Context

**Gathered:** 2026-11-16  
**Status:** Ready for planning  

<domain>
## Phase Boundary

Interactive REPL loop powered by `prompt_toolkit`, real-time streaming markdown rendering and live status spinners via `rich`, persistent command history search (`Ctrl+R`), safe interrupt routing (`Ctrl+C`), and one-shot/piped CLI query execution (`aishell -c "query"`, `cat log | aishell`).

</domain>

<decisions>
## Implementation Decisions

### REPL Session & Prompt UX
- Compact single-line prompt styled with current working directory and active model info: `aishell [~/project] (ollama) > `
- Multiline submission trigger: Standard `Enter` submits query/command; `Alt+Enter` or trailing backslash (`\`) introduces a newline without submitting
- Signal routing in REPL: `Ctrl+C` during active streaming cancels generation immediately without killing the REPL session; `Ctrl+C` at an empty prompt resets the buffer; `Ctrl+D` or double `Ctrl+C` exits the session — **Reversibility:** costly — public user interaction contract
- History navigation: Up/Down arrow navigation and reverse history search (`Ctrl+R`) backed by the SQLite audit database (`history.db`)

### Streaming Terminal Rendering & Layout
- Streaming Markdown display: Render tokens live using Rich `Live` and streaming Markdown components with syntax highlighting (Pygments `bash` lexer)
- Status spinners: Transient Rich spinner during thinking/streaming that cleanly transitions to streaming output without leaving orphaned artifacts
- Terminal degradation & SSH safety: Automatically detect terminal truecolor / ANSI support, falling back to clean text without ANSI glitches

### CLI Invocation & Pipeline Modes
- One-shot execution: Support both `aishell -c "prompt"` and bare positional arguments `aishell "prompt"` executing a single turn without entering the interactive REPL — **Reversibility:** costly — public CLI contract
- Stdin piping support: Automatically detect non-TTY stdin (`not sys.stdin.isatty()`) and ingest piped text (`cat log.txt | aishell "diagnose"`) as context or input prompt

### Decided autonomously
- [Architecture] Q: "Where should UI components reside?" → Selected: "src/aishell/ui/ package with repl.py, renderer.py, banner.py" — Clean separation from execution and storage layers; easily reorganized if needed.
- [History] Q: "How should prompt_toolkit load history from SQLite?" → Selected: "Custom prompt_toolkit.history.History adapter querying SQLite history.db" — Eliminates duplicate history files on disk and reuses Phase 1 storage.
- [Syntax Highlighting] Q: "How should code blocks be highlighted in terminal?" → Selected: "Rich syntax highlighting with bash/sh lexer and default dark theme" — Pure Python standard library / pygments, reversible via settings.

### the agent's Discretion
- Startup banner visual styling and system metadata summary format.
- Internal event loop structure connecting prompt_toolkit with asyncio.

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `src/aishell/execution/pty_runner.py`: PTY execution engine and ring buffer for command execution.
- `src/aishell/execution/builtins.py`: Builtin command interceptor (`cd`, `export`, `unset`).
- `src/aishell/storage/history.py`: `HistoryManager` and SQLite schema for reading/writing command records.
- `src/aishell/config/settings.py`: `AishellSettings` layered configuration for theme, model, and timeout.

### Established Patterns
- Pydantic Settings hierarchy with XDG Base Directory specification compliance.
- Defensive termios restoration in execution wrappers.
- Modular subpackages under `src/aishell/`.

### Integration Points
- `src/aishell/cli.py`: Bare `aishell` invocation will launch `InteractiveREPL.run()`; `aishell -c <prompt>` and `aishell <prompt>` will route to one-shot runner.
- `src/aishell/ui/repl.py` will invoke `execute_pipeline()` from Phase 1 for shell commands and prepare the stage for Phase 3 LLM providers.

</code_context>

<specifics>
## Specific Ideas

- Single-line prompt format keeps screen real estate efficient during long terminal sessions.
- Ingesting piped stdin seamlessly allows power users to chain Unix commands with aishell diagnosis.

</specifics>

<deferred>
## Deferred Ideas

- None — discussion stayed within Phase 2 scope.

</deferred>
