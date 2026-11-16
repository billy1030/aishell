# Requirements: Terminal AI Shell (aishell)

**Defined:** 2026-11-16  
**Core Value:** Empower developers and system administrators to troubleshoot, operate, and automate Linux workflows through conversational AI without leaving the terminal or risking accidental execution of unintended commands.

## v1 Requirements

Requirements for initial release. Each maps to roadmap phases.

### Interactive REPL & Terminal UI (REPL)

- [ ] **REPL-01**: User can launch an interactive shell session via `aishell` with styled prompt and system status indicators
- [ ] **REPL-02**: User can input multiline queries and navigate persistent command history (Up/Down arrows, history search)
- [ ] **REPL-03**: User sees AI responses rendered in real-time with streaming Markdown, live spinners, and syntax-highlighted shell commands
- [ ] **REPL-04**: User can cleanly interrupt active streaming output via `Ctrl+C` without terminating the REPL session
- [ ] **REPL-05**: User can execute one-shot queries from command line (`aishell -c "query"`) or via Unix pipes (`cat log | aishell "diagnose"`)

### Multi-Provider LLM Engine (PROV)

- [ ] **PROV-01**: User can configure and switch between multiple AI providers: Google Gemini, OpenAI, Anthropic, and local Ollama
- [ ] **PROV-02**: System streams response tokens asynchronously from the active provider adapter
- [ ] **PROV-03**: System parses structured command proposals (command string, purpose, explanation, and risk tier) from LLM responses
- [ ] **PROV-04**: System handles API connection errors, rate limits, and missing credentials with actionable user guidance

### System Context & Privacy Guard (CTXT)

- [ ] **CTXT-01**: System automatically inspects host environment facts (OS distribution via `/etc/os-release`, kernel version, user privileges, current working directory, git branch)
- [ ] **CTXT-02**: System sanitizes environment variables against an allowlist and redacts sensitive credentials (tokens, passwords, keys) via regex scanning
- [ ] **CTXT-03**: System encapsulates environmental observations inside untrusted boundary tags to prevent indirect prompt injection from filenames or logs
- [ ] **CTXT-04**: User can inspect the exact context and system facts sent to the model via a `/context` meta-command

### Safety Gate & Controlled Shell Execution (EXEC)

- [ ] **EXEC-01**: System categorizes proposed shell commands into risk tiers (Safe / Mutating / High-Risk) with visual risk badges
- [ ] **EXEC-02**: System halts before execution and presents an interactive confirmation gate (`[y/N/e]`) requiring explicit operator approval
- [ ] **EXEC-03**: User can press `[e]dit` at confirmation gate to load the proposed command into the prompt buffer for inline modifications before running
- [ ] **EXEC-04**: System executes approved commands in a managed pseudo-terminal (PTY) with real-time stdout/stderr streaming and signal propagation
- [ ] **EXEC-05**: System intercepts directory navigation (`cd`) and environment exports (`export`) to keep the parent process synchronized
- [ ] **EXEC-06**: System captures command exit code, execution duration, and full output for state tracking and error detection

### Diagnostics & Error Remediation (DIAG)

- [ ] **DIAG-01**: Non-zero exit code triggers automatic root-cause explanation based on command output and system state
- [ ] **DIAG-02**: System proposes a targeted follow-up remediation command with explanation and confirmation prompt
- [ ] **DIAG-03**: System caps remediation loops at a maximum of 2 cycles to prevent command thrashing or infinite repair cascades

### Configuration & Session Persistence (CONF)

- [ ] **CONF-01**: Configuration is loaded from `~/.config/aishell/config.toml` with support for environment variable overrides (`AISHELL_*`)
- [ ] **CONF-02**: Session messages, user queries, and command execution audit logs are stored in a local SQLite database (`~/.local/state/aishell/history.db`)
- [ ] **CONF-03**: System manages sliding-window context compaction to keep long interactive sessions within LLM token limits

## v2 Requirements

Deferred to future release. Tracked but not in current roadmap.

### Tool Integrations & Fleet Management (EXT)

- **EXT-01**: Model Context Protocol (MCP) server bridge for Docker, Kubernetes (`kubectl`), and cloud CLIs
- **EXT-02**: Multi-host remote SSH agent dispatch for diagnosing multi-server environments
- **EXT-03**: Interactive runbook exporter to convert troubleshooting sessions into documented executable shell scripts

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| Autonomous unconfirmed execution ("YOLO mode" for destructive actions) | Unacceptable risk of catastrophic data loss (`rm -rf /`, raw disk writes, firewall lockouts) |
| Login shell replacement (`/bin/aishell` in `/etc/passwd`) | Breaks POSIX shell contract, signal multiplexing, and standard login/SSH scripts |
| Heavy Electron or Web GUI dashboard | Bloats memory footprint and eliminates SSH/headless console usability |
| Kernel eBPF or root tracing daemon | Introduces root privilege requirements and fragile kernel version couplings |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| EXEC-04 | Phase 1 | Pending |
| EXEC-05 | Phase 1 | Pending |
| EXEC-06 | Phase 1 | Pending |
| CONF-01 | Phase 1 | Pending |
| CONF-02 | Phase 1 | Pending |
| REPL-01 | Phase 2 | Pending |
| REPL-02 | Phase 2 | Pending |
| REPL-03 | Phase 2 | Pending |
| REPL-04 | Phase 2 | Pending |
| REPL-05 | Phase 2 | Pending |
| PROV-01 | Phase 3 | Pending |
| PROV-02 | Phase 3 | Pending |
| PROV-03 | Phase 3 | Pending |
| PROV-04 | Phase 3 | Pending |
| CTXT-01 | Phase 4 | Pending |
| CTXT-02 | Phase 4 | Pending |
| CTXT-03 | Phase 4 | Pending |
| CTXT-04 | Phase 4 | Pending |
| EXEC-01 | Phase 5 | Pending |
| EXEC-02 | Phase 5 | Pending |
| EXEC-03 | Phase 5 | Pending |
| DIAG-01 | Phase 6 | Pending |
| DIAG-02 | Phase 6 | Pending |
| DIAG-03 | Phase 6 | Pending |
| CONF-03 | Phase 6 | Pending |

**Coverage:**
- v1 requirements: 25 total
- Mapped to phases: 25
- Unmapped: 0 ✓

---
*Requirements defined: 2026-11-16*  
*Last updated: 2026-11-16 after roadmap creation*
