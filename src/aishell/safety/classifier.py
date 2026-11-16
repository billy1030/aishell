"""Deterministic risk classification engine and static heuristics per D-01 and EXEC-01."""

import re
import shlex
from enum import Enum
from typing import List, Optional


class RiskLevel(str, Enum):
    """Blast-radius risk tier for proposed shell commands with ordinal ranking."""

    SAFE = "safe"
    MUTATING = "mutating"
    HIGH_RISK = "high_risk"

    @property
    def rank(self) -> int:
        """Ordinal rank for risk comparisons (safe: 0, mutating: 1, high_risk: 2)."""
        ranks = {
            RiskLevel.SAFE: 0,
            RiskLevel.MUTATING: 1,
            RiskLevel.HIGH_RISK: 2,
        }
        return ranks[self]

    def __lt__(self, other: object) -> bool:
        if isinstance(other, RiskLevel):
            return self.rank < other.rank
        if isinstance(other, str):
            try:
                return self.rank < RiskLevel(other.lower()).rank
            except ValueError:
                return False
        return NotImplemented

    def __le__(self, other: object) -> bool:
        if isinstance(other, RiskLevel):
            return self.rank <= other.rank
        if isinstance(other, str):
            try:
                return self.rank <= RiskLevel(other.lower()).rank
            except ValueError:
                return False
        return NotImplemented

    def __gt__(self, other: object) -> bool:
        if isinstance(other, RiskLevel):
            return self.rank > other.rank
        if isinstance(other, str):
            try:
                return self.rank > RiskLevel(other.lower()).rank
            except ValueError:
                return False
        return NotImplemented

    def __ge__(self, other: object) -> bool:
        if isinstance(other, RiskLevel):
            return self.rank >= other.rank
        if isinstance(other, str):
            try:
                return self.rank >= RiskLevel(other.lower()).rank
            except ValueError:
                return False
        return NotImplemented


# Known read-only inspection commands that do not alter system state
_SAFE_ROOT_COMMANDS = {
    "ls",
    "cat",
    "head",
    "tail",
    "grep",
    "egrep",
    "fgrep",
    "find",
    "df",
    "du",
    "ps",
    "top",
    "htop",
    "stat",
    "file",
    "uptime",
    "whoami",
    "id",
    "uname",
    "pwd",
    "which",
    "whereis",
    "echo",
    "printf",
    "env",
    "printenv",
    "wc",
    "diff",
    "cmp",
    "comm",
    "sort",
    "uniq",
    "cut",
    "awk",
    "less",
    "more",
    "man",
    "info",
    "help",
    "date",
    "cal",
    "hostname",
    "free",
    "lsblk",
    "lscpu",
    "lsof",
    "netstat",
    "ss",
    "ping",
    "traceroute",
    "dig",
    "nslookup",
    "host",
    "curl",
    "wget",
    "tree",
}

# Regex patterns matching high-risk destructive commands
_HIGH_RISK_REGEXES = [
    # rm with recursive and force flags (e.g. rm -rf, rm -fr, rm --recursive -f, rm -r -f)
    re.compile(r"\brm\s+-[a-zA-Z0-9]*[rR][a-zA-Z0-9]*[fF]|\brm\s+-[a-zA-Z0-9]*[fF][a-zA-Z0-9]*[rR]", re.IGNORECASE),
    re.compile(r"\brm\s+.*--recursive.*-f|\brm\s+.*-f.*--recursive", re.IGNORECASE),
    # Raw disk formatting and partitioning
    re.compile(r"\b(?:mkfs|mkfs\.[a-z0-9]+|fdisk|gdisk|parted|sfdisk)\b", re.IGNORECASE),
    # Raw block device writes via dd
    re.compile(r"\bdd\s+.*(?:of=/dev/|if=/dev/)", re.IGNORECASE),
    # System shutdown, reboot, halt, init states
    re.compile(r"\b(?:reboot|shutdown|poweroff|halt|init\s+[06])\b", re.IGNORECASE),
    # Recursive chmod 777 or 000
    re.compile(r"\bchmod\s+-[a-zA-Z0-9]*[rR]\s+(?:777|000|a\+rwx|a-rwx)\b", re.IGNORECASE),
    # Recursive chown /
    re.compile(r"\bchown\s+-[a-zA-Z0-9]*[rR]\b", re.IGNORECASE),
    # Firewall flush / disable
    re.compile(r"\b(?:iptables\s+-[Ff]|iptables\s+--flush|ufw\s+disable|nft\s+flush)\b", re.IGNORECASE),
    # Swap management
    re.compile(r"\b(?:mkswap|swapon|swapoff)\b", re.IGNORECASE),
    # Direct redirection to physical or raw devices
    re.compile(r">\s*/dev/(?:sd[a-z]|nvme[0-9]|hd[a-z]|vd[a-z]|mmcblk)", re.IGNORECASE),
    # Direct overwrite of critical system configs
    re.compile(r">\s*/etc/(?:passwd|shadow|fstab|sudoers)", re.IGNORECASE),
    # Web pipe to shell (curl http... | sh, wget -O- ... | bash)
    re.compile(r"(?:curl|wget)\s+[^|]+\|\s*(?:sh|bash|zsh)\b", re.IGNORECASE),
    # Classic fork bomb
    re.compile(r":\(\)\s*\{\s*:\|:&\s*\};:", re.IGNORECASE),
]

