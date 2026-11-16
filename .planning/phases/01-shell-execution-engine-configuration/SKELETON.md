# Walking Skeleton — Terminal AI Shell (aishell)

**Phase:** 1
**Generated:** 2026-11-16

## Capability Proven End-to-End

An operator can execute a shell command via `aishell exec '<cmd>'` through a managed PTY with parent builtin interception (`cd`/`export`), configuration loaded from `config.toml`/env, real-time output streamed, and an audit record persisted in SQLite `history.db`.

## Architectural Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Runtime & CLI Framework | Python 3.10+ with `typer` CLI entrypoint | Ubiquitous on modern Linux distros (Ubuntu 22.04+, Debian 12+), zero compilation overhead, native `tomllib` (Python 3.11+), and elegant type-hinted CLI subcommands. |
| Configuration Management | `pydantic-settings` layered hierarchy | Robust typed validation supporting CLI flags > environment variables (`AISHELL_*`, API keys) > `~/.config/aishell/config.toml` (0600 perms) > Pydantic defaults without interactive wizard delays (D-13, D-14, D-15). |
| Data & Audit Persistence | SQLite3 with WAL mode at `$XDG_STATE_HOME/aishell/history.db` | Zero external database daemons, ACID compliance, concurrent multi-terminal safety via WAL mode (D-12), comprehensive audit schema (D-09), and 0700 private state storage (D-10). |
| Subprocess Execution Core | Managed POSIX pseudo-terminal (`pty.openpty`) with process group isolation | Prevents subshell amnesia and terminal state corruption; allocates real PTY for live streaming output (D-01), routes `SIGINT` to child process group (`os.killpg`) without killing aishell (D-02), and handles terminal resize (`TIOCSWINSZ` / `SIGWINCH`) (D-04). |
| State Synchronization | Parent-shell builtin interception (`shlex` pre-parsing) | Intercepts `cd` (supporting `~`, `cd -`, `..`) via `os.chdir` (D-05, D-07) and `export`/`unset` via `os.environ` (D-08), plus compound cwd sync (D-06), ensuring session state persists across command runs. |
| Output Management | Live terminal streaming with memory ring buffer | Streams 100% of stdout/stderr directly to the user while capturing a rolling ring buffer of the last 50KB / 1,000 lines in memory for SQLite audit logging and error diagnosis (D-03). |
| Directory Layout | Modular package under `src/aishell/` | Clear boundary separation: `aishell.config`, `aishell.storage`, `aishell.execution`, and `aishell.cli` entrypoint. |

## Stack Touched in Phase 1

- [x] Project scaffold (`pyproject.toml`, packaging metadata, `pytest` test runner)
- [x] Configuration — `AishellSettings` layered loader with auto-generated `config.toml` (0600 perms)
- [x] Execution substrate — Managed PTY runner with process group isolation (`os.setsid`) and signal forwarding
- [x] Shell builtins — `cd` (with `OLDPWD`, `~`, `..`), `export`, `unset`, and compound cwd synchronization
- [x] Database — SQLite audit log insertion (`history.db`) with WAL mode and FIFO bounded retention
- [x] CLI entrypoint — `aishell exec '<cmd>'` wiring config, execution, output streaming, and audit logging end-to-end
- [x] Test suite — Automated test suite covering configuration, storage, builtins, and PTY execution

## Out of Scope (Deferred to Later Slices)

- Interactive multiline prompt REPL loop (`prompt_toolkit` session, keybindings, history search) — Phase 2
- Streaming Markdown presentation and syntax-highlighted display (`rich` Live display) — Phase 2
- Multi-provider LLM integrations (Google Gemini, OpenAI, Anthropic, Ollama) — Phase 3
- System context gathering, host inspection, and credential secret scrubber — Phase 4
- Command risk classification badges and interactive confirmation gate `[y/N/e]` — Phase 5
- Multi-turn error diagnosis and automated remediation loops — Phase 6

## Subsequent Slice Plan

Each later phase adds one vertical slice on top of this skeleton without altering its architectural decisions:

- Phase 2: Interactive REPL & Streaming Terminal UI (`prompt_toolkit` loop on top of PTY substrate and history storage)
- Phase 3: Multi-Provider LLM Integration (pluggable cloud and local model client adapters)
- Phase 4: System Context Inspection & Privacy Guard (OS discovery and regex credential scrubber)
- Phase 5: Safety Gate & Controlled Command Execution (risk tiers, interactive confirmation gate `[y/N/e]`, inline editing)
- Phase 6: Multi-Turn Orchestration, Error Diagnostics & Remediation Loop (exit code feedback, bounded auto-fix)
