# Phase 5 Discussion Log: Safety Gate & Controlled Command Execution

## Topics Discussed & Resolved

### 1. Risk Tier Taxonomy & Deterministic Enforcement (EXEC-01)
- **Question**: Should the risk tier rely solely on the LLM's classification or client-side rules?
- **Resolution**: Use a client-side deterministic rule engine (`RuleEngine` / `classify_risk`). The final risk is `max(heuristic_risk, model_risk)`. Dangerous commands like `rm -rf`, `mkfs`, `dd`, `chmod -R 777`, and `reboot` are unconditionally escalated to `high_risk`.
- **Status**: Locked (D-01).

### 2. Proposal Visual Design & Badging (EXEC-01)
- **Question**: How should risk badges and command proposals be styled in Rich?
- **Resolution**: Structured panel with:
  - `[bold green][SAFE][/bold green]`
  - `[bold yellow][MUTATING][/bold yellow]`
  - `[bold white on red][HIGH-RISK][/bold white on red]` with a red border and warning notice.
  - Syntax highlighted command box and flag breakdown.
- **Status**: Locked (D-02).

### 3. Confirmation Gate Interaction Model (EXEC-02)
- **Question**: What is the default option and behavior when pressing Enter?
- **Resolution**: Default is `N` (cancel). Only explicit `y` or `yes` runs the command. Entering empty text or any unrecognized character defaults to cancel for safety.
- **Status**: Locked (D-03).

### 4. Inline Editing UX (EXEC-03)
- **Question**: How does `[e]dit` interact with prompt_toolkit?
- **Resolution**: Prompt toolkit allows setting `default=proposed_command`. In both REPL and one-shot, this loads the proposed string directly into the editable line buffer with full cursor control.
- **Status**: Locked (D-04).

### 5. Architectural Packaging
- **Question**: Where should the safety engine code reside?
- **Resolution**: Create dedicated package `src/aishell/safety/` with `classifier.py`, `gate.py`, and `display.py`, exported through `src/aishell/safety/__init__.py`.
- **Status**: Locked (D-05).

