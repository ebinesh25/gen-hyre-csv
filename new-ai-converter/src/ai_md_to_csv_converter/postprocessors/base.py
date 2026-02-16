"""Abstract base class for postprocessors."""
from abc import ABC, abstractmethod
from typing import Dict, Any

from ..models.results import PipelineContext


class BasePostprocessor(ABC):
    """Base class for all postprocessors.

    All postprocessors must inherit from this class and implement
    the process() method.
    """

    def __init__(self, config: Dict[str, Any]):
        """Initialize the postprocessor.

        Args:
            config: Postprocessor-specific configuration dictionary
        """
        self.config = config
        self.enabled = config.get("enabled", True)
        self.name = config.get("name", self.__class__.__name__)

    @abstractmethod
    async def process(self, content: str, context: PipelineContext) -> str:
        """Process the CSV content.

        Args:
            content: The CSV content to process
            context: The pipeline context object

        Returns:
            Processed CSV content

        Raises:
            PostprocessError: If postprocessing fails
        """
        pass

    def _log_info(self, message: str) -> None:
        """Log an info message.

        Args:
            message: Message to log
        """
        from ..utils.logger import get_logger
        get_logger(__name__).info(f"[{self.name}] {message}")

    def _log_warning(self, message: str) -> None:
        """Log a warning message.

        Args:
            message: Message to log
        """
        from ..utils.logger import get_logger
        get_logger(__name__).warning(f"[{self.name}] {message}")

    def _log_debug(self, message: str) -> None:
        """Log a debug message.

        Args:
            message: Message to log
        """
        from ..utils.logger import get_logger
        get_logger(__name__).debug(f"[{self.name}] {message}")
