# Phase 1: Shell Execution Engine & Configuration - Context

**Gathered:** 2026-11-16  
**Status:** Ready for planning  

<domain>
## Phase Boundary

Managed pseudo-terminal (PTY) command execution, subshell state synchronization (parent-process `cd` and `export` persistence), configuration loading via Pydantic-settings, and persistent execution audit logging in SQLite.

</domain>

<decisions>
## Implementation Decisions

### PTY & Subprocess Mechanics
- **D-01:** Dual-mode execution engine — allocate pseudo-terminal (PTY via `pty.openpty()`) for live streaming subprocesses, and cleanly suspend the REPL for full TTY passthrough when interactive commands run (`sudo -v`, `nano`, `vim`, `less`). — **Reversibility:** costly — changing process orchestration touches the entire core execution pipeline.
- **D-02:** Process group isolation — spawn commands in an isolated process group (`preexec_fn=os.setsid`) and forward `SIGINT` (Ctrl+C) via `os.killpg()` so compound pipelines terminate cleanly without exiting `aishell`. — **Reversibility:** reversible
- **D-03:** Live stream output with circular ring buffer — stream 100% of stdout/stderr directly to the terminal, and retain a rolling ring buffer (last 50KB / 1,000 lines) in memory for error diagnosis and SQLite audit logging. — **Reversibility:** reversible
- **D-04:** Dynamic `TIOCSWINSZ` propagation — query host terminal dimensions at launch and trap `SIGWINCH` to propagate resize events dynamically to the child PTY slave. — **Reversibility:** reversible

### Shell Builtin Interception (`cd` & `export`)
- **D-05:** Pre-parsing leading tokens with `shlex` — intercept leading `cd` (`os.chdir`) and `export` (`os.environ`) in the parent Python process before delegating to external binaries. — **Reversibility:** costly — touches shell execution dispatch.
- **D-06:** Post-execution cwd synchronization — after successful execution of compound commands (e.g. `mkdir foo && cd foo`), query and synchronize `os.getcwd()` with the parent process. — **Reversibility:** reversible
- **D-07:** Full POSIX path navigation — support home directory expansion (`~`), previous directory toggle (`cd -` maintaining `OLDPWD`), and relative `..` pathing in the internal `cd` handler. — **Reversibility:** reversible
- **D-08:** Session-scoped environment mutations — `export` and `unset` modify `os.environ` for the duration of the `aishell` session (inherited by all child commands) without altering host shell rc files (`~/.bashrc`). — **Reversibility:** reversible

### Execution Audit & SQLite Schema
- **D-09:** Comprehensive audit schema — record `id`, `session_id`, `timestamp`, `command`, `cwd`, `exit_code`, `duration_ms`, `output_preview` (first/last 2KB), and `executed_by` (`user` vs `ai_proposal`). — **Reversibility:** one-way — database schema migrations require altering existing user SQLite tables.
- **D-10:** Strict XDG State specification — store database at `$XDG_STATE_HOME/aishell/history.db` (default `~/.local/state/aishell/history.db`) with `0700` directory permissions for privacy. — **Reversibility:** reversible
- **D-11:** Bounded FIFO retention — retain the most recent 10,000 commands by default (configurable in `config.toml`), pruning oldest rows during startup. — **Reversibility:** reversible
- **D-12:** SQLite WAL mode concurrency — enable `PRAGMA journal_mode=WAL;` with a busy timeout so multiple terminal tabs/sessions can write concurrently without database locks. — **Reversibility:** reversible

### Configuration Lifecycle & First-Run
- **D-13:** Sensible default initialization — auto-generate a well-documented default `~/.config/aishell/config.toml` on first launch with sensible defaults (local Ollama default or environment key auto-detection), without blocking the user with an interactive mandatory wizard. — **Reversibility:** reversible
- **D-14:** Layered configuration hierarchy — CLI flags > environment variables (`AISHELL_*`, `GEMINI_API_KEY`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`) > `config.toml` > internal Pydantic defaults. — **Reversibility:** costly — defines user configuration contract.
- **D-15:** Secure configuration permissions — create `~/.config/aishell/config.toml` with `0600` permissions (read/write by owner only) to safeguard stored API tokens. — **Reversibility:** reversible

### the agent's Discretion
- Formatting and color scheme of startup diagnostic messages and execution time logs.
- SQLite indexing strategy (`timestamp`, `session_id`, `command`).
- Internal helper utility organization (`aishell.core`, `aishell.execution`, `aishell.config`, `aishell.storage`).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Architecture & Stack Standards
- `.planning/research/STACK.md` — Core dependencies: `pydantic-settings`, `distro`, `psutil`, stdlib `pty`, `subprocess`, `sqlite3`
- `.planning/research/PITFALLS.md` §1 & §2 — PTY allocation edge cases, signal routing, and terminal restoration (`termios`)
- `.planning/research/ARCHITECTURE.md` §3 & §5 — Execution Sandbox Layer, Subprocess Runner, and Shell Builtin Interceptor

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- Greenfield codebase — establishing the root Python package structure (`aishell/`) and core execution modules.

### Established Patterns
- POSIX-compliant pseudo-terminal handling using stdlib `pty`, `termios`, and `select`/`selectors`.
- Modern Pydantic V2 Settings for configuration modeling.

### Integration Points
- `aishell.execution.pty_runner` will be consumed by Phase 2 (REPL loop) and Phase 5 (Safety Gate).
- `aishell.config.settings` and `aishell.storage.history` will serve as singletons across the entire application.

</code_context>

<specifics>
## Specific Ideas

- Dual-mode execution ensures interactive commands like `sudo apt update` or `nano file.txt` operate seamlessly without terminal freeze.
- Parent-shell directory synchronization ensures commands like `cd /var/log` don't disappear into subshell ether.

</specifics>

<deferred>
## Deferred Ideas

- None — discussion stayed within phase scope.

</deferred>

---

*Phase: 1-Shell Execution Engine & Configuration*  
*Context gathered: 2026-11-16*

