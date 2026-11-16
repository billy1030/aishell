# Architecture Research

**Domain:** Terminal AI Console Assistant & REPL Shell (Linux/POSIX CLI)  
**Researched:** 2026-11-16  
**Confidence:** HIGH (synthesized from established CLI/REPL agent architectures including Shell-GPT, Open Interpreter, Aider, and POSIX subprocess/TUI design patterns)

---

## Standard Architecture

Terminal AI shell assistants (e.g., `aishell`) bridge conversational LLMs with the host operating system. Unlike pure chatbots, they operate as an active loop: taking natural language intent, observing host state, synthesizing shell commands, prompting for explicit user confirmation, executing them via subprocess/PTY pipelines, and feeding terminal output back for error diagnosis and remediation.

### System Overview

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│                               Presentation Layer                                 │
│  ┌────────────────────────────────────────────────────────────────────────────┐  │
│  │                    Interactive REPL UI (prompt_toolkit)                    │  │
│  │     - Multi-line input & keybindings        - Persistent history (~/.aishell)│  │
│  │     - Command auto-completion / hints       - Session lifecycle management  │  │
│  ├────────────────────────────────────────────────────────────────────────────┤  │
│  │                     Output & TUI Renderer (Rich)                           │  │
│  │     - Streaming Markdown renderer           - Syntax highlighter (Shell/Bash)│  │
│  │     - Live status spinners & badges         - Confirmation dialog ([y/N/e]) │  │
│  └──────────────────────────────────────┬─────────────────────────────────────┘  │
└─────────────────────────────────────────┼────────────────────────────────────────┘
                                          │ User Input / Confirmation Decisions
┌─────────────────────────────────────────▼────────────────────────────────────────┐
│                              Core Agent Layer                                    │
│  ┌────────────────────────────────────────────────────────────────────────────┐  │
│  │                        Agent Orchestrator                                  │  │
│  │  - Multi-turn conversation state    - Sliding context window compaction    │  │
│  │  - Command extraction & parsing     - Remediation / Self-correction loop   │  │
│  └───────────────┬──────────────────────────────┬───────────────────────────────┘  │
│                  │ Queries Context              │ Dispatches Inference Requests    │
│  ┌───────────────▼───────────────┐     ┌────────▼───────────────────────────────┐  │
│  │       Context Collector       │     │          Model Client Engine           │  │
│  │  - OS & Kernel inspection     │     │  ┌──────────────────────────────────┐  │  │
│  │  - CWD & Git repository state │     │  │     Provider Strategy Interface  │  │  │
│  │  - Shell & User privileges    │     │  └────────┬───────┬─────────┬───────┘  │  │
│  │  - Secret / Env redaction     │     │           │       │         │          │  │
│  └───────────────────────────────┘     │     ┌─────▼┐  ┌───▼────┐  ┌─▼───────┐  │  │
│                                        │     │Gemini│  │OpenAI/ │  │ Local   │  │  │
│                                        │     │Client│  │Anthropic│ │(Ollama) │  │  │
│                                        │     └──────┘  └────────┘  └─────────┘  │  │
│                                        └────────────────────────────────────────┘  │
└─────────────────────────────────────────┬────────────────────────────────────────┘
                                          │ Approved Command Execution Request
┌─────────────────────────────────────────▼────────────────────────────────────────┐
│                        Execution & Sandbox Layer                                 │
│  ┌────────────────────────────────────────────────────────────────────────────┐  │
│  │                       Safety Gatekeeper & Sandbox                          │  │
│  │  - Command Risk Classifier (Safe / Warn / Block)                           │  │
│  │  - Destructive pattern heuristics (`rm -rf`, `dd`, `mkfs`, raw device writes)│  │
│  │  - Human-in-the-loop interactive confirmation enforcement                 │  │
│  ├────────────────────────────────────────────────────────────────────────────┤  │
│  │                       Subprocess Shell Executor                            │  │
│  │  - Streaming stdout / stderr capture       - Process timeout enforcement   │  │
│  │  - Signal propagation (SIGINT / Ctrl+C)     - Exit code inspection          │  │
│  └──────────────────────────────────────┬─────────────────────────────────────┘  │
└─────────────────────────────────────────┼────────────────────────────────────────┘
                                          │ Executes Commands / Observes Exit & Output
