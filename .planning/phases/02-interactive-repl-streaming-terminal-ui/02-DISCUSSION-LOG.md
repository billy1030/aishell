# Phase 2: Interactive REPL & Streaming Terminal UI — Discussion Log

**Date:** 2026-11-16  
**Phase:** 2 — Interactive REPL & Streaming Terminal UI  
**Status:** Complete  

## Area 1: REPL Session & Prompt UX

| # | Question | Selected Answer | Options Considered |
|---|----------|-----------------|-------------------|
| 1 | How should the interactive REPL prompt be styled? | Compact single-line prompt with path and model info (e.g. `aishell [~/project] (ollama) > `) | 1. Compact single-line (Chosen)<br>2. Two-line prompt with header<br>3. Minimal classic shell prompt |
| 2 | How should multiline query submission be triggered in the REPL? | Standard `Enter` executes command; `Alt+Enter` or trailing backslash introduces a newline | 1. Enter executes; Alt+Enter newline (Chosen)<br>2. Auto-detect unclosed quotes/brackets<br>3. Meta-key submission |
| 3 | What is the Ctrl+C signal handling lifecycle? | `Ctrl+C` cancels active streaming without terminating REPL; at empty prompt, double `Ctrl+C` or `Ctrl+D` exits session | 1. Stream cancellation + clean session preserve (Chosen)<br>2. Hard interrupt terminates process |

## Area 2: CLI Invocation & Pipeline Modes

| # | Question | Selected Answer | Options Considered |
|---|----------|-----------------|-------------------|
| 1 | How should one-shot CLI queries and Unix stdin piping be invoked? | Support both: `aishell -c "prompt"` and bare arguments `aishell "prompt"` for one-shot queries, plus piped stdin (`cat error.log \| aishell`) | 1. Support both -c and bare positional args + pipe (Chosen)<br>2. Strict flag only (-c) |

## Decided autonomously

- [auto] [Architecture] — Q: "Where should UI components reside?" → Selected: "src/aishell/ui/ package with repl.py, renderer.py, banner.py" (reversible technical — decided autonomously: standard modular Python package layout)
- [auto] [History] — Q: "How should prompt_toolkit load history from SQLite?" → Selected: "Custom prompt_toolkit.history.History adapter querying SQLite history.db" (reversible technical — decided autonomously: direct integration with Phase 1 SQLite audit storage)
- [auto] [Syntax Highlighting] — Q: "How should code blocks be highlighted in terminal?" → Selected: "Rich syntax highlighting with bash/sh lexer and default dark theme" (reversible technical — decided autonomously: standard Pygments/Rich capabilities)
