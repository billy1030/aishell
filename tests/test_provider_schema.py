"""Unit tests for CommandProposal schema and resilient dual-mode parser."""

import pytest
from pydantic import ValidationError

from aishell.providers.schema import CommandProposal, parse_proposal_from_text


def test_command_proposal_valid():
    prop = CommandProposal(
        command="find /var/log -name '*.log' -size +100M",
        purpose="Find large log files",
        explanation="-size +100M matches files larger than 100 megabytes",
        risk_tier="safe",
        requires_sudo=False,
    )
    assert prop.command == "find /var/log -name '*.log' -size +100M"
    assert prop.risk_tier == "safe"
    assert prop.requires_sudo is False
    assert prop.remediation is False


def test_command_proposal_empty_command_fails():
    with pytest.raises(ValidationError):
        CommandProposal(command="   ", purpose="Empty command")


def test_command_proposal_invalid_risk_tier_fails():
    with pytest.raises(ValidationError):
        CommandProposal(command="ls", purpose="list", risk_tier="catastrophic")  # type: ignore


def test_parse_proposal_raw_json():
    raw = """
    {
        "command": "df -h",
        "purpose": "Check disk space usage",
        "explanation": "-h prints human readable sizes",
        "risk_tier": "safe",
        "requires_sudo": false,
        "remediation": false
    }
    """
    prop = parse_proposal_from_text(raw)
    assert prop.command == "df -h"
    assert prop.purpose == "Check disk space usage"
    assert prop.risk_tier == "safe"


def test_parse_proposal_markdown_json_fence():
    raw = """Here is the command you requested:
```json
{
    "command": "systemctl restart nginx",
    "purpose": "Restart Nginx web server",
    "explanation": "Reloads configuration and restarts worker processes",
    "risk_tier": "mutating",
    "requires_sudo": true,
    "remediation": false
}
```
Let me know if you need more help!
"""
    prop = parse_proposal_from_text(raw)
    assert prop.command == "systemctl restart nginx"
    assert prop.purpose == "Restart Nginx web server"
    assert prop.risk_tier == "mutating"
    assert prop.requires_sudo is True


def test_parse_proposal_bash_code_fence_fallback():
    raw = """To check open ports on your Linux server, run the following command:

```bash
ss -tulpn
```

This uses socket statistics to list all listening TCP and UDP sockets with process IDs.
"""
    prop = parse_proposal_from_text(raw)
    assert prop.command == "ss -tulpn"
    assert "open ports" in prop.purpose.lower()
    assert prop.risk_tier == "mutating"  # safe default for unstructured fallback
    assert prop.requires_sudo is False


def test_parse_proposal_sudo_bash_fence():
    raw = """Run this to remove temporary files:
```sh
sudo rm -rf /tmp/build_*
```
"""
    prop = parse_proposal_from_text(raw)
    assert prop.command == "sudo rm -rf /tmp/build_*"
    assert prop.requires_sudo is True


def test_parse_proposal_plain_text_fallback():
    raw = "uptime"
    prop = parse_proposal_from_text(raw)
    assert prop.command == "uptime"
    assert prop.risk_tier == "mutating"
