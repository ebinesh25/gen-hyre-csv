"""AI-based CSV fixer using Claude CLI provider."""
import json
import re
from pathlib import Path
from typing import Dict, Any

from .base import BaseFixer
from ..ai_md_to_csv_converter.models.results import PipelineContext
from ..ai_md_to_csv_converter.core.exceptions import ConversionError


class AICsvFixer(BaseFixer):
    """AI-based CSV fixer that uses Claude CLI to correct structural errors.

    This fixer is designed to ONLY fix structural issues like:
    - Splitting merged data into proper columns
    - Rearranging data in wrong columns
    - Fixing CSV formatting issues

    It does NOT change content - only structure.
    """

    def __init__(self, config: Dict[str, Any]):
        """Initialize the AI CSV fixer.

        Args:
            config: Fixer configuration with keys:
                - provider: AI provider to use (default: "claude_cli")
                - single_attempt: Only try once (default: true)
                - validate_output: Validate fixed CSV structure (default: true)
        """
        super().__init__(config)
        self.provider_name = config.get("provider", "claude_cli")
        self.single_attempt = config.get("single_attempt", True)
        self.validate_output = config.get("validate_output", True)

    async def fix(
        self,
        md_content: str,
        csv_content: str,
        error_report: Dict[str, Any],
        context: PipelineContext
    ) -> str:
        """Fix CSV errors using AI.

        Args:
            md_content: Original markdown content
            csv_content: Generated CSV with errors
            error_report: Verification error report
            context: Pipeline context

        Returns:
            Fixed CSV content

        Raises:
            ConversionError: If fixing fails
        """
        self._log_info(f"Starting AI-based CSV fixing")

        # Load prompt template
        prompt = await self._build_prompt(md_content, csv_content, error_report)

        # Get provider and call AI
        from ..ai_md_to_csv_converter.providers.factory import ProviderFactory

        provider_config = {
            "name": self.provider_name,
            **context.config.pipeline.provider.settings.get(self.provider_name, {})
        }
        provider = ProviderFactory.create(self.provider_name, provider_config)

        # Build system prompt (simple instruction for fixing)
        system_prompt = """You are a CSV data correction specialist. Your only job is to fix STRUCTURAL errors in CSV files.

STRICTLY PROHIBITED:
- Do NOT change any question text, option text, or explanation text
- Do NOT "correct" answers or modify content
- Do NOT add or remove data

ALLOWED:
- Split merged data into correct columns
- Rearrange data that's in wrong columns
- Fix CSV formatting (quotes, commas, newlines)

Output ONLY the corrected CSV - no markdown, no intro, no summary."""

        try:
            self._log_debug("Sending prompt to AI for fixing")
            fixed_csv = await provider.convert(system_prompt, prompt)

            # Clean AI output (remove conversational text)
            fixed_csv = self._clean_ai_output(fixed_csv)

            # Validate CSV structure if enabled
            if self.validate_output:
                self._validate_csv_structure(fixed_csv)

            self._log_info("AI-based CSV fixing completed successfully")
            return fixed_csv

        except Exception as e:
            self._log_error(f"AI fixing failed: {e}")
            raise ConversionError(f"AI-based CSV fixing failed: {e}") from e

    async def _build_prompt(
        self,
        md_content: str,
        csv_content: str,
        error_report: Dict[str, Any]
    ) -> str:
        """Build the AI prompt with MD, CSV, and error report.

        Args:
            md_content: Original markdown content
            csv_content: Generated CSV with errors
            error_report: Verification error report

        Returns:
            Complete prompt string
        """
        # Load prompt template
        template_path = Path(__file__).parent / "templates" / "prompts" / "fix_prompt.txt"

        if not template_path.exists():
            # Fallback to built-in template
            template = self._get_fallback_template()
        else:
            template = template_path.read_text(encoding='utf-8')

        # Format error report for readability
        formatted_errors = self._format_error_report(error_report)

        # Build prompt
        prompt = template.format(
            error_report=formatted_errors,
            md_content=md_content[:50000],  # Limit MD content to avoid token overflow
            csv_content=csv_content
        )

        return prompt

    def _format_error_report(self, error_report: Dict[str, Any]) -> str:
        """Format error report for readability.

        Args:
            error_report: Raw error report

        Returns:
            Formatted error report string
        """
        formatted = []

        # Add summary
        total_errors = len(error_report.get("errors", []))
        formatted.append(f"Total Errors: {total_errors}")
        formatted.append("")

        # Add each error
        for i, error in enumerate(error_report.get("errors", []), 1):
            formatted.append(f"Error {i}:")
            formatted.append(f"  Row: {error.get('row', 'unknown')}")
            formatted.append(f"  Column: {error.get('column', 'unknown')}")
            formatted.append(f"  Message: {error.get('message', 'unknown error')}")
            formatted.append(f"  Reason: {error.get('reason', 'unknown')}")
            if 'value' in error:
                formatted.append(f"  Value: {error['value'][:100]}...")  # Truncate long values
            formatted.append("")

        return "\n".join(formatted)

    def _clean_ai_output(self, csv_output: str) -> str:
        """Clean up the AI-generated CSV output.

        Args:
            csv_output: Raw output from AI

        Returns:
            Cleaned CSV string
        """
        # Clean up any conversational prefix
        if "Question Type,Question" in csv_output:
            csv_start = csv_output.find("Question Type,Question")
            csv_output = csv_output[csv_start:]

        # Clean up markdown code blocks
        if "```csv" in csv_output:
            csv_output = csv_output.replace("```csv", "").replace("```", "")
        # Also remove any standalone ``` lines
        csv_output = re.sub(r'^```\s*$', '', csv_output, flags=re.MULTILINE)

        # Clean up conversational text at the end
        lines = csv_output.split('\n')
        csv_lines = []
        for line in lines:
            line = line.strip()
            # Keep header line and lines starting with "objective"
            if line.startswith("Question Type,") or line.startswith("objective,"):
                csv_lines.append(line)
            # Stop at first non-CSV line (conversational text)
            elif csv_lines and not (line.startswith("Question Type,") or line.startswith("objective,")):
                break

        return '\n'.join(csv_lines).strip()

    def _validate_csv_structure(self, csv_content: str) -> None:
        """Validate that the CSV has the correct structure.

        Args:
            csv_content: CSV content to validate

        Raises:
            ConversionError: If CSV structure is invalid
        """
        lines = csv_content.strip().split('\n')

        if len(lines) < 1:
            raise ConversionError("Fixed CSV is empty")

        # Check header
        expected_header = "Question Type,Question,Option count"
        if not lines[0].startswith(expected_header):
            self._log_warning(f"Fixed CSV header doesn't match expected format: {lines[0][:50]}...")

        # Check that we have data rows
        if len(lines) < 2:
            self._log_warning("Fixed CSV has no data rows")

    def _get_fallback_template(self) -> str:
        """Get fallback prompt template if file is missing.

        Returns:
            Fallback template string
        """
        return """You are a CSV data correction specialist. Fix validation errors by STRUCTURAL changes ONLY.

## CRITICAL CONSTRAINTS
ALLOWED: Split merged data, rearrange wrong columns, fix CSV formatting
PROHIBITED: Change actual content/text, "correct" answers, modify question data

## VERIFICATION ERRORS
{error_report}

## ORIGINAL MARKDOWN SOURCE
```markdown
{md_content}
```

## CURRENT CSV WITH ERRORS
```csv
{csv_content}
```

## OUTPUT
Output ONLY the corrected CSV starting with header. No markdown, no intro text.
"""
