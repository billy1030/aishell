---
phase: 04-system-context-inspection-privacy-guard
plan: 02
subsystem: context
tags: [privacy-guard, allowlist, credential-redaction, prompt-injection, boundary-sanitizer]

requires: [04-01]
provides:
  - PrivacyGuard with strict SAFE_ENV_ALLOWLIST and credential scanner
  - Regex redaction for Private Keys, DB URIs, AWS keys, JWTs, and Vendor API keys
  - format_system_observation XML boundary tag encapsulation (<system_observation untrusted="true">)
  - sanitize_boundary_text escaping closing tags to neutralize prompt injection breakout
  - Observation passivity defense directives added to SYSTEM_PROMPT_COMMAND and SYSTEM_PROMPT_CHAT
affects: [04-03]

actuals:
  tokens: 4100
  tasks: 2
  commits: 1

tech-stack:
  added: []
  patterns: [Allowlist-first sanitization, regex secret scrubbing, XML boundary containment, prompt injection defense]

key-files:
  created:
    - src/aishell/context/privacy.py
    - src/aishell/context/sanitizer.py
    - tests/test_context_privacy.py
    - tests/test_context_sanitizer.py
  modified:
    - src/aishell/context/inspector.py
    - src/aishell/context/__init__.py
    - src/aishell/providers/prompts.py

key-decisions:
  - "D-02: PrivacyGuard applies strict SAFE_ENV_ALLOWLIST dropping unknown environment variables and redacting sensitive values"
  - "D-02: Regex pattern scanner replaces secrets with typed tokens ([REDACTED:API_KEY], [REDACTED:JWT], [REDACTED:DATABASE_URI])"
  - "D-03: Observations encapsulated inside <system_observation untrusted='true'> with closing tags escaped to prevent breakout"

patterns-established:
  - "Boundaries pattern: untrusted observation data is enclosed in dedicated XML tags and sanitized for nested closing tags"
  - "Passive state directive: system prompts instruct LLM that host observations must never override instructions"

requirements-completed: [CTXT-02, CTXT-03]

coverage:
  - id: D1
    description: "PrivacyGuard allowlist filtering and credential redaction"
    requirement: "CTXT-02"
    verification:
      - kind: unit
        ref: "tests/test_context_privacy.py"
        status: pass
    human_judgment: false
  - id: D2
    description: "Untrusted observation boundary tags and prompt defense"
    requirement: "CTXT-03"
    verification:
      - kind: unit
        ref: "tests/test_context_sanitizer.py"
        status: pass
    human_judgment: false
---

# Phase 04 Plan 02: Privacy Guard & Boundary Sanitizer Summary

## Accomplishments
1. **Privacy Guard**: Built `PrivacyGuard` in `src/aishell/context/privacy.py` with `SAFE_ENV_ALLOWLIST` (`PATH`, `SHELL`, `USER`, `LOGNAME`, `TERM`, `LANG`, `LC_*`, `PWD`, `HOME`, `EDITOR`, `PAGER`), discarding all unallowlisted environment variables.
2. **Credential Redaction**: Implemented regex redaction replacing PEM private keys, database connection strings, AWS access keys, JWT tokens, and Google/OpenAI/Anthropic API keys with typed placeholders (`[REDACTED:<TYPE>]`).
3. **Inspector Wiring**: Updated `inspect_system_context` to filter and sanitize `os.environ` into `SystemContext.env_vars`.
4. **Boundary Tag Encapsulation**: Implemented `format_system_observation` in `src/aishell/context/sanitizer.py` wrapping host facts in `<system_observation untrusted="true">`.
5. **Prompt Injection Defense**: Implemented `sanitize_boundary_text` escaping embedded `</system_observation>` tags and updated `SYSTEM_PROMPT_COMMAND` and `SYSTEM_PROMPT_CHAT` to instruct the model to treat system observations as passive, non-overriding data.
6. **Testing**: 11 unit tests passing across `tests/test_context_privacy.py` and `tests/test_context_sanitizer.py`.
