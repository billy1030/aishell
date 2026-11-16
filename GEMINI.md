<!-- GSD:project-start source:PROJECT.md -->

## Project

**Terminal AI Shell (aishell)**

An interactive, system-aware Linux AI console assistant and REPL designed for developers and sysadmins. It bridges natural language intent with Linux terminal operations by generating and explaining shell commands, gathering system context, and safely running commands with explicit user confirmation.

**Core Value:** Empower developers and system administrators to troubleshoot, operate, and automate Linux workflows through conversational AI without leaving the terminal or risking accidental execution of unintended commands.

### Constraints

- **Tech stack**: Python 3.10+, `rich`, `prompt_toolkit` — enables rich TUI without heavy binary dependencies
- **Security**: Mandatory human-in-the-loop confirmation before running any proposed shell commands
- **Compatibility**: POSIX-compliant terminal environments, SSH-friendly

<!-- GSD:project-end -->

<!-- GSD:stack-start source:research/STACK.md -->

## Technology Stack

## Recommended Stack

### Core Technologies

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| **Python** | `>=3.10, <3.14` (Target: 3.11+) | Core runtime environment | Ubiquitous across Linux distributions (Ubuntu 22.04+ ships 3.10+, Debian 12 ships 3.11+, Ubuntu 24.04 ships 3.12+). Python 3.11+ provides native `tomllib` and `asyncio.TaskGroup` for high-performance concurrent streaming and system inspection without extra C-extension build requirements. |
| **prompt-toolkit** | `>=3.0.50, <4.0.0` (Latest: `3.0.53`) | Interactive REPL & terminal input | The industry standard engine for Python REPLs (powers IPython, ptpython, pgcli, mycli). Delivers asynchronous event loop integration, multiline input editing, persistent command history, vi/emacs keybindings, auto-suggestions, and tab completion without terminal flickering. |
| **rich** | `>=14.0.0, <16.0.0` (Latest: `15.0.0`) | Terminal formatting & stream rendering | Defacto standard for modern terminal UI in Python. Provides first-class markdown rendering, syntax highlighting for shell commands (bash/zsh), live streaming status spinners, clean diff views, styled confirmation prompts, and graceful degradation across raw TTYs and SSH sessions. |
| **typer** | `>=0.16.0, <1.0.0` (Latest: `0.29.1`) | CLI entrypoint & subcommands | Built on `click` with type-hinted argument validation, automatic shell completion generation, and native integration with `rich` for elegant `--help` and CLI error formatting. Allows both direct command execution (`aishell "how do I find large files"`) and launching the interactive REPL (`aishell`). |
| **pydantic** | `>=2.10.0, <3.0.0` (Latest: `2.14.3`) | Data validation & structured LLM schemas | Rust-backed high-performance validation engine. Essential for parsing structured LLM responses (command proposals, risk classification, intent breakdown, remediation actions) and validating user configuration. |
| **pydantic-settings** | `>=2.16.0, <3.0.0` (Latest: `2.16.3`) | Configuration management | Robust hierarchy for loading settings from `~/.config/aishell/config.toml`, environment variables (`AISHELL_*`), and CLI flags with automatic type casting and helpful validation errors. |

### LLM Provider Architecture

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| **openai** | `>=3.50.0, <4.0.0` (Latest: `3.51.0`) | OpenAI API & universal compatible endpoints | Used for OpenAI models (GPT-4o, o3-mini) AND any OpenAI-compatible provider: local Ollama (`http://localhost:11434/v1`), Groq, DeepSeek, vLLM, and LocalAI. Streamlines multi-provider compatibility with a single rock-solid SDK. |
| **google-genai** | `>=3.3.0, <4.0.0` (Latest: `3.3.0`) | Google Gemini API | Official modern Google GenAI SDK (replaces legacy `google-generativeai`). Powers Gemini 2.0 / 1.5 Pro and Flash with streaming text, system instructions, and structured outputs. |
| **anthropic** | `>=2.8.0, <3.0.0` (Latest: `2.8.0`) | Anthropic Claude API | Official Claude SDK for Claude 3.5 Sonnet / Haiku. Delivers streaming token generation and tool use protocols. |
| **httpx** | `>=0.28.0, <1.0.0` (Latest: `0.28.1`) | Async HTTP client & fallback transport | Underlying async transport for direct Ollama native REST calls (`/api/chat`), custom LLM gateways, and health-checking local Ollama daemon status with zero overhead. |

