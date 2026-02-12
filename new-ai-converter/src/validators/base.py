"""Abstract base class for validators."""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

from ..models.results import PipelineContext


class BaseValidator(ABC):
    """Base class for all validators.

    All validators must inherit from this class and implement
    the verify() method.
    """

    def __init__(self, config):
        """Initialize the validator.

        Args:
            config: Validator-specific configuration
        """
        self.config = config
        self.enabled = config.get("enabled", True)
        self.name = config.get("name", self.__class__.__name__)

    @abstractmethod
    async def verify(self, file_path, context: PipelineContext) -> Optional[Dict[str, Any]]:
        """Verify a file.

        Args:
            file_path: Path to file to verify
            context: Pipeline context

        Returns:
            Verification result dict, or None if verification failed
        """
        pass
