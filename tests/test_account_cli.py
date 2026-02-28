"""Tests for account CLI commands."""

import pytest
from click.testing import CliRunner
from unittest.mock import Mock, patch, MagicMock

from src.cli.main import cli
from src.ggg.models import Character, CharacterItems, PassiveTree, Item
from src.ggg.exceptions import PrivateProfileError, CharacterNotFoundError, GGGAPIError


@pytest.fixture
def runner():
    """Create a CLI runner."""
    return CliRunner()


@pytest.fixture
def mock_characters():
    """Create mock character data."""
    return [
        Character(
            name="TestWitch",
            class_name="Witch",
            class_id=3,
            ascendancy_class=2,
            ascendancy_name="Elementalist",
            league="Settlers",
            level=95,
            experience=1000000000,
        ),
        Character(
            name="TestShadow",
            class_name="Shadow",
            class_id=6,
            ascendancy_class=1,
            ascendancy_name="Assassin",
            league="Standard",
            level=100,
            experience=2000000000,
        ),
    ]


@pytest.fixture
def mock_passives():
    """Create mock passive data."""
    return PassiveTree(
        hashes=[26725, 45272, 9408, 12345, 67890],
        hashes_ex=[],
        mastery_effects={54247: 31821},
        jewel_data={},
    )


class TestAccountCommand:
    """Tests for account command group."""

    def test_account_help(self, runner):
        """Test account --help output."""
        result = runner.invoke(cli, ["account", "--help"])
        assert result.exit_code == 0
        assert "Import characters from Path of Exile account" in result.output
        assert "list" in result.output
        assert "import" in result.output

    def test_account_alias_acc(self, runner):
        """Test 'acc' alias for account."""
        result = runner.invoke(cli, ["acc", "--help"])
        assert result.exit_code == 0
        assert "Import characters from Path of Exile account" in result.output


class TestListCommand:
    """Tests for account list command."""

    @patch("src.ggg.client.GGGClient")
    def test_list_characters_success(self, mock_client_class, runner, mock_characters):
        """Test successful character listing."""
        mock_client = Mock()
        mock_client.get_characters.return_value = mock_characters
        mock_client_class.return_value = mock_client

        result = runner.invoke(cli, ["account", "list", "TestAccount"])

        assert result.exit_code == 0
        assert "TestWitch" in result.output
        assert "TestShadow" in result.output
        assert "95" in result.output
        assert "100" in result.output

    @patch("src.ggg.client.GGGClient")
    def test_list_characters_with_league_filter(
        self, mock_client_class, runner, mock_characters
    ):
        """Test character listing with league filter."""
        mock_client = Mock()
        mock_client.get_characters.return_value = mock_characters
        mock_client_class.return_value = mock_client

        result = runner.invoke(
            cli, ["account", "list", "TestAccount", "--league", "Settlers"]
        )

        assert result.exit_code == 0
        assert "TestWitch" in result.output
        assert "TestShadow" not in result.output  # Standard league

    @patch("src.ggg.client.GGGClient")
    def test_list_characters_private_profile(self, mock_client_class, runner):
        """Test handling of private profile error."""
        mock_client = Mock()
        mock_client.get_characters.side_effect = PrivateProfileError("Private")
        mock_client_class.return_value = mock_client

        result = runner.invoke(cli, ["account", "list", "PrivateAccount"])

        assert result.exit_code != 0
        assert "private" in result.output.lower()
        assert "poesessid" in result.output.lower()

    @patch("src.ggg.client.GGGClient")
    def test_list_characters_json_output(
        self, mock_client_class, runner, mock_characters
    ):
        """Test JSON output format."""
        mock_client = Mock()
        mock_client.get_characters.return_value = mock_characters
        mock_client_class.return_value = mock_client

        result = runner.invoke(cli, ["account", "list", "TestAccount", "--json"])

        assert result.exit_code == 0
        # JSON output should include account and count
        assert "TestAccount" in result.output or "account" in result.output.lower()

    @patch("src.ggg.client.GGGClient")
    def test_list_no_characters(self, mock_client_class, runner):
        """Test listing with no characters."""
        mock_client = Mock()
        mock_client.get_characters.return_value = []
        mock_client_class.return_value = mock_client

        result = runner.invoke(cli, ["account", "list", "EmptyAccount"])

        assert result.exit_code == 0
        assert "No characters found" in result.output