# Mutating commands modifying single files, packages, or services
_MUTATING_ROOT_COMMANDS = {
    "touch",
    "mkdir",
    "cp",
    "mv",
    "rm",
    "rmdir",
    "chmod",
    "chown",
    "chgrp",
    "truncate",
    "ln",
    "unlink",
    "tar",
    "unzip",
    "gzip",
    "gunzip",
    "bzip2",
    "bunzip2",
    "xz",
    "unxz",
    "apt",
    "apt-get",
    "dnf",
    "yum",
    "pacman",
    "zypper",
    "apk",
    "npm",
    "yarn",
    "pnpm",
    "pip",
    "pip3",
    "pipx",
    "cargo",
    "gem",
    "systemctl",
    "service",
    "kill",
    "killall",
    "pkill",
    "useradd",
    "userdel",
    "usermod",
    "groupadd",
    "groupdel",
    "passwd",
    "chsh",
    "crontab",
    "make",
    "docker",
    "kubectl",
    "sed",
}


def max_risk(tier_a: str, tier_b: str) -> str:
    """Compute the higher of two risk tiers per D-01.

    Ordering: safe < mutating < high_risk.
    Unknown values are treated as mutating.
    """
    try:
        level_a = RiskLevel(tier_a.lower())
    except ValueError:
        level_a = RiskLevel.MUTATING

    try:
        level_b = RiskLevel(tier_b.lower())
    except ValueError:
        level_b = RiskLevel.MUTATING

    return max(level_a, level_b).value


def split_compound_command(command: str) -> List[str]:
    """Decompose compound command strings across shell operators and subshells.

    Splits on unquoted:
      - Pipes: |
      - Semicolons: ;
      - Logical AND/OR: &&, ||
      - Subshell invocations: $(...), `...`
    Preserves quoted string contents and escape sequences.
    """
    cleaned = command.strip()
    if not cleaned:
        return []

    # Step 1: Extract any subshells $(...) and `...`
    extracted_subshells: List[str] = []
    # Match $(...)
    for match in re.finditer(r"\$\(([^)]+)\)", cleaned):
        inner = match.group(1).strip()
        if inner:
            extracted_subshells.append(inner)
    # Match `...`
    for match in re.finditer(r"`([^`]+)`", cleaned):
        inner = match.group(1).strip()
        if inner:
            extracted_subshells.append(inner)

    # Step 2: Split main string on unquoted |, ;, &&, ||
    components: List[str] = []
    current_token: List[str] = []
    in_single_quote = False
    in_double_quote = False
    escape = False
    i = 0
    n = len(cleaned)

    while i < n:
        char = cleaned[i]

        if escape:
            current_token.append(char)
            escape = False
            i += 1
            continue

        if char == "\\":
            escape = True
            current_token.append(char)
            i += 1
            continue

        if char == "'" and not in_double_quote:
            in_single_quote = not in_single_quote
            current_token.append(char)
            i += 1
            continue

        if char == '"' and not in_single_quote:
            in_double_quote = not in_double_quote
            current_token.append(char)
            i += 1
            continue

        if not in_single_quote and not in_double_quote:
            # Check for && or ||
            if i + 1 < n and cleaned[i : i + 2] in ("&&", "||"):
                comp = "".join(current_token).strip()
                if comp:
                    components.append(comp)
                current_token = []
                i += 2
                continue

            # Check for | or ;
            if char in ("|", ";"):
                comp = "".join(current_token).strip()
                if comp:
                    components.append(comp)
                current_token = []
                i += 1
                continue

        current_token.append(char)
        i += 1

    remaining = "".join(current_token).strip()
    if remaining:
        components.append(remaining)

    # Combine split components with extracted subshells
    all_commands = components + extracted_subshells
    return [cmd.strip() for cmd in all_commands if cmd.strip()]


def _strip_sudo_and_prefixes(cmd: str) -> str:
    """Strip leading sudo, env, or variable assignments from command."""
    current = cmd.strip()

    # Strip environment variable prefixes (e.g. FOO=bar BAZ=1 cmd)
    while True:
        parts = current.split(maxsplit=1)
        if not parts:
            break
        if "=" in parts[0] and not parts[0].startswith(("-", "/")):
            current = parts[1].strip() if len(parts) > 1 else ""
        else:
            break

    # Strip sudo and common flags (-u user, -E, -n, -S, -i, -s, --)
    if current.startswith("sudo"):
        tokens = current.split()
        idx = 1
        while idx < len(tokens):
            tok = tokens[idx]
            if tok in ("-u", "-g", "-p", "-C", "-D", "-R", "-T"):
                idx += 2  # skip flag and its argument
            elif tok.startswith("-"):
                idx += 1
            else:
                break
        current = " ".join(tokens[idx:]).strip() if idx < len(tokens) else ""

    return current


