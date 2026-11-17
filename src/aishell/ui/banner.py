"""Startup banner and compact prompt formatting for aishell REPL."""

import os
import platform
import sys
from pathlib import Path
from typing import List, Optional, Tuple
import distro
from prompt_toolkit.styles import Style
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from aishell import __version__
from aishell.config.settings import AishellSettings, get_settings


def contract_path(path: Optional[str] = None) -> str:
    """Contract home directory path to ~ per D-01."""
    raw_path = Path(path).resolve() if path else Path.cwd().resolve()
    try:
        home = Path.home().resolve()
        try:
            rel = raw_path.relative_to(home)
            rel_str = str(rel).replace("\\", "/")
            return "~" if rel_str == "." else f"~/{rel_str}"
        except ValueError:
            # Not a subpath of home
            return str(raw_path).replace("\\", "/")
    except Exception:
        return str(raw_path).replace("\\", "/")


def is_root_user() -> bool:
    """Check if current process is running as root / superuser."""
    try:
        if hasattr(os, "geteuid"):
            return os.geteuid() == 0
    except Exception:
        pass
    user = os.environ.get("USER", os.environ.get("USERNAME", ""))
    return user.lower() == "root"


def format_prompt_string(
    cwd: Optional[str] = None,
    model_name: Optional[str] = None,
    is_root: Optional[bool] = None,
) -> str:
    """Format clean shell prompt with current directory: 'aishell:~/repo $ ' or 'aishell:~/repo # '."""
    root = is_root if is_root is not None else is_root_user()
    symbol = "#" if root else "$"
    path_str = contract_path(cwd)
    return f"aishell:{path_str} {symbol} "


def format_prompt(
    cwd: Optional[str] = None,
    model_name: Optional[str] = None,
    is_root: Optional[bool] = None,
) -> List[Tuple[str, str]]:
    """Format prompt as prompt_toolkit styled tokens: 'aishell:~/repo $ ' or 'aishell:~/repo # '."""
    root = is_root if is_root is not None else is_root_user()
    symbol = "#" if root else "$"
    path_str = contract_path(cwd)
    return [
        ("class:prompt.brand", "aishell"),
        ("class:prompt.text", ":"),
        ("class:prompt.path", path_str),
        ("class:prompt.symbol", f" {symbol} "),
    ]


def get_prompt_style() -> Style:
    """Return prompt_toolkit styling dictionary."""
    return Style.from_dict(
        {
            "prompt.brand": "#00afff bold",
            "prompt.path": "#5faf00",
            "prompt.model": "#af87d7",
            "prompt.symbol": "#ffd700 bold",
            "prompt.text": "#8a8a8a",
        }
    )


def get_git_commit() -> Optional[str]:
    """Retrieve short git commit hash from local repo or installed package metadata."""
    try:
        import subprocess

        repo_dir = Path(__file__).resolve().parents[3]
        if (repo_dir / ".git").exists():
            out = subprocess.check_output(
                ["git", "rev-parse", "--short", "HEAD"],
                cwd=str(repo_dir),
                stderr=subprocess.DEVNULL,
                text=True,
                timeout=1,
            ).strip()
            if out:
                return out
    except Exception:
        pass

    try:
        import json
        from importlib.metadata import distribution

        dist = distribution("aishell")
        direct_url = dist.read_text("direct_url.json")
        if direct_url:
            data = json.loads(direct_url)
            commit_id = data.get("vcs_info", {}).get("commit_id")
            if commit_id:
                return commit_id[:7]
    except Exception:
        pass

    return None


def get_system_summary() -> dict[str, str]:
    """Retrieve host system, python, and environment metadata."""
    distro_name = distro.name(pretty=True)
    if not distro_name:
        distro_name = f"{platform.system()} {platform.release()}"

    return {
        "version": __version__,
        "commit": get_git_commit() or "",
        "os": distro_name,
        "python": platform.python_version(),
    }


def render_banner(
    console: Optional[Console] = None, settings: Optional[AishellSettings] = None
) -> None:
    """Render startup banner with system metadata summary per REPL-01, D-13."""
    con = console or Console()
    st = settings or get_settings()
    sys_info = get_system_summary()

    provider = st.general.default_provider
    model = st.general.model

    table = Table.grid(padding=(0, 2))
    table.add_column(style="dim cyan", justify="right")
    table.add_column(style="white")

    version_str = f"[bold cyan]aishell[/bold cyan] v{sys_info['version']}"
    if sys_info.get("commit"):
        version_str += f" [dim]({sys_info['commit']})[/dim]"
    table.add_row("Version:", version_str)
    table.add_row("Repo:", "[dim]https://github.com/billy1030/aishell[/dim]")
    table.add_row("System:", sys_info["os"])
    table.add_row("Python:", sys_info["python"])
    table.add_row("AI Model:", f"[bold green]{provider}[/bold green] / [bold yellow]{model}[/bold yellow]")
    table.add_row("Shortcuts:", "[dim]Alt+Enter (newline) • Ctrl+R (history) • :exit or Ctrl+D (quit)[/dim]")

    panel = Panel(
        table,
        title="[bold cyan]Terminal AI Shell[/bold cyan]",
        subtitle="[dim]Ready for natural language intent & shell execution[/dim]",
        border_style="cyan",
        expand=False,
    )
    con.print(panel)