class TestImportCommand:
    """Tests for account import command."""

    @patch("src.ggg.client.GGGClient")
    def test_import_character_pob_code(
        self, mock_client_class, runner, mock_characters, mock_passives
    ):
        """Test importing character as PoB code."""
        mock_client = Mock()
        mock_client.get_characters.return_value = mock_characters
        mock_client.get_passive_skills.return_value = mock_passives
        mock_client_class.return_value = mock_client

        result = runner.invoke(
            cli,
            ["account", "import", "TestAccount", "TestWitch", "--pob-code", "--passives-only"],
        )

        assert result.exit_code == 0
        # PoB codes start with "eN" (base64 of zlib compressed data)
        assert result.output.strip().startswith("eN") or len(result.output.strip()) > 50

    @patch("src.ggg.client.GGGClient")
    def test_import_character_xml(
        self, mock_client_class, runner, mock_characters, mock_passives
    ):
        """Test importing character as XML."""
        mock_client = Mock()
        mock_client.get_characters.return_value = mock_characters
        mock_client.get_passive_skills.return_value = mock_passives
        mock_client.get_items.return_value = CharacterItems(
            character={"name": "TestWitch"}, items=[]
        )
        mock_client_class.return_value = mock_client

        result = runner.invoke(
            cli, ["account", "import", "TestAccount", "TestWitch"]
        )

        assert result.exit_code == 0
        assert "<PathOfBuilding>" in result.output
        assert "<Build" in result.output
        assert "<Tree" in result.output

    @patch("src.ggg.client.GGGClient")
    def test_import_character_not_found(self, mock_client_class, runner, mock_characters):
        """Test importing non-existent character."""
        mock_client = Mock()
        mock_client.get_characters.return_value = mock_characters
        mock_client_class.return_value = mock_client

        result = runner.invoke(
            cli, ["account", "import", "TestAccount", "NonExistent"]
        )

        assert result.exit_code != 0
        assert "not found" in result.output.lower()

    @patch("src.ggg.client.GGGClient")
    def test_import_passives_only(
        self, mock_client_class, runner, mock_characters, mock_passives
    ):
        """Test importing with --passives-only flag."""
        mock_client = Mock()
        mock_client.get_characters.return_value = mock_characters
        mock_client.get_passive_skills.return_value = mock_passives
        mock_client_class.return_value = mock_client

        result = runner.invoke(
            cli,
            ["account", "import", "TestAccount", "TestWitch", "--passives-only"],
        )

        assert result.exit_code == 0
        # Should not have called get_items
        mock_client.get_items.assert_not_called()

    @patch("src.ggg.client.GGGClient")
    def test_import_with_poesessid(
        self, mock_client_class, runner, mock_characters, mock_passives
    ):
        """Test importing with POESESSID."""
        mock_client = Mock()
        mock_client.get_characters.return_value = mock_characters
        mock_client.get_passive_skills.return_value = mock_passives
        mock_client_class.return_value = mock_client

        result = runner.invoke(
            cli,
            [
                "account",
                "import",
                "TestAccount",
                "TestWitch",
                "--poesessid",
                "test-session-id",
                "--passives-only",
            ],
        )

        assert result.exit_code == 0
        # Verify POESESSID was passed to client
        mock_client_class.assert_called_once()
        call_kwargs = mock_client_class.call_args.kwargs
        assert call_kwargs.get("poesessid") == "test-session-id"

    @patch("src.ggg.client.GGGClient")
    def test_import_api_error(self, mock_client_class, runner):
        """Test handling of API error during import."""
        mock_client = Mock()
        mock_client.get_characters.side_effect = GGGAPIError("API Error")
        mock_client_class.return_value = mock_client

        result = runner.invoke(
            cli, ["account", "import", "TestAccount", "TestChar"]
        )

        assert result.exit_code != 0
        assert "API error" in result.output

    def test_import_help(self, runner):
        """Test import --help output."""
        result = runner.invoke(cli, ["account", "import", "--help"])

        assert result.exit_code == 0
        assert "Import a character to PoB format" in result.output
        assert "--pob-code" in result.output
        assert "--passives-only" in result.output
        assert "--poesessid" in result.output


class TestCommandAliases:
    """Tests for command aliases."""

    def test_import_alias(self, runner):
        """Test 'import' as alias for 'account'."""
        # The 'import' alias should show account help
        result = runner.invoke(cli, ["import", "--help"])
        assert result.exit_code == 0
        # Should show account group help
        assert "Import characters" in result.output or "account" in result.output.lower()
