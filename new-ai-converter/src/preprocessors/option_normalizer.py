"""Option normalizer preprocessor - ensures consistent option format."""
import re
from typing import Dict, Any, List, Tuple

from .base import BasePreprocessor
from ..models.results import PipelineContext
from ..core.exceptions import PreprocessError


class OptionNormalizerPreprocessor(BasePreprocessor):
    """Normalizes option format in markdown questions.

    Ensures:
    1. All options have letter prefixes (A., B., C., etc.)
    2. Options are properly formatted
    3. Validates option count consistency
    """

    def __init__(self, config: Dict[str, Any]):
        """Initialize option normalizer preprocessor.

        Args:
            config: Configuration with options:
                - ensure_letter_prefixes: Add missing letter prefixes (default: true)
                - validate_option_counts: Warn on inconsistent option counts (default: true)
        """
        super().__init__(config)
        self.ensure_letter_prefixes = config.get("ensure_letter_prefixes", True)
        self.validate_option_counts = config.get("validate_option_counts", True)

    async def process(self, content: str, context: PipelineContext) -> str:
        """Process and normalize option format.

        Args:
            content: Markdown content
            context: Pipeline context

        Returns:
            Content with normalized options

        Raises:
            PreprocessError: If processing fails
        """
        try:
            self._log_debug("Starting option normalization")

            if self.ensure_letter_prefixes:
                content = self._ensure_letter_prefixes(content)

            if self.validate_option_counts:
                self._validate_option_counts(content, context)

            self._log_info("Option normalization complete")
            return content

        except Exception as e:
            raise PreprocessError(f"Option normalization failed: {e}") from e

    def _ensure_letter_prefixes(self, content: str) -> str:
        """Ensure all options have letter prefixes (A., B., C., etc.).

        Detects option-like lines that are missing prefixes and adds them.

        Args:
            content: Content to process

        Returns:
            Content with normalized option prefixes
        """
        lines = content.split('\n')
        result_lines = []
        option_index = 0

        for line in lines:
            stripped = line.strip()

            # Check if this is an option line
            # Pattern: "**A. option" or "A. option" or "A) option"
            option_match = re.match(r'^(\*\*)?([A-Z])[\.\)]\s*(.+)$', stripped)

            if option_match:
                prefix = option_match.group(1) or ''  # Preserve bold marker if present
                letter = option_match.group(2)
                option_text = option_match.group(3)

                # Reset option count on new option (A.)
                if letter == 'A':
                    option_index = 1
                else:
                    option_index += 1

                # Verify letters are sequential
                expected_letter = chr(64 + option_index)  # 65 = 'A'
                if letter != expected_letter:
                    self._log_warning(
                        f"Non-sequential option letters: expected {expected_letter}, got {letter}"
                    )

                result_lines.append(line)

            elif self._is_option_without_prefix(stripped):
                # Line looks like an option but has no prefix
                # Try to determine the appropriate letter
                option_index += 1
                letter = chr(64 + option_index)

                # Check if previous line had bold prefix
                prev_line = result_lines[-1] if result_lines else ""
                bold_marker = "**" if "**Options:" in prev_line or "**Options" in prev_line else ""

                # Add the prefix
                new_line = f"{bold_marker}{letter}. {stripped}"
                result_lines.append(new_line)
                self._log_debug(f"Added option prefix: '{stripped}' → '{new_line}'")

            else:
                # Not an option line, reset index
                if stripped and not stripped.startswith('**'):
                    option_index = 0
                result_lines.append(line)

        return '\n'.join(result_lines)

    def _is_option_without_prefix(self, line: str) -> bool:
        """Check if a line is an option without a letter prefix.

        Heuristics:
        - Short text (typically 1-10 words)
        - Not a question (doesn't end with ?)
        - Not a header/solution/answer line
        - After "**Options" marker

        Args:
            line: Line to check

        Returns:
            True if line appears to be an option without prefix
        """
        # Skip empty lines
        if not line:
            return False

        # Skip known non-option lines
        skip_prefixes = (
            "**Answer",
            "**Solution",
            "Answer:",
            "Solution:",
            "Explanation:",
            "NOTE:",
            "#",
            "##",
        )
        if line.startswith(skip_prefixes):
            return False

        # Skip questions (typically end with ?)
        if line.endswith('?'):
            return False

        # Check for option-like content
        # Options are typically short (1-50 chars) and don't contain complex formatting
        if 1 < len(line) < 100:
            # Check if it's just plain text (no markdown)
            if not line.startswith('*') and not line.startswith('`'):
                # Avoid false positives: skip if it looks like a sentence
                # Options rarely have multiple sentences
                if line.count('. ') <= 1 and line.count(', ') <= 2:
                    return True

        return False

    def _validate_option_counts(self, content: str, context: PipelineContext) -> None:
        """Validate that option counts are consistent.

        Checks for:
        - Questions with varying option counts (2, 3, 4, 5, 6)
        - Warns if there's significant inconsistency

        Args:
            content: Content to validate
            context: Pipeline context for storing metadata
        """
        questions = self._extract_questions_with_options(content)

        if not questions:
            return

        option_counts = [q['option_count'] for q in questions]

        # Count by option count
        count_distribution = {}
        for count in option_counts:
            count_distribution[count] = count_distribution.get(count, 0) + 1

        self._log_debug(f"Option count distribution: {count_distribution}")

        # Store in context for later use
        context.metadata['option_counts'] = option_counts
        context.metadata['option_count_distribution'] = count_distribution

        # Warn if there are many different counts
        unique_counts = len(count_distribution)
        if unique_counts > 3:
            self._log_warning(
                f"Found {unique_counts} different option counts: {list(count_distribution.keys())}"
            )

    def _extract_questions_with_options(self, content: str) -> List[Dict[str, Any]]:
        """Extract questions and count their options.

        Args:
            content: Markdown content

        Returns:
            List of questions with option counts
        """
        questions = []
        lines = content.split('\n')
        current_question = None
        option_count = 0

        for line in lines:
            stripped = line.strip()

            # Detect question start (ends with ? and has a number prefix)
            if re.match(r'^\d+\. ', stripped) or re.match(r'^\d+\\\.', stripped):
                # Save previous question if exists
                if current_question:
                    questions.append({
                        'question': current_question,
                        'option_count': option_count
                    })

                current_question = stripped
                option_count = 0

            # Detect options
            elif re.match(r'^(\*\*)?[A-Z][\.\)]', stripped):
                option_count += 1

            # Detect answer line (end of options)
            elif stripped.startswith("**Answer") or stripped.startswith("Answer:"):
                if current_question:
                    questions.append({
                        'question': current_question,
                        'option_count': option_count
                    })
                    current_question = None
                    option_count = 0

        # Don't forget the last question
        if current_question:
            questions.append({
                'question': current_question,
                'option_count': option_count
            })

        return questions
