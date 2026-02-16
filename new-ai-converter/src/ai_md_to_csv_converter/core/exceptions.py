"""Custom exceptions for the converter system."""


class ConverterError(Exception):
    """Base exception for all converter errors."""
    pass


class ConfigError(ConverterError):
    """Configuration related errors."""
    pass


class PreprocessError(ConverterError):
    """Preprocessing errors."""
    pass


class ConversionError(ConverterError):
    """AI conversion errors."""
    pass


class ProviderError(ConverterError):
    """AI provider errors."""
    pass


class RateLimitError(ProviderError):
    """Rate limit error with retry information."""

    def __init__(self, message: str, retry_after: int = 60):
        super().__init__(message)
        self.retry_after = retry_after


class PostprocessError(ConverterError):
    """Postprocessing errors."""
    pass


class VerificationError(ConverterError):
    """Verification errors."""
    pass


class RetryableError(ConverterError):
    """Base for errors that can be retried."""
    pass
