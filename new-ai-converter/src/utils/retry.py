"""Retry handler with exponential backoff."""
import asyncio
import random
from typing import Callable, TypeVar, Optional

from ..core.exceptions import RetryableError
from .logger import get_logger

T = TypeVar('T')


class RetryHandler:
    """Handler for retrying operations with backoff."""

    def __init__(self, config: dict):
        """Initialize retry handler from configuration.

        Args:
            config: Retry configuration dictionary with keys:
                - max_retries: Maximum number of retries
                - base_delay: Base delay in seconds
                - exponential_backoff: Whether to use exponential backoff
                - jitter: Whether to add jitter
                - jitter_range: Jitter range (0-1)
        """
        self.max_retries = config.get("max_retries", 5)
        self.base_delay = config.get("base_delay", 60)
        self.exponential_backoff = config.get("exponential_backoff", True)
        self.jitter = config.get("jitter", True)
        self.jitter_range = config.get("jitter_range", 0.1)
        self.logger = get_logger(__name__)

    async def execute(self, func: Callable[[], T]) -> T:
        """Execute function with retry logic.

        Args:
            func: Function to execute (can be async or sync)

        Returns:
            Result of the function

        Raises:
            Exception: If all retries are exhausted
        """
        last_error = None

        for attempt in range(self.max_retries + 1):
            try:
                if attempt > 0:
                    delay = self._calculate_delay(attempt)
                    self.logger.info(f"Retry attempt {attempt}/{self.max_retries} after {delay:.1f}s")
                    await asyncio.sleep(delay)

                result = await func() if asyncio.iscoroutinefunction(func) else func()

                if attempt > 0:
                    self.logger.info(f"Success after {attempt} retries")

                return result

            except RetryableError as e:
                last_error = e
                if hasattr(e, 'retry_after') and e.retry_after:
                    # Use explicit retry time from error
                    await asyncio.sleep(e.retry_after)
                elif attempt < self.max_retries:
                    continue
                else:
                    raise
            except Exception as e:
                # Non-retryable error
                if attempt == self.max_retries:
                    raise
                last_error = e
                self.logger.warning(f"Non-retryable error on attempt {attempt+1}: {e}")
                raise

        raise last_error or RuntimeError("Max retries exceeded")

    def _calculate_delay(self, attempt: int) -> float:
        """Calculate delay with exponential backoff and jitter.

        Args:
            attempt: Attempt number (1-based)

        Returns:
            Delay in seconds
        """
        base_delay = self.base_delay

        if self.exponential_backoff:
            base_delay *= (2 ** (attempt - 1))

        if self.jitter:
            jitter_range = base_delay * self.jitter_range
            base_delay += random.uniform(-jitter_range, jitter_range)

        return max(0, base_delay)
