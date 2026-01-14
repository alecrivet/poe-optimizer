"""
Main CLI entry point for poe-optimizer.

Usage:
    poe-optimizer <command> [options]

Commands:
    optimize    Optimize a build's passive tree
    analyze     Analyze build statistics
    diff        Compare two builds
    jewels      Show jewel information
    encode      Encode XML to PoB code
    decode      Decode PoB code to XML
    setup       First-time setup
"""

import click
import sys
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from .commands import optimize, analyze, diff, jewels, codec, setup, account


# Version from package or fallback
VERSION = "0.9.0"


class AliasedGroup(click.Group):
    """Click group that supports command aliases."""

    def get_command(self, ctx, cmd_name):
        # Check for aliases
        aliases = {
            "opt": "optimize",
            "stats": "analyze",
            "compare": "diff",
            "enc": "encode",
            "dec": "decode",
            "acc": "account",
            "import": "account",
        }
        cmd_name = aliases.get(cmd_name, cmd_name)
        return super().get_command(ctx, cmd_name)


@click.group(cls=AliasedGroup, invoke_without_command=True)
@click.option("--version", "-V", is_flag=True, help="Show version and exit.")
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output.")
@click.option("--quiet", "-q", is_flag=True, help="Minimal output.")
@click.pass_context
def cli(ctx, version, verbose, quiet):
    """
    Path of Exile Build Optimizer - Optimize passive trees using PoB calculations.

    \b
    Quick Start:
      poe-optimizer optimize build.xml --objective dps
      poe-optimizer analyze build.xml
      poe-optimizer decode "eNr1Wltv..."

    \b
    For more help on a command:
      poe-optimizer <command> --help
    """
    # Ensure context object exists
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose
    ctx.obj["quiet"] = quiet

    if version:
        click.echo(f"poe-optimizer version {VERSION}")
        ctx.exit(0)

    # Show help if no command given
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


# Register commands
cli.add_command(optimize.optimize)
cli.add_command(analyze.analyze)
cli.add_command(diff.diff)
cli.add_command(jewels.jewels)
cli.add_command(codec.encode)
cli.add_command(codec.decode)
cli.add_command(setup.setup)
cli.add_command(account.account)


def main():
    """Entry point for console script."""
    cli(obj={})


if __name__ == "__main__":
    main()
