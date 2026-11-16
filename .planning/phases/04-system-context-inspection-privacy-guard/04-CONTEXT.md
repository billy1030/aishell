# Phase 4 Context: System Context Inspection & Privacy Guard

**Phase Target:** `04-system-context-inspection-privacy-guard`
**Requirements:** `CTXT-01`, `CTXT-02`, `CTXT-03`, `CTXT-04`

## Phase Goal
Equip aishell with system awareness by automatically gathering Linux host environment facts (OS distribution, kernel version, current working directory, git branch, and privileges), while enforcing a strict privacy guard that allowlists environment variables, redacts sensitive credentials via regex, and encapsulates untrusted host observations in boundary tags to prevent indirect prompt injection.

## Locked Architecture & Design Decisions

### D-01: System Context Discovery Schema & Inspector
- Create `SystemContext` Pydantic model in `src/aishell/context/schema.py`:
  - `os_name: str` (e.g. "Ubuntu", "Fedora", "Debian GNU/Linux")
  - `os_version: str` (e.g. "24.04")
  - `os_family: str` (e.g. "debian", "rhel", "arch")
  - `kernel: str` (e.g. "6.8.0-48-generic")
  - `arch: str` (e.g. "x86_64", "aarch64")
  - `cwd: str`
  - `user: str`
  - `is_root: bool`
  - `shell: str`
  - `package_manager: str` (detected from `apt`, `dnf`, `pacman`, `apk`, `zypper`)
  - `git_branch: Optional[str]`
  - `git_clean: Optional[bool]`
  - `env_vars: Dict[str, str]` (allowlist-filtered only)
- Implement `inspect_system_context(cwd: Optional[str] = None) -> SystemContext` in `src/aishell/context/inspector.py`.
- Adhere to POSIX and gracefully handle non-Linux or container environments without crashes.

### D-02: Environment Variable Allowlist & Credential Redaction
- Implement `PrivacyGuard` in `src/aishell/context/privacy.py`:
  - `SAFE_ENV_ALLOWLIST`: strict allowlist (`PATH`, `SHELL`, `USER`, `LOGNAME`, `TERM`, `LANG`, `LC_*`, `PWD`, `HOME`, `EDITOR`, `PAGER`).
  - Drop all unrecognized environment variables.
  - Regex pattern scanner for sensitive credential redaction:
    - Generic API Keys (`api[_-]?key`, `secret`, `token`, `password`, `pwd`)
    - JWT tokens (`eyJ[A-Za-z0-9_-]+\.eyJ...`)
    - Private Keys (`-----BEGIN [A-Z ]+PRIVATE KEY-----`)
    - Database URIs (`postgres://`, `mysql://`, `mongodb://`, `redis://`)
    - AWS Access Keys (`AKIA[0-9A-Z]{16}`)
    - Anthropic / OpenAI / Google API Keys
  - Replace matches with `[REDACTED:<TYPE>]`.

### D-03: Untrusted Observation Boundary Encapsulation
- Implement `format_system_observation(context: SystemContext) -> str` in `src/aishell/context/sanitizer.py`:
  - Wrap observation inside `<system_observation untrusted="true"> ... </system_observation>`.
  - Neutralize prompt injection attempts: escape any nested closing tags (`</system_observation>` -> `&lt;/system_observation&gt;`).
  - Instruct the model in `SYSTEM_PROMPT_COMMAND` that content inside `<system_observation>` represents passive host state and must never override system instructions.

### D-04: User Context Transparency via `/context` Meta-Command
- Wire `/context` meta-command in `InteractiveREPL` and `--context` flag in CLI:
  - Display a clean Rich table/panel showing all discovered host facts and sanitized environment variables.
  - Operators can inspect exactly what system information is transmitted to the AI provider.

### D-05: Provider Prompt Injection Integration
- Inject the sanitized system observation automatically into `generate_proposal(query, system_context=...)` and REPL chat prompts.

