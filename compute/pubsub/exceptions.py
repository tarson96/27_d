"""
Custom exceptions for the SN27 Validator Pub/Sub library.
"""


class PubSubError(Exception):
    """Base exception for all pub/sub related errors."""
    pass


class MessageValidationError(PubSubError):
    """Raised when message validation fails."""
    pass


class PublishError(PubSubError):
    """Raised when message publishing fails."""
    pass


class ConnectionError(PubSubError):
    """Raised when connection to pub/sub service fails."""
    pass


class AuthenticationError(PubSubError):
    """Raised when authentication with GCP fails."""
    pass


class TopicNotFoundError(PubSubError):
    """Raised when specified topic doesn't exist."""
    pass


class ConfigurationError(PubSubError):
    """Raised when configuration is invalid."""
    pass
