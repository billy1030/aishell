# Phase 6 Discussion Log: Multi-Turn Orchestration, Error Diagnostics & Remediation Loop

## Topics Discussed & Resolved

### 1. Error Triggering & Signal Filtering (DIAG-01)
- **Question**: Should all non-zero exit codes trigger diagnosis, including operator Ctrl+C?
- **Resolution**: Exclude exit code 130 (SIGINT). Ctrl+C represents intentional user cancellation, not a failure. All other non-zero exit codes (1..129, 131..255) trigger diagnosis.
- **Status**: Locked (D-01).

### 2. Output Trimming & Privacy Guard Application (DIAG-01)
- **Question**: How much command output should be sent to the model for diagnosis?
- **Resolution**: Capture the last 50 lines (up to 4KB), sanitize through `PrivacyGuard.redact_credentials` to prevent leaking tokens or connection strings from logs, and wrap in XML diagnostic tags.
- **Status**: Locked (D-01).

### 3. Remediation Safety Compliance (DIAG-02)
- **Question**: Can remediation commands run automatically if classified as 'safe'?
- **Resolution**: No. All remediation commands must undergo full `SafetyGate` review and require explicit `[y/N/e]` confirmation from the operator.
- **Status**: Locked (D-02).

### 4. Cycle Enforcement Semantics (DIAG-03)
- **Question**: How is the 2-cycle remediation limit tracked?
- **Resolution**: An instance of `RemediationController` tracks `attempts: int = 0`. Each failed attempt increments the counter. Upon reaching 2, automated suggestions are disabled until a fresh user query is initiated.
- **Status**: Locked (D-03).

### 5. Multi-Turn Compaction Strategy (CONF-03)
- **Question**: How should long REPL sessions be compacted?
- **Resolution**: Implement `ConversationManager` using a sliding window with summary compression. The latest host facts and system prompt remain active, while older history is replaced by an aggregated summary turn.
- **Status**: Locked (D-04).