┌─────────────────────────────────────────▼────────────────────────────────────────┐
│                           Host Operating System                                  │
│                 (Linux / POSIX Environment: Bash, Zsh, Filesystem)               │
└──────────────────────────────────────────────────────────────────────────────────┘
```

---

### Component Responsibilities

| Component | Responsibility | Typical Implementation |
|-----------|----------------|------------------------|
| **REPL UI** | Captures multiline user queries, manages prompt history, handles keyboard shortcuts, and renders interactive menus. | `prompt_toolkit` `PromptSession`, history file backend, key binding managers. |
| **TUI Renderer** | Displays streamed token chunks, renders Markdown explanations, highlights proposed shell syntax, and shows execution badges. | `rich.console.Console`, `rich.live.Live`, `rich.syntax.Syntax`, `rich.panel.Panel`. |
| **Agent Orchestrator** | Coordinates the full turn: gathers context, builds prompt payloads, invokes model client, parses proposed commands, queries safety gate, dispatches execution, and manages conversation history. | Pure Python domain coordinator class managing a state machine across states (`IDLE`, `THINKING`, `CONFIRMING`, `EXECUTING`, `EVALUATING`). |
| **Context Collector** | Inspects host OS, active directory, git branch/status, environment variables, system load, and recent command exit codes. Sanitizes confidential tokens. | `os`, `platform`, `subprocess` (for `git status`), `psutil`, and regex-based secret scrubber. |
| **Model Client Engine** | Abstract provider protocol standardizing streaming responses, tool calling, and token tracking across multiple backends. | Abstract Base Class `BaseProvider` with implementations for Google GenAI (`google-genai`), OpenAI/Anthropic SDKs, and local REST (`ollama`). |
| **Safety Gatekeeper** | Analyzes proposed commands for destructive patterns, assigns safety tiers (`LOW`, `MEDIUM`, `HIGH_RISK`), and enforces explicit human authorization. | Rule-based AST/regex matcher + interactive user confirmation prompt (`[y/N/e]` with command edit option). |
| **Shell Executor** | Runs approved commands in the target shell, captures real-time interleaved stdout/stderr, tracks execution duration, and returns exit status. | Python `subprocess.Popen` with non-blocking stream readers, or `pty` (pseudo-terminal) for color preservation and interactive commands. |

---

## Recommended Project Structure

```
aishell/
├── pyproject.toml              # Project metadata, dependencies, entrypoints (cli: `aishell`)
├── README.md                   # User documentation and quickstart
└── src/
    └── aishell/
        ├── __init__.py         # Package version and export
        ├── main.py             # CLI entrypoint and argument parser (Click or Typer)
        ├── config/             # Configuration management
        │   ├── __init__.py
        │   ├── settings.py     # Pydantic Settings model (model choice, temperature, safety rules)
        │   └── loader.py       # YAML/TOML loader for ~/.aishell/config.yaml
        ├── core/               # Domain models and orchestrator
        │   ├── __init__.py
        │   ├── models.py       # Message, CommandProposal, ExecutionResult, SystemContext
        │   ├── orchestrator.py # Core conversation & execution state machine
        │   └── session.py      # Conversation session history persistence & compaction
        ├── context/            # Host environment inspection
        │   ├── __init__.py
        │   ├── collector.py    # Gathers OS, kernel, distro, CWD, git metadata
        │   ├── sanitizer.py    # Scrubbing secrets, API keys, passwords from env/context
        │   └── git_info.py     # Git status, diff summary, and current branch extractor
        ├── providers/          # Pluggable LLM interfaces
        │   ├── __init__.py
        │   ├── base.py         # Abstract BaseLLMProvider protocol
        │   ├── factory.py      # Provider resolver (reads config/flags to instantiate client)
        │   ├── gemini.py       # Google Gemini provider adapter
        │   ├── openai_compat.py# OpenAI and compatible providers (e.g., DeepSeek, Groq)
        │   ├── anthropic.py    # Anthropic Claude provider adapter
        │   └── ollama.py       # Ollama local HTTP provider adapter
        ├── execution/          # Command execution & safety checks
        │   ├── __init__.py
        │   ├── safety.py       # Risk classification engine & pattern heuristic database
        │   ├── executor.py     # Subprocess runner, streaming output capture, timeouts
        │   └── signals.py      # Signal handling (SIGINT forwarding, graceful cancellation)
        └── ui/                 # Terminal user interface
            ├── __init__.py
            ├── repl.py         # prompt_toolkit loop, history navigation, auto-suggestions
            ├── renderer.py     # Rich markdown, syntax highlighting, and layout cards
            └── prompts.py      # Confirmation prompts ([y/N], edit before run, explanation toggles)
