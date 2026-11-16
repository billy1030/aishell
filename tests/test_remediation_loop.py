"""Tests for bounded remediation controller and 2-cycle loop state machine."""

from typing import AsyncIterator, List, Optional
import pytest
from rich.console import Console

from aishell.diagnostics.engine import DiagnosticEngine
from aishell.diagnostics.remediation import (
    HALT_NOTICE,
    MAX_REMEDIATION_CYCLES,
    RemediationController,
)
from aishell.providers.base import BaseProvider, ChatMessage
from aishell.providers.schema import CommandProposal
from aishell.safety.gate import SafetyGate


class MockProvider(BaseProvider):
    """Mock provider cycling through preconfigured response chunks."""

    def __init__(self, responses: List[str]) -> None:
        super().__init__(name="mock", model="mock-model")
        self.responses = responses
        self.call_count = 0

    def validate_credentials(self) -> None:
        pass

    async def generate_proposal(
        self, query: str, system_context: Optional[str] = None
    ) -> CommandProposal:
        raise NotImplementedError

    async def stream_chat(
        self, messages: List[ChatMessage], system_prompt: Optional[str] = None
    ) -> AsyncIterator[str]:
        if self.call_count < len(self.responses):
            resp = self.responses[self.call_count]
            self.call_count += 1
        else:
            resp = self.responses[-1] if self.responses else ""
        yield resp


def test_remediation_controller_state_machine() -> None:
    """RemediationController enforces MAX_REMEDIATION_CYCLES = 2 and reset."""
    controller = RemediationController()
    assert controller.cycle_count == 0
    assert controller.can_remediate() is True

    assert controller.record_attempt() == 1
    assert controller.can_remediate() is True

    assert controller.record_attempt() == 2
    assert controller.can_remediate() is False

    controller.reset()
    assert controller.cycle_count == 0
    assert controller.can_remediate() is True


def test_remediation_loop_success_cycle_1() -> None:
    """When operator confirms and remediation succeeds in Cycle 1, counter resets to 0."""
    response_json = """The log directory is missing.
```json
{
  "command": "mkdir -p /var/log/app",
  "purpose": "Create missing directory",
  "risk_tier": "mutating",
  "requires_sudo": false,
  "remediation": true
}
```"""
    provider = MockProvider([response_json])
    engine = DiagnosticEngine(provider=provider)
    gate = SafetyGate(console=Console(record=True))
    controller = RemediationController()

    executed_commands = []

    def mock_executor(cmd: str):
        executed_commands.append(cmd)
        return 0, "Created directory"

    # Input 'y' for confirmation
    exit_code = controller.run_remediation_loop(
        failed_command="cat /var/log/app/log.txt",
        exit_code=1,
        output="No such file or directory",
        diagnostic_engine=engine,
        safety_gate=gate,
        executor_fn=mock_executor,
        input_fn=lambda _: "y",
    )

    assert exit_code == 0
    assert controller.cycle_count == 0  # Reset upon success
    assert executed_commands == ["mkdir -p /var/log/app"]
    assert provider.call_count == 1


def test_remediation_loop_two_cycles_and_hard_stop() -> None:
    """If Cycle 1 fails, Cycle 2 runs. If Cycle 2 fails, automated loop halts with notice."""
    resp1 = """Cycle 1 explanation.
```json
{
  "command": "systemctl restart app",
  "purpose": "Attempt restart",
  "risk_tier": "mutating",
  "remediation": true
}
```"""
    resp2 = """Cycle 2 explanation.
```json
{
  "command": "journalctl -u app --no-pager -n 20",
  "purpose": "Inspect daemon logs",
  "risk_tier": "safe",
  "remediation": true
}
```"""
    provider = MockProvider([resp1, resp2])
    engine = DiagnosticEngine(provider=provider)
    record_console = Console(record=True)
    gate = SafetyGate(console=record_console)
    controller = RemediationController()

    executed_commands = []

    def mock_failing_executor(cmd: str):
        executed_commands.append(cmd)
        return 1, f"Failed executing {cmd}"

    exit_code = controller.run_remediation_loop(
        failed_command="curl http://localhost:8080",
        exit_code=7,
        output="Failed to connect to localhost port 8080: Connection refused",
        diagnostic_engine=engine,
        safety_gate=gate,
        executor_fn=mock_failing_executor,
        console=record_console,
        input_fn=lambda _: "y",  # Approve both attempts
    )

    assert exit_code == 1
    assert controller.cycle_count == 2
    assert executed_commands == [
        "systemctl restart app",
        "journalctl -u app --no-pager -n 20",
    ]
    output_text = record_console.export_text()
    assert "Maximum remediation attempts (2) reached" in output_text


def test_remediation_loop_user_cancellation() -> None:
    """When user cancels at confirmation prompt, remediation stops immediately."""
    response_json = """Need root permission.
```json
{
  "command": "sudo rm -rf /tmp/corrupt",
  "purpose": "Clear corrupt state",
  "risk_tier": "high_risk",
  "remediation": true
}
```"""
    provider = MockProvider([response_json])
    engine = DiagnosticEngine(provider=provider)
    gate = SafetyGate(console=Console(record=True))
    controller = RemediationController()

    executed_commands = []

    def mock_executor(cmd: str):
        executed_commands.append(cmd)
        return 0, ""

    # Input 'n' to cancel
    exit_code = controller.run_remediation_loop(
        failed_command="app-cleanup",
        exit_code=1,
        output="Permission denied",
        diagnostic_engine=engine,
        safety_gate=gate,
        executor_fn=mock_executor,
        input_fn=lambda _: "n",
    )

    assert exit_code == 1
    assert len(executed_commands) == 0
    assert controller.cycle_count == 1  # 1 attempt was prepared, then cancelled


def test_remediation_loop_bypasses_sigint_130() -> None:
    """Exit code 130 (SIGINT / Ctrl+C) must bypass remediation entirely."""
    provider = MockProvider([])
    engine = DiagnosticEngine(provider=provider)
    gate = SafetyGate(console=Console(record=True))
    controller = RemediationController()

    exit_code = controller.run_remediation_loop(
        failed_command="ping 8.8.8.8",
        exit_code=130,
        output="",
        diagnostic_engine=engine,
        safety_gate=gate,
        executor_fn=lambda _: 0,
    )

    assert exit_code == 130
    assert controller.cycle_count == 0
    assert provider.call_count == 0

