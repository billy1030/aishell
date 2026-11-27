"""Live execution plan & checklist parser and Rich panel renderer."""

import re
from typing import List, Literal, Optional
from pydantic import BaseModel
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

PlanStatus = Literal["pending", "in_progress", "done", "failed"]

_PLAN_BLOCK_RE = re.compile(r"<plan>([\s\S]*?)</plan>", re.IGNORECASE)
_UNCLOSED_PLAN_RE = re.compile(r"<plan>[\s\S]*$", re.IGNORECASE)
_STEP_LINE_RE = re.compile(r"^\s*(?:[-*]|\d+\.)\s*\[([^\]]*)\]\s*(.+)$")


class PlanStep(BaseModel):
    """Single item in an AI execution checklist."""

    title: str
    status: PlanStatus = "pending"


def strip_plan_blocks(text: str) -> str:
    """Remove <plan>...</plan> XML blocks from Markdown display text."""
    if "<plan>" not in text.lower():
        return text
    cleaned = _PLAN_BLOCK_RE.sub("", text)
    cleaned = _UNCLOSED_PLAN_RE.sub("", cleaned)
    return cleaned.strip()


class ExecutionPlan:
    """Tracks and renders a live step-by-step checklist from <plan> blocks."""

    def __init__(self) -> None:
        self.steps: List[PlanStep] = []

    def clear(self) -> None:
        self.steps.clear()

    def update_from_text(self, text: str) -> bool:
        """Parse the latest <plan>...</plan> block from LLM output.

        Returns True if a valid plan with at least 1 step was parsed.
        """
        matches = _PLAN_BLOCK_RE.findall(text or "")
        if not matches:
            return False

        raw_block = matches[-1]
        parsed: List[PlanStep] = []
        for line in raw_block.splitlines():
            m = _STEP_LINE_RE.match(line)
            if not m:
                continue
            marker = m.group(1).strip().lower()
            title = m.group(2).strip()
            if not title:
                continue
            if marker in ("x", "✓", "v", "done"):
                status: PlanStatus = "done"
            elif marker in ("~", ">", "→", "/", "in_progress"):
                status = "in_progress"
            elif marker in ("!", "✗", "fail", "failed"):
                status = "failed"
            else:
                status = "pending"
            parsed.append(PlanStep(title=title, status=status))

        if parsed:
            self.steps = parsed
            return True
        return False

    def render(self, console: Optional[Console] = None) -> None:
        """Render the current checklist in a Rich Panel."""
        c = console or Console()
        if not self.steps:
            c.print("[dim]No active execution plan.[/dim]")
            return

        done_count = sum(1 for s in self.steps if s.status == "done")
        total = len(self.steps)

        table = Table.grid(padding=(0, 1))
        table.add_column(width=2)
        table.add_column()

        for step in self.steps:
            if step.status == "done":
                table.add_row("[bold green]✓[/bold green]", f"[dim strike]{step.title}[/dim strike]")
            elif step.status == "in_progress":
                table.add_row("[bold yellow]→[/bold yellow]", f"[bold white]{step.title}[/bold white]")
            elif step.status == "failed":
                table.add_row("[bold red]✗[/bold red]", f"[red]{step.title}[/red]")
            else:
                table.add_row("[dim]○[/dim]", f"[white]{step.title}[/white]")

        panel = Panel(
            table,
            title=f"[bold magenta]Execution Plan ({done_count}/{total})[/bold magenta]",
            border_style="magenta",
            expand=False,
        )
        c.print(panel)
