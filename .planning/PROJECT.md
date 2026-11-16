# Terminal AI Shell (aishell)

## What This Is

An interactive, system-aware Linux AI console assistant and REPL designed for developers and sysadmins. It bridges natural language intent with Linux terminal operations by generating and explaining shell commands, gathering system context, and safely running commands with explicit user confirmation.

## Core Value

Empower developers and system administrators to troubleshoot, operate, and automate Linux workflows through conversational AI without leaving the terminal or risking accidental execution of unintended commands.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] Interactive REPL shell with multiline input, command history, and session management
- [ ] Pluggable LLM provider architecture supporting cloud APIs (Gemini, OpenAI, Anthropic) and local models (Ollama)
- [ ] Safe command execution loop: propose command, explain risk/intent, and require explicit confirmation (`[y/N]`) before execution
- [ ] System context inspector: auto-gather OS/distro details, working directory, git status, environment variables, and command exit codes
- [ ] Rich terminal UI featuring markdown rendering, syntax highlighting for shell commands, progress indicators, and streamed responses
- [ ] Command error diagnosis and interactive remediation loop when executed commands fail

### Out of Scope

- GUI or web dashboard — strictly focused on the terminal and console experience
- Autonomous non-confirmed command execution for destructive actions — safety is mandatory
- Proprietary lock-in to a single AI vendor — multi-provider is a core design requirement
- Kernel-level hooks or root daemon replacement — runs as standard user-space CLI tool

## Context

- Target environment: Linux console / terminal (bash, zsh, SSH sessions)
- Architecture: Python CLI package installable via pip/pipx with clean separation between UI (prompt_toolkit/Rich), system inspection (subprocess/psutil), and AI orchestration.

## Constraints

- **Tech stack**: Python 3.10+, `rich`, `prompt_toolkit` — enables rich TUI without heavy binary dependencies
- **Security**: Mandatory human-in-the-loop confirmation before running any proposed shell commands
- **Compatibility**: POSIX-compliant terminal environments, SSH-friendly

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Python with Rich & prompt_toolkit | Fast development, excellent TUI rendering, cross-distro portability | — Pending |
| Dedicated interactive REPL | Allows rich multi-turn context and seamless switching between conversation and command execution | — Pending |
| Pluggable multi-provider (Cloud + Ollama) | Supports offline/private local setups and high-capability cloud models | — Pending |
| Human confirmation gate | Prevents unintended system changes or data loss from hallucinated shell commands | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-11-16 after initialization*

