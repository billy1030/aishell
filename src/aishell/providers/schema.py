"""Structured command proposal schema and resilient dual-mode parser."""

import json
import re
from typing import Any, Dict, Literal, Optional
from pydantic import BaseModel, Field, field_validator


class CommandProposal(BaseModel):
    """Structured proposal representing a planned shell command with risk assessment."""

    command: str = Field(..., description="The exact executable shell command string")
    purpose: str = Field(..., description="Concise one-sentence description of intent")
    explanation: str = Field(
        default="", description="Explanation of flags, parameters, and mechanics"
    )
    risk_tier: Literal["safe", "mutating", "high_risk"] = Field(
        default="safe",
        description="Blast-radius risk tier: safe (read-only), mutating (writes/alters), high_risk (destructive/system-wide)",
    )
    requires_sudo: bool = Field(
        default=False, description="Whether command needs administrative/root privileges"
    )
    remediation: bool = Field(
        default=False, description="Whether this proposal remediates a prior command failure"
    )

    @field_validator("command")
    @classmethod
    def validate_command_non_empty(cls, v: str) -> str:
        clean = v.strip()
        if not clean:
            raise ValueError("Command string cannot be empty")
        return clean


def _extract_json_block(text: str) -> Optional[str]:
    """Find and return JSON block from text if present."""
    # Pattern 1: ```json ... ```
    match = re.search(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", text, re.IGNORECASE)
    if match:
        return match.group(1)

    # Pattern 2: Raw outermost { ... }
    match = re.search(r"(\{[\s\S]*\})", text)
    if match:
        return match.group(1)

    return None


def _extract_bash_block(text: str) -> Optional[str]:
    """Extract code inside explicit ```bash, ```sh, ```zsh, or ```shell code block."""
    match = re.search(r"```(?:bash|sh|zsh|shell)\s*\n([\s\S]*?)\n```", text, re.IGNORECASE)
    if match:
        cmd = match.group(1).strip()
        if cmd:
            return cmd
    return None


def extract_proposal_from_text(raw_text: str) -> Optional[CommandProposal]:
    """Extract a CommandProposal from model output if structured JSON or a code block is found.

    Returns None if no structured proposal or command code block is present.
    """
    clean_text = raw_text.strip()
    if not clean_text:
        return None

    # Step 1: Attempt JSON extraction
    json_candidate = _extract_json_block(clean_text)
    if json_candidate:
        try:
            data = json.loads(json_candidate)
            if isinstance(data, dict) and "command" in data and str(data["command"]).strip():
                return CommandProposal.model_validate(data)
        except Exception:
            pass

    # Step 2: Attempt fallback markdown bash code fence extraction
    bash_candidate = _extract_bash_block(clean_text)
    if bash_candidate and bash_candidate.strip():
        from aishell.safety.classifier import classify_risk

        cmd_clean = bash_candidate.strip()
        lines = [
            line.strip()
            for line in clean_text.splitlines()
            if line.strip() and not line.strip().startswith("```") and not line.strip().startswith("#")
        ]
        purpose = lines[0] if lines else "Execute proposed command"
        requires_sudo = cmd_clean.startswith("sudo ")
        inferred_risk = classify_risk(cmd_clean).value
        return CommandProposal(
            command=cmd_clean,
            purpose=purpose,
            explanation="Extracted from markdown code block",
            risk_tier=inferred_risk,
            requires_sudo=requires_sudo,
        )

    return None


def parse_proposal_from_text(raw_text: str) -> CommandProposal:
    """Parse a CommandProposal from model output with resilient dual-mode fallback.

    Mode 1: Structured JSON block (either raw or wrapped in ```json ``` markdown).
    Mode 2: Markdown code fence fallback (```bash ... ```) with surrounding text as purpose.
    Mode 3: Single-line fallback.
    """
    proposal = extract_proposal_from_text(raw_text)
    if proposal is not None:
        return proposal

    clean_text = raw_text.strip()
    # Step 3: Single line command fallback
    first_line = clean_text.splitlines()[0] if clean_text else "true"
    return CommandProposal(
        command=first_line,
        purpose="Execute command",
        explanation="Raw text proposal",
        risk_tier="mutating",
    )
