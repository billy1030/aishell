"""Multi-turn conversational memory and sliding-window context compaction."""

import json
from pathlib import Path
from typing import List, Optional
from aishell.providers.base import ChatMessage

DEFAULT_MAX_WINDOW_MESSAGES: int = 8  # 4 user + 4 assistant turns per D-04
DEFAULT_MAX_ESTIMATED_TOKENS: int = 4000  # Token threshold per CONF-03, D-04


def estimate_tokens(text: str) -> int:
    """Estimate token count for text using the standard ~4 characters per token heuristic."""
    if not text:
        return 0
    return max(1, len(text) // 4)


class ConversationManager:
    """Manages multi-turn conversation history with sliding-window compaction."""

    def __init__(
        self,
        max_window_messages: int = DEFAULT_MAX_WINDOW_MESSAGES,
        max_estimated_tokens: int = DEFAULT_MAX_ESTIMATED_TOKENS,
    ) -> None:
        self.max_window_messages = max_window_messages
        self.max_estimated_tokens = max_estimated_tokens
        self.messages: List[ChatMessage] = []
        self.summary: Optional[str] = None

    def add_user_message(self, content: str) -> None:
        """Add a user turn and compact if limits are exceeded."""
        if content and content.strip():
            self.messages.append(ChatMessage(role="user", content=content.strip()))
            self.compact_history()

    def add_assistant_message(self, content: str) -> None:
        """Add an assistant turn and compact if limits are exceeded."""
        if content and content.strip():
            self.messages.append(ChatMessage(role="assistant", content=content.strip()))
            self.compact_history()

    def get_total_estimated_tokens(self) -> int:
        """Calculate total estimated token load of current message history and summary."""
        total = 0
        if self.summary:
            total += estimate_tokens(self.summary)
        for msg in self.messages:
            total += estimate_tokens(msg.content)
        return total

    def _summarize_slice(self, old_messages: List[ChatMessage]) -> str:
        """Create a compact deterministic summary from pruned messages."""
        topics = []
        for msg in old_messages:
            if msg.role == "user":
                # Take first line or up to 60 characters of user query
                first_line = msg.content.splitlines()[0][:60].strip()
                if first_line:
                    topics.append(f"user asked about '{first_line}'")
            elif msg.role == "assistant":
                # Take first line or up to 60 characters of assistant response
                first_line = msg.content.splitlines()[0][:60].strip()
                if first_line:
                    topics.append(f"assistant addressed '{first_line}'")

        summary_body = "; ".join(topics) if topics else "prior conversation turns"
        if self.summary:
            return f"{self.summary} -> then {summary_body}"
        return summary_body

    def compact_history(self) -> bool:
        """Compact older history into summary if exceeding window or token threshold."""
        needs_compaction = (
            len(self.messages) > self.max_window_messages
            or self.get_total_estimated_tokens() > self.max_estimated_tokens
        )

        if not needs_compaction:
            return False

        # Determine how many messages to retain in recent sliding window
        excess_count = len(self.messages) - self.max_window_messages
        if excess_count <= 0 and self.get_total_estimated_tokens() > self.max_estimated_tokens:
            # Token limit exceeded even with fewer messages than window, slice oldest pair
            excess_count = max(2, len(self.messages) // 2)

        # Ensure we always prune in pairs (user + assistant) to maintain turn alignment when possible
        prune_count = min(len(self.messages), max(2, excess_count))
        # Keep prune_count even if len(self.messages) allows
        if prune_count % 2 != 0 and prune_count < len(self.messages):
            prune_count += 1

        to_prune = self.messages[:prune_count]
        self.messages = self.messages[prune_count:]

        # Update summary
        new_summary = self._summarize_slice(to_prune)
        self.summary = new_summary
        return True

    def get_messages_for_llm(self, system_instruction: str = "") -> List[ChatMessage]:
        """Return active message history structured for LLM streaming.

        If a summary exists, prepends an introductory summary turn before recent messages.
        """
        output_messages: List[ChatMessage] = []

        if self.summary:
            summary_content = f"[Conversation Summary: earlier troubleshooting discussed {self.summary}]"
            output_messages.append(ChatMessage(role="system", content=summary_content))

        output_messages.extend(self.messages)
        return output_messages

    def clear(self) -> None:
        """Reset all conversational messages and compaction summary."""
        self.messages.clear()
        self.summary = None

    def save_to_file(self, path: Path) -> None:
        """Persist active conversation summary and messages to JSON."""
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                "summary": self.summary,
                "messages": [{"role": m.role, "content": m.content} for m in self.messages],
            }
            path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        except Exception:
            pass

    def load_from_file(self, path: Path) -> int:
        """Restore conversation summary and messages from JSON. Returns restored message count."""
        if not path.is_file():
            return 0
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            raw_msgs = data.get("messages", [])
            restored: List[ChatMessage] = []
            for item in raw_msgs:
                if isinstance(item, dict) and item.get("role") and item.get("content"):
                    restored.append(ChatMessage(role=str(item["role"]), content=str(item["content"])))
            self.messages = restored
            raw_summary = data.get("summary")
            self.summary = str(raw_summary) if raw_summary else None
            return len(self.messages)
        except Exception:
            return 0

