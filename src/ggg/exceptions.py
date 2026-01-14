"""
Custom exceptions for GGG API operations.
"""


class GGGAPIError(Exception):
    """Base exception for GGG API errors."""
    pass


class AuthenticationError(GGGAPIError):
    """Invalid or expired POESESSID."""
    pass


class RateLimitError(GGGAPIError):
    """API rate limit exceeded."""
    pass


class CharacterNotFoundError(GGGAPIError):
    """Character or account not found."""
    pass


class PrivateProfileError(GGGAPIError):
    """Profile is private and requires authentication."""
    pass


class ConversionError(Exception):
    """Error during JSON to XML conversion."""
    pass
