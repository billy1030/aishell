"""Unit tests for PrivacyGuard allowlist filtering and credential redaction."""

from aishell.context.inspector import inspect_system_context
from aishell.context.privacy import PrivacyGuard


def test_privacy_guard_allowlist():
    raw_env = {
        "PATH": "/usr/local/bin:/usr/bin",
        "SHELL": "/bin/bash",
        "USER": "deploy",
        "LANG": "en_US.UTF-8",
        "LC_ALL": "C.UTF-8",
        "LC_CTYPE": "en_US.UTF-8",
        "AWS_SECRET_ACCESS_KEY": "supersecretkey123",
        "GITHUB_TOKEN": "ghp_1234567890abcdef",
        "OPENAI_API_KEY": "sk-1234567890abcdef1234567890",
        "DATABASE_URL": "postgres://user:pass@localhost:5432/db",
        "MY_CUSTOM_SECRET": "confidential",
    }
    filtered = PrivacyGuard.filter_env(raw_env)

    # Allowed variables
    assert "PATH" in filtered
    assert "SHELL" in filtered
    assert "USER" in filtered
    assert "LANG" in filtered
    assert "LC_ALL" in filtered
    assert "LC_CTYPE" in filtered

    # Denied / sensitive variables
    assert "AWS_SECRET_ACCESS_KEY" not in filtered
    assert "GITHUB_TOKEN" not in filtered
    assert "OPENAI_API_KEY" not in filtered
    assert "DATABASE_URL" not in filtered
    assert "MY_CUSTOM_SECRET" not in filtered


def test_redact_pem_private_key():
    sample_key = (
        "-----BEGIN RSA PRIVATE KEY-----\n"
        "MIIEowIBAAKCAQEA0Y1+abcdefghijklmnopqrstuvwxyz1234567890\n"
        "-----END RSA PRIVATE KEY-----"
    )
    redacted = PrivacyGuard.redact_credentials(f"Certificate config:\n{sample_key}\nDone.")
    assert "[REDACTED:PRIVATE_KEY]" in redacted
    assert "BEGIN RSA PRIVATE KEY" not in redacted


def test_redact_database_uri():
    text = "Connect string: postgres://admin:secret123@db.internal:5432/analytics"
    redacted = PrivacyGuard.redact_credentials(text)
    assert "[REDACTED:DATABASE_URI]" in redacted
    assert "admin:secret123" not in redacted


def test_redact_aws_key():
    text = "Deploying with AKIAIOSFODNN7EXAMPLE key"
    redacted = PrivacyGuard.redact_credentials(text)
    assert "[REDACTED:AWS_KEY]" in redacted
    assert "AKIAIOSFODNN7EXAMPLE" not in redacted


def test_redact_api_keys():
    # OpenAI key
    text_openai = "key is sk-abcdefghijklmnopqrstuvwxyz123456"
    assert "[REDACTED:API_KEY]" in PrivacyGuard.redact_credentials(text_openai)

    # Anthropic key
    text_ant = "token: sk-ant-api03-abcdefghijklmnopqrstuvwxyz123456"
    assert "[REDACTED:API_KEY]" in PrivacyGuard.redact_credentials(text_ant)

    # Google API key
    text_google = "AIzaSyD-1234567890abcdefghijklmnopqrstuv"
    assert "[REDACTED:API_KEY]" in PrivacyGuard.redact_credentials(text_google)


def test_redact_jwt():
    jwt = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4ifQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
    text = f"Authorization: Bearer {jwt}"
    redacted = PrivacyGuard.redact_credentials(text)
    assert "[REDACTED:JWT]" in redacted
    assert jwt not in redacted


def test_redact_key_value_assignments():
    text = "password=SuperSecretPassword123 api_key: 'my_secret_api_token_here'"
    redacted = PrivacyGuard.redact_credentials(text)
    assert "SuperSecretPassword123" not in redacted
    assert "my_secret_api_token_here" not in redacted
    assert "[REDACTED:SECRET]" in redacted


def test_sanitize_env_vars_and_inspector_integration():
    ctx = inspect_system_context()
    # Check that env_vars is populated
    assert isinstance(ctx.env_vars, dict)
    # Check that only allowed variables exist in ctx.env_vars
    for k in ctx.env_vars.keys():
        assert PrivacyGuard.is_env_allowed(k)
