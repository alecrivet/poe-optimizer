"""
Account command - Import characters from GGG account.
"""

import click
from typing import Optional

from ..utils import get_output_handler, common_options


@click.group()
def account():
    """
    Import characters from Path of Exile account.

    \b
    Examples:
      poe-optimizer account list MyAccountName
      poe-optimizer account import MyAccountName MyCharacter
      poe-optimizer account import MyAccountName MyCharacter --poesessid=xxx
    """
    pass


@account.command("list")
@click.argument("account_name", required=True)
@click.option(
    "--realm", "-r",
    type=click.Choice(["pc", "xbox", "sony"]),
    default="pc",
    help="Game realm. Default: pc"
)
@click.option(
    "--poesessid", "-s",
    envvar="POESESSID",
    default=None,
    help="Session ID for private profiles. Can also use POESESSID env var."
)
@click.option(
    "--league", "-l",
    default=None,
    help="Filter by league name."
)
@common_options
@click.pass_context
def list_characters(
    ctx,
    account_name: str,
    realm: str,
    poesessid: Optional[str],
    league: Optional[str],
    json_output: bool,
    output_file: Optional[str],
):
    """
    List characters on an account.

    \b
    Examples:
      poe-optimizer account list MyAccountName
      poe-optimizer account list MyAccountName --league Settlers
      poe-optimizer account list MyAccountName --json
    """
    from src.ggg.client import GGGClient, Realm
    from src.ggg.exceptions import GGGAPIError, PrivateProfileError

    output = get_output_handler(ctx, json_output, output_file)

    output.progress(f"Fetching characters for {account_name}...")

    try:
        realm_enum = Realm(realm)
        client = GGGClient(poesessid=poesessid, realm=realm_enum)
        characters = client.get_characters(account_name)

        # Filter by league if specified
        if league:
            characters = [c for c in characters if league.lower() in c.league.lower()]

        if not characters:
            output.warning("No characters found.")
            return

        # Format output
        result = {
            "account": account_name,
            "count": len(characters),
            "characters": [
                {
                    "name": c.name,
                    "level": c.level,
                    "class": c.class_name,
                    "ascendancy": c.ascendancy_name or "None",
                    "league": c.league,
                }
                for c in characters
            ],
        }

        output.output(result, title="CHARACTERS")

    except PrivateProfileError:
        raise click.ClickException(
            "Profile is private. Use --poesessid or set POESESSID environment variable."
        )
    except GGGAPIError as e:
        raise click.ClickException(f"API error: {e}")


@account.command("import")
@click.argument("account_name", required=True)
@click.argument("character_name", required=True)
@click.option(
    "--realm", "-r",
    type=click.Choice(["pc", "xbox", "sony"]),
    default="pc",
    help="Game realm. Default: pc"
)
@click.option(
    "--poesessid", "-s",
    envvar="POESESSID",
    default=None,
    help="Session ID for private profiles."
)
@click.option(
    "--pob-code", "-c",
    is_flag=True,
    help="Output PoB import code instead of XML."
)
@click.option(
    "--passives-only", "-p",
    is_flag=True,
    help="Import only passive tree (faster, smaller output)."
)
@click.option(
    "--tree-version", "-t",
    default=None,
    help="Passive tree version. Default: auto-detect latest from PoB data."
)
@common_options
@click.pass_context
def import_character(
    ctx,
    account_name: str,
    character_name: str,
    realm: str,
    poesessid: Optional[str],
    pob_code: bool,
    passives_only: bool,
    tree_version: Optional[str],
    json_output: bool,
    output_file: Optional[str],
):
    """
    Import a character to PoB format.

    \b
    Examples:
      poe-optimizer account import MyAccount MyChar -o build.xml
      poe-optimizer account import MyAccount MyChar --pob-code
      poe-optimizer account import MyAccount MyChar --passives-only

    \b
    Pipe to optimize command:
      poe-optimizer account import MyAccount MyChar --pob-code | \\
        poe-optimizer optimize - --objective dps
    """
    from src.ggg.client import GGGClient, Realm
    from src.ggg.converter import GGGToPoB, ConversionOptions
    from src.ggg.exceptions import GGGAPIError, PrivateProfileError, CharacterNotFoundError
    from src.pob.codec import encode_pob_code

    output = get_output_handler(ctx, json_output, output_file)

    try:
        realm_enum = Realm(realm)
        client = GGGClient(poesessid=poesessid, realm=realm_enum)

        # Fetch character data
        output.progress("Fetching character list...")
        characters = client.get_characters(account_name)

        character = None
        for c in characters:
            if c.name.lower() == character_name.lower():
                character = c
                break

        if not character:
            raise click.ClickException(
                f"Character '{character_name}' not found on account '{account_name}'"
            )

        output.progress(
            f"Found {character.name} "
            f"(Level {character.level} {character.ascendancy_name or character.class_name})"
        )

        # Fetch passive tree
        output.progress("Fetching passive tree...")
        passives = client.get_passive_skills(account_name, character.name)

        # Fetch items (unless passives-only)
        items = None
        if not passives_only:
            output.progress("Fetching items...")
            items = client.get_items(account_name, character.name)

        # Convert to PoB format
        output.progress("Converting to PoB format...")
        options = ConversionOptions(
            include_items=not passives_only,
            include_passives=True,
            tree_version=tree_version,
        )

        converter = GGGToPoB(options)
        xml_str = converter.convert(character, items, passives)

        # Output result
        if pob_code:
            code = encode_pob_code(xml_str)
            if output_file:
                with open(output_file, "w") as f:
                    f.write(code)
                output.success(f"PoB code saved to: {output_file}")
            elif json_output:
                result = {
                    "character": character.name,
                    "pob_code": code,
                }
                output.output(result)
            else:
                # Raw output for piping
                click.echo(code)
        elif json_output:
            result = {
                "character": {
                    "name": character.name,
                    "level": character.level,
                    "class": character.class_name,
                    "ascendancy": character.ascendancy_name,
                    "league": character.league,
                },
                "passive_nodes": len(passives.hashes) + len(passives.hashes_ex),
                "mastery_effects": len(passives.mastery_effects),
                "items": len(items.items) if items else 0,
                "pob_code": encode_pob_code(xml_str),
            }
            output.output(result)
        else:
            if output_file:
                with open(output_file, "w") as f:
                    f.write(xml_str)
                output.success(f"Build saved to: {output_file}")
            else:
                click.echo(xml_str)

        # Summary message (only if not raw output)
        if output_file or json_output:
            item_count = len(items.items) if items else 0
            output.success(
                f"Imported {character.name}: "
                f"{len(passives.hashes) + len(passives.hashes_ex)} passives, "
                f"{len(passives.mastery_effects)} masteries"
                + (f", {item_count} items" if items else "")
            )

    except PrivateProfileError:
        raise click.ClickException(
            "Profile is private. Use --poesessid or set POESESSID environment variable."
        )
    except CharacterNotFoundError as e:
        raise click.ClickException(str(e))
    except GGGAPIError as e:
        raise click.ClickException(f"API error: {e}")
