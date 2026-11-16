"""Integration tests for REPL diagnostic capture and bounded remediation loop."""

from typing import AsyncIterator, List, Optional
import pytest
from rich.console import Console

from aishell.config.settings import AishellSettings
from aishell.providers.base import BaseProvider, ChatMessage
from aishell.providers.schema import CommandProposal
from aishell.ui.repl import InteractiveREPL


class MockStreamingProvider(BaseProvider):
    """Mock provider returning structured responses."""

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


def test_repl_direct_command_failure_triggers_remediation_success() -> None:
    """Direct shell execution failure (!cmd) invokes diagnostic engine and remediation."""
    remediation_json = """Target file is missing.
```json
{
  "command": "touch /tmp/created.txt",
  "purpose": "Create the missing file",
  "risk_tier": "mutating",
  "remediation": true
}
```"""
    provider = MockStreamingProvider([remediation_json])
    record_console = Console(record=True)

    executed = []

    def mock_executor(cmd: str):
        executed.append(cmd)
        if cmd == "cat /tmp/missing.txt":
            return 1, "cat: /tmp/missing.txt: No such file or directory"
        return 0, ""

    settings = AishellSettings()
    repl = InteractiveREPL(
        settings=settings,
        console=record_console,
        provider=provider,
        executor_fn=mock_executor,
    )

    # Monkeypatch safety gate input to confirm
    repl.safety_gate.process_proposal = lambda proposal, **kwargs: proposal.command

    repl.dispatch_input("!cat /tmp/missing.txt")

    assert executed == ["cat /tmp/missing.txt", "touch /tmp/created.txt"]
    assert repl.remediation_controller.cycle_count == 0
    output_text = record_console.export_text()
    assert "Remediation successful" in output_text


def test_repl_remediation_hard_stop_after_two_cycles() -> None:
    """If remediation attempts fail twice, REPL halts recovery with explicit notice."""
    resp1 = """Cycle 1 fix.
```json
{
  "command": "fix1",
  "purpose": "Attempt 1",
  "risk_tier": "safe",
  "remediation": true
}
```"""
    resp2 = """Cycle 2 fix.
```json
{
  "command": "fix2",
  "purpose": "Attempt 2",
  "risk_tier": "safe",
  "remediation": true
}
```"""
    provider = MockStreamingProvider([resp1, resp2])
    record_console = Console(record=True)

    executed = []

    def mock_always_failing_executor(cmd: str):
        executed.append(cmd)
        return 1, f"Error running {cmd}"

    repl = InteractiveREPL(
        settings=AishellSettings(),
        console=record_console,
        provider=provider,
        executor_fn=mock_always_failing_executor,
    )

    # Auto-confirm remediation commands
    repl.safety_gate.process_proposal = lambda proposal, **kwargs: proposal.command

    repl.dispatch_input("!broken_cmd")

    assert executed == ["broken_cmd", "fix1", "fix2"]
    assert repl.remediation_controller.cycle_count == 2
    output_text = record_console.export_text()
    assert "Maximum remediation attempts (2) reached" in output_text


def test_repl_exit_code_130_bypasses_remediation() -> None:
    """Exit code 130 (SIGINT / Ctrl+C) must not trigger remediation in REPL."""
    provider = MockStreamingProvider([])
    record_console = Console(record=True)

    def mock_sigint_executor(cmd: str):
        return 130, ""

    repl = InteractiveREPL(
        settings=AishellSettings(),
        console=record_console,
        provider=provider,
        executor_fn=mock_sigint_executor,
    )

    repl.dispatch_input("!sleep 100")

    assert repl.remediation_controller.cycle_count == 0
    assert provider.call_count == 0


def test_repl_operator_declining_remediation() -> None:
    """Operator declining proposal ([n]) cancels remediation immediately."""
    resp = """Fix available.
```json
{
  "command": "dangerous-fix",
  "purpose": "Risky repair",
  "risk_tier": "high_risk",
  "remediation": true
}
```"""
    provider = MockStreamingProvider([resp])
    record_console = Console(record=True)

    executed = []

    def mock_executor(cmd: str):
        executed.append(cmd)
        return 1, "Failed"

    repl = InteractiveREPL(
        settings=AishellSettings(),
        console=record_console,
        provider=provider,
        executor_fn=mock_executor,
    )

    # Operator declines (returns None)
    repl.safety_gate.process_proposal = lambda proposal, **kwargs: None

    repl.dispatch_input("!bad_command")

    assert executed == ["bad_command"]
    output_text = record_console.export_text()
    assert "Remediation cancelled by operator" in output_text

