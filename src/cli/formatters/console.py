"""Console output formatter with colors and tables."""

import click
from typing import Dict, Any, List, Optional


class ConsoleFormatter:
    """Format output for console display."""

    @staticmethod
    def table(headers: List[str], rows: List[List[Any]], title: Optional[str] = None):
        """Print a simple table."""
        if title:
            click.echo(f"\n{title}")
            click.echo("-" * len(title))

        # Calculate column widths
        widths = [len(h) for h in headers]
        for row in rows:
            for i, cell in enumerate(row):
                widths[i] = max(widths[i], len(str(cell)))

        # Print header
        header_row = " | ".join(h.ljust(w) for h, w in zip(headers, widths))
        click.echo(header_row)
        click.echo("-+-".join("-" * w for w in widths))

        # Print rows
        for row in rows:
            cells = [str(cell).ljust(w) for cell, w in zip(row, widths)]
            click.echo(" | ".join(cells))

    @staticmethod
    def stats_comparison(
        original: Dict[str, float],
        optimized: Dict[str, float],
        metrics: List[str],
    ):
        """Print a stats comparison table with color-coded changes."""
        click.echo("\n" + "="*60)
        click.echo("  STAT COMPARISON")
        click.echo("="*60)

        click.echo(f"\n{'Metric':<15} {'Original':<12} {'Optimized':<12} {'Change':<10}")
        click.echo("-" * 50)

        for metric in metrics:
            orig = original.get(metric, 0)
            opt = optimized.get(metric, 0)

            if orig == 0:
                change_pct = 0 if opt == 0 else 100
            else:
                change_pct = ((opt - orig) / orig) * 100

            # Color based on improvement (higher is better for most stats)
            if change_pct > 0:
                color = "green"
                sign = "+"
            elif change_pct < 0:
                color = "red"
                sign = ""
            else:
                color = "white"
                sign = ""

            click.echo(
                f"{metric:<15} {orig:<12,.0f} {opt:<12,.0f} ",
                nl=False
            )
            click.secho(f"{sign}{change_pct:.1f}%", fg=color)

    @staticmethod
    def progress_bar(current: int, total: int, prefix: str = "", width: int = 40):
        """Print a simple progress bar."""
        pct = current / total if total > 0 else 0
        filled = int(width * pct)
        bar = "█" * filled + "░" * (width - filled)
        click.echo(f"\r{prefix} [{bar}] {pct*100:.0f}%", nl=False)
        if current >= total:
            click.echo()

    @staticmethod
    def section(title: str, content: Dict[str, Any]):
        """Print a titled section with key-value pairs."""
        click.echo(f"\n{title}")
        click.echo("-" * len(title))
        for key, value in content.items():
            if isinstance(value, float):
                formatted = f"{value:,.2f}"
            elif isinstance(value, int):
                formatted = f"{value:,}"
            else:
                formatted = str(value)
            click.echo(f"  {key}: {formatted}")
