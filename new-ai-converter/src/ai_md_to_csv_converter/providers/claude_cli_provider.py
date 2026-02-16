"""Claude CLI provider for MD to CSV conversion."""
import os
import re
import subprocess
from typing import Optional
from concurrent.futures import ThreadPoolExecutor

from .base import BaseProvider
from ..core.exceptions import ProviderError, RateLimitError
from ..utils.logger import get_logger


class ClaudeCliProvider(BaseProvider):
    """Claude CLI provider for AI conversion (uses claude command)."""

    def __init__(self, config: dict):
        """Initialize Claude CLI provider.

        Args:
            config: Provider configuration with keys:
                - timeout: Timeout in seconds (default: 300)
                - max_retries: Maximum retry attempts (default: 5)
        """
        super().__init__(config)
        self.logger = get_logger(__name__)

        # Check if claude CLI is available
        try:
            result = subprocess.run(
                ["claude", "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode != 0:
                raise ProviderError("Claude CLI not found. Install with: npm install -g @anthropic-ai/claude-cli")
            self.logger.info(f"Claude CLI version: {result.stdout.strip()}")
        except FileNotFoundError:
            raise ProviderError("Claude CLI not found. Install with: npm install -g @anthropic-ai/claude-cli")
        except subprocess.TimeoutExpired:
            raise ProviderError("Claude CLI timeout during version check")

        self.timeout = config.get("timeout", 300)
        self.max_retries = config.get("max_retries", 5)

    @property
    def supports_async(self) -> bool:
        """Claude CLI is synchronous, uses thread pool wrapper."""
        return False

    async def convert(self, system_prompt: str, user_prompt: str) -> str:
        """Convert markdown to CSV using Claude CLI.

        Args:
            system_prompt: The system prompt for the AI
            user_prompt: The user prompt containing markdown content

        Returns:
            CSV output as a string

        Raises:
            ProviderError: If conversion fails
            RateLimitError: If rate limit is hit (with retry info)
        """
        # Combine system and user prompt for CLI
        combined_prompt = f"{system_prompt}\n\n{user_prompt}"

        retry_count = 0

        while retry_count < self.max_retries:
            try:
                self.logger.debug(f"Calling Claude CLI (attempt {retry_count + 1})")

                # Run in thread pool since this is blocking
                loop = __import__('asyncio').get_event_loop()
                csv_output = await loop.run_in_executor(
                    None,
                    self._run_claude_cli,
                    combined_prompt
                )

                # Clean up the output
                csv_output = self._clean_output(csv_output)

                self.logger.info("Claude CLI conversion successful")
                return csv_output

            except subprocess.TimeoutExpired as e:
                retry_count += 1
                if retry_count >= self.max_retries:
                    raise ProviderError(f"Claude CLI: Max retries ({self.max_retries}) reached due to timeout") from e
                self.logger.warning(f"Timeout. Retrying {retry_count}/{self.max_retries}...")
                import asyncio
                await asyncio.sleep(10)

            except Exception as e:
                error_str = str(e)

                # Check if it's a rate limit error
                if "rate limit" in error_str.lower() or "429" in error_str:
                    retry_after = self._extract_retry_after(error_str)
                    retry_count += 1

                    if retry_count >= self.max_retries:
                        raise RateLimitError(
                            f"Rate limit: Max retries ({self.max_retries}) reached",
                            retry_after=retry_after
                        )

                    wait_str = self._format_wait_time(retry_after)
                    self.logger.warning(f"Rate limit hit. Waiting {wait_str} before retry {retry_count}/{self.max_retries}")

                    import asyncio
                    await asyncio.sleep(retry_after)
                else:
                    raise ProviderError(f"Claude CLI error: {error_str}") from e

        raise ProviderError("Max retries reached")

    def _run_claude_cli(self, prompt: str) -> str:
        """Run Claude CLI synchronously.

        Args:
            prompt: Combined system and user prompt

        Returns:
            Raw output from Claude CLI

        Raises:
            subprocess.TimeoutExpired: If timeout is exceeded
            ProviderError: If CLI returns non-zero exit code
        """
        result = subprocess.run(
            ["claude", "--print", "--tools", "", "--no-session-persistence"],
            input=prompt,
            capture_output=True,
            text=True,
            timeout=self.timeout,
        )

        if result.returncode != 0:
            error_msg = result.stderr or result.stdout
            raise ProviderError(f"Claude CLI error: {error_msg}")

        return result.stdout.strip()

    def _clean_output(self, csv_output: str) -> str:
        """Clean up the AI-generated CSV output.

        Args:
            csv_output: Raw output from Claude CLI

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
            error_msg: Error message from Claude CLI

        Returns:
            Retry time in seconds
        """
        # Look for patterns like "Please try again in 2h23m30.624s"
        match = re.search(r'Please try again in ([\dhms\.]+)', error_msg)
        if match:
            time_str = match.group(1)
            total_seconds = 0

            # Parse hours, minutes, seconds
            h_match = re.search(r'(\d+)h', time_str)
            m_match = re.search(r'(\d+)m', time_str)
            s_match = re.search(r'([\d\.]+)s', time_str)

            if h_match:
                total_seconds += int(h_match.group(1)) * 3600
            if m_match:
                total_seconds += int(m_match.group(1)) * 60
            if s_match:
                total_seconds += float(s_match.group(1))

            # Add 10% buffer and round up
            return int(total_seconds * 1.1) + 10

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
        """Claude CLI has no direct API cost.

        Args:
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens

        Returns:
            None (no direct cost for CLI)
        """
        return None