### Supporting Libraries

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| **distro** | `>=1.9.0, <2.0.0` (Latest: `1.9.0`) | Linux OS distribution detection | Used by the system context inspector to accurately identify the Linux distribution, version, and family (Debian/Ubuntu vs RHEL/CentOS vs Arch vs Alpine) by parsing `/etc/os-release`. Enables LLM to suggest distro-specific package managers (`apt`, `dnf`, `pacman`, `apk`). |
| **psutil** | `>=7.0.0, <8.0.0` (Latest: `7.2.2`) | System metrics & process inspection | Inspects current system load, memory pressure, active shell PID/process name, and child process trees to enrich AI context when diagnosing errors. |
| **tomli** / **tomli-w** | `tomli >= 2.0.1` (Python 3.10), `tomli-w >= 1.1.0` | TOML reading & writing | Used to read and write `~/.config/aishell/config.toml`. On Python 3.11+, stdlib `tomllib` is used for reading; `tomli-w` is used to persist user configuration changes. |
| **pygments** | `>=2.19.0, <3.0.0` | Shell command syntax highlighting | Integrated into `prompt-toolkit` and `rich` for syntax highlighting bash/sh/zsh scripts, command inputs, and execution logs. |

### Standard Library Components (Zero-Dependency Assets)

| Module | Purpose | Why Prefer Standard Library |
|--------|---------|-----------------------------|
| `sqlite3` | Session history & command audit database | Stores conversation history, executed commands, exit codes, and timestamps at `~/.local/state/aishell/history.db`. Zero external dependencies, ACID-compliant, lightning-fast queries. |
| `subprocess` & `pty` | Controlled shell execution & PTY allocation | POSIX pseudo-terminal handling for capturing interactive command output, ANSI escape sequence passthrough, exit codes, and safe signal propagation (`SIGINT` / `Ctrl+C`). |
| `shlex` | Command parsing & argument splitting | Safely tokens and sanitizes shell strings, avoiding naive whitespace splitting bugs. |
| `pathlib` | Filesystem & path management | Clean, object-oriented path manipulation adhering to XDG base directory specifications (`~/.config/aishell`, `~/.local/state/aishell`). |

### Development & Tooling

| Tool | Version | Purpose | Notes |
|------|---------|---------|-------|
| **ruff** | `>=0.17.0` (Latest: `0.17.5`) | Linting & code formatting | Replaces Black, Flake8, and isort. Blazing fast (written in Rust) with zero configuration drift. |
| **pytest** | `>=9.0.0` (Latest: `9.2.0`) | Test runner | Comprehensive unit and integration testing. |
| **pytest-asyncio** | `>=1.5.0` (Latest: `1.5.0`) | Async test support | Crucial for testing `asyncio` loops in REPL handlers, streaming LLM providers, and command execution pipelines. |
| **mypy** | `>=1.15.0` | Static type checking | Enforces strict type boundaries across provider adapters, data schemas, and UI components. |
| **uv** | Latest | Package management & virtualenvs | Fast package installer and resolver for local development. |

## Installation

# Core CLI, REPL, formatting, and system inspection

# Multi-provider LLM support

# Development dependencies

## Alternatives Considered

