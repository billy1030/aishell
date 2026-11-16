# Phase 5 Context: Safety Gate & Controlled Command Execution

## Phase Goal
Operators review and approve proposed commands with visual risk badges and inline editing before any command touches the host system.

## Requirements
- **EXEC-01**: System categorizes proposed shell commands into risk tiers (Safe / Mutating / High-Risk) with visual risk badges.
- **EXEC-02**: System halts before execution and presents an interactive confirmation gate (`[y/N/e]`) requiring explicit operator approval.
- **EXEC-03**: Operator can press `[e]dit` at the confirmation gate to load the proposed command into the prompt buffer for inline modifications before running.

## Architectural Decisions

### D-01: Deterministic Risk Classification Engine
- **Decision**: Command risk level is determined by deterministic client-side heuristic rules combined with model assessment, using `max_risk(heuristic_risk, model_risk)`:
  - **Safe (Read-Only)**: Commands that inspect state without modifying files, processes, or configurations (e.g. `ls`, `cat`, `grep`, `find`, `df`, `du`, `ps`, `top`, `git status`, `git log`, `git diff`, `stat`, `file`, `uptime`, `whoami`).
  - **Mutating**: Commands that create, modify, or delete single user files, install packages, change user settings, or alter git branch state (e.g. `touch`, `mkdir`, `cp`, `mv`, `rm <file>`, `git commit`, `git checkout`, `chmod <user>`, `apt install`, `dnf install`, `npm install`, `systemctl status/restart`).
  - **High-Risk**: Commands with system-wide blast radius, recursive destructive operations, disk formatting, kernel/device operations, or firewall flushes (e.g. `rm -rf`, `dd`, `mkfs`, `fdisk`, `parted`, `chmod -R 777`, `chown -R`, `reboot`, `shutdown`, `> /dev/`, `iptables -F`, `curl ... | sh`, `sudo rm`).
- **Rationale**: LLMs can misjudge or hallucinate danger levels. A client-side static rule engine ensures catastrophic commands can never be downgraded to "safe".

### D-02: Visual Risk Badges and Proposal Presentation
- **Decision**: Render command proposals in structured Rich panels containing:
  - Header with purpose and color-coded risk badge:
    - Safe: `[bold green][SAFE][/bold green]`
    - Mutating: `[bold yellow][MUTATING][/bold yellow]`
    - High-Risk: `[bold white on red][HIGH-RISK][/bold white on red]` with an explicit warning banner
  - Command preview highlighted with Pygments/Rich bash syntax highlighting
  - Detailed explanation of flags, arguments, and mechanics
  - Sudo privilege requirement indicator if `requires_sudo=True`
- **Rationale**: Immediate visual clarity ensures operators know the potential blast radius before approving.

### D-03: Interactive Confirmation Gate (`[y/N/e]`)
- **Decision**: The gate halts execution and prompts: `Execute command? [y/N/e]: `
  - `y` or `yes`: Confirm execution and run through `execute_pipeline()` (or session executor).
  - `n`, `no`, or Enter (default): Cancel execution cleanly with notice (`Command cancelled by operator`).
  - `e` or `edit`: Launch inline prompt buffer editor.
  - Non-interactive safety: If standard input is not a TTY or cannot accept interactive input, execution is aborted with an error unless an explicit override is configured.
- **Rationale**: Protects against accidental execution on Enter and blocks automated or runaway loops.

### D-04: Inline Command Editing (`[e]dit`)
- **Decision**: When `e` is selected, prompt_toolkit's `prompt(default=command)` is invoked with the proposed command pre-loaded.
  - The operator can freely edit using standard terminal readline/vi/emacs navigation keys.
  - On Enter: The modified command is re-evaluated by the risk engine. If the command was changed, a confirmation prompt confirms the updated command; if approved, it executes.
  - On Ctrl+C or empty string: Editing is aborted without execution.
- **Rationale**: Operators often need to tweak a flag, file path, or option without retyping the entire command or leaving the assistant.

### D-05: Integrated Safety Gate Workflow
- **Decision**: Encapsulate the safety gate into a modular `SafetyGate` service (`src/aishell/safety/`):
  - `classify_risk(command: str, model_risk: Optional[str] = None) -> RiskLevel`
  - `render_proposal(proposal: CommandProposal, console: Console)`
  - `prompt_confirmation(proposal: CommandProposal, session: Optional[PromptSession] = None) -> Tuple[GateAction, Optional[str]]`
  - Wire `SafetyGate` directly into `execute_one_shot()` and `InteractiveREPL.dispatch_input()`.
- **Rationale**: Single point of truth for risk rules and confirmation logic across both one-shot CLI execution and interactive REPL sessions.

