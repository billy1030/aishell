# aishell — Terminal AI Shell

An interactive, system-aware Linux AI console assistant and REPL designed for developers and sysadmins.

## Features

- **Managed Pseudo-Terminal (PTY):** Real-time command execution with full terminal fidelity.
- **State Synchronization:** Intercepts `cd`, `export`, `unset`, and compound directory navigation in the parent Python process to eliminate subshell amnesia.
- **Execution Audit Logging:** Concurrently safe SQLite database recording exit codes, duration, timestamps, and 2KB head/tail output previews in `$XDG_STATE_HOME/aishell/history.db`.
- **Layered Configuration:** Flexible configuration hierarchy loaded from CLI flags, environment variables (`AISHELL_*`), and `~/.config/aishell/config.toml`.

## Installation

```bash
pip install -e .
```

## Quick Start

```bash
# Execute a command through the managed execution engine
aishell exec "ls -la"

# Verify shell builtin persistence
aishell exec "cd /tmp"
```
