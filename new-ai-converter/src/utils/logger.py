"""Logging configuration."""
import logging
import sys
from pathlib import Path
from typing import Optional
import json
from datetime import datetime


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data)


def setup_logging(
    level: str = "INFO",
    format_type: str = "detailed",
    console_output: bool = True,
    file_output: bool = False,
    log_dir: Optional[Path] = None
) -> None:
    """Configure logging for the application.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        format_type: Format type (simple, detailed, json)
        console_output: Whether to output to console
        file_output: Whether to output to file
        log_dir: Directory for log files
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper()))

    # Remove existing handlers
    root_logger.handlers.clear()

    # Console handler
    if console_output:
        console_handler = logging.StreamHandler(sys.stdout)

        if format_type == "json":
            console_handler.setFormatter(JSONFormatter())
        elif format_type == "simple":
            console_handler.setFormatter(logging.Formatter("%(message)s"))
        else:  # detailed
            console_handler.setFormatter(
                logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
            )

        root_logger.addHandler(console_handler)

    # File handler
    if file_output and log_dir:
        log_dir.mkdir(parents=True, exist_ok=True)

        log_file = log_dir / f"converter_{datetime.now().strftime('%Y%m%d')}.log"
        file_handler = logging.FileHandler(log_file)

        if format_type == "json":
            file_handler.setFormatter(JSONFormatter())
        else:
            file_handler.setFormatter(
                logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
            )

        root_logger.addHandler(file_handler)


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance.

    Args:
        name: Logger name

    Returns:
        Logger instance
    """
    return logging.getLogger(name)
