"""
Setup command - First-time setup and installation verification.
"""

import click
import subprocess
import shutil
from pathlib import Path
from typing import Optional

from ..utils import get_output_handler


@click.command()
@click.option(
    "--check", "-c",
    is_flag=True,
    help="Only check installation status, don't make changes."
)
@click.option(
    "--decompress-timeless", "-t",
    is_flag=True,
    help="Decompress timeless jewel data files."
)
@click.option(
    "--force", "-f",
    is_flag=True,
    help="Force re-setup even if already done."
)
@click.pass_context
def setup(ctx, check: bool, decompress_timeless: bool, force: bool):
    """
    First-time setup and installation verification.

    Checks:
    - PathOfBuilding submodule is initialized
    - Lua/LuaJIT is installed
    - Timeless jewel data is decompressed

    \b
    Examples:
      poe-optimizer setup --check
      poe-optimizer setup --decompress-timeless
      poe-optimizer setup --force
    """
    output = get_output_handler(ctx)

    click.echo("\n" + "="*60)
    click.echo("  POE-OPTIMIZER SETUP")
    click.echo("="*60 + "\n")

    all_ok = True
    project_root = Path(__file__).parent.parent.parent.parent

    # Check 1: PathOfBuilding submodule
    click.echo("Checking PathOfBuilding submodule...")
    pob_path = project_root / "PathOfBuilding"
    pob_src = pob_path / "src"
    headless = pob_src / "HeadlessWrapper.lua"

    if headless.exists():
        click.secho("  ✓ PathOfBuilding submodule initialized", fg="green")
    else:
        click.secho("  ✗ PathOfBuilding submodule not initialized", fg="red")
        if not check:
            click.echo("    Run: git submodule update --init --recursive")
        all_ok = False

    # Check 2: Lua/LuaJIT
    click.echo("\nChecking Lua installation...")
    lua_cmd = None
    for cmd in ["luajit", "lua5.1", "lua"]:
        if shutil.which(cmd):
            lua_cmd = cmd
            break

    if lua_cmd:
        try:
            result = subprocess.run(
                [lua_cmd, "-v"],
                capture_output=True,
                text=True,
                timeout=5
            )
            version = result.stdout.strip() or result.stderr.strip()
            click.secho(f"  ✓ {lua_cmd} found: {version}", fg="green")
        except Exception as e:
            click.secho(f"  ✗ {lua_cmd} found but failed to run: {e}", fg="red")
            all_ok = False
    else:
        click.secho("  ✗ No Lua interpreter found (luajit, lua5.1, lua)", fg="red")
        click.echo("    Install with: brew install luajit (macOS) or apt install luajit (Linux)")
        all_ok = False

    # Check 3: Timeless jewel data
    click.echo("\nChecking timeless jewel data...")
    timeless_dir = pob_src / "Data" / "TimelessJewelData"
    jewel_types = ["LethalPride", "BrutalRestraint", "MilitantFaith", "ElegantHubris", "GloriousVanity"]

    if timeless_dir.exists():
        bin_files = list(timeless_dir.glob("*.bin"))
        zip_files = list(timeless_dir.glob("*.zip*"))

        if len(bin_files) >= 5:
            click.secho(f"  ✓ Timeless jewel data decompressed ({len(bin_files)} .bin files)", fg="green")
        elif len(zip_files) >= 5:
            click.secho(f"  ! Timeless jewel data compressed ({len(zip_files)} .zip files)", fg="yellow")
            click.echo("    Run: poe-optimizer setup --decompress-timeless")

            if decompress_timeless or force:
                click.echo("\n    Decompressing timeless jewel data...")
                try:
                    from scripts.decompress_timeless_data import decompress_timeless_jewel_files
                    decompress_timeless_jewel_files(output_to_pob=True)
                    click.secho("    ✓ Timeless jewel data decompressed", fg="green")
                except Exception as e:
                    click.secho(f"    ✗ Failed to decompress: {e}", fg="red")
                    all_ok = False
        else:
            click.secho("  ✗ Timeless jewel data missing", fg="red")
            all_ok = False
    else:
        click.secho("  ✗ Timeless jewel data directory not found", fg="red")
        all_ok = False

    # Check 4: Python dependencies
    click.echo("\nChecking Python dependencies...")
    missing_deps = []
    for package in ["click", "networkx", "numpy"]:
        try:
            __import__(package)
        except ImportError:
            missing_deps.append(package)

    if not missing_deps:
        click.secho("  ✓ Core Python dependencies installed", fg="green")
    else:
        click.secho(f"  ✗ Missing packages: {', '.join(missing_deps)}", fg="red")
        click.echo("    Run: pip install -r requirements.txt")
        all_ok = False

    # Summary
    click.echo("\n" + "="*60)
    if all_ok:
        click.secho("  ✓ All checks passed! Ready to optimize.", fg="green")
    else:
        click.secho("  ✗ Some checks failed. See above for details.", fg="red")
    click.echo("="*60 + "\n")

    if not all_ok:
        ctx.exit(1)
