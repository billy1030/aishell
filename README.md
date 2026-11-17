# Terminal AI Shell (`aishell`)

<a href="https://buymeacoffee.com/billy1030" target="_blank"><img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" alt="Buy Me A Coffee" height="50"></a>

An interactive, system-aware Linux AI console assistant and REPL designed for developers and sysadmins. It bridges natural language intent with Linux terminal operations by generating and explaining shell commands, gathering local system context, and safely running commands with mandatory human confirmation.

![Terminal AI Shell Demo](docs/assets/demo-v2.jpg)

---

## Key Features

- **Managed Pseudo-Terminal (PTY):** Real-time command execution with full terminal fidelity, ANSI escape sequence handling, and interactive process management.
- **State Synchronization:** Eliminates subshell amnesia by synchronizing directory changes (`cd`) and environment variable operations (`export`, `unset`) in the parent session.
- **Autonomous Agentic Loop & AI Skills:**
  - Multi-step autonomous execution up to `max_agent_steps` (default `100`): `aishell` runs an approved command or MCP tool, ingests `<command_output>` / `<mcp_output>`, and continues reasoning until the task is complete.
  - Hierarchical AI Skills (`project` > `user` > `builtin`) with built-in `@repo-study`, `@web-search`, `@web-fetch`, `@find-skills`, `@systemd-triage`, `@docker-debug`, and `@network-audit`. Use `:skills`, `:findskills <query>`, or `:skills reload` to manage skills.
  - Pre-approved read-only skills (`@web-search`, `@web-fetch`) and interactive session/permanent skill auto-approval (`[y=this session / p=permanent / N=ask each time]`).
- **Model Context Protocol (MCP):**
  - Lightweight `stdio` MCP client reading `~/.config/aishell/mcp.json`. Use `:mcp` / `:mcp reload` to inspect and refresh connected servers and tools.
- **Bash-Style Tab Autocompletion & Rich UI:**
  - Press `Tab` to complete file/directory paths, `@skill-name`, `:skills` / `:mcp` / `:autorun` / `:save` / `:export` / `:resume` / `/context` meta commands, aliases, and Linux shell commands (`Escape` closes the completion menu).
  - Prompt displays current directory and Git branch/dirty status (`aishell:~/repo (main*) $ `).
  - `AI Assistant` bordered panel with condensed 2-line `<think>` streaming and `Ctrl+Z` / `Ctrl+D` / `:exit` clean exit.
- **Shell Aliases, Autorun & Session Tools:**
  - Built-in aliases (`ll`, `la`, `l`, `..`, `alias`, `unalias`) plus automatic import from `~/.bash_aliases` and `~/.bashrc`.
  - Optional `auto_approve_safe = true` (or `:autorun safe|off`) to auto-run `[SAFE]` read-only commands while still gating `[MODIFIES SYSTEM]` and `[HIGH-RISK]`.
  - `:skills install <url|owner/repo@skill>` and `:skills create <name>` to manage custom skills; `:save file.md`, `:export script.sh`, and `:resume` to export or restore sessions.
- **Deterministic Safety Gate:** Commands are evaluated before execution and categorized by blast-radius:
  - `[READ_ONLY]` (Green) — Safe observation commands (`ls`, `ps`, `cat`).
  - `[MUTATING]` (Yellow) — State-changing commands (`mkdir`, `systemctl restart`).
  - `[HIGH_RISK]` (Red) — Destructive operations, file deletions (`rm -rf`), and privilege escalation (`sudo`).
  - Interactive `[y=run / a=all / N=cancel / e=edit]` human gate with inline command editing and per-task `a=all` approval.
- **Privacy & Prompt Injection Defense:**
  - Automated credential redaction (`PrivacyGuard`) strips API tokens, private keys, and passwords before sending prompts to the AI provider.
  - Untrusted system metadata and command outputs are enclosed in `<context untrusted="true">` blocks.
- **Self-Healing & Diagnostics:** Non-zero command exit codes trigger root-cause analysis and automated remediation suggestions, strictly capped to a 2-cycle recovery loop (user `Ctrl+C` / SIGINT 130 is ignored).
- **Interactive REPL & Clean Prompt:** Multiline input with vi/emacs bindings, syntax highlighting, history search (`Ctrl+R`), and a clean standard prompt:
  - `aishell $ ` for regular users
  - `aishell # ` for root users
- **Multi-Provider Architecture:** Pluggable adapters supporting MiniMax, Google Gemini, OpenAI, Anthropic Claude, Local Ollama, and any custom OpenAI-compatible endpoint (DeepSeek, Groq, vLLM).

---

## Installation

### Ubuntu / Debian (Bare Metal, VPS, or Desktop)

