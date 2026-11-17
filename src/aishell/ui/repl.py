"""Interactive REPL session using prompt_toolkit and Rich."""

import os
import re
import shutil
import sys
import time
import uuid
from typing import Callable, Iterable, List, Optional, Tuple
from prompt_toolkit import PromptSession
from prompt_toolkit.completion import Completer, Completion, PathCompleter, WordCompleter, merge_completers
from prompt_toolkit.filters import has_focus
from prompt_toolkit.formatted_text import to_formatted_text
from prompt_toolkit.key_binding import KeyBindings
from rich.console import Console
from rich.panel import Panel

from aishell.config.settings import AishellSettings, get_settings
from aishell.conversation.manager import ConversationManager
from aishell.diagnostics.engine import DiagnosticEngine
from aishell.diagnostics.remediation import RemediationController
from aishell.mcp.client import MCPManager
from aishell.mcp.schema import extract_mcp_call_from_text
from aishell.providers.base import BaseProvider
from aishell.safety.gate import SafetyGate
from aishell.skills.manager import SkillManager
from aishell.ui.banner import format_prompt, get_prompt_style, render_banner
from aishell.ui.history import SQLiteHistory
from aishell.ui.renderer import RichStreamRenderer


class AishellCompleter(Completer):
    """Bash-style Tab completer for paths, meta commands, @skills, and shell commands."""

    _META_COMMANDS = (
        ":exit", ":quit", ":help", ":clear", ":context", ":skills", ":skills reload", ":findskills", ":mcp", ":mcp reload",
        "/exit", "/quit", "/help", "/clear", "/context", "/skills", "/skills reload", "/findskills", "/mcp", "/mcp reload",
        "/provider", "/model",
    )

    def __init__(self, skill_manager: SkillManager, shell_commands: frozenset[str]) -> None:
        self.skill_manager = skill_manager
        self.shell_commands = shell_commands
        self.path_completer = PathCompleter(expanduser=True)

    def get_completions(self, document, complete_event):
        text = document.text_before_cursor
        stripped = text.lstrip()

        # 1. Meta commands (:skills, /context, etc.)
        if stripped.startswith((":", "/")) and " " not in stripped:
            for cmd in self._META_COMMANDS:
                if cmd.startswith(stripped):
                    yield Completion(cmd, start_position=-len(stripped))
            return

        # 2. @skill-name completion
        word = document.get_word_before_cursor(WORD=True)
        if word.startswith("@"):
            prefix = word[1:].lower()
            for skill in self.skill_manager.list_skills():
                if skill.name.lower().startswith(prefix):
                    yield Completion(f"@{skill.name}", start_position=-len(word))
            return

        # 3. First-token shell command completion (when not a path)
        if " " not in stripped and not stripped.startswith((".", "/", "~")):
            for cmd in sorted(self.shell_commands):
                if cmd.startswith(stripped):
                    yield Completion(cmd, start_position=-len(stripped))

        # 4. File & directory path completion (like Bash)
        yield from self.path_completer.get_completions(document, complete_event)


