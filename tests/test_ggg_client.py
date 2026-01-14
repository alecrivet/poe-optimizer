"""Tests for GGG API client."""

import pytest
from unittest.mock import Mock, patch, MagicMock

from src.ggg.client import GGGClient, GGGClientConfig, Realm
from src.ggg.exceptions import (
    GGGAPIError,
    AuthenticationError,
    RateLimitError,
    CharacterNotFoundError,
    PrivateProfileError,
)


class TestRealm:
    """Tests for Realm enum."""

    def test_realm_values(self):
        """Test realm enum values."""
        assert Realm.PC.value == "pc"
        assert Realm.XBOX.value == "xbox"
        assert Realm.SONY.value == "sony"


class TestGGGClientConfig:
    """Tests for GGGClientConfig."""

    def test_default_config(self):
        """Test default configuration values."""
        config = GGGClientConfig()
        assert "poe-optimizer" in config.user_agent
        assert config.base_url == "https://www.pathofexile.com"
        assert config.timeout == 30
        assert config.rate_limit_delay == 1.0
        assert config.max_retries == 3

    def test_custom_config(self):
        """Test custom configuration."""
        config = GGGClientConfig(
            user_agent="custom/1.0",
            timeout=60,
            rate_limit_delay=2.0,
        )
        assert config.user_agent == "custom/1.0"
        assert config.timeout == 60
        assert config.rate_limit_delay == 2.0


class TestGGGClient:
    """Tests for GGGClient."""

    @pytest.fixture
    def client(self):
        """Create a client with no rate limiting for tests."""
        config = GGGClientConfig(rate_limit_delay=0)
        return GGGClient(config=config)

    @pytest.fixture
    def mock_response(self):
        """Create a mock response."""
        response = Mock()
        response.status_code = 200
        response.json.return_value = []
        return response

    def test_init_without_auth(self):
        """Test client initialization without auth."""
        client = GGGClient()
        assert "POESESSID" not in client._session.cookies

    def test_init_with_auth(self):
        """Test client initialization with POESESSID."""
        client = GGGClient(poesessid="test-session-id")
        assert client._session.cookies.get("POESESSID") == "test-session-id"

    def test_init_with_realm(self):
        """Test client initialization with realm."""
        client = GGGClient(realm=Realm.XBOX)
        assert client.realm == Realm.XBOX

    @patch("requests.Session.get")
    def test_get_characters_success(self, mock_get, client):
        """Test successful character list retrieval."""
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = [
            {
                "name": "TestChar1",
                "class": "Witch",
                "classId": 3,
                "ascendancyClass": 2,
                "league": "Settlers",
                "level": 95,
            },
            {
                "name": "TestChar2",
                "class": "Shadow",
                "classId": 6,
                "ascendancyClass": 1,
                "league": "Standard",
                "level": 100,
            },
        ]

        characters = client.get_characters("TestAccount")

        assert len(characters) == 2
        assert characters[0].name == "TestChar1"
        assert characters[0].level == 95
        assert characters[1].name == "TestChar2"

        # Verify request parameters
        mock_get.assert_called_once()
        call_args = mock_get.call_args
        assert call_args.kwargs["params"]["accountName"] == "TestAccount"

    @patch("requests.Session.get")
    def test_get_characters_with_realm(self, mock_get, client):
        """Test character list with non-PC realm."""
        client.realm = Realm.XBOX
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = []

        client.get_characters("TestAccount")

        call_args = mock_get.call_args
        assert call_args.kwargs["params"]["realm"] == "xbox"

    @patch("requests.Session.get")
    def test_get_characters_private_profile(self, mock_get, client):
        """Test handling of private profile."""
        mock_get.return_value.status_code = 403

        with pytest.raises(PrivateProfileError):
            client.get_characters("PrivateAccount")

    @patch("requests.Session.get")
    def test_get_characters_not_found(self, mock_get, client):
        """Test handling of account not found."""
        mock_get.return_value.status_code = 404

        with pytest.raises(CharacterNotFoundError):
            client.get_characters("NonExistentAccount")

    @patch("requests.Session.get")
    def test_get_characters_auth_error(self, mock_get, client):
        """Test handling of authentication error."""
        mock_get.return_value.status_code = 401

        with pytest.raises(AuthenticationError):
            client.get_characters("TestAccount")

    @patch("requests.Session.get")
    def test_get_items_success(self, mock_get, client):
        """Test successful item retrieval."""
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            "character": {"name": "TestChar"},
            "items": [
                {
                    "id": "item1",
                    "typeLine": "Hubris Circlet",
                    "baseType": "Hubris Circlet",
                    "frameType": 2,  # Rare
                    "ilvl": 84,
                    "identified": True,
                    "inventoryId": "Helm",
                },
            ],
        }

        items = client.get_items("TestAccount", "TestChar")

        assert items.character["name"] == "TestChar"
        assert len(items.items) == 1
        assert items.items[0].inventory_id == "Helm"

    @patch("requests.Session.get")
    def test_get_passive_skills_success(self, mock_get, client):
        """Test successful passive tree retrieval."""
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            "hashes": [1000, 2000, 3000],
            "hashes_ex": [90000],
            "mastery_effects": {"10000": 20000},
        }

        passives = client.get_passive_skills("TestAccount", "TestChar")

        assert passives.hashes == [1000, 2000, 3000]
        assert passives.hashes_ex == [90000]
        assert passives.mastery_effects[10000] == 20000

    @patch("requests.Session.get")
    @patch("time.sleep")
    def test_rate_limit_retry(self, mock_sleep, mock_get, client):
        """Test rate limit retry behavior."""
        # First call returns 429, second succeeds
        rate_limited = Mock()
        rate_limited.status_code = 429
        rate_limited.headers = {"Retry-After": "5"}

        success = Mock()
        success.status_code = 200
        success.json.return_value = []

        mock_get.side_effect = [rate_limited, success]

        characters = client.get_characters("TestAccount")

        assert mock_get.call_count == 2
        mock_sleep.assert_called_with(5)

    @patch("requests.Session.get")
    @patch("time.sleep")
    def test_rate_limit_exhausted(self, mock_sleep, mock_get, client):
        """Test rate limit exhausted after max retries."""
        rate_limited = Mock()
        rate_limited.status_code = 429
        rate_limited.headers = {"Retry-After": "5"}

        # Return rate limit for all attempts
        mock_get.return_value = rate_limited

        with pytest.raises(RateLimitError):
            client.get_characters("TestAccount")

        # Should have tried max_retries + 1 times
        assert mock_get.call_count == client.config.max_retries + 1

    @patch("requests.Session.get")
    def test_get_full_character(self, mock_get, client):
        """Test getting full character data."""
        # Mock responses for each call
        characters_response = Mock()
        characters_response.status_code = 200
        characters_response.json.return_value = [
            {
                "name": "TestChar",
                "class": "Witch",
                "classId": 3,
                "ascendancyClass": 0,
                "league": "Standard",
                "level": 90,
            },
        ]

        items_response = Mock()
        items_response.status_code = 200
        items_response.json.return_value = {
            "character": {"name": "TestChar"},
            "items": [],
        }

        passives_response = Mock()
        passives_response.status_code = 200
        passives_response.json.return_value = {
            "hashes": [1000, 2000],
            "hashes_ex": [],
            "mastery_effects": {},
        }

        mock_get.side_effect = [
            characters_response,
            items_response,
            passives_response,
        ]

        result = client.get_full_character("TestAccount", "TestChar")

        assert result["character"].name == "TestChar"
        assert result["items"] is not None
        assert result["passives"] is not None
        assert mock_get.call_count == 3

    @patch("requests.Session.get")
    def test_get_full_character_not_found(self, mock_get, client):
        """Test get_full_character with non-existent character."""
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = [
            {
                "name": "OtherChar",
                "class": "Witch",
                "classId": 3,
                "ascendancyClass": 0,
                "league": "Standard",
                "level": 90,
            },
        ]

        with pytest.raises(CharacterNotFoundError):
            client.get_full_character("TestAccount", "NonExistent")

    @patch("requests.Session.get")
    def test_timeout_handling(self, mock_get, client):
        """Test timeout error handling."""
        import requests

        mock_get.side_effect = requests.Timeout("Connection timed out")

        with pytest.raises(GGGAPIError) as exc_info:
            client.get_characters("TestAccount")

        assert "timed out" in str(exc_info.value)

    @patch("requests.Session.get")
    def test_connection_error_handling(self, mock_get, client):
        """Test connection error handling."""
        import requests

        mock_get.side_effect = requests.ConnectionError("Failed to connect")

        with pytest.raises(GGGAPIError) as exc_info:
            client.get_characters("TestAccount")

        assert "Connection error" in str(exc_info.value)