| Recommended | Alternative | When to Use Alternative | Why Recommended Won for `aishell` |
|-------------|-------------|-------------------------|-----------------------------------|
| **Modular Provider Adapters (`openai` + `google-genai` + `anthropic` + `httpx`)** | **LiteLLM (`litellm`)** | Large enterprise multi-tenant microservices or server proxies needing 100+ model fallbacks and central billing dashboards. | **Startup latency & footprint**: LiteLLM imports take 1.5–2.5+ seconds, pulls in hundreds of MBs of dependencies, makes remote network calls on import to fetch pricing maps, and experienced security supply-chain compromises (v1.107.0). Terminal users expect an interactive shell to launch in `<150ms`. Direct SDKs + OpenAI-compatibility layer provide instant startup and total control. |
| **Modular Provider Adapters** | **LangChain / LlamaIndex** | Complex autonomous multi-agent graphs, document chunking/RAG vector search pipelines. | Extreme bloat, debugging opacity, and rapid deprecation cycles. `aishell` needs predictable, fast streaming for single-turn intent-to-command and multi-turn shell diagnosis. |
| **`prompt-toolkit` + `rich`** | **`textual`** | Full-screen dashboard TUI apps with multiple widgets, panels, and mouse-driven windows (like `htop` or `lazygit`). | `textual` takes over the entire alternate screen buffer, obscuring the user's terminal scrollback. `aishell` is an inline REPL and assistant that must preserve standard terminal scrollback, command execution history, and piped stdout/stderr. |
| **`prompt-toolkit`** | **`readline` (stdlib)** | Extremely basic single-line prompt without styling, syntax highlighting, or async integration. | Standard `readline` lacks multiline editing, rich syntax highlighting, vi/emacs mode switching, auto-suggestions, and native `asyncio` event loop integration. |
| **`typer`** | **`click`** | Legacy codebases or projects avoiding Pydantic/type-hint dependencies. | `typer` is built on top of `click` but leverages Python standard type hints, reducing boilerplate while automatically integrating with `rich` for terminal help screens. |
| **`distro`** | **Manual `/etc/os-release` parsing** | Zero-dependency micro-scripts. | Linux distributions exhibit dozens of edge cases (`/etc/debian_version`, `/etc/redhat-release`, container overlays). `distro` is tiny (<50KB), battle-tested, and handles all Linux flavors cleanly. |
| **`sqlite3` (stdlib)** | **Plain text / JSONL history** | Trivial linear history without search or metadata needs. | SQLite offers indexed searching across commands, exit codes, execution duration, and AI sessions with atomic writes, preventing history file corruption on shell crashes or abrupt terminal termination. |

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| **`litellm` (monolithic import)** | High import overhead (>1.5s), bloated dependency graph, remote pricing fetches at runtime, and supply-chain risk. Freezes CLI startup. | Lightweight modular `BaseProvider` protocol using `openai` (covers OpenAI, Ollama, Groq, DeepSeek) + official `google-genai` and `anthropic` SDKs. |
| **`langchain` / `langchain-core`** | Massive abstraction bloat, slow startup, uncontrolled prompt modification, brittle API churn. | Direct vendor SDKs with explicit Pydantic schemas and system prompts. |
| **`google-generativeai`** | Deprecated legacy Google SDK; lacks modern streaming and tool-calling interfaces of the new Gemini platform. | Official **`google-genai`** SDK (`>=3.3.0`). |
| **`os.system()` / `subprocess.Popen(shell=True)` without validation** | Severe security vulnerability. Shell injection risk from hallucinated or unescaped LLM output. | `subprocess.Popen(shlex.split(cmd), shell=False)` or explicit pseudo-terminal `pty` with mandatory interactive `[y/N]` human confirmation gate. |
| **`curses` / `urwid`** | 1990s-era terminal libraries with poor UTF-8/Unicode support, broken 24-bit truecolor handling, and fragile cross-platform behavior. | `rich` (for rendering) + `prompt-toolkit` (for input). |
| **`inquirer` / `PyInquirer`** | Abandoned/unmaintained packages with incompatible dependency trees on modern Python (3.10+). | Built-in `prompt-toolkit` prompts or `rich.prompt.Confirm`. |
| **Global `pip install`** | Pollutes system Python on modern Linux distros (PEP 668 `externally-managed-environment` error on Debian/Ubuntu/Fedora). | Distribute via `pipx` or isolated virtualenv packaging (`uv tool install aishell`). |

## Stack Patterns by Variant

### Variant 1: Cloud-First Setup (Gemini, Claude, GPT-4o)

- **Primary Transport:** Native vendor SDKs (`google-genai`, `anthropic`, `openai`).
- **Configuration:** API keys stored in `~/.config/aishell/config.toml` or passed via environment variables (`GEMINI_API_KEY`, `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`).
- **Advantage:** Maximum model reasoning capability, zero local compute required, fast token generation over streaming HTTPS.