Ubuntu 24.04+ manages Python packages via PEP 668. We recommend installing `aishell` in an isolated environment using **`pipx`**:

```bash
# 1. Install prerequisites
sudo apt update && sudo apt install -y python3 python3-pip pipx git curl

# 2. Ensure ~/.local/bin is in your PATH
pipx ensurepath
source ~/.bashrc

# 3. Install aishell from GitHub
pipx install git+https://github.com/billy1030/aishell.git
```

### Windows Subsystem for Linux (WSL)

Inside your WSL terminal (e.g. Ubuntu):

```bash
sudo apt update && sudo apt install -y pipx git
pipx ensurepath
source ~/.bashrc
pipx install git+https://github.com/billy1030/aishell.git
```

You can then run `aishell` inside WSL or launch it directly from Windows PowerShell:
```powershell
wsl aishell
```

---

## REPL Commands & Triggers (`:` & `?`)

- **`:` Meta Commands** (also works with `/`):
  - `:help` — Show REPL shortcuts and commands
  - `:skills` / `:findskills <query>` / `:skills install <spec>` / `:skills create <name>` / `:skills reload`
  - `:mcp` / `:mcp reload` — List or reload MCP servers and tools
  - `:autorun safe` / `:autorun off` — Toggle auto-running `[SAFE]` read-only commands
  - `:history [N]` — Show last `N` commands (or press `Alt+H`)
  - `:save file.md` / `:export script.sh` / `:resume` — Save, export, or restore your session
  - `:context` / `:clear` / `:exit` (or `Ctrl+D` / `Ctrl+Z`)
- **`?` Force AI Query**: Prefix with `?` (e.g. `? ls -la`) to ask the AI instead of running the command directly. You can also wake the AI with `@skill-name` or `ai_triggers` (`hi`, `please`, `ais`, `ai`, `help`).

### Complex Multi-Step Task Examples

- **Repo Study (`@repo-study`)**:
  ```text
  @repo-study clone https://github.com/elie222/rakazo into /tmp/rakazo, inspect its package manifests and entrypoints, and summarize the architecture and how to run it locally
  ```
- **Full System & Service Audit (`@systemd-triage` + `@network-audit`)**:
  ```text
  ? audit this server: check disk usage, memory/CPU load, failed systemd units, and all listening ports, then give me a prioritized summary of any issues
  ```
- **Docker + Logs Investigation (`@docker-debug`)**:
  ```text
  @docker-debug inspect all running and exited containers, check the last 50 log lines of any unhealthy or recently restarted container, and diagnose the root cause
  ```

---

## Configuration

`aishell` loads configuration with layered precedence:
1. CLI flags (`--provider`, `--model`)
2. Environment variables (`AISHELL_*`, `OPENAI_API_KEY`, `GEMINI_API_KEY`, `ANTHROPIC_API_KEY`)
3. `~/.config/aishell/config.toml`

### Setup `config.toml`

Copy the provided template to your home configuration directory:

```bash
mkdir -p ~/.config/aishell
cp config.example.toml ~/.config/aishell/config.toml
chmod 600 ~/.config/aishell/config.toml
```

### Configuration Parameters

| Section | Parameter | Default | Description |
| --- | --- | --- | --- |
| `[general]` | `default_provider` | `"ollama"` | Active AI provider (`minimax`, `openai`, `gemini`, `anthropic`, `ollama`, or custom) |
| `[general]` | `model` | `"qwen2.5-coder:7b"` | Model name or endpoint identifier |
| `[general]` | `theme` | `"dark"` | Terminal theme (`dark` or `light`) |
| `[general]` | `max_agent_steps` | `100` | Maximum autonomous agent loop steps per goal |
| `[general]` | `system_prompt` | `None` | Optional custom system prompt appended to assistant instructions |
| `[general]` | `ai_triggers` | `["hi", "hello", "hey", "please", "ais", "ai", "help"]` | Keywords/prefixes that wake the AI assistant (plus `?` and `@skill`) |
| `[general]` | `auto_approve_safe` | `false` | Automatically execute `[SAFE]` read-only commands without prompting |
| `[execution]` | `timeout_seconds` | `300.0` | Process execution timeout in seconds |
| `[execution]` | `max_output_buffer_kb` | `50` | Maximum in-memory output buffer (KB) |
| `[execution]` | `ring_buffer_lines` | `1000` | Maximum in-memory output lines retained |
| `[storage]` | `history_db_path` | `~/.local/state/aishell/history.db` | Path to SQLite command history database |
| `[storage]` | `max_history_records` | `10000` | FIFO history retention limit |
| `[providers.<name>]` | `api_key` | `None` | Provider API key or token |
| `[providers.<name>]` | `base_url` | `None` | Custom OpenAI-compatible endpoint base URL |

