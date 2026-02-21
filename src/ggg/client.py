"""
GGG API Client for Path of Exile character data.

Handles authentication, rate limiting, and API requests to GGG's
character-window endpoints.
"""

import time
import logging
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from enum import Enum

import requests

from .exceptions import (
    GGGAPIError,
    AuthenticationError,
    RateLimitError,
    CharacterNotFoundError,
    PrivateProfileError,
)
from .models import Character, CharacterItems, PassiveTree
from src import __version__

logger = logging.getLogger(__name__)


class Realm(Enum):
    """Supported game realms."""
    PC = "pc"
    XBOX = "xbox"
    SONY = "sony"


@dataclass
class GGGClientConfig:
    """Configuration for GGG API client."""
    user_agent: str = ""
    base_url: str = "https://www.pathofexile.com"
    timeout: int = 30
    rate_limit_delay: float = 1.0  # seconds between requests
    max_retries: int = 3

    def __post_init__(self):
        if not self.user_agent:
            self.user_agent = f"poe-optimizer/{__version__} (https://github.com/alecrivet/poe-optimizer)"


class GGGClient:
    """
    Client for GGG's character-window API endpoints.

    Supports both public profiles (no auth) and private profiles
    (POESESSID cookie required).

    Usage:
        # Public profile
        client = GGGClient()
        characters = client.get_characters("AccountName")

        # Private profile
        client = GGGClient(poesessid="your-session-id")
        characters = client.get_characters("AccountName")
    """

    ENDPOINTS = {
        "characters": "/character-window/get-characters",
        "items": "/character-window/get-items",
        "passives": "/character-window/get-passive-skills",
    }

    def __init__(
        self,
        poesessid: Optional[str] = None,
        config: Optional[GGGClientConfig] = None,
        realm: Realm = Realm.PC,
    ):
        self.config = config or GGGClientConfig()
        self.realm = realm
        self._session = requests.Session()
        self._last_request_time = 0.0

        # Set up headers
        self._session.headers.update({
            "User-Agent": self.config.user_agent,
            "Accept": "application/json",
        })

        # Set up authentication cookie if provided
        if poesessid:
            self._session.cookies.set("POESESSID", poesessid)
            logger.debug("POESESSID cookie configured")

    def _rate_limit(self) -> None:
        """Enforce rate limiting between requests."""
        elapsed = time.time() - self._last_request_time
        if elapsed < self.config.rate_limit_delay:
            sleep_time = self.config.rate_limit_delay - elapsed
            logger.debug(f"Rate limiting: sleeping {sleep_time:.2f}s")
            time.sleep(sleep_time)
        self._last_request_time = time.time()

    def _request(
        self,
        endpoint: str,
        params: Dict[str, Any],
        retries: int = 0,
    ) -> Dict[str, Any]:
        """Make an API request with retry logic."""
        self._rate_limit()

        url = f"{self.config.base_url}{endpoint}"
        logger.debug(f"GET {url} params={params}")

        try:
            response = self._session.get(
                url,
                params=params,
                timeout=self.config.timeout,
            )

            # Handle rate limiting (429)
            if response.status_code == 429:
                if retries < self.config.max_retries:
                    retry_after = int(response.headers.get("Retry-After", 60))
                    logger.warning(f"Rate limited, waiting {retry_after}s before retry")
                    time.sleep(retry_after)
                    return self._request(endpoint, params, retries + 1)
                raise RateLimitError("Rate limit exceeded after retries")

            # Handle authentication errors
            if response.status_code == 401:
                raise AuthenticationError("Invalid POESESSID or session expired")

            # Handle forbidden (private profile)
            if response.status_code == 403:
                raise PrivateProfileError(
                    "Profile is private. Provide POESESSID for private accounts."
                )

            # Handle not found
            if response.status_code == 404:
                raise CharacterNotFoundError("Character or account not found")

            response.raise_for_status()

            data = response.json()
            logger.debug(f"Response received: {len(str(data))} chars")
            return data

        except requests.Timeout:
            raise GGGAPIError(f"Request timed out after {self.config.timeout}s")
        except requests.ConnectionError as e:
            raise GGGAPIError(f"Connection error: {e}")
        except requests.RequestException as e:
            raise GGGAPIError(f"API request failed: {e}")

    def get_characters(self, account_name: str) -> List[Character]:
        """
        Get list of characters for an account.

        Args:
            account_name: GGG account name

        Returns:
            List of Character objects
        """
        params = {"accountName": account_name}

        # Add realm for console
        if self.realm != Realm.PC:
            params["realm"] = self.realm.value

        data = self._request(self.ENDPOINTS["characters"], params)

        # API returns a list directly
        if isinstance(data, list):
            return [Character.from_dict(c) for c in data]

        # Or it might be wrapped in an object
        characters = data.get("characters", data)
        if isinstance(characters, list):
            return [Character.from_dict(c) for c in characters]

        raise GGGAPIError("Unexpected response format from get-characters")

    def get_items(self, account_name: str, character_name: str) -> CharacterItems:
        """
        Get equipped items for a character.

        Args:
            account_name: GGG account name
            character_name: Character name

        Returns:
            CharacterItems object with equipped gear
        """
        params = {
            "accountName": account_name,
            "character": character_name,
        }

        if self.realm != Realm.PC:
            params["realm"] = self.realm.value

        data = self._request(self.ENDPOINTS["items"], params)
        return CharacterItems.from_dict(data)

    def get_passive_skills(
        self,
        account_name: str,
        character_name: str,
    ) -> PassiveTree:
        """
        Get passive skill tree for a character.

        Args:
            account_name: GGG account name
            character_name: Character name

        Returns:
            PassiveTree object with allocated nodes and masteries
        """
        params = {
            "accountName": account_name,
            "character": character_name,
        }

        if self.realm != Realm.PC:
            params["realm"] = self.realm.value

        data = self._request(self.ENDPOINTS["passives"], params)
        return PassiveTree.from_dict(data)

    def get_full_character(
        self,
        account_name: str,
        character_name: str,
    ) -> Dict[str, Any]:
        """
        Get all character data (character info + items + passives).

        This is a convenience method that combines multiple API calls.

        Args:
            account_name: GGG account name
            character_name: Character name

        Returns:
            Dict with 'character', 'items', and 'passives' keys
        """
        characters = self.get_characters(account_name)

        # Find the specific character (case-insensitive)
        character = None
        for c in characters:
            if c.name.lower() == character_name.lower():
                character = c
                break

        if not character:
            raise CharacterNotFoundError(
                f"Character '{character_name}' not found on account '{account_name}'"
            )

        items = self.get_items(account_name, character.name)
        passives = self.get_passive_skills(account_name, character.name)

        return {
            "character": character,
            "items": items,
            "passives": passives,
        }

    def close(self) -> None:
        """Close the underlying requests session."""
        self._session.close()

    def __enter__(self) -> "GGGClient":
        """Enter context manager."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit context manager, closing the session."""
        self.close()

