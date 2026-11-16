"""Unit tests for ConversationManager sliding-window retention, token bounds, and compaction."""

import pytest
from aishell.conversation.manager import (
    ConversationManager,
    estimate_tokens,
)
from aishell.providers.base import ChatMessage


def test_estimate_tokens() -> None:
    """Test standard character-to-token heuristic (~4 chars/token)."""
    assert estimate_tokens("") == 0
    assert estimate_tokens("hi") == 1
    assert estimate_tokens("12345678") == 2
    assert estimate_tokens("a" * 400) == 100


def test_conversation_manager_add_and_retrieve() -> None:
    """Adding user and assistant messages populates message history."""
    manager = ConversationManager(max_window_messages=8)
    manager.add_user_message("how do I check open ports?")
    manager.add_assistant_message("Use `ss -tuln` or `netstat -tuln`.")

    msgs = manager.get_messages_for_llm()
    assert len(msgs) == 2
    assert msgs[0].role == "user"
    assert msgs[0].content == "how do I check open ports?"
    assert msgs[1].role == "assistant"
    assert msgs[1].content == "Use `ss -tuln` or `netstat -tuln`."
    assert manager.summary is None


def test_conversation_manager_sliding_window_compaction() -> None:
    """When message count exceeds max_window_messages, older turns are pruned into a summary."""
    manager = ConversationManager(max_window_messages=4)

    # Turn 1
    manager.add_user_message("step 1: list files")
    manager.add_assistant_message("run ls -la")
    # Turn 2
    manager.add_user_message("step 2: check disk")
    manager.add_assistant_message("run df -h")

    assert len(manager.messages) == 4
    assert manager.summary is None

    # Turn 3 (exceeds window of 4)
    manager.add_user_message("step 3: inspect cpu")
    manager.add_assistant_message("run top")

    # Should have compacted Turn 1 into summary
    assert len(manager.messages) <= 4
    assert manager.summary is not None
    assert "step 1" in manager.summary

    llm_msgs = manager.get_messages_for_llm()
    # First message is the summary system context
    assert llm_msgs[0].role == "system"
    assert "Conversation Summary" in llm_msgs[0].content
    assert "step 3" in llm_msgs[-1].content or "run top" in llm_msgs[-1].content


def test_conversation_manager_token_threshold_compaction() -> None:
    """Large messages exceeding max_estimated_tokens trigger compaction."""
    # 50 tokens limit = ~200 characters
    manager = ConversationManager(max_window_messages=10, max_estimated_tokens=50)

    # Add a normal turn
    manager.add_user_message("small question")
    manager.add_assistant_message("small answer")

    # Add a massive turn (>200 chars)
    massive_text = "ERROR: " + ("database connection failed with timeout. " * 10)
    manager.add_user_message(massive_text)
    manager.add_assistant_message("retry connection")

    assert manager.summary is not None
    assert len(manager.messages) < 4


def test_conversation_manager_clear() -> None:
    """clear() resets messages and summary state."""
    manager = ConversationManager(max_window_messages=2)
    manager.add_user_message("q1")
    manager.add_assistant_message("a1")
    manager.add_user_message("q2")

    assert len(manager.messages) > 0
    assert manager.summary is not None

    manager.clear()
    assert len(manager.messages) == 0
    assert manager.summary is None
    assert len(manager.get_messages_for_llm()) == 0

