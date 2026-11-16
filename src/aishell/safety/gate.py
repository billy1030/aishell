"""Interactive confirmation gate with TTY safety guard per D-03 and EXEC-02."""

import sys
from enum import Enum
from typing import Callable, Optional
from rich.console import Console

from aishell.providers.schema import CommandProposal
from aishell.safety.display import render_proposal


class GateAction(str, Enum):
    """Actions resulting from the confirmation gate prompt."""

    CONFIRM = "confirm"
    CANCEL = "cancel"
    EDIT = "edit"


def is_interactive_stdin() -> bool:
    """Check whether standard input is attached to an interactive terminal."""
    try:
        return bool(sys.stdin and hasattr(sys.stdin, "isatty") and sys.stdin.isatty())
    except Exception:
        return False


def prompt_confirmation(
    proposal: CommandProposal,
    console: Optional[Console] = None,
    input_fn: Optional[Callable[[str], str]] = None,
) -> GateAction:
    """Present the proposal and prompt operator for explicit execution confirmation.

    Halts execution and displays:
      `Execute command? [y/N/e]: `
    Options:
      - 'y' or 'yes': Proceed with execution (returns GateAction.CONFIRM)
      - 'e' or 'edit': Enter inline command editor (returns GateAction.EDIT)
      - Enter, 'n', 'no', or unrecognized: Cancel execution (returns GateAction.CANCEL)

    If standard input is not an interactive terminal and no input_fn is provided,
    execution is safely blocked and returns GateAction.CANCEL per D-03.
    """
    c = console or Console()

    # Step 1: Check for interactive TTY guard
    if input_fn is None and not is_interactive_stdin():
        c.print(
            "[bold red]Execution blocked:[/bold red] confirmation required but standard input is not interactive.",
            style="red",
        )
        return GateAction.CANCEL

    # Step 2: Render Proposal Card with visual risk badges
    render_proposal(proposal, console=c)

    # Step 3: Present interactive prompt
    prompt_str = "Execute command? [y/N/e]: "
    try:
        if input_fn is not None:
            user_response = input_fn(prompt_str)
        else:
            c.print(f"[bold cyan]{prompt_str}[/bold cyan]", end="")
            user_response = input()

        clean_resp = user_response.strip().lower()

        if clean_resp in ("y", "yes"):
            return GateAction.CONFIRM
        elif clean_resp in ("e", "edit"):
            return GateAction.EDIT
        else:
            c.print("[yellow]Command cancelled by operator.[/yellow]")
            return GateAction.CANCEL

    except (KeyboardInterrupt, EOFError):
        c.print("\n[yellow]Command cancelled by operator.[/yellow]")
        return GateAction.CANCEL
