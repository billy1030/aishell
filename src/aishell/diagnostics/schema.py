"""Schemas and data models for shell command failure diagnostics."""

from enum import Enum
import re
from typing import Optional
from pydantic import BaseModel, Field

from aishell.context.privacy import PrivacyGuard
from aishell.providers.schema import CommandProposal


class FailureCategory(str, Enum):
    """Deterministic failure classifications for Linux shell commands."""

    PERMISSION_DENIED = "PERMISSION_DENIED"
    COMMAND_NOT_FOUND = "COMMAND_NOT_FOUND"
    NO_SUCH_FILE_OR_DIR = "NO_SUCH_FILE_OR_DIR"
    SERVICE_INACTIVE = "SERVICE_INACTIVE"
    PORT_COLLISION = "PORT_COLLISION"
    DISK_FULL = "DISK_FULL"
    GENERAL_ERROR = "GENERAL_ERROR"


def trim_and_redact_output(output: str, max_lines: int = 50, max_bytes: int = 4096) -> str:
    """Extract at most trailing max_lines, enforce max_bytes limit, and scrub credentials."""
    if not output:
        return ""

    # Split lines and retain trailing max_lines
    lines = output.splitlines()
    if len(lines) > max_lines:
        lines = lines[-max_lines:]
    text = "\n".join(lines)

    # Enforce byte limit on trailing output
    encoded = text.encode("utf-8")
    if len(encoded) > max_bytes:
        # Slice the trailing max_bytes and decode cleanly
        truncated_bytes = encoded[-max_bytes:]
        text = truncated_bytes.decode("utf-8", errors="ignore")

    # Scrub sensitive credentials, keys, URIs via PrivacyGuard
    return PrivacyGuard.redact_credentials(text)


def categorize_failure(command: str, exit_code: int, output: str) -> FailureCategory:
    """Categorize failure deterministically from exit code and output text patterns."""
    # Check 1: Command not found exit code or patterns
    if exit_code == 127 or re.search(
        r"(?:command not found|not found:\s*\w+|unknown command)", output, re.IGNORECASE
    ):
        return FailureCategory.COMMAND_NOT_FOUND

    # Check 2: Permission denied / privilege errors
    if exit_code in (126, 13) or re.search(
        r"(?:permission denied|operation not permitted|eacces|access denied|must be run as root|requires superuser|are you root\?)",
        output,
        re.IGNORECASE,
    ):
        return FailureCategory.PERMISSION_DENIED

    # Check 3: Missing files or directories
    if re.search(
        r"(?:no such file or directory|enoent|cannot access|cannot find path|directory does not exist|file not found)",
        output,
        re.IGNORECASE,
    ):
        return FailureCategory.NO_SUCH_FILE_OR_DIR

    # Check 4: Port collisions / address in use
    if re.search(
        r"(?:address already in use|eaddrinuse|port \d+ (?:is )?already in use|bind failed|could not bind to address)",
        output,
        re.IGNORECASE,
    ):
        return FailureCategory.PORT_COLLISION

    # Check 5: Disk full / quota exceeded
    if re.search(
        r"(?:no space left on device|enospc|disk quota exceeded|disk full|out of disk space)",
        output,
        re.IGNORECASE,
    ):
        return FailureCategory.DISK_FULL

    # Check 6: System services inactive / unit not found
    if re.search(
        r"(?:unit [^\s]+ (?:could not be found|not found)|service [^\s]+ (?:could not be found|not found)|inactive \(dead\)|failed to start [^\s]*|systemctl [^\s]* failed)",
        output,
        re.IGNORECASE,
    ):
        return FailureCategory.SERVICE_INACTIVE

    return FailureCategory.GENERAL_ERROR


def sanitize_failure_boundary(text: str) -> str:
    """Neutralize command failure tag breakout attempts."""
    if not text:
        return ""
    sanitized = text.replace("</command_failure>", "&lt;/command_failure&gt;")
    sanitized = sanitized.replace("<command_failure", "&lt;command_failure")
    return sanitized


class FailurePayload(BaseModel):
    """Captured failure incident details for diagnostics."""

    command: str = Field(..., description="The shell command that failed")
    exit_code: int = Field(..., description="Non-zero exit status code")
    output: str = Field(default="", description="Raw command stdout and stderr combined")
    trimmed_output: str = Field(default="", description="Sanitized and trimmed error output")
    cwd: str = Field(default=".", description="Current working directory where command executed")
    is_root: bool = Field(default=False, description="Whether execution was under root privileges")
    category: FailureCategory = Field(
        default=FailureCategory.GENERAL_ERROR,
        description="Deterministic classification of the failure",
    )


class DiagnosticResult(BaseModel):
    """AI-generated diagnosis and optional targeted remediation proposal."""

    root_cause: str = Field(..., description="Concise explanation of the root failure cause")
    category: FailureCategory = Field(
        default=FailureCategory.GENERAL_ERROR,
        description="Failure category associated with diagnosis",
    )
    proposal: Optional[CommandProposal] = Field(
        default=None,
        description="Targeted follow-up remediation command proposal, if applicable",
    )
    raw_response: str = Field(
        default="", description="Raw text response returned by the AI provider"
    )


def format_failure_observation(payload: FailurePayload) -> str:
    """Format FailurePayload inside untrusted boundary tags to prevent prompt injection."""
    safe_output = sanitize_failure_boundary(payload.trimmed_output)
    user_status = "root (uid 0)" if payload.is_root else "standard unprivileged user"

    lines = [
        '<command_failure untrusted="true">',
        f"Failed Command: {payload.command}",
        f"Exit Code: {payload.exit_code}",
        f"Detected Category: {payload.category.value}",
        f"Working Directory: {payload.cwd}",
        f"User Privilege: {user_status}",
        "",
        "Output (Trailing sanitized lines):",
        safe_output,
        "</command_failure>",
    ]
    return "\n".join(lines)
