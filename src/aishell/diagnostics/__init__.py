"""Diagnostic engine and error remediation modules for aishell."""

from aishell.diagnostics.engine import (
    DiagnosticEngine,
    capture_failure,
    should_diagnose,
)
from aishell.diagnostics.remediation import (
    HALT_NOTICE,
    MAX_REMEDIATION_CYCLES,
    RemediationController,
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
    "HALT_NOTICE",
    "MAX_REMEDIATION_CYCLES",
    "RemediationController",
    "capture_failure",
    "categorize_failure",
    "format_failure_observation",
    "should_diagnose",
    "trim_and_redact_output",
]