class TestGGGClientIntegration:
    """Integration-style tests (still mocked but testing full flow)."""

    @patch("requests.Session.get")
    def test_full_import_flow(self, mock_get):
        """Test full character import flow."""
        from src.ggg.converter import GGGToPoB

        # Mock all API responses
        characters_response = Mock()
        characters_response.status_code = 200
        characters_response.json.return_value = [
            {
                "name": "MyWitch",
                "class": "Witch",
                "classId": 3,
                "ascendancyClass": 2,
                "league": "Settlers",
                "level": 95,
            },
        ]

        items_response = Mock()
        items_response.status_code = 200
        items_response.json.return_value = {
            "character": {"name": "MyWitch"},
            "items": [
                {
                    "id": "helm1",
                    "typeLine": "Hubris Circlet",
                    "baseType": "Hubris Circlet",
                    "rarity": "rare",
                    "ilvl": 84,
                    "identified": True,
                    "inventoryId": "Helm",
                    "explicitMods": ["+50 to maximum Energy Shield"],
                },
            ],
        }

        passives_response = Mock()
        passives_response.status_code = 200
        passives_response.json.return_value = {
            "hashes": [26725, 45272, 9408],
            "hashes_ex": [],
            "mastery_effects": {"54247": 31821},
        }

        mock_get.side_effect = [
            characters_response,
            items_response,
            passives_response,
        ]

        # Create client and fetch data
        config = GGGClientConfig(rate_limit_delay=0)
        client = GGGClient(config=config)
        data = client.get_full_character("TestAccount", "MyWitch")

        # Convert to PoB
        converter = GGGToPoB()
        xml_str = converter.convert(
            data["character"],
            items=data["items"],
            passives=data["passives"],
        )

        # Verify XML structure
        import xml.etree.ElementTree as ET

        root = ET.fromstring(xml_str)

        assert root.tag == "PathOfBuilding"
        assert root.find("Build") is not None
        assert root.find("Tree") is not None
        assert root.find("Items") is not None

        # Check character info
        build = root.find("Build")
        assert build.get("level") == "95"
        assert build.get("className") == "Witch"
        assert build.get("ascendClassName") == "Elementalist"

        # Check passives
        spec = root.find("Tree/Spec")
        nodes = spec.get("nodes").split(",")
        assert len(nodes) == 3

        # Check mastery
        assert "{54247,31821}" in spec.get("masteryEffects")
