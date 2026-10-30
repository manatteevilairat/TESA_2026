"""
edge_ai/demo_progress_bar.py
Real-time Training Monitor and Progress Bar using Rich.
Supports multiple visual themes: 'smooth', 'solid', 'neon', 'squares', 'circles', 'arrow', 'hash'.
Pure English interface without emojis.
"""

import time
from typing import Iterable, Optional
from rich.console import Console, ConsoleOptions, RenderResult
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeRemainingColumn, ProgressColumn, Task
from rich.segment import Segment
from rich.table import Table, Column
from rich.panel import Panel

console = Console()

# Predefined Theme Presets
BAR_THEMES = {
    "smooth": {
        "fill": "█", "sub": [" ", "▏", "▎", "▍", "▌", "▋", "▊", "▉", "█"],
        "empty": "░", "style": "bright_green", "empty_style": "grey23",
        "bracket": False, "head": ""
    },
    "solid": {
        "fill": "█", "sub": None,
        "empty": " ", "style": "bright_cyan", "empty_style": "grey15",
        "bracket": False, "head": ""
    },
    "neon": {
        "fill": "▰", "sub": None,
        "empty": "▱", "style": "bright_magenta", "empty_style": "grey30",
        "bracket": False, "head": ""
    },
    "squares": {
        "fill": "■", "sub": None,
        "empty": "□", "style": "bright_yellow", "empty_style": "grey35",
        "bracket": False, "head": ""
    },
    "circles": {
        "fill": "●", "sub": None,
        "empty": "○", "style": "bright_blue", "empty_style": "grey30",
        "bracket": False, "head": ""
    },
    "arrow": {
        "fill": "=", "sub": None,
        "empty": " ", "style": "bold white", "empty_style": "grey23",
        "bracket": True, "head": ">"
    },
    "hash": {
        "fill": "#", "sub": None,
        "empty": ".", "style": "bold green", "empty_style": "grey35",
        "bracket": True, "head": ""
    }
}


class ConfigurableBarColumn(ProgressColumn):
    """
    Versatile progress bar column supporting various themes, bracket frames,
    and automatic responsive width expansion.
    """
    def __init__(self, theme: str = "smooth", width: Optional[int] = None):
        super().__init__()
        self.theme_cfg = BAR_THEMES.get(theme, BAR_THEMES["smooth"])
        self.bar_width = width

    def render(self, task: Task):
        return _ThemedBarWidget(
            completed=task.completed,
            total=task.total,
            theme=self.theme_cfg,
            width=self.bar_width
        )


class _ThemedBarWidget:
    def __init__(self, completed: float, total: float, theme: dict, width: Optional[int] = None):
        self.completed = completed
        self.total = total if (total is not None and total > 0) else 100.0
        self.theme = theme
        self.width = width

    def __rich_console__(self, console: Console, options: ConsoleOptions) -> RenderResult:
        width = self.width or max(10, options.max_width)
        fraction = max(0.0, min(self.completed / self.total, 1.0))
        raw_width = fraction * width
        full_count = int(raw_width)

        fill_style = console.get_style(self.theme["style"])
        empty_style = console.get_style(self.theme["empty_style"])
        bracket = self.theme.get("bracket", False)
        head = self.theme.get("head", "")
        sub_blocks = self.theme.get("sub")

        if bracket:
            yield Segment("[", console.get_style("bold dim white"))

        if sub_blocks:
            remainder = raw_width - full_count
            partial_idx = int(remainder * 8)
            empty_count = max(0, width - full_count - (1 if partial_idx > 0 else 0))
            if full_count > 0:
                yield Segment(self.theme["fill"] * full_count, fill_style)
            if partial_idx > 0:
                yield Segment(sub_blocks[partial_idx], fill_style)
            if empty_count > 0:
                yield Segment(self.theme["empty"] * empty_count, empty_style)
        else:
            if head and full_count > 0 and full_count < width:
                bar_chars = self.theme["fill"] * (full_count - 1) + head
            else:
                bar_chars = self.theme["fill"] * full_count
            empty_count = max(0, width - full_count)

            if full_count > 0:
                yield Segment(bar_chars, fill_style)
            if empty_count > 0:
                yield Segment(self.theme["empty"] * empty_count, empty_style)

        if bracket:
            yield Segment("]", console.get_style("bold dim white"))


