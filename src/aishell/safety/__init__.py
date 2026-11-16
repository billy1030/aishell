"""Safety gate, risk classification, and command execution control package."""

from aishell.safety.classifier import (
    RiskLevel,
    classify_risk,
    classify_single_command,
    max_risk,
    split_compound_command,
)
from aishell.safety.display import (
    get_risk_badge,
    render_proposal,
)
from aishell.safety.gate import (
    GateAction,
    SafetyGate,
    is_interactive_stdin,
    prompt_confirmation,
    prompt_edit_command,
)

__all__ = [
    "GateAction",
    "RiskLevel",
    "SafetyGate",
    "classify_risk",
    "classify_single_command",
    "get_risk_badge",
    "is_interactive_stdin",
    "max_risk",
    "prompt_confirmation",
    "prompt_edit_command",
    "render_proposal",
    "split_compound_command",
]
