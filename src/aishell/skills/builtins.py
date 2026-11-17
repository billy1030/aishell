"""Built-in Linux & DevOps AI skills shipped with aishell."""

from typing import List
from aishell.skills.schema import Skill

BUILTIN_SKILLS: List[Skill] = [
    Skill(
        name="repo-study",
        description="Clone and analyze GitHub repositories or local codebases step-by-step.",
        triggers=["github.com", "study", "analyze repo", "repository", "codebase", "clone"],
        source="builtin",
        instructions=(
            "When asked to study or analyze a GitHub repository or local codebase:\n"
            "1. If it is a remote GitHub URL and not yet cloned, propose a shallow clone into /tmp "
            "(e.g. `git clone --depth 1 <url> /tmp/<name>` or reuse existing directory).\n"
            "2. In the next step after receiving <command_output>, inspect the directory tree and key files "
            "(e.g. `find /tmp/<name> -maxdepth 2 -not -path '*/.*' && head -n 120 /tmp/<name>/README*`).\n"
            "3. If needed, inspect package manifests (pyproject.toml, package.json, Cargo.toml, go.mod) or main entrypoints.\n"
            "4. Once you have sufficient context, provide a structured summary covering purpose, architecture, key modules, and setup—without proposing unnecessary extra commands."
        ),
    ),
    Skill(
        name="web-fetch",
        description="Fetch and extract readable content from URLs, APIs, or web pages via curl and Python.",
        triggers=["http://", "https://", "fetch", "url", "webpage", "search internet", "api"],
        source="builtin",
        instructions=(
            "When asked to retrieve information from a specific URL or web API:\n"
            "1. Use `curl -fsSL -m 15 <url>` (and pipe through `python3` to strip HTML tags or format JSON if needed).\n"
            "2. For GitHub repositories, prefer GitHub REST API (`https://api.github.com/repos/<owner>/<repo>`) or `raw.githubusercontent.com`.\n"
            "3. Never fabricate URL contents; only summarize what appears in <command_output>."
        ),
    ),
    Skill(
        name="systemd-triage",
        description="Diagnose failing or stopped systemd services and journalctl logs.",
        triggers=["systemd", "systemctl", "service", "journalctl", "daemon", "unit failed"],
        source="builtin",
        instructions=(
            "When troubleshooting a Linux service or systemd unit:\n"
            "1. Start with read-only inspection: `systemctl status <service> --no-pager` and `journalctl -u <service> -n 50 --no-pager`.\n"
            "2. Identify the exact error line or config path before proposing any restart or configuration change."
        ),
    ),
    Skill(
        name="docker-debug",
        description="Inspect and troubleshoot Docker containers, logs, networks, and Compose stacks.",
        triggers=["docker", "container", "compose", "dockerfile", "image"],
        source="builtin",
        instructions=(
            "When troubleshooting Docker containers:\n"
            "1. Check running/exited containers with `docker ps -a`.\n"
            "2. Inspect logs with `docker logs --tail 80 <container>` or container state with `docker inspect`.\n"
            "3. Summarize the root cause before suggesting `docker restart` or rebuilds."
        ),
    ),
    Skill(
        name="network-audit",
        description="Inspect listening sockets, firewall rules, DNS resolution, and network interfaces.",
        triggers=["port", "listening", "network", "dns", "firewall", "ip", "socket", "ss ", "netstat"],
        source="builtin",
        instructions=(
            "When auditing network connectivity or open ports on Linux:\n"
            "1. Prefer `ss -tulnp` for listening ports, `ip -brief addr` for interfaces, and `resolvectl status` or `cat /etc/resolv.conf` for DNS.\n"
            "2. Keep inspection commands read-only."
        ),
    ),
]

