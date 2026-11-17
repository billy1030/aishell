"""Interactive confirmation gate and SafetyGate service per D-03, D-04, D-05, and EXEC-02, EXEC-03."""

import sys
from enum import Enum
from typing import Callable, Optional
from rich.console import Console

from aishell.providers.schema import CommandProposal
from aishell.safety.classifier import RiskLevel, classify_risk
from aishell.safety.display import render_proposal


class GateAction(str, Enum):
    """Actions resulting from the confirmation gate prompt."""

    CONFIRM = "confirm"
    ALL = "all"
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
    prompt_str = "Execute command? [y=run / a=all / N=cancel / e=edit]: "
    try:
        if input_fn is not None:
            user_response = input_fn(prompt_str)
        else:
            c.print(
                "[bold cyan]Execute command?[/bold cyan] [bold white]\\[y=run / a=all / N=cancel / e=edit][/bold white]: ",
                end="",
            )
            user_response = input()

        clean_resp = user_response.strip().lower()

        if clean_resp in ("y", "yes"):
            return GateAction.CONFIRM
        elif clean_resp in ("a", "all"):
            return GateAction.ALL
        elif clean_resp in ("e", "edit"):
            return GateAction.EDIT
        else:
            c.print("[yellow]Command cancelled by operator.[/yellow]")
            return GateAction.CANCEL

    except (KeyboardInterrupt, EOFError):
        c.print("\n[yellow]Command cancelled by operator.[/yellow]")
        return GateAction.CANCEL


def prompt_edit_command(
    initial_command: str,
    console: Optional[Console] = None,
    prompt_session: Optional[object] = None,
    input_fn: Optional[Callable[[str], str]] = None,
) -> Optional[str]:
    """Launch inline prompt buffer editor with proposed command pre-loaded per D-04 and EXEC-03.

    Allows the operator to modify flags, arguments, or file paths with full cursor
    navigation and readline keybindings.
    Returns the edited command string, or None if cancelled.
    """
    c = console or Console()

    if input_fn is not None:
        try:
            res = input_fn(initial_command)
            clean = res.strip()
            return clean if clean else None
        except (KeyboardInterrupt, EOFError):
            c.print("\n[yellow]Editing cancelled by operator.[/yellow]")
            return None

    try:
        if prompt_session is not None and hasattr(prompt_session, "prompt"):
            edited = prompt_session.prompt("Edit command: ", default=initial_command)
        else:
            from prompt_toolkit import prompt as pt_prompt

            try:
                edited = pt_prompt("Edit command: ", default=initial_command)
            except Exception:
                c.print(f"[bold cyan]Edit command (press Enter to keep, or type new):[/bold cyan]\n[dim]{initial_command}[/dim]\n> ", end="")
                val = input()
                edited = val.strip() if val.strip() else initial_command

        clean = edited.strip()
        if not clean:
            c.print("[yellow]Empty command; editing cancelled.[/yellow]")
            return None
        return clean

    except (KeyboardInterrupt, EOFError):
        c.print("\n[yellow]Editing cancelled by operator.[/yellow]")
        return None


class SafetyGate:
    """Coordinates risk evaluation, proposal display, confirmation, and inline editing per D-05."""

    def __init__(self, console: Optional[Console] = None) -> None:
        self.console = console or Console()
        self.auto_approve: bool = False

    def reset_auto_approve(self) -> None:
        """Reset per-task auto-approval flag."""
        self.auto_approve = False

    def process_proposal(
        self,
        proposal: CommandProposal,
        console: Optional[Console] = None,
        prompt_session: Optional[object] = None,
        input_fn: Optional[Callable[[str], str]] = None,
        edit_fn: Optional[Callable[[str], str]] = None,
    ) -> Optional[str]:
        """Process a command proposal through the confirmation safety gate.

        Returns:
            The approved executable shell command string, or None if cancelled.
        """
        c = console or self.console
        current_proposal = proposal

        while True:
            # 1. Reconcile risk tier with deterministic heuristics per D-01
            effective_risk = classify_risk(
                current_proposal.command,
                model_risk=current_proposal.risk_tier,
            )
            current_proposal = current_proposal.model_copy(
                update={"risk_tier": effective_risk.value}
            )

            # 2. If 'a' (All) was selected earlier in this task, auto-approve without re-prompting
            if self.auto_approve:
                render_proposal(current_proposal, console=c)
                c.print("[dim]Auto-approved (all): executing command...[/dim]")
                return current_proposal.command

            # 3. Present confirmation prompt
            action = prompt_confirmation(
                proposal=current_proposal,
                console=c,
                input_fn=input_fn,
            )

            if action == GateAction.CONFIRM:
                return current_proposal.command
            elif action == GateAction.ALL:
                self.auto_approve = True
                return current_proposal.command

            elif action == GateAction.EDIT:
                # 3. Launch inline editor
                if edit_fn is not None:
                    edited_cmd = edit_fn(current_proposal.command)
                else:
                    edited_cmd = prompt_edit_command(
                        initial_command=current_proposal.command,
                        console=c,
                        prompt_session=prompt_session,
                    )

                if not edited_cmd:
                    return None

                # 4. Re-evaluate risk on the modified command and re-prompt confirmation per D-04
                new_risk = classify_risk(edited_cmd)
                current_proposal = CommandProposal(
                    command=edited_cmd,
                    purpose=f"Edited command (was: {current_proposal.purpose})",
                    explanation=f"Modified by operator from original: {current_proposal.command}",
                    risk_tier=new_risk.value,
                    requires_sudo=edited_cmd.strip().startswith("sudo"),
                    remediation=current_proposal.remediation,
                )
                continue

            else:  # GateAction.CANCEL
                return None
