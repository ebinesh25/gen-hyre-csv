"""CSV cleaner postprocessor - removes conversational text from AI output."""
import re
from typing import Dict, Any

from .base import BasePostprocessor
from ..models.results import PipelineContext
from ..core.exceptions import PostprocessError


class CsvCleanerPostprocessor(BasePostprocessor):
    """Cleans CSV output from AI by removing conversational text.

    Removes:
    1. Markdown code blocks (```csv, ```)
    2. Conversational text at the beginning
    3. Conversational text at the end
    4. Lines that don't look like CSV data
    """

    def __init__(self, config: Dict[str, Any]):
        """Initialize CSV cleaner postprocessor.

        Args:
            config: Configuration with options:
                - remove_code_blocks: Remove ```csv and ``` markers (default: true)
                - filter_non_csv_lines: Filter lines that aren't CSV (default: true)
                - validate_header: Ensure CSV header is present (default: true)
        """
        super().__init__(config)
        self.remove_code_blocks = config.get("remove_code_blocks", True)
        self.filter_non_csv_lines = config.get("filter_non_csv_lines", True)
        self.validate_header = config.get("validate_header", True)

    async def process(self, content: str, context: PipelineContext) -> str:
        """Process and clean CSV output.

        Args:
            content: Raw CSV output from AI
            context: Pipeline context

        Returns:
            Cleaned CSV content

        Raises:
            PostprocessError: If processing fails or validation fails
        """
        try:
            self._log_debug("Starting CSV cleaning")

            original_lines = content.count('\n')

            if self.remove_code_blocks:
                content = self._remove_code_blocks(content)

            if self.filter_non_csv_lines:
                content = self._filter_csv_lines(content)

            if self.validate_header:
                self._validate_header(content)

            cleaned_lines = content.count('\n')
            removed = original_lines - cleaned_lines

            if removed > 0:
                self._log_info(f"Removed {removed} lines of conversational text")

            return content.strip()

        except Exception as e:
            raise PostprocessError(f"CSV cleaning failed: {e}") from e

    def _remove_code_blocks(self, content: str) -> str:
        """Remove markdown code block markers.

        Args:
            content: Content to process

        Returns:
            Content without code block markers
        """
        # Remove ```csv markers
        result = content.replace("```csv", "")
        result = result.replace("```CSV", "")

        # Remove standalone ``` lines
        result = re.sub(r'^```\s*$', '', result, flags=re.MULTILINE)

        return result

    def _filter_csv_lines(self, content: str) -> str:
        """Filter out non-CSV lines (conversational text).

        Keeps only:
        - Header line (starts with "Question Type,")
        - Data rows (start with "objective,")

        Args:
            content: Content to filter

        Returns:
            Content with only CSV lines
        """
        lines = content.split('\n')
        csv_lines = []

        for line in lines:
            stripped = line.strip()

            # Keep empty lines (for spacing)
            if not stripped:
                csv_lines.append(line)
                continue

            # Keep header line
            if stripped.startswith("Question Type,") or stripped.startswith("Question Type,"):
                csv_lines.append(line)
                continue

            # Keep data rows (start with "objective,")
            if stripped.startswith("objective,"):
                csv_lines.append(line)
                continue

            # If we've started seeing CSV data and hit a non-CSV line, stop
            if csv_lines:
                # Check if we've seen at least the header
                has_header = any("Question Type," in l for l in csv_lines)
                if has_header:
                    # Stop at first non-CSV line after data started
                    self._log_debug(f"Stopping at non-CSV line: {stripped[:50]}...")
                    break

        return '\n'.join(csv_lines)

    def _validate_header(self, content: str) -> None:
        """Validate that CSV header is present.

        Args:
            content: Content to validate

        Raises:
            PostprocessError: If header is missing or invalid
        """
        lines = content.strip().split('\n')

        if not lines:
            raise PostprocessError("CSV output is empty")

        header = lines[0].strip()

        # Check for expected header format
        if not header.startswith("Question Type,"):
            raise PostprocessError(
                f"Invalid CSV header. Expected to start with 'Question Type,', got: {header[:50]}"
            )

        # Check for essential columns
        required_columns = ["Question Type", "Question", "Option count", "Answer"]
        missing = []

        for col in required_columns:
            if col not in header:
                missing.append(col)

        if missing:
            self._log_warning(f"CSV header may be missing columns: {missing}")