```

### Structure Rationale

- **`src/aishell/core/`:** Houses the fundamental domain contracts (`models.py`) and central state machine (`orchestrator.py`). Isolating domain logic from UI allows thorough headless testing and potential alternate interfaces (e.g. one-shot CLI mode `aishell -c "fix nginx"` vs interactive REPL `aishell`).
- **`src/aishell/providers/`:** Completely decouples AI model vendors from the rest of the application. Adding or upgrading a provider (such as an updated Gemini SDK or Ollama endpoint) requires modifying only this package without touching REPL or execution logic.
- **`src/aishell/execution/`:** Keeps security checks and OS process spawning physically separated from UI and AI logic. This isolation ensures safety audits can focus exclusively on `safety.py` and `executor.py`.
- **`src/aishell/context/`:** Encapsulates all environmental probing. Crucially includes `sanitizer.py` to guarantee that secrets never leak into prompt payloads before reaching the `providers/` layer.
- **`src/aishell/ui/`:** Keeps terminal rendering and prompt handling distinct. If terminal dependencies update (e.g., Rich or prompt_toolkit updates), core execution logic remains untouched.

---

## Architectural Patterns

### Pattern 1: Pluggable Provider Strategy (Adapter Pattern)

**What:** Standardizes multiple LLM backends (Cloud APIs and local Ollama) behind an asynchronous protocol yielding standardized event streams.  
**When to use:** Crucial for `aishell` because users require both zero-setup cloud models (Gemini, OpenAI) and privacy-conscious local offline models (Ollama).  
**Trade-offs:** Constrains provider-specific features to the lowest common denominator or requires an extensible capability-flag dictionary.

**Example:**
```python
from abc import ABC, abstractmethod
from typing import AsyncIterator
from aishell.core.models import Message, LLMResponseChunk

