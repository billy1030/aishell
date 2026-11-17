"""Privacy Guard providing environment variable allowlist filtering and credential redaction."""

import fnmatch
import re
from typing import Dict, Pattern, Tuple

SAFE_ENV_ALLOWLIST = {
    "PATH",
    "SHELL",
    "USER",
    "LOGNAME",
    "TERM",
    "LANG",
    "PWD",
    "HOME",
    "EDITOR",
    "PAGER",
}

SAFE_ENV_PREFIXES = (
    "LC_",
    "DISTRO_",
)

# Compiled regex patterns for credential redaction in priority order
_REDACTION_PATTERNS: list[Tuple[Pattern[str], str]] = [
    # 1. PEM Private Keys
    (
        re.compile(r"-----BEGIN [A-Z ]+PRIVATE KEY-----[^-]+-----END [A-Z ]+PRIVATE KEY-----", re.DOTALL),
        "[REDACTED:PRIVATE_KEY]",
    ),
    # 2. Database connection URIs
    (
        re.compile(r"(?:postgres|postgresql|mysql|mongodb|redis)://[^\s'\"]+", re.IGNORECASE),
        "[REDACTED:DATABASE_URI]",
    ),
    # 3. AWS Access Keys
    (
        re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
        "[REDACTED:AWS_KEY]",
    ),
    # 4. Vendor API Keys (Anthropic, OpenAI, Gemini)
    (
        re.compile(r"\bsk-ant-[a-zA-Z0-9_\-]{20,}\b"),
        "[REDACTED:API_KEY]",
    ),
    (
        re.compile(r"\bsk-[a-zA-Z0-9]{20,}\b"),
        "[REDACTED:API_KEY]",
    ),
    (
        re.compile(r"\bAIza[0-9A-Za-z_-]{35,}\b"),
        "[REDACTED:API_KEY]",
    ),
    # 5. JWT Tokens
    (
        re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_\-\.]{10,}\b"),
        "[REDACTED:JWT]",
    ),
    # 6. Key-Value secret assignments (api_key=..., password=..., secret=...)
    (
        re.compile(
            r"((?:api[_-]?key|secret|token|password|pwd)\s*[:=]\s*['\"]?)([a-zA-Z0-9_\-\.]{8,})(['\"]?)",
            re.IGNORECASE,
        ),
        r"\1[REDACTED:SECRET]\3",
    ),
]


class PrivacyGuard:
    """Sanitizes environment variables and redacts sensitive credentials per D-02 and CTXT-02."""

    @classmethod
    def is_env_allowed(cls, var_name: str) -> bool:
        """Check if environment variable name matches allowlist or approved prefixes."""
        u_name = var_name.upper()
        if u_name in SAFE_ENV_ALLOWLIST:
            return True
        for prefix in SAFE_ENV_PREFIXES:
            if u_name.startswith(prefix):
                return True
        return False

    @classmethod
    def filter_env(cls, env: Dict[str, str]) -> Dict[str, str]:
        """Filter environment mapping to retain only allowlisted variables."""
        return {k: v for k, v in env.items() if cls.is_env_allowed(k)}

    @classmethod
    def redact_credentials(cls, text: str) -> str:
        """Scan text and replace sensitive credentials with typed redaction placeholders."""
        if not text:
            return ""
        result = text
        for pattern, replacement in _REDACTION_PATTERNS:
            result = pattern.sub(replacement, result)
        return result

    @classmethod
    def redact(cls, text: str) -> str:
        """Alias for redact_credentials for backwards compatibility and ease of use."""
        return cls.redact_credentials(text)

    @classmethod
    def sanitize_env_vars(cls, env: Dict[str, str]) -> Dict[str, str]:
        """Filter environment variables against allowlist and redact any credentials in values."""
        filtered = cls.filter_env(env)
        return {k: cls.redact_credentials(v) for k, v in filtered.items()}
