"""Base fixer class for CSV fixing."""
from abc import ABC, abstractmethod
from typing import Dict, Any

from ..ai_md_to_csv_converter.models.results import PipelineContext


class BaseFixer(ABC):
    """Abstract base class for CSV fixers.

    Fixers are responsible for correcting errors in CSV output,
    typically using AI or rule-based approaches.
    """

    def __init__(self, config: Dict[str, Any]):
        """Initialize the fixer.

        Args:
            config: Fixer configuration with keys:
                - name: Name of the fixer
                - enabled: Whether to enable (default: true)
                - options: Fixer-specific options
        """
        self.config = config
        self.name = config.get("name", "unnamed_fixer")
        self.enabled = config.get("enabled", True)
        self.options = config.get("options", {})

    @abstractmethod
    async def fix(
        self,
        md_content: str,
        csv_content: str,
        error_report: Dict[str, Any],
        context: PipelineContext
    ) -> str:
        """Fix CSV errors based on error report.

        Args:
            md_content: Original markdown content
            csv_content: Generated CSV with errors
            error_report: Verification error report
            context: Pipeline context

        Returns:
            Fixed CSV content

        Raises:
            FixError: If fixing fails
        """
        pass

    def _log_debug(self, message: str) -> None:
        """Log a debug message.

        Args:
            message: Message to log
        """
        from ..ai_md_to_csv_converter.utils.logger import get_logger
        get_logger(__name__).debug(f"[{self.name}] {message}")

    def _log_info(self, message: str) -> None:
        """Log an info message.

        Args:
            message: Message to log
        """
        from ..ai_md_to_csv_converter.utils.logger import get_logger
        get_logger(__name__).info(f"[{self.name}] {message}")

    def _log_warning(self, message: str) -> None:
        """Log a warning message.

        Args:
            message: Message to log
        """
        from ..ai_md_to_csv_converter.utils.logger import get_logger
        get_logger(__name__).warning(f"[{self.name}] {message}")

    def _log_error(self, message: str) -> None:
        """Log an error message.

        Args:
            message: Message to log
        """
        from ..ai_md_to_csv_converter.utils.logger import get_logger
        get_logger(__name__).error(f"[{self.name}] {message}")
