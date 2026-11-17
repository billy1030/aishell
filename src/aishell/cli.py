"""Command Line Interface for aishell."""

import os
import sys
import time
import uuid
from typing import Optional
import typer
from rich.console import Console
from typer.core import TyperGroup

from aishell.config.settings import get_settings
from aishell.execution.builtins import sync_compound_cwd, try_execute_builtin
from aishell.execution.pty_runner import run_in_pty
from aishell.storage.history import HistoryManager
from aishell.ui.renderer import RichStreamRenderer

MAX_STDIN_BYTES = 512 * 1024  # 512KB bound per T-02-01


class DefaultCommandGroup(TyperGroup):
    """Custom TyperGroup that routes unrecognised non-option arguments to the ask command."""

    def resolve_command(self, ctx, args):
        cmd_name = args[0] if args else None
        if cmd_name and cmd_name not in self.commands and not cmd_name.startswith("-"):
            # Prepend default 'ask' command for bare positional queries per D-08
            return super().resolve_command(ctx, ["ask"] + args)
        return super().resolve_command(ctx, args)


app = typer.Typer(
    cls=DefaultCommandGroup,
    name="aishell",
    help="Terminal AI Shell - Interactive, system-aware Linux AI console assistant and REPL",
    no_args_is_help=False,
)
console = Console()
_SESSION_ID = str(uuid.uuid4())[:8]


def is_interactive_terminal() -> bool:
    """Determine whether standard input is attached to an interactive terminal."""
    try:
        return bool(sys.stdin and hasattr(sys.stdin, "isatty") and sys.stdin.isatty())
    except Exception:
        return False


def read_piped_stdin() -> Optional[str]:
    """Read piped stdin if available, capped to 512KB per T-02-01."""
    try:
        if not is_interactive_terminal():
            raw_text = sys.stdin.read(MAX_STDIN_BYTES + 1024)
            if not raw_text:
                return None
            raw_bytes = raw_text.encode("utf-8", errors="replace")
            if len(raw_bytes) > MAX_STDIN_BYTES:
                console.print(
                    "[bold yellow]Warning:[/bold yellow] Piped stdin exceeds 512KB and was truncated.",
                    style="yellow",
                )
                return raw_bytes[:MAX_STDIN_BYTES].decode("utf-8", errors="replace")
            return raw_text
    except Exception:
        pass
    return None


def execute_pipeline_capture(command: str, session_id: Optional[str] = None) -> tuple[int, str]:
    """Core execution pipeline returning (exit_code, output) for diagnostics and AI context."""
    settings = get_settings()
    history = HistoryManager(
        db_path=settings.storage.history_db_path,
        max_records=settings.storage.max_history_records,
    )
    sess_id = session_id or _SESSION_ID
    current_cwd = os.getcwd()

    # Step 1: Check and intercept shell builtins (cd, export, unset) per D-05
    start_time = time.perf_counter()
    builtin_result = try_execute_builtin(command)

    if builtin_result is not None:
        exit_code, output = builtin_result
        duration_ms = (time.perf_counter() - start_time) * 1000.0
        if output:
            console.print(output)

        history.record_execution(
            session_id=sess_id,
            command=command,
            cwd=current_cwd,
            exit_code=exit_code,
            duration_ms=duration_ms,
            output=output,
            executed_by="user",
        )
        return exit_code, output or ""

    # Step 2: Dispatch external command to managed PTY runner per D-01, EXEC-04
    result = run_in_pty(
        command=command,
        cwd=current_cwd,
        timeout=float(settings.execution.timeout_seconds),
        echo_to_terminal=True,
    )

    # Step 3: Synchronize compound cwd if command contained cd per D-06
    sync_compound_cwd(command, exit_code=result.exit_code)

    # Step 4: Record execution audit record in SQLite history database per D-09, EXEC-06
    history.record_execution(
        session_id=sess_id,
        command=command,
        cwd=current_cwd,
        exit_code=result.exit_code,
        duration_ms=result.duration_ms,
        output=result.output,
        executed_by="user",
    )

    return result.exit_code, result.output or ""


