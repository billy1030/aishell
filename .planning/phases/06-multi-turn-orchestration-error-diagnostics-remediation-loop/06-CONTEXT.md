# Phase 6 Context: Multi-Turn Orchestration, Error Diagnostics & Remediation Loop

## Phase Goal
Operators can troubleshoot failures seamlessly through automated root-cause diagnosis, targeted remediation suggestions, strictly bounded recovery loops, and conversational context compaction during long-running sessions.

## Requirements
- **DIAG-01**: Non-zero exit codes trigger automatic root-cause explanation based on command output and system state.
- **DIAG-02**: System proposes a targeted follow-up remediation command with explanation and confirmation prompt.
- **DIAG-03**: System strictly caps remediation loops at a maximum of 2 cycles to prevent command thrashing or infinite repair cascades.
- **CONF-03**: System manages sliding-window context compaction to keep long interactive sessions within LLM token limits.

## Architectural Decisions

### D-01: Non-Zero Exit Code Detection & Failure Capture
- **Decision**: Commands executed in REPL (or CLI) returning non-zero exit codes (excluding exit code 130 SIGINT from operator Ctrl+C) trigger automated diagnosis.
  - Diagnostic payload includes: failed command string, exit code, trimmed stdout/stderr (last 4KB / 50 lines to prevent context flooding), current working directory, and user root status.
  - Categorizes common failure types (e.g. Permission Denied, Command Not Found, Missing File/Directory, Service Inactive, Port Collision, Disk Full) to enhance LLM prompt clarity.
- **Rationale**: Immediate error capture provides the AI provider with necessary troubleshooting context without overwhelming token limits.

### D-02: Targeted Remediation Proposals via SafetyGate
- **Decision**: Diagnosis yields both a root-cause explanation and a targeted `CommandProposal` flagged with `remediation=True`.
  - Remediation proposals are routed through the existing Phase 5 `SafetyGate` service (`render_proposal` + `prompt_confirmation [y/N/e]`).
  - No remediation command executes automatically without operator confirmation.
- **Rationale**: Even automated error recovery must obey the core human-in-the-loop safety guarantee.

### D-03: Bounded Remediation Loop (Max 2 Cycles)
- **Decision**: The remediation engine tracks `cycle_count` per incident:
  - Initial command fails -> Remediation Cycle 1 proposed.
  - If approved and Cycle 1 command succeeds (exit code 0) -> Loop resets; success reported.
  - If Cycle 1 fails -> Remediation Cycle 2 proposed with updated error output.
  - If Cycle 2 fails -> Hard stop reached (`cycle_count >= 2`). System displays an explicit halt notice: `Maximum remediation attempts (2) reached. Halting automated recovery to prevent command thrashing.` Returns control to operator prompt.
- **Rationale**: Strictly prevents infinite recursion, cascading system changes, or flapping between conflicting fixes.

### D-04: Sliding-Window Conversational Context Compaction
- **Decision**: Implement `ConversationManager` managing multi-turn conversational history:
  - System prompt and fresh `<system_observation>` are always preserved at the head.
  - Maintains a sliding window of recent conversational turns (default: 8 recent messages).
  - When history exceeds window capacity or token threshold (default: 4000 estimated tokens), older non-system messages are compacted into a single concise `[Conversation Summary: ...]` block.
- **Rationale**: Keeps LLM context size bounded, prevents token quota exhaustion, and maintains low latency during hours-long terminal sessions.

