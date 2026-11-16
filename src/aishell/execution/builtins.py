"""Shell builtin interception and state synchronization for aishell.

Intercepts builtins (cd, export, unset) in the parent Python process to eliminate
subshell amnesia per D-05, D-07, D-08, and provides post-execution compound cwd
synchronization per D-06.
"""

import os
import re
import shlex
from pathlib import Path
from typing import List, Optional, Tuple

BUILTIN_COMMANDS = {"cd", "export", "unset"}


def parse_command_tokens(command_str: str) -> List[str]:
    """Safely split command string into tokens using shlex."""
    try:
        # On POSIX systems, use posix=True. On Windows, use posix=False to preserve backslashes.
        return shlex.split(command_str, comments=False, posix=(os.name != "nt"))
    except ValueError:
        # Fallback to simple split if shlex fails on unclosed quotes
        return command_str.strip().split()


def is_builtin_command(command_str: str) -> bool:
    """Check if command is an intercepted shell builtin."""
    tokens = parse_command_tokens(command_str)
    if not tokens:
        return False
    return tokens[0] in BUILTIN_COMMANDS


def handle_cd(args: List[str]) -> Tuple[int, str]:
    """Execute cd builtin in the parent Python process.

    Supports:
    - `cd` or `cd ~`: navigate to user's home directory.
    - `cd -`: navigate to previous working directory (OLDPWD) and print it.
    - `cd ..`, `cd path/to/dir`: navigate relative or absolute path.
    - Updates OLDPWD and PWD environment variables.
    """
    old_cwd = os.getcwd()

    if not args or args[0] == "~":
        target = str(Path.home())
    elif args[0] == "-":
        oldpwd = os.environ.get("OLDPWD")
        if not oldpwd:
            return 1, "cd: OLDPWD not set"
        target = oldpwd
    elif args[0].startswith("~"):
        target = os.path.expanduser(args[0])
    else:
        target = args[0]

    try:
        target_path = Path(target).expanduser().resolve()
        if not target_path.exists():
            return 1, f"cd: no such file or directory: {args[0] if args else target}"
        if not target_path.is_dir():
            return 1, f"cd: not a directory: {args[0] if args else target}"

        os.chdir(target_path)
        new_cwd = str(target_path)
        os.environ["OLDPWD"] = old_cwd
        os.environ["PWD"] = new_cwd

        # When `cd -` succeeds, bash/zsh prints the new working directory
        output = new_cwd if (args and args[0] == "-") else ""
        return 0, output
    except Exception as e:
        return 1, f"cd: {e}"


def handle_export(args: List[str]) -> Tuple[int, str]:
    """Execute export builtin in the parent Python process.

    Modifies os.environ session-scoped per D-08 without touching shell rc files.
    Format: KEY=VALUE, KEY="VALUE", or multiple pairs.
    """
    if not args:
        # If bare export, list environment variables like POSIX export
        lines = [f"declare -x {k}=\"{v}\"" for k, v in sorted(os.environ.items())]
        return 0, "\n".join(lines)

    for item in args:
        if "=" in item:
            key, val = item.split("=", 1)
            key = key.strip()
            # Strip outer quotes if any
            if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
                val = val[1:-1]
            if key:
                os.environ[key] = val
        else:
            # If exported without '=', check if variable already exists in environ
            key = item.strip()
            if key and key not in os.environ:
                os.environ[key] = ""

    return 0, ""


def handle_unset(args: List[str]) -> Tuple[int, str]:
    """Execute unset builtin in the parent Python process.

    Removes variables from os.environ per D-08.
    """
    if not args:
        return 0, ""

    for key in args:
        k = key.strip()
        os.environ.pop(k, None)

    return 0, ""


def try_execute_builtin(command_str: str) -> Optional[Tuple[int, str]]:
    """Attempt to intercept and execute a shell builtin.

    Returns:
        (exit_code, output) if command was a recognized builtin,
        None if command is not a builtin and should be dispatched to execution runner.
    """
    tokens = parse_command_tokens(command_str)
    if not tokens:
        return None

    cmd = tokens[0]
    args = tokens[1:]

    if cmd == "cd":
        return handle_cd(args)
    elif cmd == "export":
        return handle_export(args)
    elif cmd == "unset":
        return handle_unset(args)

    return None


def sync_compound_cwd(command_str: str, exit_code: int = 0) -> None:
    """Synchronize parent process cwd after compound command execution per D-06.

    If a compound command containing 'cd' succeeds (exit_code == 0), parse and
    navigate the parent process to the target directory.
    """
    if exit_code != 0:
        return

    # Check for compound operators
    if not any(op in command_str for op in ["&&", ";", "||"]):
        return

    # Split compound command into segments separated by && or ;
    # (If || succeeded with exit code 0, either the first branch or fallback succeeded)
    segments = re.split(r"\s*(?:&&|;)\s*", command_str)
    for seg in segments:
        tokens = parse_command_tokens(seg)
        if tokens and tokens[0] == "cd":
            handle_cd(tokens[1:])