def execute_pipeline(command: str, session_id: Optional[str] = None) -> int:
    """Core execution pipeline coordinating builtins, PTY runner, and audit logging."""
    exit_code, _ = execute_pipeline_capture(command=command, session_id=session_id)
    return exit_code


def execute_pipeline_with_remediation(
    command: str,
    session_id: Optional[str] = None,
    provider=None,
    console: Optional[Console] = None,
) -> int:
    """Execute pipeline and trigger bounded remediation loop upon command failure."""
    exit_code = (
        execute_pipeline(command)
        if session_id is None
        else execute_pipeline(command, session_id)
    )

    if exit_code != 0 and exit_code != 130 and is_interactive_terminal():
        from aishell.diagnostics.engine import DiagnosticEngine
        from aishell.diagnostics.remediation import RemediationController
        from aishell.safety.gate import SafetyGate

        c = console or Console()
        diag_engine = DiagnosticEngine(provider=provider)
        controller = RemediationController()
        gate = SafetyGate(console=c)

        return controller.run_remediation_loop(
            failed_command=command,
            exit_code=exit_code,
            output="",
            diagnostic_engine=diag_engine,
            safety_gate=gate,
            executor_fn=lambda cmd: execute_pipeline(cmd) if session_id is None else execute_pipeline(cmd, session_id),
            console=c,
        )

    return exit_code


def execute_one_shot(
    query: Optional[str] = None,
    piped_stdin: Optional[str] = None,
    provider_name: Optional[str] = None,
    model_name: Optional[str] = None,
) -> None:
    """Execute a one-shot query via RichStreamRenderer and active provider per REPL-05, D-07."""
    parts = []
    if piped_stdin:
        parts.append(piped_stdin.strip())
    if query:
        parts.append(query.strip())

    combined_input = "\n\n".join(parts)
    if not combined_input:
        return

    renderer = RichStreamRenderer()
    settings = get_settings()

    try:
        import asyncio
        from aishell.providers.base import ChatMessage
        from aishell.providers.errors import ProviderError
        from aishell.providers.factory import get_provider

        provider = get_provider(
            name=provider_name,
            model=model_name,
            settings=settings,
            validate=True,
        )

        from aishell.context.inspector import inspect_system_context
        from aishell.context.sanitizer import format_system_observation
        from aishell.providers.prompts import SYSTEM_PROMPT_CHAT

        context_info = inspect_system_context()
        observation = format_system_observation(context_info)
        system_instruction = f"{SYSTEM_PROMPT_CHAT}\n\n{observation}"

        messages = [ChatMessage(role="user", content=combined_input)]

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

            agen = provider.stream_chat(messages, system_prompt=system_instruction)
            while True:
                try:
                    token = loop.run_until_complete(agen.__anext__())
                    accumulated_tokens.append(token)
                    yield token
                except StopAsyncIteration:
                    break

        renderer.stream_markdown(_token_generator())

        # Safety Gate: check if response proposed a shell command per EXEC-02, D-05
        full_text = "".join(accumulated_tokens)
        from aishell.providers.schema import extract_proposal_from_text
        from aishell.safety.gate import SafetyGate

        proposal = extract_proposal_from_text(full_text)
        if proposal and proposal.command.strip():
            gate = SafetyGate(console=console)
            approved_cmd = gate.process_proposal(proposal, console=console)
            if approved_cmd:
                execute_pipeline_with_remediation(
                    command=approved_cmd,
                    provider=provider,
                    console=console,
                )

    except ProviderError as err:
        guidance_text = f"\n\n[bold yellow]Guidance:[/bold yellow] {err.guidance}" if err.guidance else ""
        renderer.render_error(f"{err.message}{guidance_text}")
        raise typer.Exit(code=1)
    except Exception as exc:
        renderer.render_error(f"Execution error: {exc}")
        raise typer.Exit(code=1)


