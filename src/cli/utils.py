"""
CLI utilities for input/output handling and common operations.
"""

import sys
import json
import click
from pathlib import Path
from typing import Optional, Dict, Any, Union
from enum import Enum


class InputType(Enum):
    """Type of input source."""
    FILE_XML = "file_xml"
    FILE_POB_CODE = "file_pob_code"
    POB_CODE = "pob_code"
    STDIN = "stdin"


class InputHandler:
    """
    Handles various input sources and normalizes to XML.

    Supports:
    - XML file path
    - PoB code file path
    - PoB code string
    - Stdin input
    """

    @staticmethod
    def detect_input_type(input_str: str) -> InputType:
        """Detect the type of input."""
        # Check if it's stdin marker
        if input_str == "-":
            return InputType.STDIN

        # Check if it's a file path
        path = Path(input_str)
        if path.exists() and path.is_file():
            content = path.read_text(encoding="utf-8", errors="ignore")[:100]
            if content.strip().startswith("<?xml") or content.strip().startswith("<PathOfBuilding"):
                return InputType.FILE_XML
            else:
                return InputType.FILE_POB_CODE

        # Check if it looks like a PoB code (base64-ish)
        if len(input_str) > 50 and not input_str.startswith("<"):
            return InputType.POB_CODE

        # Default to treating as file path (will error if doesn't exist)
        return InputType.FILE_XML

    @staticmethod
    def load(input_str: str, input_type: Optional[InputType] = None) -> str:
        """
        Load input and return normalized XML.

        Args:
            input_str: File path, PoB code, or "-" for stdin
            input_type: Override auto-detection

        Returns:
            Build XML string
        """
        from src.pob.codec import decode_pob_code

        if input_type is None:
            input_type = InputHandler.detect_input_type(input_str)

        if input_type == InputType.STDIN:
            content = sys.stdin.read()
            # Detect if stdin content is XML or PoB code
            if content.strip().startswith("<?xml") or content.strip().startswith("<PathOfBuilding"):
                return content
            else:
                return decode_pob_code(content.strip())

        elif input_type == InputType.FILE_XML:
            path = Path(input_str)
            if not path.exists():
                raise click.ClickException(f"File not found: {input_str}")
            return path.read_text(encoding="utf-8")

        elif input_type == InputType.FILE_POB_CODE:
            path = Path(input_str)
            if not path.exists():
                raise click.ClickException(f"File not found: {input_str}")
            pob_code = path.read_text(encoding="utf-8").strip()
            return decode_pob_code(pob_code)

        elif input_type == InputType.POB_CODE:
            return decode_pob_code(input_str)

        else:
            raise click.ClickException(f"Unknown input type: {input_type}")


class OutputHandler:
    """
    Handles output formatting and destinations.

    Supports:
    - Console (rich formatted)
    - JSON
    - File output
    """

    def __init__(
        self,
        json_output: bool = False,
        output_file: Optional[str] = None,
        quiet: bool = False,
        verbose: bool = False,
    ):
        self.json_output = json_output
        self.output_file = output_file
        self.quiet = quiet
        self.verbose = verbose

    def output(self, data: Union[Dict[str, Any], str], title: Optional[str] = None):
        """Output data in the appropriate format."""
        if self.json_output:
            self._output_json(data)
        else:
            self._output_console(data, title)

    def _output_json(self, data: Union[Dict[str, Any], str]):
        """Output as JSON."""
        if isinstance(data, str):
            data = {"result": data}

        json_str = json.dumps(data, indent=2, default=str)

        if self.output_file:
            Path(self.output_file).write_text(json_str)
            if not self.quiet:
                click.echo(f"Output saved to: {self.output_file}", err=True)
        else:
            click.echo(json_str)

    def _output_console(self, data: Union[Dict[str, Any], str], title: Optional[str] = None):
        """Output formatted console text."""
        if self.output_file:
            if isinstance(data, dict):
                # For file output, use JSON
                Path(self.output_file).write_text(json.dumps(data, indent=2, default=str))
            else:
                Path(self.output_file).write_text(str(data))
            if not self.quiet:
                click.echo(f"Output saved to: {self.output_file}", err=True)
        else:
            if title and not self.quiet:
                click.echo(f"\n{'='*60}")
                click.echo(f"  {title}")
                click.echo(f"{'='*60}\n")

            if isinstance(data, dict):
                self._format_dict(data)
            else:
                click.echo(data)

    def _format_dict(self, data: Dict[str, Any], indent: int = 0):
        """Format a dictionary for console output."""
        prefix = "  " * indent
        for key, value in data.items():
            if isinstance(value, dict):
                click.echo(f"{prefix}{key}:")
                self._format_dict(value, indent + 1)
            elif isinstance(value, list):
                click.echo(f"{prefix}{key}:")
                for item in value:
                    if isinstance(item, dict):
                        self._format_dict(item, indent + 1)
                    else:
                        click.echo(f"{prefix}  - {item}")
            else:
                # Format numbers nicely
                if isinstance(value, float):
                    if abs(value) < 1:
                        formatted = f"{value:.2%}"
                    else:
                        formatted = f"{value:,.2f}"
                elif isinstance(value, int):
                    formatted = f"{value:,}"
                else:
                    formatted = str(value)
                click.echo(f"{prefix}{key}: {formatted}")

    def success(self, message: str):
        """Print success message."""
        if not self.quiet:
            click.secho(f"✓ {message}", fg="green")

    def error(self, message: str):
        """Print error message."""
        click.secho(f"✗ {message}", fg="red", err=True)

    def warning(self, message: str):
        """Print warning message."""
        if not self.quiet:
            click.secho(f"! {message}", fg="yellow", err=True)

    def info(self, message: str):
        """Print info message."""
        if not self.quiet and self.verbose:
            click.echo(f"  {message}", err=True)

    def progress(self, message: str):
        """Print progress message."""
        if not self.quiet:
            click.echo(f"  {message}", err=True)


def common_options(func):
    """Decorator to add common options to commands."""
    func = click.option(
        "--json", "-j", "json_output", is_flag=True,
        help="Output as JSON."
    )(func)
    func = click.option(
        "--output", "-o", "output_file", type=click.Path(),
        help="Save output to file."
    )(func)
    return func


def input_argument(func):
    """Decorator to add input argument to commands."""
    func = click.argument(
        "input_source",
        required=True,
        metavar="INPUT"
    )(func)
    return func


def get_output_handler(ctx, json_output: bool = False, output_file: Optional[str] = None) -> OutputHandler:
    """Create an OutputHandler from context and options."""
    return OutputHandler(
        json_output=json_output,
        output_file=output_file,
        quiet=ctx.obj.get("quiet", False),
        verbose=ctx.obj.get("verbose", False),
    )
