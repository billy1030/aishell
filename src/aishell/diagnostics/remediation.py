"""Bounded remediation controller coordinating error recovery and human-in-the-loop safety gates."""

import os
import sys
from typing import Any, Callable, Optional, Tuple, Union
from rich.console import Console

from aishell.diagnostics.engine import DiagnosticEngine, capture_failure, should_diagnose
from aishell.diagnostics.schema import DiagnosticResult
from aishell.safety.gate import SafetyGate

MAX_REMEDIATION_CYCLES: int = 2
HALT_NOTICE: str = (
    "Maximum remediation attempts (2) reached. Halting automated recovery to prevent command thrashing."
)


def default_execution_runner(command: str, cwd: Optional[str] = None) -> Tuple[int, str]:
    """Execute a command, handling builtins and PTY execution, returning (exit_code, output)."""
    from aishell.execution.builtins import sync_compound_cwd, try_execute_builtin
    from aishell.execution.pty_runner import run_in_pty

    current_cwd = cwd or os.getcwd()
    builtin_res = try_execute_builtin(command)
    if builtin_res is not None:
        exit_code, output = builtin_res
        sync_compound_cwd(command, exit_code=exit_code)
        return exit_code, output

    pty_res = run_in_pty(command=command, cwd=current_cwd, echo_to_terminal=True)
    sync_compound_cwd(command, exit_code=pty_res.exit_code)
    return pty_res.exit_code, pty_res.output


class RemediationController:
    """Manages the bounded remediation loop, ensuring maximum 2 cycles and human confirmation."""

    def __init__(self, max_cycles: int = MAX_REMEDIATION_CYCLES) -> None:
        self.max_cycles = max_cycles
        self.cycle_count: int = 0

    def can_remediate(self) -> bool:
        """Check whether another remediation attempt is permitted under the cycle cap."""
        return self.cycle_count < self.max_cycles

    def record_attempt(self) -> int:
        """Increment and return the current remediation attempt count."""
        self.cycle_count += 1
        return self.cycle_count

    def reset(self) -> None:
        """Reset the remediation cycle counter for a new incident or upon success."""
        self.cycle_count = 0

    def run_remediation_loop(
        self,
        failed_command: str,
        exit_code: int,
        output: str,
        diagnostic_engine: DiagnosticEngine,
        safety_gate: SafetyGate,
        executor_fn: Optional[Callable[[str], Any]] = None,
        console: Optional[Console] = None,
        prompt_session: Optional[object] = None,
        input_fn: Optional[Callable[[str], str]] = None,
        edit_fn: Optional[Callable[[str], str]] = None,
        cwd: Optional[str] = None,
    ) -> int:
        """Run bounded remediation loop per D-02 and D-03.

        Returns:
            Final exit code (0 if remediated successfully, non-zero if failed or cancelled).
        """
        c = console or safety_gate.console or Console()

        # Step 0: Ignore exit code 130 (SIGINT) or success (0)
        if not should_diagnose(exit_code):
            return exit_code

        current_cmd = failed_command
        current_exit_code = exit_code
        current_output = output
        current_cwd = cwd or os.getcwd()

        runner = executor_fn or default_execution_runner

        while self.can_remediate():
            cycle = self.record_attempt()

            # 1. Capture failure details
            payload = capture_failure(
                command=current_cmd,
                exit_code=current_exit_code,
                output=current_output,
                cwd=current_cwd,
            )

            # 2. Request root-cause diagnosis & remediation proposal
            c.print(
                f"\n[bold yellow]Diagnosing failure (remediation cycle {cycle}/{self.max_cycles})...[/bold yellow]"
            )
            diag_result: DiagnosticResult = diagnostic_engine.diagnose_sync(payload)

            # 3. Display diagnostic explanation
            c.print(
                f"\n[bold red]Failure Detected[/bold red] (exit code {current_exit_code}, category: [bold yellow]{diag_result.category.value}[/bold yellow]):\n"
                f"[dim]{diag_result.root_cause}[/dim]\n"
            )

            # 4. If no remediation proposal exists, halt automated loop
            if not diag_result.proposal or not diag_result.proposal.command.strip():
                c.print("[yellow]No automated remediation proposal available.[/yellow]")
                break

            # 5. Route proposal through interactive SafetyGate ([y/N/e]) per D-02
            proposal = diag_result.proposal
            proposal.remediation = True

            approved_cmd = safety_gate.process_proposal(
                proposal=proposal,
                console=c,
                prompt_session=prompt_session,
                input_fn=input_fn,
                edit_fn=edit_fn,
            )

            # 6. If cancelled by operator, halt recovery immediately
            if not approved_cmd:
                c.print("[yellow]Remediation cancelled by operator.[/yellow]")
                return current_exit_code

            # 7. Execute approved remediation command
            c.print(
                f"\n[bold cyan]Running remediation command (attempt {cycle}/{self.max_cycles}):[/bold cyan] [bold]{approved_cmd}[/bold]"
            )
            exec_result = runner(approved_cmd)

            # Unpack execution result
            if hasattr(exec_result, "exit_code") and hasattr(exec_result, "output"):
                new_exit_code = exec_result.exit_code
                new_output = exec_result.output
            elif isinstance(exec_result, tuple) and len(exec_result) == 2:
                new_exit_code, new_output = exec_result
            elif isinstance(exec_result, int):
                new_exit_code = exec_result
                new_output = f"Command exited with code {new_exit_code}"
            else:
                new_exit_code = 0
                new_output = ""

            # 8. Check outcome
            if new_exit_code == 0:
                c.print("\n[bold green]✓ Remediation successful.[/bold green]\n")
                self.reset()
                return 0

            # Remediation command itself failed
            current_cmd = approved_cmd
            current_exit_code = new_exit_code
            current_output = new_output

        # Exited loop without resolution
        if self.cycle_count >= self.max_cycles and current_exit_code != 0:
            c.print(f"\n[bold red]{HALT_NOTICE}[/bold red]\n")

        return current_exit_code

