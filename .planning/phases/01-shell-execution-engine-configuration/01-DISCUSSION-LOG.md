# Phase 1: Shell Execution Engine & Configuration - Discussion Log

**Date:** 2026-11-16  
**Phase:** 1 — Shell Execution Engine & Configuration  

## Discussion Records

### PTY & Subprocess Mechanics

#### Q1: Interactive Commands vs Standard Streaming
- **Question:** How should the executor handle interactive full-screen or password-prompting commands (nano, vim, sudo -v) compared to standard streaming commands?
- **Options Presented:**
  1. Dual-mode execution: allocate pseudo-terminal (PTY) for live streaming, and suspend REPL for full TTY passthrough when interactive commands run (Selected)
  2. Strict PTY master/slave emulation for all commands with ANSI terminal sequence parsing
  3. You decide — pick the most reliable pattern for standard Linux consoles and SSH
- **Selection:** Option 1 — Dual-mode execution.

#### Q2: Ctrl+C (SIGINT) and Process Lifecycle
- **Question:** How should Ctrl+C (SIGINT) and process lifecycle be managed during command execution?
- **Options Presented:**
  1. Process group isolation: run command in a new process group (os.setsid) and forward SIGINT via os.killpg() so piped children are terminated without exiting aishell (Selected)
  2. Direct PID signal: forward SIGINT directly to the root child process PID only
  3. You decide — use the safest POSIX process group pattern
- **Selection:** Option 1 — Process group isolation.

#### Q3: Output Buffering and Truncation
- **Question:** How should command output buffering and truncation be handled for history logging and AI error diagnostics?
- **Options Presented:**
  1. Stream all output live to terminal, but retain a rolling ring buffer (last 50KB / 1,000 lines) in memory for history and error diagnosis (Selected)
  2. Capture complete unconstrained output in memory (risk of high memory usage on large outputs)
  3. You decide — balance diagnostics completeness with memory safety
- **Selection:** Option 1 — Stream all output live, retain rolling ring buffer (50KB / 1,000 lines).

#### Q4: Terminal Window Resizing (SIGWINCH)
- **Question:** How should terminal window resizing (SIGWINCH) be synchronized with the child PTY?
- **Options Presented:**
  1. Dynamic TIOCSWINSZ propagation: query host terminal size at launch and trap SIGWINCH to dynamically resize the child PTY slave (Selected)
  2. Static terminal dimensions: query host dimensions once at process launch without handling dynamic SIGWINCH window resizes
  3. You decide — follow standard POSIX pseudo-terminal resize protocols
- **Selection:** Option 1 — Dynamic TIOCSWINSZ propagation.

---

### Shell Builtin Interception (`cd` & `export`)

#### Q1: Builtin Detection & Execution
- **Question:** How should shell builtins like `cd` and `export` be detected and synchronized with the parent process?
- **Selection:** Token pre-parsing (`shlex`): parse leading tokens and handle `cd` (`os.chdir`) and `export` (`os.environ`) directly in the parent Python process.

#### Q2: Compound Commands with `cd`
- **Question:** How should compound commands with chained `cd` operations (e.g., `git clone repo && cd repo`) update the shell's working directory?
- **Selection:** Post-execution cwd probe: query and synchronize `os.getcwd()` after successful command completion.

#### Q3: Directory Navigation Conveniences
- **Question:** Which directory navigation conveniences should the internal `cd` handler support?
- **Selection:** Full POSIX navigation (`~`, `cd -` with `OLDPWD`, relative paths).

#### Q4: Environment Persistence Scope
- **Question:** What should be the persistence scope of `export` and `unset` commands executed within aishell?
- **Selection:** Session-scoped environment: mutate `os.environ` for the active `aishell` process without altering host shell rc files (`~/.bashrc`).

---

### Execution Audit & SQLite Schema

#### Q1: Audit Schema Fields
- **Question:** What schema and metadata should be recorded in SQLite for executed commands?
- **Selection:** Comprehensive audit row: `id`, `session_id`, `timestamp`, `command`, `cwd`, `exit_code`, `duration_ms`, `output_preview`, `executed_by`.

#### Q2: Database Location
- **Question:** Where should the SQLite database file be stored on the filesystem?
- **Selection:** Strict XDG State specification: `$XDG_STATE_HOME/aishell/history.db` (`~/.local/state/aishell/history.db`) with `0700` permissions.

#### Q3: Retention & Pruning
- **Question:** How should history database retention and pruning be managed?
- **Selection:** Bounded FIFO retention: retain the most recent 10,000 commands by default.

#### Q4: Database Concurrency
- **Question:** How should concurrent database access across multiple terminal windows or SSH sessions be handled?
- **Selection:** Enable SQLite WAL mode (Write-Ahead Logging) with a busy timeout.

---

### Configuration Lifecycle & First-Run
- **Auto-resolved via `/gsd auto`:** Sensible default `config.toml` auto-generation on first run, layered configuration hierarchy (CLI > Env > Config File > Defaults), and `0600` file permissions.

