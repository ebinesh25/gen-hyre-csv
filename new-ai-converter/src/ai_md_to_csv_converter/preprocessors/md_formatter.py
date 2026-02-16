"""MD formatter preprocessor - fixes common markdown formatting issues."""
import re
from typing import Dict, Any

from .base import BasePreprocessor
from ..models.results import PipelineContext
from ..core.exceptions import PreprocessError


class MDFormatterPreprocessor(BasePreprocessor):
    """Fixes common markdown formatting issues in question files.

    Fixes applied:
    1. Fixes escaped question numbers (e.g., "6\." → "6.")
    2. Normalizes spacing (multiple blank lines → single blank line)
    3. Adds missing "Options:" headers where needed
    4. Standardizes answer format
    5. Removes markdown code blocks
    """

    def __init__(self, config: Dict[str, Any]):
        """Initialize MD formatter preprocessor.

        Args:
            config: Configuration with options:
                - fix_question_numbers: Enable question number fixing (default: true)
                - normalize_spacing: Enable spacing normalization (default: true)
                - add_options_headers: Enable adding Options: headers (default: true)
        """
        super().__init__(config)
        self.fix_question_numbers = config.get("fix_question_numbers", True)
        self.normalize_spacing = config.get("normalize_spacing", True)
        self.add_options_headers = config.get("add_options_headers", True)

    async def process(self, content: str, context: PipelineContext) -> str:
        """Process and fix markdown formatting.

        Args:
            content: Raw markdown content
            context: Pipeline context

        Returns:
            Fixed markdown content

        Raises:
            PreprocessError: If processing fails
        """
        try:
            self._log_debug("Starting MD formatting")

            # Apply fixes in sequence
            if self.fix_question_numbers:
                content = self._fix_question_numbers(content)

            if self.normalize_spacing:
                content = self._normalize_spacing(content)

            if self.add_options_headers:
                content = self._add_options_headers(content)

            content = self._remove_code_blocks(content)
            content = self._standardize_answers(content)

            self._log_info("MD formatting complete")
            return content

        except Exception as e:
            raise PreprocessError(f"MD formatting failed: {e}") from e

    def _fix_question_numbers(self, content: str) -> str:
        """Fix escaped question numbers like '6\.' → '6.'.

        Args:
            content: Content to fix

        Returns:
            Content with fixed question numbers
        """
        # Pattern: digit(s) followed by \. (escaped period) at line start
        # e.g., "6\. The sequence..." → "6. The sequence..."
        pattern = r'^(\d+)\\\. '
        replacement = r'\1. '

        result = re.sub(pattern, replacement, content, flags=re.MULTILINE)

        if result != content:
            fixes = len(re.findall(pattern, content, flags=re.MULTILINE))
            self._log_debug(f"Fixed {fixes} escaped question numbers")

        return result

    def _normalize_spacing(self, content: str) -> str:
        """Normalize spacing - collapse multiple blank lines to single blank line.

        Args:
            content: Content to normalize

        Returns:
            Content with normalized spacing
        """
        # Replace 3+ newlines with exactly 2 newlines (single blank line)
        result = re.sub(r'\n\n\n+', '\n\n', content)

        # Also trim trailing whitespace from lines
        lines = result.split('\n')
        lines = [line.rstrip() for line in lines]
        result = '\n'.join(lines)

        return result

    def _add_options_headers(self, content: str) -> str:
        """Add missing "Options:" headers before option lists.

        Detects patterns where options are listed without a header and adds one.

        Args:
            content: Content to process

        Returns:
            Content with Options: headers added
        """
        lines = content.split('\n')
        result_lines = []

        for i, line in enumerate(lines):
            result_lines.append(line)

            # Check if this line looks like a question ending
            # and the next line starts with an option
            if i + 1 < len(lines):
                current_line = line.strip()
                next_line = lines[i + 1].strip()

                # Pattern: Question ends with ?, next line has option format
                # Option format: "A." or "**A." or "A)" etc.
                is_question = current_line.endswith('?')
                is_option = re.match(r'^(\*\*)?[A-Z]\.?', next_line)

                # Also check for "**Options:" patterns that need fixing
                if current_line == "**Options" and not next_line.startswith(":"):
                    # Fix "**Options" → "**Options:**"
                    result_lines[-1] = "**Options:**"

        return '\n'.join(result_lines)

    def _remove_code_blocks(self, content: str) -> str:
        """Remove markdown code block markers.

        Args:
            content: Content to process

        Returns:
            Content with code blocks removed
        """
        # Remove ```markdown and ``` markers
        result = re.sub(r'```markdown?\n?', '', content)
        result = re.sub(r'```\n?', '', result)

        return result

    def _standardize_answers(self, content: str) -> str:
        """Standardize answer format.

        Various formats like:
        - "**Answer : D.40**"
        - "**Answer: B. x = 24, y = 30**"
        - "Answer: Yes"

        Are normalized to a consistent format.

        Args:
            content: Content to process

        Returns:
            Content with standardized answers
        """
        # Ensure consistent spacing around colons in Answer: lines
        # "**Answer : D" → "**Answer: D**"
        result = re.sub(r'\*\*Answer\s*:\s*', '**Answer: ', content)

        # Also fix non-bold Answer: lines
        result = re.sub(r'^Answer\s*:\s*', 'Answer: ', result, flags=re.MULTILINE)

        return result
