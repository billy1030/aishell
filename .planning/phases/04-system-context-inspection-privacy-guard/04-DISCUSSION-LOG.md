# Phase 4 Discussion Log: System Context Inspection & Privacy Guard

## Discussion Summary
Autonomous pre-planning discussion for Phase 4:
1. **Linux Distribution & Environment Detection (`CTXT-01`)**:
   - Use standard `distro` library for `/etc/os-release` parsing (Debian, Ubuntu, RHEL, Fedora, Arch, Alpine).
   - Lightweight git inspection reading `.git/HEAD` or running `git rev-parse --abbrev-ref HEAD` with timeout.
   - Detect primary package manager based on binaries present in PATH (`apt-get`, `dnf`, `pacman`, `apk`, `zypper`).
2. **Environment Variable Sanitization & Credential Redaction (`CTXT-02`)**:
   - Strict allowlist approach rather than denylist: only pre-approved variables are retained.
   - Regex scanning of query and observations for secrets (API keys, private keys, JWTs, connection strings).
3. **Indirect Prompt Injection Defense (`CTXT-03`)**:
   - Encapsulate observations inside `<system_observation untrusted="true">`.
   - Prevent jailbreaks from untrusted filenames or logs by escaping boundary tags.
4. **Context Transparency (`CTXT-04`)**:
   - Meta-command `/context` in REPL and `--context` CLI option.

