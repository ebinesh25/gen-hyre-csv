"""OpenAI AI provider for MD to CSV conversion."""
import os
import re
from typing import Optional

from openai import AsyncOpenAI

from .base import BaseProvider
from ..core.exceptions import ProviderError, RateLimitError
from ..utils.logger import get_logger


class OpenAIProvider(BaseProvider):
    """OpenAI API provider for AI conversion."""

    def __init__(self, config: dict):
        """Initialize OpenAI provider.

        Args:
            config: Provider configuration with keys:
                - api_key: OpenAI API key (or uses OPENAI_HYRE_API_KEY env var)
                - model: Model name (default: gpt-4o)
                - temperature: Temperature setting (default: 0)
                - max_tokens: Max tokens (default: 16000)
        """
        super().__init__(config)
        self.logger = get_logger(__name__)

        # Check for OPENAI_HYRE_API_KEY first, then OPENAI_API_KEY, then config
        api_key = (
            config.get("api_key") or
            os.getenv("OPENAI_HYRE_API_KEY") or
            os.getenv("OPENAI_API_KEY")
        )
        if not api_key:
            raise ProviderError(
                "OpenAI API key not provided. Set OPENAI_HYRE_API_KEY or OPENAI_API_KEY, "
                "or provide in config."
            )

        self.client = AsyncOpenAI(api_key=api_key)
        self.model = config.get("model", "gpt-4o")
        self.temperature = config.get("temperature", 0)
        self.max_tokens = config.get("max_tokens", 16000)

    @property
    def supports_async(self) -> bool:
        """OpenAI SDK has async support."""
        return True

    async def convert(self, system_prompt: str, user_prompt: str) -> str:
        """Convert markdown to CSV using OpenAI API.

        Args:
            system_prompt: The system prompt for the AI
            user_prompt: The user prompt containing markdown content

        Returns:
            CSV output as a string

        Raises:
            ProviderError: If conversion fails
            RateLimitError: If rate limit is hit (with retry info)
        """
        retry_count = 0
        max_retries = self.config.get("max_retries", 5)

        while retry_count < max_retries:
            try:
                self.logger.debug(f"Calling OpenAI API (attempt {retry_count + 1})")

                response = await self.client.chat.completions.create(
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    model=self.model,
                    temperature=self.temperature,
                    max_tokens=self.max_tokens,
                )

                csv_output = response.choices[0].message.content

                # Clean up the output
                csv_output = self._clean_output(csv_output)

                self.logger.info(f"OpenAI conversion successful")
                return csv_output

            except Exception as e:
                error_str = str(e)

                # Check if it's a rate limit error
                if "rate_limit" in error_str.lower() or "429" in error_str:
                    retry_after = self._extract_retry_after(error_str)
                    retry_count += 1

                    if retry_count >= max_retries:
                        raise RateLimitError(
                            f"OpenAI rate limit: Max retries ({max_retries}) reached",
                            retry_after=retry_after
                        )

                    # Format wait time for logging
                    wait_str = self._format_wait_time(retry_after)
                    self.logger.warning(
                        f"Rate limit hit. Waiting {wait_str} before retry "
                        f"{retry_count}/{max_retries}"
                    )

                    # Wait before retry
                    import asyncio
                    await asyncio.sleep(retry_after)
                else:
                    # Non-rate-limit error
                    raise ProviderError(f"OpenAI API error: {error_str}") from e

        raise ProviderError("Max retries reached")

    def _clean_output(self, csv_output: str) -> str:
        """Clean up the AI-generated CSV output.

        Args:
            csv_output: Raw output from OpenAI

        Returns:
            Cleaned CSV string
        """
        # Clean up any conversational prefix
        if "Question Type,Question" in csv_output:
            csv_start = csv_output.find("Question Type,Question")
            csv_output = csv_output[csv_start:]

        # Clean up markdown code blocks - handle both ```csv and standalone ```
        if "```csv" in csv_output:
            csv_output = csv_output.replace("```csv", "").replace("```", "")
        # Also remove any standalone ``` lines (for cases where AI didn't use ```csv)
        csv_output = re.sub(r'^```\s*$', '', csv_output, flags=re.MULTILINE)

        # Clean up conversational text at the end (AI summaries like "I've processed all...")
        # Split by lines and only keep valid CSV lines (start with "objective" or header)
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

    def _extract_retry_after(self, error_msg: str) -> int:
        """Extract retry time in seconds from rate limit error message.

        Args:
            error_msg: Error message from OpenAI API

        Returns:
            Retry time in seconds
        """
        # OpenAI typically returns retry_after in the error response
        # Look for patterns like "retry after" or numeric seconds
        match = re.search(r'retry[_\s]after[:\s]+(\d+)', error_msg.lower())
        if match:
            return int(match.group(1))

        # Default retry delay for OpenAI rate limits
        return self.config.get("base_retry_delay", 60)

    def _format_wait_time(self, seconds: int) -> str:
        """Format wait time in human-readable format.

        Args:
            seconds: Wait time in seconds

        Returns:
            Formatted string (e.g., "2h 30m 15s")
        """
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60

        parts = []
        if hours > 0:
            parts.append(f"{hours}h")
        if minutes > 0:
            parts.append(f"{minutes}m")
        parts.append(f"{secs}s")

        return " ".join(parts)

    def estimate_cost(self, input_tokens: int, output_tokens: int) -> Optional[float]:
        """Estimate cost for a conversion.

        OpenAI pricing (as of 2025):
        - GPT-4o: $2.50/1M input, $10.00/1M output

        Args:
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens

        Returns:
            Estimated cost in USD
        """
        # Pricing for gpt-4o
        input_cost_per_million = 2.50
        output_cost_per_million = 10.00

        input_cost = (input_tokens / 1_000_000) * input_cost_per_million
        output_cost = (output_tokens / 1_000_000) * output_cost_per_million

        return input_cost + output_cost