### Variant 2: Local & Air-Gapped / Privacy Setup (Ollama / LocalAI)

- **Primary Transport:** `openai` client configured with `base_url="http://localhost:11434/v1"` or direct `httpx` async client.
- **System Requirements:** Local Ollama daemon running models such as `qwen2.5-coder:7b`, `llama3.2`, or `mistral`.
- **Advantage:** 100% private, zero network data egress, operates fully offline on Linux workstations or private servers.

### Variant 3: Minimal Headless / SSH Console

- **Primary Transport:** Dynamic terminal detection (`rich.console.Console(force_terminal=...)`).
- **Behavior:** Automatically detects whether terminal supports 24-bit TrueColor, 256 colors, or standard ANSI; disables Unicode glyphs on degraded ASCII terminals or SSH serial consoles while retaining full REPL safety gates.

## Version Compatibility Matrix

| Package | Tested Version | Compatible Range | Compatibility & Integration Notes |
|---------|----------------|------------------|-----------------------------------|
| `prompt-toolkit` | `3.0.53` | `>=3.0.50, <4.0.0` | Seamless integration with `asyncio` event loop. Works cleanly alongside `rich.live.Live` and `rich.console.Console`. |
| `rich` | `15.0.0` | `>=14.0.0, <16.0.0` | High-speed ANSI rendering. Fully compatible with Python 3.10–3.13. |
| `typer` | `0.29.1` | `>=0.16.0, <1.0.0` | Built on `click >= 8.1.8`. Integrates natively with `rich` for formatting. |
| `pydantic` | `2.14.3` | `>=2.10.0, <3.0.0` | Pydantic V2 core. Compatible with `pydantic-settings >= 2.16.0`. |
| `openai` | `3.51.0` | `>=3.50.0, <4.0.0` | Universal client for OpenAI API, Ollama (`/v1`), Groq, DeepSeek, Together. |
| `google-genai` | `3.3.0` | `>=3.0.0, <4.0.0` | Replaces legacy `google-generativeai`. Requires Python `>=3.10`. |
| `anthropic` | `2.8.0` | `>=2.8.0, <3.0.0` | Official client for Claude models with native async streaming support. |
| `psutil` | `7.2.2` | `>=7.0.0, <8.0.0` | Native C extension with pre-compiled wheels for all standard Linux architectures (`x86_64`, `aarch64`). |
| `distro` | `1.9.0` | `>=1.9.0, <2.0.0` | Pure Python, zero dependencies. Reliable across all Linux distros. |

## Sources

- **PyPI Official Registry API** (Verified live 2026-11-16):
- **Google GenAI Documentation** (`google-genai` v3+): Migration from legacy `google-generativeai` to `google-genai` [HIGH Confidence]
- **Ollama API Documentation**: OpenAI-compatibility specification on `/v1/chat/completions` [HIGH Confidence]
- **LiteLLM Architecture & Performance Analysis**: Dependency bloat, import startup latency (>1.5s), and remote pricing map network overhead [HIGH Confidence]
- **Linux Terminal Ecosystem Standards**: XDG Base Directory specification, POSIX pseudo-terminal handling (`pty`/`termios`) [HIGH Confidence]

<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->

## Conventions

Conventions not yet established. Will populate as patterns emerge during development.
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->

## Architecture

Architecture not yet mapped. Follow existing patterns found in the codebase.
<!-- GSD:architecture-end -->

<!-- GSD:skills-start source:skills/ -->

## Project Skills

No project skills found. Add skills to any of: `.agents/skills/`, `.agents/skills/`, `.cursor/skills/`, `.github/skills/`, or `.codex/skills/` with a `SKILL.md` index file.
<!-- GSD:skills-end -->

<!-- GSD:workflow-start source:GSD defaults -->

## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:
- `/gsd-fast` for a trivial task inline, with no subagents and no PLAN.md
- `/gsd-quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd-debug` for investigation and bug fixing
- `/gsd-execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->

<!-- GSD:profile-start -->

## Developer Profile

> Profile not yet configured. Run `/gsd-profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