def classify_single_command(cmd: str) -> RiskLevel:
    """Classify a single atomic command without operators into a RiskLevel tier."""
    clean = cmd.strip()
    if not clean:
        return RiskLevel.SAFE

    # 1. Check against explicit high-risk regexes
    for pattern in _HIGH_RISK_REGEXES:
        if pattern.search(clean):
            return RiskLevel.HIGH_RISK

    # 2. Check for shell redirection targeting files (e.g. > file, >> file)
    # Exclude /dev/null redirection (e.g. 2>/dev/null, > /dev/null)
    cleaned_null = re.sub(r"[0-9]?>\s*/dev/null", "", clean)
    if ">" in cleaned_null:
        return RiskLevel.MUTATING

    # 3. Strip sudo and prefixes to identify core binary
    stripped = _strip_sudo_and_prefixes(clean)
    if not stripped:
        return RiskLevel.SAFE

    # Parse arguments safely with shlex
    try:
        tokens = shlex.split(stripped)
    except Exception:
        tokens = stripped.split()

    if not tokens:
        return RiskLevel.SAFE

    binary = tokens[0].split("/")[-1].lower()
    args = tokens[1:]

    # Check rm specifically with token inspection
    if binary == "rm" and args:
        has_recursive = any(
            arg in ("-r", "-R", "--recursive")
            or (arg.startswith("-") and not arg.startswith("--") and any(c in "rR" for c in arg))
            for arg in args
        )
        has_force = any(
            arg in ("-f", "-F", "--force")
            or (arg.startswith("-") and not arg.startswith("--") and any(c in "fF" for c in arg))
            for arg in args
        )
        if has_recursive and has_force:
            return RiskLevel.HIGH_RISK
        # Recursive delete targeting root or wildcard is high risk
        if has_recursive and any(arg in ("/", "/*", "/etc", "/var", "/usr", "/bin", "/boot") for arg in args):
            return RiskLevel.HIGH_RISK
        return RiskLevel.MUTATING

    # Check git commands specifically
    if binary == "git" and args:
        subcmd = args[0].lower()
        safe_git = {"status", "log", "diff", "show", "branch", "tag", "remote", "rev-parse", "describe", "config"}
        if subcmd == "branch" and any(arg in ("-d", "-D", "--delete") for arg in args):
            return RiskLevel.MUTATING
        if subcmd in safe_git:
            return RiskLevel.SAFE
        return RiskLevel.MUTATING

    # Check docker / kubectl commands specifically
    if binary in ("docker", "podman") and args:
        subcmd = args[0].lower()
        if subcmd in ("ps", "images", "image", "logs", "top", "version", "info", "inspect"):
            return RiskLevel.SAFE
        return RiskLevel.MUTATING

    if binary == "kubectl" and args:
        subcmd = args[0].lower()
        if subcmd in ("get", "describe", "logs", "cluster-info", "version", "api-resources"):
            return RiskLevel.SAFE
        return RiskLevel.MUTATING

    # Check sed -i
    if binary == "sed" and any("-i" in arg for arg in args):
        return RiskLevel.MUTATING

    # Check Safe Commands
    if binary in _SAFE_ROOT_COMMANDS:
        return RiskLevel.SAFE

    # Check Mutating Commands
    if binary in _MUTATING_ROOT_COMMANDS:
        return RiskLevel.MUTATING

    # Default to Mutating for unrecognized commands per fail-safe principle
    return RiskLevel.MUTATING


def classify_risk(command: str, model_risk: Optional[str] = None) -> RiskLevel:
    """Classify the effective risk tier of a command per D-01 and EXEC-01.

    Decomposes compound commands into subcomponents, computes the maximum
    heuristic risk across all subcomponents, and reconciles with model_risk via
    max_risk(heuristic_risk, model_risk) to guarantee model hallucinations can
    never downgrade a dangerous command.
    """
    clean_full = command.strip()
    if not clean_full:
        base_heuristic = RiskLevel.SAFE
    else:
        # Check high-risk patterns on the full command string first (e.g. curl ... | sh)
        is_high_risk = False
        for pattern in _HIGH_RISK_REGEXES:
            if pattern.search(clean_full):
                is_high_risk = True
                break

        if is_high_risk:
            base_heuristic = RiskLevel.HIGH_RISK
        else:
            subcommands = split_compound_command(clean_full)
            if not subcommands:
                base_heuristic = RiskLevel.SAFE
            else:
                highest = RiskLevel.SAFE
                for subcmd in subcommands:
                    tier = classify_single_command(subcmd)
                    if tier > highest:
                        highest = tier
                    if highest == RiskLevel.HIGH_RISK:
                        break
                base_heuristic = highest

    if model_risk:
        reconciled_tier = max_risk(base_heuristic.value, model_risk)
        return RiskLevel(reconciled_tier)

    return base_heuristic
