# Terminal AI Shell (`aishell`) — Technical Documentation

## 1. System Architecture

`aishell` is organized into modular, single-responsibility Python packages under `src/aishell/`:

```text
src/aishell/
├── cli.py                  # Typer CLI entrypoint, one-shot mode, and execution pipelines
├── config/
│   ├── settings.py         # Layered Pydantic v2 configuration (CLI > Env > TOML > Defaults)
│   └── defaults.py         # Default config.toml generator with 0700/0600 POSIX permissions
├── context/
│   ├── inspector.py        # OS/distro, shell, user, and process telemetry gathering
│   ├── privacy.py          # PrivacyGuard credential & secret redaction engine
│   ├── sanitizer.py        # Untrusted XML delimiter wrapping (<system_observation>)
│   └── display.py          # Rich system context diagnostic table
├── conversation/
│   └── manager.py          # Sliding-window memory (8 turns / 4000 tokens) & compaction
├── diagnostics/
│   ├── schema.py           # FailureCategory, FailurePayload, output trimming & redaction
│   ├── engine.py           # DiagnosticEngine (ignores exit code 130 SIGINT)
│   └── remediation.py      # RemediationController (strictly bounded 2-cycle self-healing)
├── execution/
│   ├── builtins.py         # Parent-process cd, export, unset synchronization
│   ├── pty_runner.py       # Managed POSIX PTY runner with Windows fallback & ring buffer
│   └── ring_buffer.py      # Circular in-memory output buffer (lines / KB bounds)
├── mcp/
│   ├── __init__.py         # Public exports for MCPManager and MCPTool schemas
│   ├── client.py           # Lightweight JSON-RPC 2.0 stdio MCP client & server manager
│   └── schema.py           # MCPServerConfig, MCPTool, MCPToolCall, & <mcp_call> parser
├── providers/
│   ├── base.py             # Abstract BaseProvider interface & ChatMessage model
│   ├── factory.py          # Provider resolution (minimax, openai, gemini, anthropic, ollama, custom)
│   ├── openai.py           # AsyncOpenAI adapter (OpenAI, MiniMax, DeepSeek, Groq, vLLM)
│   ├── gemini.py           # Google GenAI SDK adapter
│   ├── anthropic.py        # Anthropic Claude SDK adapter
│   ├── ollama.py           # Local Ollama REST/OpenAI-compatible adapter
│   ├── prompts.py          # System prompt templates (command JSON & interactive chat)
│   ├── schema.py           # CommandProposal extraction & validation
│   └── errors.py           # Actionable error types (Auth, RateLimit, Connection)
├── safety/
│   ├── classifier.py       # Deterministic AST/regex blast-radius risk classifier
│   ├── display.py          # Color-coded Proposal Card renderer
│   └── gate.py             # SafetyGate human confirmation ([y=run / N=cancel / e=edit])
├── skills/
│   ├── __init__.py         # Public exports for Skill and SkillManager
│   ├── builtins.py         # Built-in Linux/DevOps skills (repo-study, web-search, web-fetch, etc.)
│   ├── manager.py          # Hierarchical SKILL.md discovery (project > user > builtin) & matching
│   └── schema.py           # Pydantic Skill model (name, description, instructions, triggers)
├── storage/
│   └── history.py          # ACID SQLite command audit log (~/.local/state/aishell/history.db)
└── ui/
    ├── banner.py           # Startup system banner (with version & commit ID) & clean UNIX prompt
    ├── history.py          # PromptToolkit SQLite-backed reverse search history (Ctrl+R)
    ├── renderer.py         # Rich Live Markdown streamer with 'Thinking...' spinner
    └── repl.py             # InteractiveREPL event loop, autonomous agentic loop, & async cleanup
```

---

## 2. Input Routing & Execution Flow

### 2.1 Smart Input Classification (`InteractiveREPL._classify_input`)

Inside the interactive REPL, user input is routed without waking the AI unnecessarily:

1. **Meta Commands**: `:exit`, `:quit`, `:help`, `:clear`, `:context`, `:skills` (`reload`, `install`, `create`), `:findskills`, `:mcp` (`reload`), `:autorun` (`safe`, `off`), `:save`, `:export`, `:resume`, `/provider`, `/model`. `Ctrl+D` or `Ctrl+Z` also exits cleanly.
2. **Explicit AI Wake-Up Triggers**: Inputs starting with `@` (skill mention), `ais`, `ai`, `hi`, `hello`, `hey`, `please`, or `?` always route to the AI assistant—even if followed by a command name (e.g., `ais ls`).
3. **Direct Shell Execution**:
   - Explicit prefixes (`!cmd`, `$cmd`).
   - Shell builtins (`cd`, `export`, `unset`, `pwd`, `echo`, `alias`, `source`).
   - Common Linux commands (`ls`, `df`, `ps`, `free`, `cat`, `git`, `docker`, `systemctl`, `sudo`, etc.) or any executable resolved via `shutil.which()`.
