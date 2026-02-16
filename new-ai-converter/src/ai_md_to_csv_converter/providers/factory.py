"""Factory for creating AI provider instances."""
from typing import Dict, Type

from .base import BaseProvider
from .groq_provider import GroqProvider
from .claude_cli_provider import ClaudeCliProvider
from .openai_provider import OpenAIProvider
from ..core.exceptions import ProviderError


class ProviderFactory:
    """Factory for creating AI provider instances."""

    _providers: Dict[str, Type[BaseProvider]] = {
        "groq": GroqProvider,
        "claude_cli": ClaudeCliProvider,
        "openai": OpenAIProvider,
    }

    @classmethod
    def create(cls, provider_name: str, config: dict) -> BaseProvider:
        """Create a provider instance.

        Args:
            provider_name: Name of the provider (e.g., "groq", "claude_cli")
            config: Provider-specific configuration

        Returns:
            Provider instance

        Raises:
            ProviderError: If provider is not registered
        """
        provider_name_lower = provider_name.lower()

        if provider_name_lower not in cls._providers:
            available = ", ".join(cls._providers.keys())
            raise ProviderError(
                f"Unknown provider: '{provider_name}'. "
                f"Available providers: {available}"
            )

        provider_class = cls._providers[provider_name_lower]
        return provider_class(config)

    @classmethod
    def register(cls, name: str, provider_class: Type[BaseProvider]) -> None:
        """Register a new provider.

        Args:
            name: Name to register the provider under
            provider_class: Provider class (must inherit from BaseProvider)
        """
        if not issubclass(provider_class, BaseProvider):
            raise ProviderError(f"{provider_class} must inherit from BaseProvider")

        cls._providers[name.lower()] = provider_class

    @classmethod
    def list_providers(cls) -> list:
        """List all registered providers.

        Returns:
            List of provider names
        """
        return list(cls._providers.keys())
