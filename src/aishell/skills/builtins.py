"""Built-in Linux & DevOps AI skills shipped with aishell."""

from typing import List
from aishell.skills.schema import Skill

BUILTIN_SKILLS: List[Skill] = [
    Skill(
        name="repo-study",
        description="Clone and analyze GitHub repositories or local codebases step-by-step.",
        triggers=["github.com", "gitlab.com", "study repo", "analyze repo", "repository", "codebase", "clone"],
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
        name="web-search",
        description="Search the web from the terminal using curl and Python (DuckDuckGo Lite / Wikipedia).",
        triggers=["search", "web search", "google", "duckduckgo", "look up", "find online", "search internet"],
        source="builtin",
        instructions=(
            "When asked to search the internet or look up current information:\n"
            "1. Propose a read-only command using `curl` and `python3` to query DuckDuckGo Lite (`https://lite.duckduckgo.com/lite/?q=<url_encoded_query>`) "
            "and parse the top result titles, URLs, and snippets cleanly.\n"
            "2. Example one-liner:\n"
            "   `python3 -c \"import urllib.request, urllib.parse, re, html; q=urllib.parse.quote('YOUR QUERY'); "
            "req=urllib.request.Request('https://lite.duckduckgo.com/lite/?q='+q, headers={'User-Agent':'Mozilla/5.0'}); "
            "raw=urllib.request.urlopen(req, timeout=15).read().decode('utf-8','ignore'); "
            "links=re.findall(r'<a[^>]+class=\\\"result-link\\\"[^>]+href=\\\"([^\\\"]+)\\\"[^>]*>(.*?)</a>', raw, re.S); "
            "print('\\n'.join(f'{i+1}. {html.unescape(re.sub(r\\\"<[^>]+>\\\",\\\"\\\",t)).strip()} -> {u}' for i,(u,t) in enumerate(links[:8])))\"`\n"
            "3. After receiving <command_output>, summarize the relevant findings or propose fetching a specific result URL if more detail is needed.\n"
            "4. Never fabricate search results; only report what appears in <command_output>."
        ),
    ),
    Skill(
        name="web-fetch",
        description="Fetch and extract readable content from URLs, APIs, or web pages via curl and Python.",
        triggers=["http://", "https://", "fetch", "url", "webpage", "search internet", "api"],
        source="builtin",
        instructions=(
            "When asked to retrieve information from a specific URL or web API:\n"
            "1. Start by fetching the exact URL the user provided using `curl -fsSL -m 15 <url>`.\n"
            "2. When stripping HTML in Python, remove `<script>`, `<style>`, `<nav>`, `<header>`, `<footer>`, and `<aside>` first (and prefer `<main>` or `<article>` if present) so navigation sidebars don't waste output.\n"
            "3. For GitHub repositories, prefer GitHub REST API (`https://api.github.com/repos/<owner>/<repo>`) or `raw.githubusercontent.com`.\n"
            "4. Never fabricate URL contents; only summarize what appears in <command_output>."
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
        name="find-skills",
        description="Search local aishell skills or discover/install community SKILL.md skills via skills.sh / GitHub.",
        triggers=["findskills", "find skills", "search skills", "discover skills", "install skill", "skills.sh"],
        source="builtin",
        instructions=(
            "When asked to find, discover, or install AI skills:\n"
            "1. For local skills, remind the user they can run `:skills` or `:findskills <keyword>` in aishell.\n"
            "2. To search the community skills ecosystem (skills.sh / vercel-labs/skills), propose:\n"
            "   `npx skills find <query>` (if Node/npx is available) or search GitHub:\n"
            "   `curl -fsSL \"https://api.github.com/search/repositories?q=SKILL.md+<topic>&sort=stars&per_page=5\" | python3 -c \"import sys,json; [print(r['full_name'], '-', r.get('description','')) for r in json.load(sys.stdin).get('items',[])]\"`\n"
            "3. To install a skill from skills.sh / GitHub into the project (`.agents/skills/`) or user (`~/.config/aishell/skills/`), "
            "propose `npx skills add <owner/repo@skill>` or download the `SKILL.md` into `~/.config/aishell/skills/<name>/SKILL.md` and run `:skills reload`."
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

