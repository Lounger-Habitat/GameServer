# GameServer Rich Logger

A powerful and flexible logging utility for the GameServer project, combining Python's built-in `logging` module with the `rich` library for enhanced terminal output.

## Design Document

### Overview

The GameServer Rich Logger is designed to provide consistent, colorful, and structured logging across the entire GameServer project. It supports both console and file-based logging, with the ability to customize log formats, log levels, and output destinations.

### Key Features

- **Rich Console Output**: Colorful, well-formatted console logs with syntax highlighting
- **File Logging**: Automatically dated log files organized by component
- **Flexible Log Levels**: Standard levels (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- **Error Tracebacks**: Enhanced tracebacks with local variable inspection for easier debugging
- **Consistent Format**: Standardized log format across all components

### Architecture

The logging utility consists of:

1. **`GameLogger` Class**: The main class that encapsulates logging functionality
2. **`get_logger` Function**: A factory function to easily create pre-configured loggers
3. **Configuration System**: Flexible initialization parameters for customization

### Log File Organization

- All log files are stored in the `gameserver/storage/logs` directory by default
- Log files are named with the pattern `{component_name}_{YYYYMMDD}.log`
- Each component gets its own log file to make debugging easier

### Log Format

The default log format is:
```
{timestamp} | {logger_name} | {level} | {message}
```

## Usage Guide

### Basic Usage

```python
from gameserver.utils.logger import get_logger

# Create a logger with default settings
logger = get_logger("my_module")

# Log messages with different levels
logger.info("Server started successfully")
logger.debug("Connection details: {}", connection_data)
logger.warning("Low memory detected")
logger.error("Failed to process request: {}", error_message)
logger.critical("Database connection lost")

# Log exceptions with traceback
try:
    result = complex_operation()
except Exception as e:
    logger.exception("Operation failed")
```

### Customizing Logger

```python
from gameserver.utils.logger import get_logger

# Set custom log level
debug_logger = get_logger("debug_module", level="debug")

# Disable file logging (console only)
console_logger = get_logger("console_only", log_to_file=False)

# Specify custom log directory
custom_logger = get_logger(
    "custom_module", 
    log_dir="/path/to/custom/logs"
)

# Custom format string
formatted_logger = get_logger(
    "formatted", 
    format_string="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
```

### Integration Examples

#### API Endpoint Logging

```python
from fastapi import APIRouter
from gameserver.utils.logger import get_logger

router = APIRouter()
logger = get_logger("api.games")

@router.get("/games")
async def get_games():
    logger.info("Retrieving games list")
    try:
        # Get games logic
        games = await database.get_games()
        logger.debug(f"Retrieved {len(games)} games")
        return games
    except Exception as e:
        logger.error(f"Failed to retrieve games: {str(e)}")
        logger.exception("Exception details")
        raise
```

#### WebSocket Connection Logging

```python
from gameserver.utils.logger import get_logger

logger = get_logger("ws.game_events")

async def handle_connection(websocket):
    client_id = generate_client_id()
    logger.info(f"New client connected: {client_id}")
    
    try:
        while True:
            data = await websocket.receive_text()
            logger.debug(f"Received from {client_id}: {data}")
            # Process data
    except WebSocketDisconnect:
        logger.info(f"Client disconnected: {client_id}")
    except Exception as e:
        logger.error(f"Error handling client {client_id}")
        logger.exception("Connection handler exception")
```

## Best Practices

1. **Create a logger per module**: Each Python module should have its own logger
2. **Choose appropriate log levels**:
   - DEBUG: Detailed information for debugging
   - INFO: Confirmation that things are working as expected
   - WARNING: Indication that something unexpected happened, but the application can continue
   - ERROR: Due to a more serious problem, the software couldn't perform a function
   - CRITICAL: A serious error indicating the program may be unable to continue running
3. **Include context in log messages**: Add relevant data to help with debugging
4. **Use structured data**: For complex data, use structured formats that can be easily parsed
5. **Don't log sensitive information**: Avoid logging passwords, tokens, or personal data

## Implementation Details

The logging utility is implemented in `gameserver/utils/logger.py`, which provides:

- A `GameLogger` class that wraps Python's logging module
- The `get_logger()` factory function for easy initialization
- Default configurations suitable for most use cases
- Customization options for special use cases

## Dependencies

- Python 3.10+
- rich >= 13.0.0
