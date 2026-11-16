"""Diagnostic engine and error remediation modules for aishell."""

from aishell.diagnostics.engine import (
    DiagnosticEngine,
    capture_failure,
    should_diagnose,
)
from aishell.diagnostics.schema import (
    DiagnosticResult,
    FailureCategory,
    FailurePayload,
    categorize_failure,
    format_failure_observation,
    trim_and_redact_output,
)

__all__ = [
    "DiagnosticEngine",
    "DiagnosticResult",
    "FailureCategory",
    "FailurePayload",
    "capture_failure",
    "categorize_failure",
    "format_failure_observation",
    "should_diagnose",
    "trim_and_redact_output",
]

