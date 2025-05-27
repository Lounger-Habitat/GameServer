"""
Rich Logger module for GameServer

This module provides enhanced logging capabilities using rich library and Python's logging module.
It allows for colorful, structured logging with different log levels, and can output to both
console and log files.
"""

import os
import sys
import logging
from logging import Formatter
from datetime import datetime
from pathlib import Path
from typing import Optional, Literal, Dict, Any, Union

from rich.console import Console
from rich.logging import RichHandler
from rich.theme import Theme

# Define custom theme for rich logging
RICH_THEME = Theme(
    {
        "info": "bold green",
        "warning": "bold yellow",
        "error": "bold red",
        "critical": "bold white on red",
        "debug": "bold blue",
    }
)

# Define log levels
LOG_LEVELS = {
    "debug": logging.DEBUG,
    "info": logging.INFO,
    "warning": logging.WARNING,
    "error": logging.ERROR,
    "critical": logging.CRITICAL,
}

# Define default log format
DEFAULT_FORMAT = "%(asctime)s | %(name)s | %(levelname)s | %(message)s"
RICH_FORMAT = "%(asctime)s (%(name)s) \n\n %(message)s \n"

# logging.basicConfig(
#     level="NOTSET",
#     format=DEFAULT_FORMAT,
#     datefmt="[%X]",
#     handlers=[RichHandler(rich_tracebacks=True, tracebacks_show_locals=True)],
# )


class GameLogger:
    """
    GameLogger class that provides enhanced logging functionality for the GameServer project.
    It uses rich for console output and can also write logs to files.
    """

    def __init__(
        self,
        name: str,
        level: Union[str, int] = "info",
        log_to_file: bool = False,
        log_dir: Optional[str] = None,
        format_string: str = DEFAULT_FORMAT,
    ):
        """
        Initialize a new GameLogger instance.

        Args:
            name: Name of the logger, typically the module name
            level: Log level (debug, info, warning, error, critical) or logging level constant
            log_to_file: Whether to write logs to a file
            log_dir: Directory to store log files, defaults to gameserver/storage/logs
            format_string: Format string for log messages
        """
        self.name = name
        self.console = Console(theme=RICH_THEME)

        # Setup log level
        if isinstance(level, str):
            self.level = LOG_LEVELS.get(level.lower(), logging.INFO)
        else:
            self.level = level

        # Create logger
        self.logger = logging.getLogger(name)
        self.logger.setLevel(self.level)

        # Clear handlers if any exist
        if self.logger.handlers:
            self.logger.handlers.clear()

        # Setup console handler with rich
        console_handler = RichHandler(
            console=self.console,
            rich_tracebacks=True,
            tracebacks_show_locals=True,
            show_time=False,
            show_path=False,
        )
        console_handler.setLevel(self.level)
        console_handler.setFormatter(Formatter(RICH_FORMAT))
        self.logger.addHandler(console_handler)

        # Setup file handler if requested
        if log_to_file:
            if not log_dir:
                # Default log directory
                base_dir = Path(__file__).parent.parent.parent
                log_dir = os.path.join(base_dir, "gameserver", "storage", "logs")

            # Create log directory if it doesn't exist
            os.makedirs(log_dir, exist_ok=True)

            # Generate log filename with date
            date_str = datetime.now().strftime("%Y%m%d")
            log_file = os.path.join(log_dir, f"{name}_{date_str}.log")

            file_handler = logging.FileHandler(log_file, encoding="utf-8")
            file_handler.setLevel(self.level)

            # Create formatter for file handler
            formatter = logging.Formatter(format_string)
            file_handler.setFormatter(formatter)

            self.logger.addHandler(file_handler)

    def debug(self, message: Any, **kwargs):
        """Log a debug message."""
        self.logger.debug(message, **kwargs)

    def info(self, message: Any, **kwargs):
        """Log an info message."""
        self.logger.info(message, **kwargs)

    def warning(self, message: Any, **kwargs):
        """Log a warning message."""
        self.logger.warning(message, **kwargs)

    def error(self, message: Any, **kwargs):
        """Log an error message."""
        self.logger.error(message, **kwargs)

    def critical(self, message: Any, **kwargs):
        """Log a critical message."""
        self.logger.critical(message, **kwargs)

    def exception(self, message: Any, **kwargs):
        """Log an exception message with traceback."""
        self.logger.exception(message, **kwargs)


# Create a function to get a pre-configured logger
def get_logger(
    name: str,
    level: Union[str, int] = "info",
    log_to_file: bool = False,
    log_dir: Optional[str] = None,
    format_string: str = DEFAULT_FORMAT,
) -> GameLogger:
    """
    Get a pre-configured GameLogger instance.

    Args:
        name: Name of the logger, typically the module name
        level: Log level (debug, info, warning, error, critical) or logging level constant
        log_to_file: Whether to write logs to a file
        log_dir: Directory to store log files, defaults to gameserver/storage/logs
        format_string: Format string for log messages

    Returns:
        An instance of GameLogger
    """
    return GameLogger(
        name=name,
        level=level,
        log_to_file=log_to_file,
        log_dir=log_dir,
        format_string=format_string,
    )
