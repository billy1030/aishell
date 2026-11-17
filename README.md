# Terminal AI Shell (`aishell`)

An interactive, system-aware Linux AI console assistant and REPL designed for developers and sysadmins. It bridges natural language intent with Linux terminal operations by generating and explaining shell commands, gathering local system context, and safely running commands with mandatory human confirmation.

---

## Key Features

- **Managed Pseudo-Terminal (PTY):** Real-time command execution with full terminal fidelity, ANSI escape sequence handling, and interactive process management.
- **State Synchronization:** Eliminates subshell amnesia by synchronizing directory changes (`cd`) and environment variable operations (`export`, `unset`) in the parent session.
- **Deterministic Safety Gate:** Commands are evaluated before execution and categorized by blast-radius:
  - `[READ_ONLY]` (Green) — Safe observation commands (`ls`, `ps`, `cat`).
  - `[MUTATING]` (Yellow) — State-changing commands (`mkdir`, `systemctl restart`).
  - `[HIGH_RISK]` (Red) — Destructive operations, file deletions (`rm -rf`), and privilege escalation (`sudo`).
  - Interactive `[y/N/e]` human gate with inline command editing before running.
- **Privacy & Prompt Injection Defense:**
  - Automated credential redaction (`PrivacyGuard`) strips API tokens, private keys, and passwords before sending prompts to the AI provider.
  - Untrusted system metadata and command outputs are enclosed in `<context untrusted="true">` blocks.
- **Self-Healing & Diagnostics:** Non-zero command exit codes trigger root-cause analysis and automated remediation suggestions, strictly capped to a 2-cycle recovery loop (user `Ctrl+C` / SIGINT 130 is ignored).
- **Conversational Memory:** Multi-turn conversational memory with sliding-window compaction preserves context without token explosion.
- **Multi-Provider Architecture:** Pluggable adapters supporting Google Gemini, OpenAI, Anthropic Claude, Local Ollama, and OpenAI-compatible endpoints (MiniMax, Groq, DeepSeek, vLLM).

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

### Configuration Examples

#### 1. MiniMax (China & Global)
```toml
[general]
default_provider = "openai"
model = "MiniMax-M3.1-Flash"

[providers.openai]
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

#### 3. Google Gemini
```toml
[general]
default_provider = "gemini"
model = "gemini-2.0-flash"

[providers.gemini]
api_key = "AIzaSy-your-gemini-key-here"
```

#### 4. Anthropic Claude
```toml
[general]
default_provider = "claude"
model = "claude-3-5-sonnet-20241022"

[providers.anthropic]
api_key = "sk-ant-your-claude-key-here"
```

#### 5. Local & Offline (Ollama)
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

- Type your natural language query: `find listening ports and what process owns them`
- Review the proposed command, risk category, and explanation.
- Choose:
  - `y` — Execute immediately.
  - `N` — Cancel.
  - `e` — Edit command inline before running.
- **Built-in Slash Commands:**
  - `:help` — Show available commands.
  - `:context` — Inspect system environment, detected OS, and host telemetry.
  - `:history` — View SQLite command audit trail.
  - `:clear` — Reset conversational memory.
  - `:exit` or `Ctrl+D` — Exit the shell.

### 2. One-Shot Query Mode
Generate, confirm, and execute commands in a single command line call:
```bash
aishell -c "show top 5 memory consuming processes"
```

You can also specify a provider or model on the fly:
```bash
aishell -c "list all failed systemd units" --provider openai --model MiniMax-M3.1-Flash
```

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

# Run test suite (181 tests)
uv run pytest
```

---

## License

MIT License.