@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    command: Optional[str] = typer.Option(
        None,
        "-c",
        "--command",
        help="Execute a one-shot AI query without entering REPL",
    ),
    provider: Optional[str] = typer.Option(
        None,
        "-p",
        "--provider",
        help="AI provider: ollama, gemini, openai, anthropic",
    ),
    model: Optional[str] = typer.Option(
        None,
        "-m",
        "--model",
        help="AI model name or identifier override",
    ),
    version: Optional[bool] = typer.Option(
        None, "--version", "-v", help="Show aishell version"
    ),
    show_context: Optional[bool] = typer.Option(
        None,
        "--context",
        help="Inspect and display current system context and sanitized environment variables",
    ),
) -> None:
    """Main aishell entrypoint."""
    if version:
        from aishell import __version__

        console.print(f"[bold cyan]aishell[/bold cyan] version [green]{__version__}[/green]")
        raise typer.Exit(code=0)

    if show_context:
        from aishell.context.display import render_context_table
        from aishell.context.inspector import inspect_system_context

        ctx_info = inspect_system_context()
        render_context_table(ctx_info, console=console)
        raise typer.Exit(code=0)

    # Check for piped stdin once and stash in ctx.obj
    ctx.ensure_object(dict)
    piped_stdin = read_piped_stdin()
    ctx.obj["piped_stdin"] = piped_stdin
    ctx.obj["provider"] = provider
    ctx.obj["model"] = model

    if ctx.invoked_subcommand is None:
        if command or piped_stdin:
            execute_one_shot(
                query=command,
                piped_stdin=piped_stdin,
                provider_name=provider,
                model_name=model,
            )
            raise typer.Exit(code=0)

        # Check if stdin is a TTY for interactive REPL per REPL-01
        if is_interactive_terminal():
            from aishell.ui.repl import InteractiveREPL

            settings = get_settings()
            repl = InteractiveREPL(
                settings=settings,
                console=console,
                provider_name=provider,
                model_name=model,
            )
            try:
                repl.run()
            except (KeyboardInterrupt, EOFError):
                pass
            raise typer.Exit(code=0)
        else:
            # Fallback if stdin is not a TTY and no query provided
            console.print("[yellow]aishell: no command or query provided and standard input is not a terminal.[/yellow]")
            console.print("Run 'aishell --help' for usage, or pipe input via 'cat file | aishell'.")
            raise typer.Exit(code=0)


@app.command(name="ask", hidden=True)
def ask_cmd(
    ctx: typer.Context,
    query: str = typer.Argument(..., help="Natural language query for one-shot execution"),
    provider: Optional[str] = typer.Option(None, "-p", "--provider", help="AI provider"),
    model: Optional[str] = typer.Option(None, "-m", "--model", help="AI model"),
) -> None:
    """Execute a bare positional one-shot query."""
    obj = ctx.obj or {}
    piped_stdin = obj.get("piped_stdin")
    active_provider = provider or obj.get("provider")
    active_model = model or obj.get("model")
    execute_one_shot(
        query=query,
        piped_stdin=piped_stdin,
        provider_name=active_provider,
        model_name=active_model,
    )


@app.command(name="exec")
def exec_cmd(
    command: str = typer.Argument(..., help="Shell command string to execute"),
) -> None:
    """Execute a shell command with real-time output and exit code return (Tracer)."""
    exit_code = execute_pipeline(command)
    if exit_code != 0:
        raise typer.Exit(code=exit_code)


@app.command(name="run")
def run_cmd(
    command: str = typer.Argument(..., help="Shell command string to execute"),
) -> None:
    """Alias for exec command."""
    exit_code = execute_pipeline(command)
    if exit_code != 0:
        raise typer.Exit(code=exit_code)


if __name__ == "__main__":
    app()