### Configuration Examples

#### 1. MiniMax (China & Global)
```toml
[general]
default_provider = "minimax"
model = "MiniMax-M3.1-Flash"

[providers.minimax]
# For Mainland China (platform.minimaxi.com):
base_url = "https://api.minimaxi.com/v1"
# For Global (platform.minimax.io):
# base_url = "https://api.minimax.io/v1"
api_key = "your-minimax-api-key-here"
```

#### 2. OpenAI (GPT-4o / o3-mini)
```toml
[general]
default_provider = "openai"
model = "gpt-4o"

[providers.openai]
api_key = "sk-proj-your-openai-key-here"
```

#### 3. Any Custom OpenAI-Compatible Provider (DeepSeek, Groq, etc.)
```toml
[general]
default_provider = "deepseek"
model = "deepseek-chat"

[providers.deepseek]
base_url = "https://api.deepseek.com/v1"
api_key = "sk-your-deepseek-key-here"
```

#### 4. Google Gemini
```toml
[general]
default_provider = "gemini"
model = "gemini-2.0-flash"

[providers.gemini]
api_key = "AIzaSy-your-gemini-key-here"
```

#### 5. Anthropic Claude
```toml
[general]
default_provider = "claude"
model = "claude-3-5-sonnet-20241022"

[providers.anthropic]
api_key = "sk-ant-your-claude-key-here"
```

#### 6. Local & Offline (Ollama)
```toml
[general]
default_provider = "ollama"
model = "qwen2.5-coder:7b"

[providers.ollama]
base_url = "http://localhost:11434/v1"
```

---

## Usage

### 1. Interactive REPL Mode
Launch the full interactive console:
```bash
aishell
```

At the prompt:
```text
# Standard Linux commands run directly without waking AI:
aishell $ ls -la
aishell $ df -h

# Wake up AI using 'ais', 'please', 'hi,', '?' or natural language questions:
aishell $ ais find listening ports and what process owns them
aishell $ please check why nginx failed
```

- While waiting for the AI response, an animated `Thinking...` indicator is shown.
- Review the proposed command, risk category, and explanation.
- At **`Execute command? [y=run / N=cancel / e=edit]:`**, choose:
  - `y` — Execute immediately (output is captured into AI context for follow-ups).
  - `N` (or `Enter`) — Cancel safely.
  - `e` — Edit command inline before running.
- **Built-in Slash Commands:**
  - `:help` — Show available commands.
  - `:context` — Inspect system environment, detected OS, and host telemetry.
  - `:history` — View SQLite command audit trail.
  - `:clear` — Reset conversational memory.
  - `:exit` or `Ctrl+D` — Exit the shell cleanly.

### 2. One-Shot Query Mode
Generate, confirm, and execute commands in a single command line call:
```bash
aishell -c "show top 5 memory consuming processes"
```

You can also specify a provider or model on the fly:
```bash
aishell -c "list all failed systemd units" --provider minimax --model MiniMax-M3.1-Flash
```

---

## Updating Deployment

To update your existing Ubuntu installation to the latest version on GitHub:

```bash
pipx install --force git+https://github.com/billy1030/aishell.git
```
This updates the binary while preserving your `~/.config/aishell/config.toml` configuration and history log.

### Running as `root` (`su` / `sudo`)

If you installed `aishell` via `pipx` under a non-root user and want to run it after `su` or `sudo -i`:

```bash
sudo ln -sf "$HOME/.local/bin/aishell" /usr/local/bin/aishell
sudo mkdir -p /root/.config/aishell
sudo cp "$HOME/.config/aishell/config.toml" /root/.config/aishell/config.toml
sudo chmod 600 /root/.config/aishell/config.toml
```

---

## Documentation & Architecture

For full module architecture, input routing rules, security layers, and async lifecycle details, see [Technical Documentation](docs/TECH_DOCS.md).

---

## Audit Logs & Privacy

- All executed commands, exit codes, durations, and output previews are logged in an ACID-compliant local database:
  `~/.local/state/aishell/history.db`
- Sensitive values like passwords, API keys, and environment secrets are masked before ever touching an LLM prompt.

---

## Development & Testing

```bash
# Clone the repository
git clone https://github.com/billy1030/aishell.git
cd aishell

# Set up virtual environment and install dependencies
uv venv
source .venv/bin/activate
uv pip install -e ".[test]"

# Run test suite (184 tests)
uv run pytest
```

---

## Disclaimer

This software is provided **for study and educational purposes only**. It is provided "as is", without warranty of any kind, express or implied. The authors and contributors accept **no liability** for any damages, data loss, system changes, or unintended command executions resulting from the use of this tool. Always review AI-proposed commands carefully before approving execution.

---

## License

MIT License.
