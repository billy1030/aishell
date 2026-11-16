# Phase 3 Discussion Log: Multi-Provider LLM Integration

## Discussion Summary
Autonomous pre-planning discussion for Phase 3:
1. **SDK Selection**:
   - Google Gemini: official `google-genai` SDK (`>=3.0.0`) as established in research STACK.md, avoiding legacy `google-generativeai`.
   - Local Ollama: standard `openai` SDK pointing to `http://localhost:11434/v1`.
   - OpenAI: `openai.AsyncOpenAI`.
   - Anthropic: `anthropic.AsyncAnthropic`.
2. **Streaming Protocol**:
   - `stream_chat` yields string tokens as an async generator (`AsyncIterator[str]`).
   - Terminal renderer iterates chunks in real-time.
3. **Structured Proposals**:
   - Pydantic `CommandProposal` with risk classification (`safe`, `mutating`, `high_risk`).
   - Fallback regex parser for small local models that might return markdown fences rather than pure JSON.
4. **Actionable Error Guidance**:
   - No raw python stack traces printed to terminal.
   - Distinct guidance for missing API keys, disconnected local Ollama server, and quota limits.

