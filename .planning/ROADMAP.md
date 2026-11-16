# Roadmap: Terminal AI Shell (aishell)

## Overview

Terminal AI Shell (`aishell`) bridges natural language intent with safe Linux terminal operations through a decoupled, multi-provider architecture. The project follows a vertical MVP progression: establishing a robust pseudo-terminal (PTY) execution core with persistent audit logs, layering on an interactive REPL with live streaming terminal rendering, integrating modular cloud and local LLM providers, implementing system context inspection with automated credential scrubbing, introducing an interactive risk-classified execution safety gate, and delivering closed-loop error diagnostics with bounded remediation.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

- [x] **Phase 1: Shell Execution Engine & Configuration** - Managed PTY execution, subshell state synchronization, and persistent audit logging
- [ ] **Phase 2: Interactive REPL & Streaming Terminal UI** - prompt_toolkit REPL loop, streaming markdown rendering, and syntax highlighting
- [ ] **Phase 3: Multi-Provider LLM Integration** - Pluggable provider architecture for Google Gemini, OpenAI, Anthropic, and Ollama
- [ ] **Phase 4: System Context Inspection & Privacy Guard** - Linux environment discovery, credential scrubbing, and prompt injection defense
- [ ] **Phase 5: Safety Gate & Controlled Command Execution** - Blast-radius risk categorization, confirmation gate, and inline command editing
- [ ] **Phase 6: Multi-Turn Orchestration, Error Diagnostics & Remediation Loop** - Exit code diagnosis, automated remediation suggestions, and context compaction

## Phase Details

### Phase 1: Shell Execution Engine & Configuration
**Goal:** As an operator, I want to run shell commands through a managed PTY with synchronized directory navigation and configuration loading, so that commands execute cleanly, state persists across commands, and full execution history is audited.
**Mode:** mvp
**Depends on**: Nothing (first phase)
**Requirements**: EXEC-04, EXEC-05, EXEC-06, CONF-01, CONF-02
**Success Criteria** (what must be TRUE):
  1. Operator can execute terminal commands via managed pseudo-terminal (PTY) with real-time stdout/stderr streaming and clean signal propagation (SIGINT/Ctrl+C).
  2. Directory changes (`cd`) and environment exports (`export`) persist in the parent process across command executions.
  3. Command execution details (exit code, duration, captured output) and session audit logs are persisted in SQLite (`~/.local/state/aishell/history.db`).
  4. Configuration is loaded from `~/.config/aishell/config.toml` with override support via `AISHELL_*` environment variables.
**Plans:** 3 plans

Plans:
**Wave 1**
- [x] 01-01-PLAN.md — Project Scaffold, Layered Configuration & Tracer CLI

**Wave 2** *(blocked on Wave 1 completion)*
- [x] 01-02-PLAN.md — SQLite Audit Storage & Bounded Session History

**Wave 3** *(blocked on Wave 2 completion)*
- [x] 01-03-PLAN.md — Shell Builtin Interceptor, Managed PTY Execution & Signal Routing

### Phase 2: Interactive REPL & Streaming Terminal UI
**Goal**: Users can interact through a rich terminal REPL with multiline editing, history search, and live-streamed markdown rendering.
**Mode:** mvp
**Depends on**: Phase 1
**Requirements**: REPL-01, REPL-02, REPL-03, REPL-04, REPL-05
**Success Criteria** (what must be TRUE):
  1. User can launch `aishell` to enter an interactive session displaying a styled prompt with host status indicators.
  2. User can write multiline queries and recall previous inputs using Up/Down arrow navigation and reverse history search.
  3. User sees AI responses rendered in real-time with streaming Markdown, live spinners, and syntax-highlighted shell commands.
  4. User can press `Ctrl+C` during active streaming to halt generation immediately without terminating the REPL session.
  5. User can execute one-shot queries (`aishell -c "query"`) or pipe input directly from Unix stdin (`cat log | aishell "diagnose"`).
**Plans**: TBD
**UI hint**: yes

### Phase 3: Multi-Provider LLM Integration
**Goal**: Users can generate shell solutions using their choice of cloud LLMs (Gemini, OpenAI, Anthropic) or local offline models (Ollama).
**Mode:** mvp
**Depends on**: Phase 2
**Requirements**: PROV-01, PROV-02, PROV-03, PROV-04
**Success Criteria** (what must be TRUE):
  1. User can configure and switch the active AI provider between Google Gemini, OpenAI, Anthropic, and local Ollama via config or CLI flags.
  2. System asynchronously streams response tokens from any active provider adapter.
  3. System parses structured command proposals (command string, purpose, explanation, risk tier) from LLM responses.
  4. User receives actionable guidance for API connection errors, rate limits, or missing credentials instead of raw stack traces.
**Plans**: TBD

### Phase 4: System Context Inspection & Privacy Guard
**Goal**: Users get platform-accurate command proposals while sensitive credentials and untrusted inputs are securely sanitized.
**Mode:** mvp
**Depends on**: Phase 3
**Requirements**: CTXT-01, CTXT-02, CTXT-03, CTXT-04
**Success Criteria** (what must be TRUE):
  1. System automatically inspects host environment facts (OS distribution via `/etc/os-release`, kernel version, working directory, git branch, and user privileges).
  2. System sanitizes environment variables against an allowlist and redacts sensitive credentials (tokens, passwords, keys) via regex scanning.
  3. System encapsulates environmental observations inside untrusted boundary tags (`<system_observation untrusted="true">`) to prevent indirect prompt injection.
  4. User can inspect the exact context and system facts sent to the model via a `/context` meta-command.
**Plans**: TBD

### Phase 5: Safety Gate & Controlled Command Execution
**Goal**: Operators review and approve proposed commands with visual risk badges and inline editing before any command touches the host.
**Mode:** mvp
**Depends on**: Phase 4
**Requirements**: EXEC-01, EXEC-02, EXEC-03
**Success Criteria** (what must be TRUE):
  1. System categorizes proposed shell commands into risk tiers (Safe / Mutating / High-Risk) with visual risk badges.
  2. System halts before execution and presents an interactive confirmation gate (`[y/N/e]`) requiring explicit operator approval.
  3. Operator can press `[e]dit` at the confirmation gate to load the proposed command into the prompt buffer for inline modifications before running.
**Plans**: TBD

### Phase 6: Multi-Turn Orchestration, Error Diagnostics & Remediation Loop
**Goal**: Operators can troubleshoot failures seamlessly through automated root-cause diagnosis and bounded remediation suggestions within long-running sessions.
**Mode:** mvp
**Depends on**: Phase 5
**Requirements**: DIAG-01, DIAG-02, DIAG-03, CONF-03
**Success Criteria** (what must be TRUE):
  1. Non-zero exit codes trigger automatic root-cause explanation based on command output and system state.
  2. System proposes a targeted follow-up remediation command with explanation and confirmation prompt.
  3. System strictly caps remediation loops at a maximum of 2 cycles to prevent command thrashing or infinite repair cascades.
  4. System manages sliding-window context compaction to keep long interactive sessions within LLM token limits.
**Plans**: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5 → 6

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Shell Execution Engine & Configuration | 0/0 | Not started | - |
| 2. Interactive REPL & Streaming Terminal UI | 0/0 | Not started | - |
| 3. Multi-Provider LLM Integration | 0/0 | Not started | - |
| 4. System Context Inspection & Privacy Guard | 0/0 | Not started | - |
| 5. Safety Gate & Controlled Command Execution | 0/0 | Not started | - |
| 6. Multi-Turn Orchestration, Error Diagnostics & Remediation Loop | 0/0 | Not started | - |
