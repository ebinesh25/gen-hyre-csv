"""Abstract base class for AI providers."""
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any

from ..core.exceptions import ProviderError


class BaseProvider(ABC):
    """Base class for all AI providers.

    All AI providers must inherit from this class and implement
    the convert() and estimate_cost() methods.
    """

    def __init__(self, config: Dict[str, Any]):
        """Initialize the provider.

        Args:
            config: Provider-specific configuration dictionary
        """
        self.config = config
        self.name: str = config.get("name", "Unknown")

    @abstractmethod
    async def convert(self, system_prompt: str, user_prompt: str) -> str:
        """Convert markdown to CSV using this provider.

        Args:
            system_prompt: The system prompt for the AI
            user_prompt: The user prompt containing markdown content

        Returns:
            CSV output as a string

        Raises:
            ProviderError: If conversion fails
            RateLimitError: If rate limit is hit (with retry info)
        """
        pass

    @abstractmethod
    def estimate_cost(self, input_tokens: int, output_tokens: int) -> Optional[float]:
        """Estimate cost for a conversion (if applicable).

        Args:
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens

        Returns:
            Estimated cost in USD, or None if not applicable
        """
        pass

    @property
    @abstractmethod
    def supports_async(self) -> bool:
        """Whether this provider supports async operations natively.

        Returns:
            True if the provider has native async support,
            False if it uses thread pool wrapper
        """
        pass