class InteractiveREPL:
    """Interactive shell assistant and command REPL.

    Provides multiline input, SQLite history search (Ctrl+R), styled status prompts,
    safe stream interrupt routing (Ctrl+C), and execution dispatch per REPL-01, REPL-02, REPL-04.
    """

    def __init__(
        self,
        settings: Optional[AishellSettings] = None,
        console: Optional[Console] = None,
        history: Optional[SQLiteHistory] = None,
        executor_fn: Optional[Callable[[str], int]] = None,
        provider_name: Optional[str] = None,
        model_name: Optional[str] = None,
        provider: Optional[BaseProvider] = None,
        skill_manager: Optional[SkillManager] = None,
        mcp_manager: Optional[MCPManager] = None,
        max_agent_steps: Optional[int] = None,
        pt_input=None,
        pt_output=None,
    ) -> None:
        self.settings = settings or get_settings()
        self.console = console or Console()
        self.session_id = str(uuid.uuid4())[:8]
        self.history = history or SQLiteHistory(session_id=self.session_id)
        self.safety_gate = SafetyGate(console=self.console)
        self.renderer = RichStreamRenderer(console=self.console)
        self.executor_fn = executor_fn
        self.skill_manager = skill_manager or SkillManager()
        self.mcp_manager = mcp_manager or MCPManager()
        self._session_approved_skills: set[str] = set()
        self.max_agent_steps = max(
            1,
            max_agent_steps
            if max_agent_steps is not None
            else getattr(self.settings.general, "max_agent_steps", 6),
        )

        from aishell.providers.factory import get_provider

        if provider:
            self.provider = provider
        else:
            p_name = provider_name or self.settings.general.default_provider
            m_name = model_name or self.settings.general.model
            self.provider = get_provider(
                name=p_name,
                model=m_name,
                settings=self.settings,
                validate=False,
            )

        self.conversation = ConversationManager()
        self.diagnostic_engine = DiagnosticEngine(provider=self.provider)
        self.remediation_controller = RemediationController()

        self.last_interrupt_time: float = 0.0
        self.is_streaming: bool = False
        self.kb = self._create_keybindings()
        self.completer = AishellCompleter(self.skill_manager, self._DIRECT_SHELL_COMMANDS)

        try:
            self.session: PromptSession = PromptSession(
                history=self.history,
                key_bindings=self.kb,
                completer=self.completer,
                complete_while_typing=False,
                style=get_prompt_style(),
                multiline=True,
                enable_history_search=True,
                input=pt_input,
                output=pt_output,
            )
        except Exception:
            from prompt_toolkit.output import DummyOutput

            self.session = PromptSession(
                history=self.history,
                key_bindings=self.kb,
                completer=self.completer,
                complete_while_typing=False,
                style=get_prompt_style(),
                multiline=True,
                enable_history_search=True,
                input=pt_input,
                output=DummyOutput(),
            )

    def _trigger_remediation(self, command: str, exit_code: int, output: str) -> int:
        """Trigger bounded remediation loop on command failure."""
        self.diagnostic_engine._provider = self.provider

        runner = self.executor_fn
        if runner is None:
            from aishell.cli import execute_pipeline
            runner = lambda c: execute_pipeline(c, session_id=self.session_id)

        return self.remediation_controller.run_remediation_loop(
            failed_command=command,
            exit_code=exit_code,
            output=output,
            diagnostic_engine=self.diagnostic_engine,
            safety_gate=self.safety_gate,
            executor_fn=runner,
            console=self.console,
            prompt_session=self.session,
        )

    def _execute_with_remediation(self, command: str) -> int:
        """Execute command and trigger remediation loop if it terminates with non-zero exit code."""
        if self.executor_fn:
            try:
                res = self.executor_fn(command)
            except Exception as exc:
                self.renderer.render_error(str(exc))
                res = 1
        else:
            from aishell.cli import execute_pipeline_capture
            res = execute_pipeline_capture(command, session_id=self.session_id)

        exit_code = 0
        output = ""
        if isinstance(res, tuple) and len(res) == 2:
            exit_code, output = res
        elif isinstance(res, int):
            exit_code = res
            output = f"Command exited with code {exit_code}"

        self._last_execution = (command, exit_code, output)
        first_cmd = command.strip().split()[0].lower() if command.strip() else ""
        if exit_code != 0 and exit_code != 130 and first_cmd not in self._INTERACTIVE_NO_REMEDIATE:
            return self._trigger_remediation(command, exit_code, output)
        return exit_code

    def _create_keybindings(self) -> KeyBindings:
        """Configure multiline keybindings per D-02: Enter executes, Alt+Enter / `\\` newline."""
        kb = KeyBindings()

        @kb.add("escape", "enter")
        @kb.add("c-j")
        def _insert_newline(event):
            """Insert a newline buffer on Alt+Enter or Ctrl+J."""
            event.current_buffer.insert_text("\n")

        from prompt_toolkit.filters import is_searching

        @kb.add("enter", filter=~is_searching)
        def _handle_enter(event):
            """Submit on Enter unless line ends with trailing backslash."""
            buf = event.current_buffer
            text = buf.text
            # If buffer ends with trailing backslash, replace it with newline
            if text.endswith("\\"):
                buf.delete_before_cursor(count=1)
                buf.insert_text("\n")
            else:
                buf.validate_and_handle()

        @kb.add("c-z")
        def _exit_on_ctrl_z(event):
            """Exit aishell cleanly on Ctrl+Z."""
            event.app.exit(exception=EOFError())

        return kb

    def get_prompt_tokens(self) -> list:
        """Return clean prompt tokens: 'aishell $ ' or 'aishell # '."""
        return format_prompt()

    def handle_meta_command(self, cmd: str) -> bool:
        """Handle internal meta commands (:exit, :quit, /clear, /help, /provider, /model).

        Returns True if REPL should terminate, False otherwise.
        """
        parts = cmd.strip().split(maxsplit=1)
        action = parts[0].lower()
        arg = parts[1].strip() if len(parts) > 1 else None

        if action in (":exit", ":quit", "/exit", "/quit", "exit", "quit"):
            return True
        elif action in (":clear", "/clear", "clear"):
            self.console.clear()
            self.conversation.clear()
            return False
        elif action in (":help", "/help", "help"):
            self._print_help()
            return False
        elif action in (":provider", "/provider", "provider"):
            from aishell.providers.factory import get_provider, get_supported_providers

            if arg:
                try:
                    self.provider = get_provider(name=arg, settings=self.settings, validate=False)
                    self.diagnostic_engine._provider = self.provider
                    self.console.print(f"[green]Switched active provider to '{self.provider.name}' (model: {self.provider.model})[/green]")
                except Exception as exc:
                    self.renderer.render_error(str(exc))
            else:
                supported = ", ".join(get_supported_providers())
                self.console.print(f"[bold cyan]Active provider:[/bold cyan] {self.provider.name} (model: {self.provider.model})\n[dim]Supported: {supported}[/dim]")
            return False
        elif action in (":model", "/model", "model"):
            from aishell.providers.factory import get_provider

            if arg:
                try:
                    self.provider = get_provider(
                        name=self.provider.name,
                        model=arg,
                        settings=self.settings,
                        validate=False,
                    )
                    self.diagnostic_engine._provider = self.provider
                    self.console.print(f"[green]Switched model to '{self.provider.model}' on provider '{self.provider.name}'[/green]")
                except Exception as exc:
                    self.renderer.render_error(str(exc))
            else:
                self.console.print(f"[bold cyan]Active model:[/bold cyan] {self.provider.model} (provider: {self.provider.name})")
            return False
        elif action in (":context", "/context", "context"):
            from aishell.context.display import render_context_table
            from aishell.context.inspector import inspect_system_context

            ctx_info = inspect_system_context(cwd=os.getcwd())
            render_context_table(ctx_info, console=self.console)
            return False
        elif action in (":skills", "/skills", "skills"):
            if arg and arg.lower() == "reload":
                self.skill_manager.reload()
                self.console.print("[green]Reloaded AI skills.[/green]")
                self._print_skills_table()
            else:
                self._print_skills_table(filter_query=arg)
            return False
        elif action in (":findskills", "/findskills", "findskills"):
            self._print_skills_table(filter_query=arg)
            return False
        elif action in (":mcp", "/mcp", "mcp"):
            if arg and arg.lower() == "reload":
                self.mcp_manager.reload_config()
                self._discover_mcp_tools_sync()
                self.console.print("[green]Reloaded MCP servers and tools.[/green]")
            elif not self.mcp_manager.tools and self.mcp_manager.servers:
                self._discover_mcp_tools_sync()
            self._print_mcp_table()
            return False
        return False

    def _discover_mcp_tools_sync(self) -> None:
        """Synchronously discover tools from configured MCP servers."""
        import asyncio

        try:
            loop = asyncio.get_event_loop()
            if loop.is_closed():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        try:
            loop.run_until_complete(self.mcp_manager.discover_tools())
        except Exception as exc:
            self.renderer.render_error(f"MCP discovery error: {exc}")

    def _print_mcp_table(self) -> None:
        """Render configured MCP servers and discovered tools."""
        from rich.table import Table

        if not self.mcp_manager.servers:
            self.console.print(
                f"[yellow]No MCP servers configured.[/yellow] Create [cyan]{self.mcp_manager.config_path}[/cyan] "
                'with {"mcpServers": {...}} and run [bold]:mcp reload[/bold].'
            )
            return

        table = Table(title="MCP Servers & Tools", border_style="cyan")
        table.add_column("Server", style="bold cyan")
        table.add_column("Tool", style="bold green")
        table.add_column("Description", style="white")

        tools_by_server = {}
        for t in self.mcp_manager.tools:
            tools_by_server.setdefault(t.server, []).append(t)

        for name, cfg in self.mcp_manager.servers.items():
            srv_tools = tools_by_server.get(name, [])
            if not srv_tools:
                status = "disabled" if not cfg.enabled else "no tools discovered"
                table.add_row(name, f"[dim]({status})[/dim]", f"{cfg.command} {' '.join(cfg.args)}")
            else:
                for t in srv_tools:
                    table.add_row(name, t.name, t.description[:80])

        self.console.print(table)

    def _check_skill_approvals(self, matched_skills) -> bool:
        """Ask whether matched skills should auto-approve commands for this session or permanently."""
        if not matched_skills:
            return False

        from aishell.safety.gate import is_interactive_stdin

        permanent = self.skill_manager.load_approved_skills()
        all_approved = True

        for skill in matched_skills:
            s_key = skill.name.lower()
            if s_key in permanent or s_key in self._session_approved_skills:
                continue

            if not is_interactive_stdin():
                all_approved = False
                continue

            try:
                self.console.print(
                    f"[bold cyan]Allow skill '@{skill.name}' to auto-run commands?[/bold cyan] "
                    "[bold white]\\[y=this session / p=permanent / N=ask each time][/bold white]: ",
                    end="",
                )
                ans = input().strip().lower()
            except (KeyboardInterrupt, EOFError):
                ans = "n"

            if ans in ("y", "yes"):
                self._session_approved_skills.add(s_key)
            elif ans in ("p", "perm", "permanent"):
                self._session_approved_skills.add(s_key)
                self.skill_manager.save_approved_skill(skill.name)
                self.console.print(f"[green]Saved permanent auto-approval for '@{skill.name}'.[/green]")
            else:
                all_approved = False

        return all_approved

    def _print_skills_table(self, filter_query: Optional[str] = None) -> None:
        """Render loaded AI skills in a formatted Rich table, optionally filtered by keyword."""
        from rich.table import Table

        skills = self.skill_manager.list_skills()
        if filter_query:
            q = filter_query.strip().lower()
            skills = [
                s for s in skills
                if q in s.name.lower()
                or q in s.description.lower()
                or any(q in t.lower() for t in s.triggers)
            ]

        title = f"AI Skills matching '{filter_query}'" if filter_query else "Available AI Skills"
        table = Table(title=title, border_style="cyan")
        table.add_column("Skill", style="bold cyan")
        table.add_column("Source", style="dim")
        table.add_column("Description", style="white")

        for skill in skills:
            table.add_row(f"@{skill.name}", skill.source, skill.description)

        if not skills:
            self.console.print(f"[yellow]No local skills matched '{filter_query}'. Try '@find-skills {filter_query}' to search online.[/yellow]")
        else:
            self.console.print(table)
        self.console.print(
            f"[dim]Drop custom SKILL.md files into {self.skill_manager.user_skills_dir} and run ':skills reload'.[/dim]"
        )

    def _print_help(self) -> None:
        """Print interactive REPL help guide."""
        content = (
            "[bold cyan]aishell Interactive REPL Guide[/bold cyan]\n\n"
            "• [bold green]Natural Language Query:[/bold green] Type your question or intent directly\n"
            "• [bold green]Direct Shell Command:[/bold green] Prefix with [bold yellow]![/bold yellow] or run standard builtins (`cd`, `export`)\n"
            "• [bold green]System Context:[/bold green] Type [bold yellow]/context[/bold yellow] to inspect host facts and sanitized environment\n"
            "• [bold green]AI Skills:[/bold green] Type [bold yellow]/skills[/bold yellow] to list active skills or [bold yellow]/skills reload[/bold yellow] to refresh\n"
            "• [bold green]Switch Provider / Model:[/bold green] [bold yellow]/provider <name>[/bold yellow] or [bold yellow]/model <name>[/bold yellow]\n"
            "• [bold green]Multiline Input:[/bold green] Press [bold yellow]Alt+Enter[/bold yellow] or end line with trailing [bold yellow]\\[/bold yellow]\n"
            "• [bold green]History Search:[/bold green] Press [bold yellow]Ctrl+R[/bold yellow] to reverse search command history\n"
            "• [bold green]Interrupt Stream:[/bold green] Press [bold yellow]Ctrl+C[/bold yellow] to halt active generation\n"
            "• [bold green]Exit Session:[/bold green] Type [bold yellow]:exit[/bold yellow] or press [bold yellow]Ctrl+D[/bold yellow]"
        )
        self.console.print(Panel(content, border_style="cyan", expand=False))

    _INTERACTIVE_NO_REMEDIATE = frozenset({
        "bash", "sh", "zsh", "fish", "ssh", "tmux", "screen",
        "vi", "vim", "nano", "less", "more", "man", "top", "htop", "btop",
    })

    _DIRECT_SHELL_COMMANDS = frozenset({
        "bash", "sh", "zsh", "fish", "ssh", "scp", "rsync", "tmux", "screen",
        "ls", "ll", "la", "df", "du", "free", "ps", "top", "htop", "btop",
        "uptime", "whoami", "id", "uname", "pwd", "echo", "cat", "head",
        "tail", "less", "more", "grep", "egrep", "fgrep", "rg", "awk", "sed",
        "sort", "uniq", "wc", "cut", "tr", "mkdir", "rmdir", "rm", "cp", "mv",
        "touch", "ln", "chmod", "chown", "chgrp", "tar", "gzip", "gunzip",
        "zip", "unzip", "curl", "wget", "ping", "traceroute", "dig",
        "nslookup", "ip", "ifconfig", "ss", "netstat", "lsof", "lsblk",
        "fdisk", "mount", "umount", "git", "docker", "docker-compose",
        "kubectl", "systemctl", "journalctl", "service", "apt", "apt-get",
        "dpkg", "dnf", "yum", "pacman", "pip", "pip3", "pipx", "uv", "python",
        "python3", "node", "npm", "npx", "sudo", "su", "vi", "vim", "nano",
        "which", "whereis", "env", "printenv", "date", "cal", "kill", "pkill",
        "killall", "clear", "reset", "history", "man", "stat", "file", "tee",
        "xargs", "jq", "cd", "export", "unset", "alias", "unalias", "source",
    })

    _WAKE_PREFIX_RE = re.compile(r"^(?:ais|ai)\b[:,\s]*(.*)$", re.IGNORECASE)
    _CONVERSATIONAL_WAKE_RE = re.compile(r"^(?:hi|hello|hey|please)\b[,:\s]*(.*)$", re.IGNORECASE)
    _ENV_ASSIGN_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")

    def _classify_input(self, raw: str) -> Tuple[str, str]:
        """Classify user input into ('shell', command) or ('ai', query).

        Direct shell commands (e.g. 'ls', 'df -h', 'bash', './run.sh', '!cmd') run directly
        without waking the AI. AI is invoked for explicit wake-up prefixes ('hi,',
        'please', 'ais', '?') or natural language queries.
        """
        if raw.startswith("!") or raw.startswith("$"):
            return ("shell", raw[1:].strip())

        # Explicit AI wake-up triggers
        if raw.startswith("@"):
            return ("ai", raw)

        ais_match = self._WAKE_PREFIX_RE.match(raw)
        if ais_match:
            query = ais_match.group(1).strip() or raw
            return ("ai", query)

        if self._CONVERSATIONAL_WAKE_RE.match(raw):
            return ("ai", raw)

        if raw.startswith("?"):
            query = raw[1:].strip() or raw
            return ("ai", query)

        # Shell command, script path, variable assignment, and bash syntax detection
        tokens = raw.split()
        first_token = tokens[0].lower()

        if first_token in ("cd", "export", "unset", "pwd", "echo", "alias", "unalias", "source", "."):
            return ("shell", raw)

        if not raw.endswith("?"):
            if (
                first_token in self._DIRECT_SHELL_COMMANDS
                or first_token.startswith(("./", "/", "~/"))
                or self._ENV_ASSIGN_RE.match(tokens[0])
                or first_token in ("for", "while", "until", "if", "case", "function", "[[")
                or any(op in raw for op in ("|", ">", "<", "&&", "||", ";", "$(", "`"))
            ):
                return ("shell", raw)

            if shutil.which(first_token) and (
                len(tokens) == 1
                or any(t.startswith(("-", "/", "./", "~/")) for t in tokens[1:])
            ):
                return ("shell", raw)

        return ("ai", raw)

    def dispatch_input(self, user_input: str) -> None:
        """Dispatch user input to shell executor or stream renderer."""
        raw = user_input.strip()
        if not raw:
            return

        # Check for meta commands first
        first_token = raw.split()[0].lower()
        if (
            raw.startswith(":")
            or raw.startswith("/")
            or first_token in ("exit", "quit", "help", "clear", "provider", "model", "context", "skills", "findskills", "mcp")
        ):
            if self.handle_meta_command(raw):
                raise EOFError()
            return

        mode, payload = self._classify_input(raw)
        if mode == "shell":
            self._execute_with_remediation(payload)
            return

        # Natural language query - Stream tokens from active AI provider
        raw = payload
        self.safety_gate.reset_auto_approve()
        self.is_streaming = True
        accumulated_tokens = []
        try:
            import asyncio
            from aishell.context.inspector import inspect_system_context
            from aishell.context.privacy import PrivacyGuard
            from aishell.context.sanitizer import format_system_observation
            from aishell.providers.errors import ProviderError
            from aishell.providers.prompts import SYSTEM_PROMPT_CHAT
            from aishell.providers.schema import extract_proposal_from_text

            # Record user query in multi-turn conversation memory per D-04, CONF-03
            self.conversation.add_user_message(raw)

            # Match active AI skills based on explicit mention or triggers
            matched_skills = self.skill_manager.match_skills(raw)
            skills_context = self.skill_manager.format_skills_context(matched_skills)
            if matched_skills:
                skill_names = ", ".join(f"@{s.name}" for s in matched_skills)
                self.console.print(f"[dim]Active skills: {skill_names}[/dim]")
                if self._check_skill_approvals(matched_skills):
                    self.safety_gate.auto_approve = True

            # Autonomous agentic loop
            last_proposed_cmd = None
            last_exec = None
            for step_idx in range(self.max_agent_steps):
                context_info = inspect_system_context(cwd=os.getcwd())
                observation = format_system_observation(context_info)
                system_instruction = f"{SYSTEM_PROMPT_CHAT}\n\n{observation}"
                custom_sys_prompt = getattr(self.settings.general, "system_prompt", None)
                if custom_sys_prompt and custom_sys_prompt.strip():
                    system_instruction = f"{system_instruction}\n\n## Custom System Prompt\n{custom_sys_prompt.strip()}"
                if skills_context:
                    system_instruction = f"{system_instruction}\n\n## Active Skills\n{skills_context}"
                mcp_context = self.mcp_manager.format_mcp_context()
                if mcp_context:
                    system_instruction = f"{system_instruction}\n\n## MCP Tools\n{mcp_context}"

                messages = self.conversation.get_messages_for_llm(system_instruction)
                accumulated_tokens = []

                def _token_generator():
                    try:
                        loop = asyncio.get_event_loop()
                        if loop.is_closed():
                            loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(loop)
                    except RuntimeError:
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)

                    agen = self.provider.stream_chat(messages, system_prompt=system_instruction)
                    try:
                        while True:
                            try:
                                token = loop.run_until_complete(agen.__anext__())
                                accumulated_tokens.append(token)
                                yield token
                            except StopAsyncIteration:
                                break
                    finally:
                        try:
                            loop.run_until_complete(agen.aclose())
                        except Exception:
                            pass

                self.renderer.stream_markdown(_token_generator())

                full_text = "".join(accumulated_tokens)
                if full_text.strip():
                    self.conversation.add_assistant_message(full_text)
                accumulated_tokens = []

                # Check for MCP tool call first if no shell command was proposed
                mcp_call = extract_mcp_call_from_text(full_text)
                if mcp_call and self.mcp_manager.servers:
                    approved_mcp = self.safety_gate.auto_approve
                    if not approved_mcp:
                        try:
                            self.console.print(
                                f"[bold cyan]Execute MCP tool '{mcp_call.server}.{mcp_call.tool}'?[/bold cyan] "
                                "[bold white]\\[y=run / a=all / N=cancel][/bold white]: ",
                                end="",
                            )
                            ans = input().strip().lower()
                        except (KeyboardInterrupt, EOFError):
                            ans = "n"
                        if ans in ("a", "all"):
                            self.safety_gate.auto_approve = True
                            approved_mcp = True
                        elif ans in ("y", "yes"):
                            approved_mcp = True

                    if not approved_mcp:
                        self.console.print("[dim]MCP tool cancelled by user. Agent loop stopped.[/dim]")
                        break

                    try:
                        loop = asyncio.get_event_loop()
                        mcp_out = loop.run_until_complete(
                            self.mcp_manager.call_tool(mcp_call.server, mcp_call.tool, mcp_call.arguments)
                        )
                    except Exception as exc:
                        mcp_out = f"MCP tool error: {exc}"

                    redacted_mcp = PrivacyGuard.redact_credentials(mcp_out or "")
                    if len(redacted_mcp) > 4000:
                        redacted_mcp = redacted_mcp[:4000] + "\n...[truncated]..."
                    self.conversation.add_user_message(
                        f'<mcp_output server="{mcp_call.server}" tool="{mcp_call.tool}" untrusted="true">\n'
                        f"{redacted_mcp}\n"
                        "</mcp_output>"
                    )
                    if step_idx < self.max_agent_steps - 1:
                        self.console.print(
                            f"[dim]✓ Step {step_idx + 1}/{self.max_agent_steps} (MCP {mcp_call.server}.{mcp_call.tool}) finished. Continuing autonomously...[/dim]"
                        )
                    continue

                # Safety Gate: check if response proposed a shell command per EXEC-02, D-05
                proposal = extract_proposal_from_text(full_text)
                if not proposal or not proposal.command.strip():
                    break

                # Guard against infinite loops where the provider repeats the exact same command
                current_cmd = proposal.command.strip()
                if step_idx > 0 and current_cmd == last_proposed_cmd and last_exec and last_exec[1] == 0:
                    self.console.print("[dim]Agent proposed duplicate completed command. Stopping loop.[/dim]")
                    break
                last_proposed_cmd = current_cmd

                approved_cmd = self.safety_gate.process_proposal(
                    proposal=proposal,
                    console=self.console,
                    prompt_session=self.session,
                )
                if not approved_cmd:
                    self.console.print("[dim]Command cancelled by user. Agent loop stopped.[/dim]")
                    break

                self._execute_with_remediation(approved_cmd)
                last_exec = getattr(self, "_last_execution", None)
                if last_exec:
                    _, exec_code, exec_output = last_exec
                    redacted_out = PrivacyGuard.redact_credentials(exec_output or "")
                    if len(redacted_out) > 4000:
                        redacted_out = redacted_out[:4000] + "\n...[truncated]..."
                    self.conversation.add_user_message(
                        f'<command_output command="{approved_cmd}" exit_code="{exec_code}" untrusted="true">\n'
                        f"{redacted_out}\n"
                        "</command_output>"
                    )
                    if step_idx < self.max_agent_steps - 1:
                        self.console.print(
                            f"[dim]✓ Step {step_idx + 1}/{self.max_agent_steps} finished (exit {exec_code}). Continuing autonomously...[/dim]"
                        )
                    else:
                        self.console.print(
                            f"[yellow]Reached max agent steps ({self.max_agent_steps}). Type your next instruction to continue.[/yellow]"
                        )

        except KeyboardInterrupt:
            # If tokens were streamed before interruption, save partial response in memory
            if accumulated_tokens:
                partial_text = "".join(accumulated_tokens)
                if partial_text.strip():
                    self.conversation.add_assistant_message(partial_text)
            # Re-raise so run() handles generation cancellation without session death
            raise
        except ProviderError as err:
            guidance_text = f"\n\n[bold yellow]Guidance:[/bold yellow] {err.guidance}" if err.guidance else ""
            self.renderer.render_error(f"{err.message}{guidance_text}")
        except Exception as exc:
            self.renderer.render_error(f"Generation error: {exc}")
        finally:
            self.is_streaming = False

    def _cleanup_async_loop(self) -> None:
        """Safely shut down provider clients, async generators, and pending tasks."""
        try:
            import asyncio
            import gc
            import logging

            logging.getLogger("asyncio").setLevel(logging.CRITICAL)

            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                return

            if not loop.is_closed():
                if hasattr(self, "mcp_manager"):
                    try:
                        loop.run_until_complete(self.mcp_manager.close_all())
                    except Exception:
                        pass
                if hasattr(self, "provider") and hasattr(self.provider, "aclose"):
                    try:
                        loop.run_until_complete(self.provider.aclose())
                    except Exception:
                        pass

                gc.collect()
                try:
                    loop.run_until_complete(loop.shutdown_asyncgens())
                except Exception:
                    pass

                try:
                    pending = asyncio.all_tasks(loop)
                    for task in pending:
                        task.cancel()
                    if pending:
                        loop.run_until_complete(
                            asyncio.gather(*pending, return_exceptions=True)
                        )
                except Exception:
                    pass

                try:
                    loop.set_exception_handler(lambda *_: None)
                    loop.run_until_complete(asyncio.sleep(0))
                    loop.close()
                except Exception:
                    pass
        except Exception:
            pass

    def run(self) -> None:
        """Run interactive REPL event loop."""
        render_banner(self.console, self.settings)

        try:
            while True:
                try:
                    prompt_tokens = self.get_prompt_tokens()
                    user_input = self.session.prompt(prompt_tokens)
                    self.dispatch_input(user_input)
                    # Reset consecutive interrupt timer after successful input
                    self.last_interrupt_time = 0.0

                except KeyboardInterrupt:
                    if self.is_streaming:
                        # Cancel streaming token generation immediately without killing session per REPL-04
                        self.is_streaming = False
                        self.console.print("\n[dim yellow]^C (generation cancelled)[/dim yellow]")
                        continue

                    # Empty prompt buffer interrupt handling per D-03
                    now = time.time()
                    if now - self.last_interrupt_time <= 1.5:
                        self.console.print("\n[dim cyan]Goodbye![/dim cyan]")
                        break
                    else:
                        self.last_interrupt_time = now
                        self.console.print("\n[dim](Press Ctrl+C again or type :exit to quit)[/dim]")
                        continue

                except EOFError:
                    self.console.print("[dim cyan]Goodbye![/dim cyan]")
                    break
                except Exception as exc:
                    self.renderer.render_error(f"Unexpected error: {exc}")
        finally:
            self._cleanup_async_loop()
