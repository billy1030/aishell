"""Integration tests for REPL multi-turn conversational memory and compaction per CONF-03."""

from typing import AsyncIterator, List, Optional
import pytest
from rich.console import Console

from aishell.config.settings import AishellSettings
from aishell.providers.base import BaseProvider, ChatMessage
from aishell.providers.schema import CommandProposal
from aishell.ui.repl import InteractiveREPL


class MultiTurnTrackingProvider(BaseProvider):
    """Provider tracking received ChatMessages across multi-turn invocations."""

    def __init__(self, responses: List[str]) -> None:
        super().__init__(name="mock", model="mock-model")
        self.responses = responses
        self.received_messages_history: List[List[ChatMessage]] = []
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
        # Record a snapshot of messages received for this turn
        self.received_messages_history.append(list(messages))
        if self.call_count < len(self.responses):
            resp = self.responses[self.call_count]
            self.call_count += 1
        else:
            resp = self.responses[-1] if self.responses else "ok"
        yield resp


def test_repl_retains_multi_turn_history() -> None:
    """Subsequent REPL queries should include prior turns in stream_chat messages."""
    resp1 = "To check disk space, run `df -h`."
    resp2 = "To check memory instead, run `free -m`."

    provider = MultiTurnTrackingProvider([resp1, resp2])
    console = Console(record=True)
    repl = InteractiveREPL(
        settings=AishellSettings(),
        console=console,
        provider=provider,
    )

    # Turn 1
    repl.dispatch_input("how do I check disk space?")
    assert len(provider.received_messages_history) == 1
    turn1_msgs = provider.received_messages_history[0]
    assert len(turn1_msgs) == 1
    assert turn1_msgs[0].role == "user"
    assert "disk space" in turn1_msgs[0].content

    # Turn 2: Follow-up question
    repl.dispatch_input("what about memory?")
    assert len(provider.received_messages_history) == 2
    turn2_msgs = provider.received_messages_history[1]

    # Turn 2 should contain: User 1, Assistant 1, User 2
    assert len(turn2_msgs) == 3
    assert turn2_msgs[0].role == "user"
    assert "disk space" in turn2_msgs[0].content
    assert turn2_msgs[1].role == "assistant"
    assert "df -h" in turn2_msgs[1].content
    assert turn2_msgs[2].role == "user"
    assert "what about memory?" in turn2_msgs[2].content


def test_repl_compaction_in_long_session() -> None:
    """Long REPL conversations trigger sliding window compaction, passing summary turn."""
    # Create responses for 6 turns
    responses = [f"Answer for step {i}" for i in range(1, 7)]
    provider = MultiTurnTrackingProvider(responses)
    repl = InteractiveREPL(
        settings=AishellSettings(),
        console=Console(record=True),
        provider=provider,
    )

    # Set smaller window (4 messages = 2 turns) to verify compaction quickly
    repl.conversation.max_window_messages = 4

    for i in range(1, 5):
        repl.dispatch_input(f"step {i}: check condition {i}")

    # After 4 turns, compaction should have occurred
    assert repl.conversation.summary is not None

    last_received = provider.received_messages_history[-1]
    # First message in compacted history is the system summary
    assert any(m.role == "system" and "Conversation Summary" in m.content for m in last_received)


def test_repl_clear_resets_conversation_memory() -> None:
    """Invoking /clear or :clear resets conversation memory and summary."""
    resp = "Files listed."
    provider = MultiTurnTrackingProvider([resp, "Turn after clear"])
    repl = InteractiveREPL(
        settings=AishellSettings(),
        console=Console(record=True),
        provider=provider,
    )

    repl.dispatch_input("turn 1 before clear")
    assert len(repl.conversation.messages) == 2

    # Issue clear meta command
    repl.dispatch_input(":clear")
    assert len(repl.conversation.messages) == 0
    assert repl.conversation.summary is None

    # Next turn should be fresh (only 1 user message)
    repl.dispatch_input("turn 1 after clear")
    last_turn_msgs = provider.received_messages_history[-1]
    assert len(last_turn_msgs) == 1
    assert last_turn_msgs[0].content == "turn 1 after clear"

