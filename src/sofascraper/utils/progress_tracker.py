from __future__ import annotations

import time

from rich.console import Console
from rich.live import Live
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TaskID,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)
from rich.table import Table
from rich.text import Text

_console = Console(highlight=False)


class StyledTimeElapsed(TimeElapsedColumn):
    def render(self, task):
        text = super().render(task)
        return Text(str(text), style="white")


class StyledTimeRemaining(TimeRemainingColumn):
    def render(self, task):
        text = super().render(task)
        return Text(str(text), style="dim")


class ProgressTracker:
    """
    Context manager that renders a Rich progress bar for a scraping job.

    Args:
        total   : total number of items to process
        label   : short description shown in the bar header (e.g. "Matches", "Dates")
    """

    def __init__(self, total: int, label: str = "Items") -> None:
        self.total = total
        self.label = label
        self._completed = 0
        self._failed = 0
        self._start_time: float = 0.0
        self._current_item: str = ""

        self._progress = Progress(
            SpinnerColumn(style="dim cyan"),
            TextColumn("[white]{task.description}"),
            BarColumn(style="grey37", complete_style="cyan"),
            MofNCompleteColumn(),
            StyledTimeElapsed(),
            TextColumn("[dim]ETA"),
            StyledTimeRemaining(),
            console=_console,
            transient=False,
        )
        self._task_id: TaskID | None = None
        self._live: Live | None = None

    def _build_collection_table(links: int, page: int, direction: str, elapsed: float) -> Table:
        grid = Table.grid(padding=(0, 2))

        grid.add_row(
            Text("Collecting match links", style="bold cyan"),
        )
        grid.add_row(Text("─" * 52, style="dim"))
        grid.add_row(
            Text("Links found", style="dim"), Text(str(links), style="bold green")
        )
        grid.add_row(
            Text("Pages visited", style="dim"), Text(str(page), style="bold")
        )
        grid.add_row(
            Text("Direction", style="dim"), Text(direction, style="cyan")
        )
        grid.add_row(
            Text("Elapsed", style="dim"), Text(f"{elapsed:.1f}s", style="yellow")
        )
        grid.add_row(Text("─" * 52, style="dim"))

        return grid

    def advance(self, status: str = "", failed: bool = False) -> None:
        """
        Call once after each item finishes.

        Args:
            status: short string describing the item just processed
            failed: set True if this item failed so the failure counter increments
        """
        self._completed += 1
        if failed:
            self._failed += 1
        self._current_item = status

        if self._task_id is not None:
            self._progress.update(
                self._task_id,
                advance=1,
                description=self._bar_description(),
            )

    async def __aenter__(self) -> ProgressTracker:
        self._start_time = time.monotonic()
        self._task_id = self._progress.add_task(
            description=self._bar_description(),
            total=self.total,
        )
        self._live = Live(
            self._render(),
            console=_console,
            refresh_per_second=4,
        )
        self._live.start()
        return self

    async def __aexit__(self, *_) -> None:
        # Final refresh so the bar shows 100 % on completion
        if self._task_id is not None:
            self._progress.update(
                self._task_id,
                completed=self._completed,
                description=self._bar_description(),
            )
        if self._live is not None:
            self._live.update(self._render())
            self._live.stop()

        self._print_summary()

    def _bar_description(self) -> str:
        succeeded = self._completed - self._failed
        if self._failed:
            return f"[bold]{self.label}[/bold] [green]{succeeded} ok[/green] [red]{self._failed} failed[/red]"
        return f"[bold]{self.label}[/bold]"

    def _render(self) -> Table:
        """Build the composite renderable shown inside the Live context."""
        grid = Table.grid(padding=(0, 1))
        grid.add_row(self._progress)
        if self._current_item:
            short = self._current_item[:72] + "…" if len(self._current_item) > 72 else self._current_item
            grid.add_row(Text(f"  ↳ {short}", style="dim"))
        return grid

    def _print_summary(self) -> None:
        elapsed = time.monotonic() - self._start_time
        succeeded = self._completed - self._failed

        h, rem = divmod(int(elapsed), 3600)
        m, s = divmod(rem, 60)
        elapsed_str = f"{h:02d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"

        avg = elapsed / self._completed if self._completed else 0

        lines = [
            f"[bold]{'─' * 52}[/bold]",
            f"  [bold cyan]{self.label} complete[/bold cyan]",
            f"  Total      : [bold]{self.total}[/bold]",
            f"  Succeeded  : [bold green]{succeeded}[/bold green]",
        ]
        if self._failed:
            lines.append(f"  Failed     : [bold red]{self._failed}[/bold red]")
        lines += [
            f"  Elapsed    : [bold yellow]{elapsed_str}[/bold yellow]",
            f"  Time / item : [bold]{avg:.1f}s[/bold]",
            f"[bold]{'─' * 52}[/bold]",
        ]

        _console.print("\n" + "\n".join(lines))
