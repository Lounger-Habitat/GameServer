from gameserver.utils.log.logger import get_logger

logger = get_logger(__name__)


def ws_env(original_function):
    def wrapper_function(*args, **kwargs):
        ws_type = kwargs.get("ws_type", None)
        if ws_type == "env":
            result = original_function(*args, **kwargs)
            return result
        else:
            logger.error(f"Invalid WebSocket type: {ws_type}. Expected 'env'.")

    return wrapper_function


def ws_agent(original_function):
    def wrapper_function(*args, **kwargs):
        ws_type = kwargs.get("ws_type", None)
        if ws_type == "agent":
            result = original_function(*args, **kwargs)
            return result
        else:
            logger.error(f"Invalid WebSocket type: {ws_type}. Expected 'agent'.")

    return wrapper_function


def ws_human(original_function):
    def wrapper_function(*args, **kwargs):
        ws_type = kwargs.get("ws_type", None)
        if ws_type == "human":
            result = original_function(*args, **kwargs)
            return result
        else:
            logger.error(f"Invalid WebSocket type: {ws_type}. Expected 'human'.")

    return wrapper_function
