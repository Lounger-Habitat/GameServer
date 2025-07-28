"""
Example demonstrating the usage of GameServer Rich Logger
"""

import sys
import os
from pathlib import Path

# Add the project root to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from gameserver.utils.log import get_logger


def main():
    # Create loggers with different configurations
    default_logger = get_logger("example.default")
    debug_logger = get_logger("example.debug", level="debug")
    console_only_logger = get_logger("example.console", log_to_file=False)

    # Demonstrate different log levels
    default_logger.info("This is an INFO message")
    default_logger.warning("This is a WARNING message")
    default_logger.error("This is an ERROR message")

    # Debug messages only show up if level is set to debug
    debug_logger.debug("This DEBUG message will be visible")
    default_logger.debug("This DEBUG message won't be visible with default settings")

    # Demonstrate logging exceptions
    try:
        # Intentionally cause an error
        result = 1 / 0
    except Exception as e:
        default_logger.exception(f"Caught an exception: {str(e)}")

    # Demonstrate logging with context data
    user_data = {"id": 12345, "username": "player1", "level": 42}
    default_logger.info(f"User logged in: {user_data}")

    # Console-only logger doesn't write to file
    console_only_logger.info("This message only appears in console, not in log file")


if __name__ == "__main__":
    main()
