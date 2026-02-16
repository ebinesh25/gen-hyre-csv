"""Factory for creating fixer instances."""
from typing import Dict, Type

from .base import BaseFixer
from .ai_csv_fixer import AICsvFixer
from ..ai_md_to_csv_converter.core.exceptions import PreprocessError


class FixerFactory:
    """Factory for creating fixer instances."""

    _fixers: Dict[str, Type[BaseFixer]] = {
        "ai_csv_fixer": AICsvFixer,
    }

    @classmethod
    def create(cls, fixer_config: dict) -> BaseFixer:
        """Create a fixer instance.

        Args:
            fixer_config: Configuration dict with keys:
                - name: Name of the fixer
                - enabled: Whether to enable (default: true)
                - options: Fixer-specific options

        Returns:
            Fixer instance

        Raises:
            PreprocessError: If fixer is not registered
        """
        name = fixer_config.get("name")
        if not name:
            raise PreprocessError("Fixer config must include 'name'")

        name_lower = name.lower()

        if name_lower not in cls._fixers:
            available = ", ".join(cls._fixers.keys())
            raise PreprocessError(
                f"Unknown fixer: '{name}'. "
                f"Available fixers: {available}"
            )

        # Merge name and options into config
        config = dict(fixer_config)
        config.setdefault("name", name)

        fixer_class = cls._fixers[name_lower]
        return fixer_class(config)

    @classmethod
    def register(cls, name: str, fixer_class: Type[BaseFixer]) -> None:
        """Register a new fixer.

        Args:
            name: Name to register the fixer under
            fixer_class: Fixer class (must inherit from BaseFixer)
        """
        if not issubclass(fixer_class, BaseFixer):
            raise PreprocessError(f"{fixer_class} must inherit from BaseFixer")

        cls._fixers[name.lower()] = fixer_class

    @classmethod
    def list_fixers(cls) -> list:
        """List all registered fixers.

        Returns:
            List of fixer names
        """
        return list(cls._fixers.keys())