4. **Natural Language Fallback**: Multi-word questions (especially ending in `?`) route to the AI assistant.

### 2.2 AI Streaming & Multi-Step Context Capture

1. `RichStreamRenderer.stream_markdown()` displays an animated `⠋ Thinking...` spinner via `rich.live.Live` until the first token arrives from the provider.
2. `extract_proposal_from_text()` inspects the completed Markdown/JSON response for an executable shell command.
3. If a command is found, `SafetyGate.process_proposal()` presents the Proposal Card and prompts:
   `Execute command? [y=run / N=cancel / e=edit]: `
   - **`y` / `yes`**: Executes via `execute_pipeline_capture()`.
   - **`e` / `edit`**: Opens the inline command editor (`prompt_edit_command`) and re-evaluates risk.
   - **`n` / `no` / `Enter` / `Ctrl+C`**: Cancels execution safely.
4. After execution completes, `stdout`/`stderr` is scrubbed by `PrivacyGuard` and recorded into `ConversationManager` inside `<command_output command="..." exit_code="..." untrusted="true">` tags so the user can ask follow-ups or type `ais continue`.

---

## 3. Defense-in-Depth Security Model

| Layer                        | Component               | Responsibility                                                                                                                                    |
| ---------------------------- | ----------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------- |
| **1. Human Gate**            | `SafetyGate`            | Mandatory `[y=run / N=cancel / e=edit]` confirmation before executing any AI-proposed command. Non-TTY stdin blocks execution automatically.      |
| **2. Risk Classification**   | `classify_risk()`       | Deterministic classification into `READ_ONLY` (green), `MUTATING` (yellow), and `HIGH_RISK` (red: `rm -rf`, `dd`, `mkfs`, `sudo`, pipe-to-shell). |
| **3. Secret Redaction**      | `PrivacyGuard`          | Masks API keys (`sk-*`, `AIza*`), Bearer tokens, private keys, AWS credentials, and DB connection strings before LLM transmission.                |
| **4. Injection Containment** | `sanitizer.py`          | Wraps host facts, environment observations, and command outputs in `<... untrusted="true">` XML delimiters.                                       |
| **5. Bounded Recovery**      | `RemediationController` | Caps automatic error remediation loops to `MAX_REMEDIATION_CYCLES = 2` and ignores user `SIGINT` (exit code 130).                                 |

---

## 4. Multi-Provider Configuration & Precedence

Configuration loads in strict priority order:

1. CLI overrides (`-p/--provider`, `-m/--model`)
2. Environment variables (`AISHELL_*`, `AISHELL_CONFIG_FILE`, `MINIMAX_API_KEY`, `OPENAI_API_KEY`, `GEMINI_API_KEY`, `ANTHROPIC_API_KEY`)
3. TOML config file (`~/.config/aishell/config.toml`)
4. Pydantic defaults

### Custom & OpenAI-Compatible Providers

`ProvidersConfig` uses `ConfigDict(extra="allow")` and universal fallback in `get_provider()`, enabling any provider name (e.g., `volcengine`, `minimax`, `deepseek`, `groq`, or custom names) to resolve via `OpenAIProvider` using `[providers.<name>]`, `<NAME>_API_KEY`/`<NAME>_BASE_URL`, or `[providers.openai]` fallback.

---

## 5. Async & PTY Lifecycle

- **PTY Management (`pty_runner.py`)**: Allocates a POSIX pseudo-terminal (`pty.openpty()`), saves/restores `termios` attributes in a `finally` block, forwards `SIGINT` / `SIGWINCH`, and falls back to `subprocess.Popen` on non-POSIX hosts (Windows).
- **Clean Shutdown (`InteractiveREPL._cleanup_async_loop`)**:
  - `OpenAIProvider.stream_chat` wraps SSE streams in `async with response:` and closes `AsyncStream` in `finally`.
  - On exit (`exit`, `:exit`, `Ctrl+D`, or double `Ctrl+C`), `_cleanup_async_loop()` awaits `provider.aclose()`, runs `gc.collect()`, executes `loop.shutdown_asyncgens()`, cancels pending tasks, and closes the event loop cleanly without dangling task warnings.

---

## 6. Testing

The automated test suite verifies all modules across 185 unit and integration tests:

```bash
uv run pytest
```
