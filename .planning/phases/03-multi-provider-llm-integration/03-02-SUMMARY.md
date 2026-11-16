---
phase: 03-multi-provider-llm-integration
plan: 02
subsystem: providers
tags: [llm, ollama, openai, gemini, anthropic, factory, stream-chat]

requires: [03-01]
provides:
  - OllamaProvider supporting localhost:11434 streaming and proposal generation
  - OpenAIProvider supporting GPT-4o with rate-limit and auth error mapping
  - GeminiProvider supporting official google-genai Client and gemini-2.0-flash
  - AnthropicProvider supporting AsyncAnthropic and Claude 3.5 Sonnet
  - get_provider factory with registry, defaults, overrides, and credential validation
affects: [03-03]

actuals:
  tokens: 4900
  tasks: 3
  commits: 2

tech-stack:
  added: [google.genai.Client, openai.AsyncOpenAI, anthropic.AsyncAnthropic]
  patterns: [Adapter pattern over BaseProvider, Factory pattern with lazy client instantiation, SDK exception mapping]

key-files:
  created:
    - src/aishell/providers/ollama.py
    - src/aishell/providers/openai.py
    - src/aishell/providers/gemini.py
    - src/aishell/providers/anthropic.py
    - src/aishell/providers/factory.py
    - tests/test_provider_adapters.py
    - tests/test_provider_factory.py
  modified:
    - src/aishell/providers/__init__.py

key-decisions:
  - "D-01: Concrete provider adapters implementing stream_chat, generate_proposal, and validate_credentials"
  - "D-03: 4 dedicated adapters (Ollama, OpenAI, Gemini via google-genai, Anthropic via AsyncAnthropic)"
  - "D-04: get_provider factory with dynamic name/model resolution, configuration injection, and credential validation"
  - "D-05: Mapping vendor SDK errors (401, 403, 404, 429, connection refused) to aishell's ProviderError hierarchy"

patterns-established:
  - "Lazy client instantiation pattern: client is initialized inside _get_client() upon validate_credentials() or execution"
  - "Factory registry pattern: _PROVIDER_REGISTRY maps lowercase names to adapter classes"

requirements-completed: [PROV-01, PROV-02, PROV-04]

coverage:
  - id: D1
    description: "Multi-provider adapter implementations and error mapping"
    requirement: "PROV-01, PROV-02, PROV-04"
    verification:
      - kind: unit
        ref: "tests/test_provider_adapters.py"
        status: pass
    human_judgment: false
  - id: D2
    description: "Provider factory resolution and credential validation"
    requirement: "PROV-01, PROV-04"
    verification:
      - kind: unit
        ref: "tests/test_provider_factory.py"
        status: pass
    human_judgment: false
---

# Phase 03 Plan 02: Provider Adapters & Factory Summary

## Accomplishments
1. **Ollama Adapter**: Implemented `OllamaProvider` connecting to local daemon at `http://localhost:11434/v1`, streaming tokens asynchronously, and translating connection failures to `ConnectionError` with `ollama serve` instructions and missing models to `ModelNotFoundError` with `ollama pull` suggestions.
2. **OpenAI Adapter**: Implemented `OpenAIProvider` with lazy client initialization, asynchronous token streaming, and translation of 401/429 errors to `AuthenticationError` and `RateLimitError`.
3. **Google Gemini Adapter**: Implemented `GeminiProvider` using the modern `google-genai` SDK (`client.aio.models.generate_content_stream`), mapping API errors to actionable guidance.
4. **Anthropic Adapter**: Implemented `AnthropicProvider` using `AsyncAnthropic` client with Claude 3.5 Sonnet support and custom exception mapping.
5. **Provider Factory**: Implemented `get_provider()` and `get_supported_providers()` in `src/aishell/providers/factory.py` supporting dynamic resolution, CLI/config overrides, and credential validation.
6. **Testing**: 17 unit tests passing across `tests/test_provider_adapters.py` and `tests/test_provider_factory.py`.