class SpacedProgress(Progress):
    """
    Subclassed Progress that injects configurable vertical blank line(s)
    between multiple concurrent task progress bars.
    """
    def __init__(self, *columns, spacing: int = 1, **kwargs):
        super().__init__(*columns, **kwargs)
        self.spacing = spacing

    def make_tasks_table(self, tasks: Iterable[Task]) -> Table:
        table_columns = (
            (
                Column(no_wrap=True)
                if isinstance(_column, str)
                else _column.get_table_column().copy()
            )
            for _column in self.columns
        )
        table = Table.grid(*table_columns, padding=(0, 1), expand=self.expand)

        tasks_list = [t for t in tasks if t.visible]
        for i, task in enumerate(tasks_list):
            table.add_row(
                *(
                    (
                        column.format(task=task)
                        if isinstance(column, str)
                        else column(task)
                    )
                    for column in self.columns
                )
            )
            # Add blank spacer row between tasks
            if i < len(tasks_list) - 1:
                for _ in range(self.spacing):
                    table.add_row()
        return table


def run_training_demo(theme: str = "smooth", spacing: int = 1):
    console.print(Panel.fit(
        "[bold green]TESA Top Gun Rally 2026: Coffee Bean AI Model Training Monitor[/bold green]\n"
        "[cyan]Simulating Robusta Coffee Defect Detection Pipeline...[/cyan]",
        border_style="green"
    ))

    # Multi-layer progress bar with configurable theme & row spacing
    with SpacedProgress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        ConfigurableBarColumn(theme=theme),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeRemainingColumn(),
        console=console,
        spacing=spacing
    ) as progress:

        total_epochs = 5
        epoch_task = progress.add_task("[bold yellow]Overall Epochs", total=total_epochs)
        batch_task = progress.add_task("[cyan]Batch Processing", total=100)

        for epoch in range(1, total_epochs + 1):
            progress.reset(batch_task)
            progress.update(batch_task, description=f"[cyan]Epoch {epoch}/{total_epochs} (Processing Batches)")

            loss = round(2.5 / epoch, 4)
            map50 = round(min(0.95, 0.45 + (epoch * 0.1)), 3)

            for b in range(100):
                time.sleep(0.012)  # Simulating computation
                progress.update(batch_task, advance=1)

            progress.update(epoch_task, advance=1)
            console.print(f"   [dim]-> Finished Epoch {epoch}: Loss = [bold red]{loss}[/bold red] | mAP50 = [bold green]{map50}[/bold green][/dim]")

    # Final evaluation summary table
    table = Table(title="\nFinal Model Evaluation Summary (Validation Set)", border_style="blue")
    table.add_column("Class ID", justify="center", style="cyan")
    table.add_column("Class Name", style="bold white")
    table.add_column("Precision", justify="right", style="green")
    table.add_column("Recall", justify="right", style="green")
    table.add_column("mAP50", justify="right", style="bold yellow")

    table.add_row("0", "Healthy Bean", "94.2%", "92.0%", "0.945")
    table.add_row("1", "Black Bean", "91.8%", "89.5%", "0.912")
    table.add_row("2", "Mold Bean", "88.5%", "86.0%", "0.880")
    table.add_row("3", "Broken Bean", "93.0%", "90.2%", "0.923")

    console.print(table)
    console.print("\n[bold green]Model training completed. Model ready for ONNX export (best.onnx) for Raspberry Pi 5 deployment.[/bold green]\n")


if __name__ == "__main__":
    # Choose from: 'smooth', 'solid', 'neon', 'squares', 'circles', 'arrow', 'hash'
    run_training_demo(theme="smooth", spacing=1)

