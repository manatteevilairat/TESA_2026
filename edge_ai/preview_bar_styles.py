"""
edge_ai/preview_bar_styles.py
Visual Gallery of Progress Bar Styles for CLI/Terminal.
Demonstrates various Unicode and ASCII progress bar themes.
Pure English interface without emojis.
"""

import time
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeRemainingColumn, ProgressColumn, Task
from rich.segment import Segment

console = Console()

THEMES = {
    "1. Smooth Blocks (HuggingFace AI)": {
        "fill": "█", "sub": [" ", "▏", "▎", "▍", "▌", "▋", "▊", "▉", "█"],
        "empty": "░", "style": "bright_green", "empty_style": "grey23"
    },
    "2. High-Contrast Solid (Minimalist)": {
        "fill": "█", "sub": None,
        "empty": " ", "style": "bright_cyan", "empty_style": "grey15"
    },
    "3. Neon Segmented (Cyberpunk / Game UI)": {
        "fill": "▰", "sub": None,
        "empty": "▱", "style": "bright_magenta", "empty_style": "grey30"
    },
    "4. Geometric Squares": {
        "fill": "■", "sub": None,
        "empty": "□", "style": "bright_yellow", "empty_style": "grey35"
    },
    "5. Bullet Circles (Modern Mobile UI)": {
        "fill": "●", "sub": None,
        "empty": "○", "style": "bright_blue", "empty_style": "grey30"
    },
    "6. Classic Unix Arrow (wget / apt-get)": {
        "fill": "=", "sub": None, "bracket": True, "head": ">",
        "empty": " ", "style": "bold white", "empty_style": "grey23"
    },
    "7. Classic Pip / Hash": {
        "fill": "#", "sub": None, "bracket": True, "head": "",
        "empty": ".", "style": "bold green", "empty_style": "grey35"
    }
}


class ThemedBarWidget:
    def __init__(self, completed: float, total: float, theme_cfg: dict, width: int = 32):
        self.completed = completed
        self.total = total if (total is not None and total > 0) else 100.0
        self.theme = theme_cfg
        self.width = width

    def __rich_console__(self, console: Console, options):
        width = self.width
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


class ThemedProgressColumn(ProgressColumn):
    def __init__(self, theme_cfg: dict, width: int = 30):
        super().__init__()
        self.theme_cfg = theme_cfg
        self.bar_width = width

    def render(self, task: Task):
        return ThemedBarWidget(
            completed=task.completed,
            total=task.total,
            theme_cfg=self.theme_cfg,
            width=self.bar_width,
        )


def main():
    console.print(Panel.fit(
        "[bold cyan]Progress Bar Style Gallery: Visual Selection[/bold cyan]\n"
        "[dim]Demonstrating 7 different progress bar visual styles in action...[/dim]",
        border_style="cyan"
    ))

    # Test static preview at 70%
    console.print("\n[bold]Static Preview at 70% Progress:[/bold]\n")
    for name, cfg in THEMES.items():
        widget = ThemedBarWidget(completed=70, total=100, theme_cfg=cfg, width=30)
        console.print(f"  {name:<40} ", end="")
        console.print(widget, end="")
        console.print("  [bold green]70%[/bold green]")

    # Live animated preview
    console.print("\n\n[bold]Live Animation Test (0% -> 100%):[/bold]\n")
    with Progress(
        TextColumn("[bold yellow]{task.description:<36}"),
        ThemedProgressColumn(THEMES["1. Smooth Blocks (HuggingFace AI)"]),
        TextColumn("[green]{task.percentage:>3.0f}%"),
        TimeRemainingColumn(),
        console=console,
    ) as progress:
        task1 = progress.add_task("1. Smooth Blocks", total=100)
        for i in range(101):
            time.sleep(0.015)
            progress.update(task1, advance=1)

    console.print("\n[bold green]Gallery preview complete. Select any style above for your training scripts.[/bold green]\n")


if __name__ == "__main__":
    main()
