# Phase 3 Context: Multi-Provider LLM Integration

**Phase Target:** `03-multi-provider-llm-integration`
**Requirements:** `PROV-01`, `PROV-02`, `PROV-03`, `PROV-04`

## Phase Goal
Empower users to generate shell commands and troubleshoot systems using their choice of cloud LLMs (Google Gemini, OpenAI, Anthropic) or local offline models (Ollama), with real-time async token streaming, structured command proposals with risk tiers, and actionable guidance for missing credentials or connection failures.

## Locked Architecture & Design Decisions

### D-01: Modular Provider Protocol & Chat Message Schema
- Define `BaseProvider` abstract base class in `src/aishell/providers/base.py`:
  - `async def stream_chat(self, messages: List[ChatMessage], system_prompt: Optional[str] = None) -> AsyncIterator[str]`
  - `async def generate_proposal(self, query: str, system_context: Optional[str] = None) -> CommandProposal`
  - `def validate_credentials(self) -> None`
- Define `ChatMessage` with `role: Literal["system", "user", "assistant"]` and `content: str`.

### D-02: Structured Command Proposal Schema & Resilient Parser
- Define `CommandProposal` Pydantic model in `src/aishell/providers/schema.py`:
  - `command: str` (exact executable shell command string)
  - `purpose: str` (concise intent description)
  - `explanation: str` (explanation of flags and parameters)
  - `risk_tier: Literal["safe", "mutating", "high_risk"]`
  - `requires_sudo: bool = False`
  - `remediation: bool = False`
- Resilient dual-mode parsing (`parse_proposal_from_text`):
  - Primary: structured JSON parsing with validation against `CommandProposal`.
  - Fallback: markdown code fence regex parser extracting commands from ````bash ... ```` blocks when non-JSON models are queried.

### D-03: Modular Provider Adapters
- Implement 4 dedicated adapters inheriting `BaseProvider`:
  1. `OllamaProvider` (`src/aishell/providers/ollama.py`): OpenAI-compatible client targeted at local daemon (`http://localhost:11434/v1`).
  2. `GeminiProvider` (`src/aishell/providers/gemini.py`): official modern `google-genai` SDK (`google.genai.Client`) with `gemini-2.0-flash` default.
  3. `OpenAIProvider` (`src/aishell/providers/openai.py`): `openai.AsyncOpenAI` client for GPT-4o / o3-mini.
  4. `AnthropicProvider` (`src/aishell/providers/anthropic.py`): `anthropic.AsyncAnthropic` client for Claude 3.5 Sonnet / Haiku.

### D-04: Provider Factory & Dynamic Switching
- Provide `get_provider(name, model, settings)` factory in `src/aishell/providers/factory.py`.
- Support runtime provider selection via CLI flags `-p` / `--provider`, `-m` / `--model`, and config file overrides.
- Support switching provider and model in the REPL session.

### D-05: Actionable Error Guidance & Custom Exception Hierarchy
- Create custom exceptions in `src/aishell/providers/errors.py`:
  - `ProviderError` (base)
  - `AuthenticationError`: informs operator about missing `GEMINI_API_KEY`, `OPENAI_API_KEY`, or `ANTHROPIC_API_KEY` with exact export commands.
  - `ConnectionError`: identifies unreachable Ollama daemon (`localhost:11434`) and suggests running `ollama serve`.
  - `RateLimitError`: identifies HTTP 429 quota exhaustion.
  - `ModelNotFoundError`: identifies missing Ollama model and suggests `ollama pull <model>`.
- Format all provider exceptions via `RichStreamRenderer.render_error()` with zero unhandled stack traces.

### D-06: Standard System Prompts
- Centralize system prompts in `src/aishell/providers/prompts.py` instructing models to produce precise Linux shell commands, avoid unnecessary prose, output structured JSON for proposals, and accurately assess risk tier.

### D-07: REPL & One-Shot End-to-End Wiring
- Replace the Phase 2 placeholder in `InteractiveREPL.dispatch_input()` and `execute_one_shot()` with active async streaming from the selected provider.

