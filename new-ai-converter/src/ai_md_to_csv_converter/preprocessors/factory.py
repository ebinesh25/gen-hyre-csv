"""Factory for creating preprocessor instances."""
from typing import Dict, Type, List

from .base import BasePreprocessor
from .md_formatter import MDFormatterPreprocessor
from .option_normalizer import OptionNormalizerPreprocessor
from .answer_validator import AnswerValidatorPreprocessor
from ..core.exceptions import PreprocessError


class PreprocessorFactory:
    """Factory for creating preprocessor instances."""

    _preprocessors: Dict[str, Type[BasePreprocessor]] = {
        "md_formatter": MDFormatterPreprocessor,
        "option_normalizer": OptionNormalizerPreprocessor,
        "answer_validator": AnswerValidatorPreprocessor,
    }

    @classmethod
    def create(cls, preprocessor_config: dict) -> BasePreprocessor:
        """Create a preprocessor instance.

        Args:
            preprocessor_config: Configuration dict with keys:
                - name: Name of the preprocessor
                - enabled: Whether to enable (default: true)
                - options: Preprocessor-specific options

        Returns:
            Preprocessor instance

        Raises:
            PreprocessError: If preprocessor is not registered
        """
        name = preprocessor_config.get("name")
        if not name:
            raise PreprocessError("Preprocessor config must include 'name'")

        name_lower = name.lower()

        if name_lower not in cls._preprocessors:
            available = ", ".join(cls._preprocessors.keys())
            raise PreprocessError(
                f"Unknown preprocessor: '{name}'. "
                f"Available preprocessors: {available}"
            )

        # Merge name and options into config
        config = dict(preprocessor_config)
        config.setdefault("name", name)

        preprocessor_class = cls._preprocessors[name_lower]
        return preprocessor_class(config)

    @classmethod
    def create_pipeline(cls, configs: List[dict]) -> List[BasePreprocessor]:
        """Create a pipeline of preprocessors.

        Args:
            configs: List of preprocessor configurations

        Returns:
            List of enabled preprocessor instances
        """
        preprocessors = []

        for config in configs:
            # Check if enabled
            if not config.get("enabled", True):
                continue

            try:
                preprocessor = cls.create(config)
                if preprocessor.enabled:
                    preprocessors.append(preprocessor)
            except PreprocessError as e:
                # Log but continue with other preprocessors
                from ..utils.logger import get_logger
                get_logger(__name__).warning(f"Failed to create preprocessor: {e}")

        return preprocessors

    @classmethod
    def register(cls, name: str, preprocessor_class: Type[BasePreprocessor]) -> None:
        """Register a new preprocessor.

        Args:
            name: Name to register the preprocessor under
            preprocessor_class: Preprocessor class (must inherit from BasePreprocessor)
        """
        if not issubclass(preprocessor_class, BasePreprocessor):
            raise PreprocessError(f"{preprocessor_class} must inherit from BasePreprocessor")

        cls._preprocessors[name.lower()] = preprocessor_class

    @classmethod
    def list_preprocessors(cls) -> List[str]:
        """List all registered preprocessors.

        Returns:
            List of preprocessor names
        """
        return list(cls._preprocessors.keys())
