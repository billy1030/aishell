---
phase: 03-multi-provider-llm-integration
plan: 01
subsystem: providers
tags: [llm, provider-protocol, pydantic, schema, error-handling, prompts]

requires: []
provides:
  - BaseProvider abstract protocol (stream_chat, generate_proposal, validate_credentials)
  - ChatMessage conversational message model
  - CommandProposal schema with risk_tier validation and requirements
  - parse_proposal_from_text dual-mode parser with JSON extraction and markdown fence fallback
  - ProviderError hierarchy with actionable operator guidance
  - Centralized Linux system prompts in prompts.py
affects: [03-02, 03-03]

actuals:
  tokens: 4100
  tasks: 2
  commits: 2

tech-stack:
  added: [openai, google-genai, anthropic, httpx]
  patterns: [Pydantic schema validation, resilient dual-mode JSON/regex parsing, actionable error guidance]

key-files:
  created:
    - src/aishell/providers/base.py
    - src/aishell/providers/errors.py
    - src/aishell/providers/schema.py
    - src/aishell/providers/prompts.py
    - src/aishell/providers/__init__.py
    - tests/test_provider_errors.py
    - tests/test_provider_schema.py
  modified:
    - pyproject.toml

key-decisions:
  - "D-01: Modular BaseProvider protocol defining stream_chat, generate_proposal, validate_credentials"
  - "D-02: Structured CommandProposal schema with safe, mutating, high_risk tiers and resilient dual-mode parser"
  - "D-05: Custom ProviderError exception hierarchy with actionable remediation guidance property and clean __str__"
  - "D-06: Centralized Linux system prompts instructing models to output exact commands and JSON proposals"

patterns-established:
  - "Resilient parsing pattern: json block regex -> loads -> CommandProposal; fallback: markdown bash code fence -> CommandProposal"
  - "Error guidance pattern: ProviderError subclasses carry explicit .guidance with shell commands for remediation"

requirements-completed: [PROV-03, PROV-04]

coverage:
  - id: D1
    description: "Provider error hierarchy with actionable remediation guidance"
    requirement: "PROV-04"
    verification:
      - kind: unit
        ref: "tests/test_provider_errors.py"
        status: pass
    human_judgment: false
  - id: D2
    description: "CommandProposal schema and resilient dual-mode parser"
    requirement: "PROV-03"
    verification:
      - kind: unit
        ref: "tests/test_provider_schema.py"
        status: pass
    human_judgment: false
---

# Phase 03 Plan 01: Provider Core Protocol, Schema & Errors Summary

## Accomplishments
1. **Registered Dependencies**: Added `openai`, `google-genai`, `anthropic`, and `httpx` to `pyproject.toml`.
2. **Provider Base Protocol**: Implemented `BaseProvider` protocol and `ChatMessage` dataclass in `src/aishell/providers/base.py` per D-01.
3. **Actionable Exception Hierarchy**: Created `ProviderError`, `AuthenticationError`, `ConnectionError`, `RateLimitError`, and `ModelNotFoundError` in `src/aishell/providers/errors.py` with explicit `.guidance` properties giving operators copy-paste remediation commands per D-05.
4. **Structured Proposal Schema & Dual-Mode Parser**: Implemented `CommandProposal` with risk classification (`safe`, `mutating`, `high_risk`) and `parse_proposal_from_text` in `src/aishell/providers/schema.py` supporting JSON blocks, markdown code blocks, and plain text per D-02.
5. **Standard System Prompts**: Centralized `SYSTEM_PROMPT_COMMAND` and `SYSTEM_PROMPT_CHAT` in `src/aishell/providers/prompts.py` per D-06.
6. **Testing**: 17 unit tests passing across `tests/test_provider_errors.py` and `tests/test_provider_schema.py`.