class BaseLLMProvider(ABC):
    """Abstract interface for all model providers."""

    @abstractmethod
    async def stream_chat(
        self,
        messages: list[Message],
        system_instruction: str,
    ) -> AsyncIterator[LLMResponseChunk]:
        """Stream conversational output and structured command proposals."""
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Validate credentials or server reachability."""
        pass
```

---

### Pattern 2: Two-Phase Proposal-Confirmation-Execution Loop (Human-in-the-Loop Gatekeeper)

**What:** Separates the generation of a shell command from its execution via an explicit verification gate. The model can *propose* actions, but cannot invoke them without user approval.  
**When to use:** Mandatory for all CLI assistants capable of running commands to prevent data loss, security violations, or unintended system mutations.  
**Trade-offs:** Slightly slows down autonomous multi-step operations, but provides 100% safety and transparency.

**Example:**
```python
from enum import Enum
from pydantic import BaseModel

class RiskLevel(str, Enum):
    LOW = "LOW"             # e.g., ls, pwd, cat, git status
    MEDIUM = "MEDIUM"       # e.g., apt update, systemctl restart, git commit
    HIGH = "HIGH"           # e.g., rm -rf, dd, mkfs, iptables -F, > /dev/sdX

class CommandProposal(BaseModel):
    command: str
    explanation: str
    risk_level: RiskLevel
    suggested_cwd: str | None = None

class UserConfirmation(str, Enum):
    EXECUTE = "y"
    SKIP = "n"
    EDIT = "e"
    EXPLAIN = "x"
```

---

### Pattern 3: Streaming Subprocess Output with PTY / Non-blocking Pipes

**What:** Executes shell commands as asynchronous subprocesses, streaming standard output and error in real-time to the Rich renderer while monitoring for abort signals (Ctrl+C).  
**When to use:** Long-running commands (e.g., `apt-get upgrade`, `docker build`, `tail -f`) must not block the terminal UI or hide output until completion.  
**Trade-offs:** Raw subprocess pipes do not allocate a TTY by default, which can cause tools like `git diff` or `grep --color` to disable colors; using a pseudo-terminal (`pty`) restores colors but adds platform-specific complexity on POSIX systems.

**Example:**
```python
import asyncio
from typing import AsyncIterator

async def run_command_streaming(
    cmd: str, cwd: str, timeout_seconds: float = 300.0
) -> AsyncIterator[tuple[str, str]]:
    """Runs a shell command and yields ('stdout'|'stderr', text_chunk)."""
    proc = await asyncio.create_subprocess_shell(
        cmd,
        cwd=cwd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    async def read_stream(stream, stream_name):
        while line := await stream.readline():
            yield stream_name, line.decode(errors="replace")

    # Merge streams with real-time yielding
    # Ensures terminal shows progress immediately
```

---

### Pattern 4: Closed-Loop Diagnostic & Remediation Loop

**What:** When an executed command fails (non-zero exit code or stderr output), the orchestrator automatically packages the command, exit code, and captured stderr into a diagnostic payload and asks the model for an analysis and immediate fix.  
**When to use:** When troubleshooting failed builds, permission errors, missing packages, or syntax errors.  
**Trade-offs:** Increases token usage; must have a cycle threshold (e.g., max 3 auto-remediations) to prevent infinite loops on unfixable errors.

---

## Data Flow

### Request Flow

```
[User Input: "Find all ports listening on 8080 and stop the process"]
    │
    ▼
[REPL Interface (prompt_toolkit)]
    │ Captures string, checks for local built-ins (/exit, /clear, /model)
    ▼
[Agent Orchestrator]
    ├───► [Context Collector]
    │         Reads OS (Linux 6.8 Ubuntu 24.04), current user ($USER),
    │         active CWD, sanitizes environment variables
    │         Returns ContextSnapshot
    │
    ├───► [Prompt Formatter]
    │         Builds System Prompt + Context Snapshot + Chat History + User Query
    │
    ▼
[Model Client (e.g. Gemini / Ollama)]
    │ Streams response tokens (explanation + CommandProposal)
    ▼
[TUI Renderer (Rich)]
    │ Streams text explanation, formats code block: `lsof -i :8080 | awk 'NR>1 {print $2}' | xargs kill`
    ▼
[Safety Gatekeeper]
    │ Analyzes command syntax, flags as MEDIUM risk (process termination)
    ▼
[User Interactive Gate]
    │ Prompts: "Execute this command? [y/N/e/x]: "
    │ User inputs: 'y'
    ▼
[Shell Executor]
    │ Spawns subprocess in active CWD
    │ Streams stdout/stderr to TUI Renderer
    │ Captures exit code (e.g., code=0 or code=1)
    ▼
[Feedback Loop]
    ├── If exit == 0: Appends success to session history, returns to IDLE REPL
    └── If exit != 0: Formats error context into Orchestrator -> Model proposes diagnostic fix
```

---

### State Management

```
┌─────────────────────────────────────────────────────────────┐
│                       Session State                         │
│  ┌───────────────────────────────────────────────────────┐  │
│  │ Conversation History: list[Message]                   │  │
│  │ (User queries, Assistant explanations, Tool commands) │  │
│  ├───────────────────────────────────────────────────────┤  │
│  │ Context Cache: Last gathered host metadata & git state│  │
│  ├───────────────────────────────────────────────────────┤  │
│  │ Active Configuration: Active model, temp, safety mode │  │
│  ├───────────────────────────────────────────────────────┤  │
│  │ Execution Record: Last command, stdout, stderr, exit  │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

- **Persistence:** Saved locally in `~/.aishell/sessions/{session_id}.json` and `~/.aishell/history` for shell history navigation.
- **Window Management:** Sliding context window with token counting. Older turns are summarized or trimmed when context approaches model limits.

---

## Component Boundaries & Interfaces

### 1. REPL UI ↔ Agent Orchestrator
- **Communication:** Direct async call.
- **Contract:**
  ```python
  async def handle_user_input(
      user_text: str,
      session: SessionState,
      on_token_callback: Callable[[str], None],
  ) -> CommandProposal | None: ...
  ```
- **Boundary Rule:** The REPL UI never directly touches the LLM API or subprocess execution. It only renders what the Orchestrator emits and returns user choices.

### 2. Agent Orchestrator ↔ Context Collector
- **Communication:** Synchronous or fast async query.
- **Contract:**
  ```python
  def gather_system_context(cwd: str, redact_secrets: bool = True) -> SystemContext: ...
  ```
- **Boundary Rule:** The Context Collector is read-only. It gathers system facts (OS, distro, active user, git branch, directory listing) and runs zero mutations.

### 3. Agent Orchestrator ↔ Model Client
- **Communication:** Abstract interface (`BaseLLMProvider`).
- **Contract:**
  ```python
  async def stream_chat(
      messages: list[Message],
      system_instruction: str,
  ) -> AsyncIterator[LLMResponseChunk]: ...
  ```
- **Boundary Rule:** Core code never imports vendor SDKs (`google.genai`, `openai`, `anthropic`) directly. It only interacts with `BaseLLMProvider`.

### 4. Agent Orchestrator ↔ Safety Gate & Shell Executor
- **Communication:** Sequenced two-step dispatch.
- **Contract:**
  ```python
  def evaluate_risk(cmd: str) -> RiskAssessment: ...
  async def execute_command(
      cmd: str,
      cwd: str,
      on_output: Callable[[str, str], None],
  ) -> ExecutionResult: ...
  ```
- **Boundary Rule:** `execute_command` must reject any invocation that has not been approved through the explicit safety validation check.

---

## Safety & Sandboxing Architecture

Terminal AI assistants must treat generated code as untrusted input. The safety architecture comprises three defensive barriers:

1. **Environmental Sanitization (Pre-Inference):**
   - The Context Collector scans environment variables before assembling prompts.
   - Any key matching sensitive patterns (`*KEY*`, `*TOKEN*`, `*SECRET*`, `*PASS*`, `*AUTH*`, `*CREDENTIAL*`) is redacted to `[REDACTED]`.
   - Prevents accidental exfiltration of cloud credentials, SSH agent keys, or API tokens to external LLM providers.

2. **Heuristic Risk Analysis (Post-Inference, Pre-Confirmation):**
   - Commands are parsed and matched against a known risk database:
     - **BLOCKED / CRITICAL:** `rm -rf /`, `mkfs.*`, raw writes to `/dev/sd*`, fork bombs (`:(){ :|:& };:`), tampering with `/etc/sudoers`.
     - **HIGH RISK (Requires explicit typing confirmation):** Recursive deletes, modifying firewall rules (`ufw`, `iptables`), system reboot/shutdown, running unknown scripts downloaded from URLs (`curl ... | bash`).
     - **MEDIUM RISK (Standard `[y/N]` prompt):** Package installations (`apt install`, `pip install`), stopping system services (`systemctl stop`), git force push.
     - **LOW RISK (Quick confirmation):** Informational commands (`ls`, `ps`, `docker ps`, `grep`, `git status`).

3. **Subprocess Execution Boundaries:**
   - Command runs strictly under the invoking user's existing permissions (no automatic `sudo`). If `sudo` is needed, the user is explicitly warned and prompted.
   - Execution includes a hard timeout (default 300s, configurable) to prevent hung processes.
   - Proper process group creation allows clean termination of children processes on SIGINT (Ctrl+C).

---

## Suggested Build Order & Dependencies

The dependencies between components dictate the optimal implementation order:

```
┌──────────────────────────────────────────────┐
│  Phase 1: Foundation & Domain Models         │
│  - Core data classes (Message, Proposal, etc)│
│  - Configuration loader (~/.aishell/config)  │
└──────────────────────┬───────────────────────┘
                       │
       ┌───────────────┴───────────────┐
       ▼                               ▼
┌─────────────────────────────┐ ┌─────────────────────────────┐
│  Phase 2: Context Collector │ │  Phase 3: Model Clients     │
│  - OS/Distro/Git inspection │ │  - BaseProvider abstraction │
│  - Secret scrubber/sanitizer│ │  - Cloud & Local adapters   │
└──────────────┬──────────────┘ └──────────────┬──────────────┘
               │                               │
               └───────────────┬───────────────┘
                               ▼
┌──────────────────────────────────────────────┐
│  Phase 4: Safety Gate & Shell Executor       │
│  - Risk heuristic classifier                 │
│  - Streaming subprocess runner & signal traps│
└──────────────────────┬───────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────┐
│  Phase 5: Agent Orchestrator & Remediation   │
│  - Multi-turn conversation state machine     │
│  - Command extraction & error feedback loop  │
└──────────────────────┬───────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────┐
│  Phase 6: Interactive REPL UI & TUI Polish   │
│  - prompt_toolkit input loop & history       │
│  - Rich streaming Markdown & confirmation UI │
└──────────────────────────────────────────────┘
```

### Build Order Rationale

1. **Phase 1: Foundation & Models:** Defining domain contracts first ensures all subsequent modules share identical data types (`Message`, `CommandProposal`, `ExecutionResult`), preventing costly refactors.
2. **Phase 2 & Phase 3 (Parallelizable):** `Context Collector` and `Model Client Engine` have zero dependencies on each other. Both can be built and tested independently using simple unit tests.
3. **Phase 4: Safety & Executor:** Building execution in isolation guarantees that process handling, signal management, and safety barriers work reliably before tying them to AI generation.
4. **Phase 5: Orchestrator:** Connects context gathering, model streaming, and command execution into an integrated multi-turn workflow with automated error remediation.
5. **Phase 6: REPL UI:** The terminal interface is built last on top of an already verified, end-to-end operational orchestrator. This allows testing all core logic headlessly before adding prompt_toolkit keybindings and Rich animations.

---

## Scaling Considerations

While `aishell` is a single-user CLI application rather than a distributed cloud service, it faces unique local resource and terminal scaling bottlenecks:

| Scale Factor | Bottleneck | Mitigation Strategy |
|--------------|------------|---------------------|
| **Multi-turn History** | Session context grows to 50k+ tokens; latency and API cost increase. | Implement a sliding window memory policy: keep recent 10 turns in full fidelity; summarize earlier turns into a compact context header. |
| **Voluminous Command Output** | A command dumps 100,000 lines (e.g. `cat huge.log` or verbose compiler output) causing terminal lag or LLM context blowout. | The Shell Executor caps captured stdout buffer (e.g. max 100KB / last 200 lines) sent to the LLM context, while streaming full output to the terminal screen. |
| **Local Model Latency** | Running local 7B+ models via Ollama on lower-spec hardware has high time-to-first-token. | Implement streaming token rendering immediately upon first chunk receipt; display animated progress spinners during prompt evaluation. |

---

## Anti-Patterns to Avoid

### 1. Autonomous Non-Confirmed Execution ("YOLO Mode by Default")
- **What people do:** Allowing the AI model to directly execute any bash command it generates without pausing for human verification.
- **Why it's wrong:** LLMs regularly hallucinate command flags, mistake directories, or output destructive commands (e.g., executing `rm -rf *` in the wrong folder).
- **Do this instead:** Human-in-the-loop confirmation is an immutable default. Commands must be displayed clearly with risk indicators and require explicit key confirmation (`[y/N]`).

### 2. God Orchestrator Mixing UI and Business Logic
- **What people do:** Writing the REPL loop, prompt_toolkit keybindings, LLM HTTP calls, and subprocess execution in a single giant monolithic script.
- **Why it's wrong:** Makes unit testing impossible, prevents adding alternative CLI subcommands (like a one-shot `aishell exec "..."`), and creates tight coupling.
- **Do this instead:** Keep the UI strictly as a presentation layer (`ui/`), orchestrator as the state coordinator (`core/`), and providers as swappable plugins (`providers/`).

### 3. Leaking Host Secrets in Prompt Payloads
- **What people do:** Dumping `os.environ` entirely into the LLM system prompt so the model knows the environment.
- **Why it's wrong:** Exposes AWS keys, GitHub tokens, database passwords, and personal credentials to remote LLM API providers.
- **Do this instead:** Strict sanitization whitelist/blacklist filter in `Context Collector` that scrubs all credential patterns before prompt construction.

---

## Integration Points

### External Services
| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| **Google Gemini API** | `google-genai` SDK or HTTP REST streaming | High speed, large context window, excellent reasoning on Linux tooling. |
| **OpenAI / Anthropic** | Official Python SDKs (`openai`, `anthropic`) | Standard chat completion streaming protocol. |
| **Ollama Local API** | Local HTTP REST (`http://localhost:11434/api/chat`) | Full offline capability, zero data leaves machine, supports Llama 3/Mistral/Qwen. |

### Internal Boundaries
| Boundary | Communication Pattern | Notes |
|----------|-----------------------|-------|
| **REPL UI ↔ Orchestrator** | Asynchronous method calls with streaming callbacks | Ensures terminal UI remains responsive during long API streams or command execution. |
| **Orchestrator ↔ Subprocess** | Async `asyncio.subprocess` with stream reader tasks | Isolates host processes from python runtime; enables graceful Ctrl+C cancellation. |
| **Orchestrator ↔ Storage** | JSON files in user home directory (`~/.aishell/`) | Stores history, preferences, and session logs without requiring a heavy SQL database. |

---

## Sources

- [Open Interpreter Architecture](https://github.com/OpenInterpreter/open-interpreter) (HIGH confidence) — Standard reference for terminal code execution and human confirmation gates.
- [Shell-GPT Architecture](https://github.com/TheR1D/shell_gpt) (HIGH confidence) — Clean CLI pattern for shell command generation, execution, and error diagnostics.
- [Aider Architecture](https://github.com/paul-gauthier/aider) (HIGH confidence) — Best practices for git context extraction, prompt engineering, and terminal streaming.
- [Python prompt_toolkit Documentation](https://python-prompt-toolkit.readthedocs.io/) (HIGH confidence) — Industry standard for advanced terminal REPLs and keyboard event handling.
- [Rich Terminal Formatting](https://rich.readthedocs.io/) (HIGH confidence) — Standard for terminal Markdown rendering, syntax highlighting, and progress live-displays.

---
*Architecture research for: Linux AI Console Assistant (aishell)*  
*Researched: 2026-11-16*
