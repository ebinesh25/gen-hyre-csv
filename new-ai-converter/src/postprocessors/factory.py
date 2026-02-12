"""Factory for creating postprocessor instances."""
from typing import Dict, Type, List

from .base import BasePostprocessor
from .csv_cleaner import CsvCleanerPostprocessor
from ..core.exceptions import PostprocessError


class PostprocessorFactory:
    """Factory for creating postprocessor instances."""

    _postprocessors: Dict[str, Type[BasePostprocessor]] = {
        "csv_cleaner": CsvCleanerPostprocessor,
    }

    @classmethod
    def create(cls, postprocessor_config: dict) -> BasePostprocessor:
        """Create a postprocessor instance.

        Args:
            postprocessor_config: Configuration dict with keys:
                - name: Name of the postprocessor
                - enabled: Whether to enable (default: true)
                - options: Postprocessor-specific options

        Returns:
            Postprocessor instance

        Raises:
            PostprocessError: If postprocessor is not registered
        """
        name = postprocessor_config.get("name")
        if not name:
            raise PostprocessError("Postprocessor config must include 'name'")

        name_lower = name.lower()

        if name_lower not in cls._postprocessors:
            available = ", ".join(cls._postprocessors.keys())
            raise PostprocessError(
                f"Unknown postprocessor: '{name}'. "
                f"Available postprocessors: {available}"
            )

        # Merge name and options into config
        config = dict(postprocessor_config)
        config.setdefault("name", name)

        postprocessor_class = cls._postprocessors[name_lower]
        return postprocessor_class(config)

    @classmethod
    def create_pipeline(cls, configs: List[dict]) -> List[BasePostprocessor]:
        """Create a pipeline of postprocessors.

        Args:
            configs: List of postprocessor configurations

        Returns:
            List of enabled postprocessor instances
        """
        postprocessors = []

        for config in configs:
            # Check if enabled
            if not config.get("enabled", True):
                continue

            try:
                postprocessor = cls.create(config)
                if postprocessor.enabled:
                    postprocessors.append(postprocessor)
            except PostprocessError as e:
                # Log but continue with other postprocessors
                from ..utils.logger import get_logger
                get_logger(__name__).warning(f"Failed to create postprocessor: {e}")

        return postprocessors

    @classmethod
    def register(cls, name: str, postprocessor_class: Type[BasePostprocessor]) -> None:
        """Register a new postprocessor.

        Args:
            name: Name to register the postprocessor under
            postprocessor_class: Postprocessor class (must inherit from BasePostprocessor)
        """
        if not issubclass(postprocessor_class, BasePostprocessor):
            raise PostprocessError(f"{postprocessor_class} must inherit from BasePostprocessor")

        cls._postprocessors[name.lower()] = postprocessor_class

    @classmethod
    def list_postprocessors(cls) -> List[str]:
        """List all registered postprocessors.

        Returns:
            List of postprocessor names
        """
        return list(cls._postprocessors.keys())
