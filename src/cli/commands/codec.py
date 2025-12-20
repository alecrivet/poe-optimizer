"""
Codec commands - Encode/decode PoB codes.
"""

import click
from typing import Optional
from pathlib import Path

from ..utils import InputHandler, get_output_handler


@click.command()
@click.argument("input_source", required=True, metavar="INPUT")
@click.option(
    "--output", "-o",
    type=click.Path(),
    help="Save output to file."
)
@click.pass_context
def encode(ctx, input_source: str, output: Optional[str]):
    """
    Encode XML to PoB code.

    \b
    INPUT should be:
      - Path to XML file (build.xml)
      - "-" for stdin

    \b
    Examples:
      poe-optimizer encode build.xml
      poe-optimizer encode build.xml -o build_code.txt
      cat build.xml | poe-optimizer encode -
    """
    from src.pob.codec import encode_pob_code

    out = get_output_handler(ctx, output_file=output)

    # Load XML
    out.progress(f"Loading XML from {input_source}...")

    if input_source == "-":
        import sys
        xml_content = sys.stdin.read()
    else:
        path = Path(input_source)
        if not path.exists():
            raise click.ClickException(f"File not found: {input_source}")
        xml_content = path.read_text(encoding="utf-8")

    # Validate it's XML
    if not xml_content.strip().startswith("<?xml") and not xml_content.strip().startswith("<PathOfBuilding"):
        raise click.ClickException("Input does not appear to be valid XML")

    # Encode
    try:
        pob_code = encode_pob_code(xml_content)
    except Exception as e:
        raise click.ClickException(f"Failed to encode: {e}")

    # Output
    if output:
        Path(output).write_text(pob_code)
        out.success(f"PoB code saved to: {output}")
        out.info(f"Code length: {len(pob_code)} characters")
    else:
        click.echo(pob_code)


@click.command()
@click.argument("input_source", required=True, metavar="INPUT")
@click.option(
    "--output", "-o",
    type=click.Path(),
    help="Save output to file."
)
@click.option(
    "--pretty/--no-pretty",
    default=True,
    help="Pretty-print XML output. Default: yes"
)
@click.pass_context
def decode(ctx, input_source: str, output: Optional[str], pretty: bool):
    """
    Decode PoB code to XML.

    \b
    INPUT can be:
      - PoB code string
      - Path to file containing PoB code
      - "-" for stdin

    \b
    Examples:
      poe-optimizer decode "eNr1Wltv2zgQ..."
      poe-optimizer decode build_code.txt -o build.xml
      cat code.txt | poe-optimizer decode -
    """
    from src.pob.codec import decode_pob_code
    import xml.dom.minidom

    out = get_output_handler(ctx, output_file=output)

    # Load input
    out.progress(f"Loading PoB code from {input_source}...")

    if input_source == "-":
        import sys
        pob_code = sys.stdin.read().strip()
    elif Path(input_source).exists():
        pob_code = Path(input_source).read_text(encoding="utf-8").strip()
    else:
        # Assume it's the PoB code itself
        pob_code = input_source

    # Validate it's not XML
    if pob_code.startswith("<?xml") or pob_code.startswith("<PathOfBuilding"):
        raise click.ClickException("Input appears to be XML, not PoB code. Use 'encode' command instead.")

    # Decode
    try:
        xml_content = decode_pob_code(pob_code)
    except Exception as e:
        raise click.ClickException(f"Failed to decode: {e}")

    # Pretty print if requested
    if pretty:
        try:
            dom = xml.dom.minidom.parseString(xml_content.encode("utf-8"))
            xml_content = dom.toprettyxml(indent="  ")
            # Remove extra blank lines
            lines = [line for line in xml_content.split("\n") if line.strip()]
            xml_content = "\n".join(lines)
        except Exception:
            pass  # Fall back to unformatted

    # Output
    if output:
        Path(output).write_text(xml_content)
        out.success(f"XML saved to: {output}")
    else:
        click.echo(xml_content)
