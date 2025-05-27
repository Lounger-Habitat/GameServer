"""Agent related API endpoints."""

import yaml
import os
import sys
import time
import json
import traceback
import asyncio
from typing import List
from enum import Enum
from datetime import datetime

# Rich logging imports
import logging
from logging.handlers import RotatingFileHandler
from rich.logging import RichHandler
from rich.console import Console
from rich.panel import Panel
from rich.traceback import install as install_rich_traceback
from rich import print as rprint

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse

from pydantic import BaseModel, Field

from gameserver.models.user import User
from gameserver.utils.auth.api_auth import get_current_active_user

from mlong import Model
from mlong import user, system
from mlong import RoleAgent
from mlong import GTGConversation

# from mlong import VectorStore

# Setup rich traceback display
install_rich_traceback(show_locals=True)
console = Console()

# Create logs directory if it doesn't exist
STORAGE_BASE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "storage"
)
LOGS_DIR = os.path.join(STORAGE_BASE_PATH, "logs")
os.makedirs(LOGS_DIR, exist_ok=True)

# Configure logging with both console and file handlers
log_file = os.path.join(LOGS_DIR, f"agent_api_{datetime.now().strftime('%Y%m%d')}.log")

# Create file handler with rotation (10MB max size, keep 5 backup files)
file_handler = RotatingFileHandler(
    log_file, maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8"
)
file_handler.setFormatter(
    logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
)

# Configure rich logger
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(rich_tracebacks=True, console=console), file_handler],
)

# Get a logger instance for this module
logger = logging.getLogger("agent_api")
logger.info(f"Logging to file: {log_file}")

DEFAULT_MEMORY_SPACE = os.path.join(STORAGE_BASE_PATH, "memory")
DEFAULT_ROLE_PATH = os.path.join(STORAGE_BASE_PATH, "configs", "roles")
DEFAULT_TOPIC_PROMPT = os.path.join(
    STORAGE_BASE_PATH, "configs", "topics", "topic_v3.yaml"
)

logger.info(f"Storage path: {STORAGE_BASE_PATH}")
logger.info(f"Memory space: {DEFAULT_MEMORY_SPACE}")
logger.info(f"Role path: {DEFAULT_ROLE_PATH}")

router = APIRouter()


def log_response(
    user: str, endpoint: str, req_data: dict, response_data, elapsed: float
):
    """Log response to both console and file"""
    # Truncate long responses for console display
    if isinstance(response_data, str) and len(response_data) > 500:
        console_response = response_data[:500] + "... [truncated]"
    elif isinstance(response_data, dict) and "response" in response_data:
        if (
            isinstance(response_data["response"], str)
            and len(response_data["response"]) > 500
        ):
            console_response = {
                **response_data,
                "response": response_data["response"][:500] + "... [truncated]",
            }
        else:
            console_response = response_data
    else:
        console_response = response_data

    # Log to console with rich formatting
    console.print(
        Panel(
            f"[bold green]Response[/bold green] ({elapsed:.2f}s)\n"
            + f"[yellow]User:[/yellow] {user}\n"
            + f"[yellow]Endpoint:[/yellow] {endpoint}\n"
            + f"[yellow]Response:[/yellow]\n{console_response}",
            title="API Response",
            border_style="blue",
        )
    )

    # Log complete response to file
    logger.info(
        f"RESPONSE - User: {user}, Endpoint: {endpoint}, "
        f"Elapsed: {elapsed:.2f}s, Request: {json.dumps(req_data)}, "
        f"Response: {response_data}"
    )


# 定义模型ID枚举类型
class ModelID(str, Enum):
    CLAUDE_3_7_SONNET = "Claude-3.7-Sonnet"
    DEEPSEEK_R1_V1 = "us.deepseek.r1-v1:0"
    DEEPSEEK_REASONER = "deepseek-reasoner"
    DEEPSEEK_CHAT = "deepseek-chat"
    GPT_4O = "gpt-4o"
    CLAUDE_3_5_SONNET = "claude-3-5-sonnet-20241022"
    AMAZON_NOVA_PRO = "us.amazon.nova-pro-v1:0"
    ANTHROPIC_CLAUDE_3_5 = "us.anthropic.claude-3-5-sonnet-20241022-v2:0"
    ANTHROPIC_CLAUDE_3_7 = "us.anthropic.claude-3-7-sonnet-20250219-v1:0"
    COHERE_EMBED = "cohere.embed-multilingual-v3"


# 定义请求和响应模型
class Message(BaseModel):
    role: str
    content: str


class TestMessage(BaseModel):
    message: Message
    model_id: ModelID = ModelID.ANTHROPIC_CLAUDE_3_7
    stream: bool = False


class ChatParam(BaseModel):
    messages: List[Message]
    model_id: ModelID = ModelID.ANTHROPIC_CLAUDE_3_7
    temperature: float = 0
    max_tokens: int = 8192
    stream: bool = False


class RoleParam(BaseModel):
    role_name: str
    message: str
    model_id: ModelID = ModelID.ANTHROPIC_CLAUDE_3_7
    stream: bool = False


class ConversationParam(BaseModel):
    active_role: str
    passive_role: str
    topic: str
    model_id: ModelID = ModelID.ANTHROPIC_CLAUDE_3_7


@router.get("/model_list")
async def get_model_list(current_user=Depends(get_current_active_user)):
    """获取可用的模型列表"""
    logger.info(f"Model list request received from {current_user.username}")
    try:
        # 模拟从模型管理器获取模型列表
        model_list = [model_id for model_id in ModelID]
        logger.info("Model list retrieved successfully")
        return {"models": model_list}
    except Exception as e:
        logger.error(f"Error retrieving model list: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/test")
async def test(message: TestMessage, current_user=Depends(get_current_active_user)):
    logger.info(f"Test request received from user: {current_user.username}")
    logger.info(f"Using model: {message.model_id}")

    start_time = time.time()
    model = Model()
    try:
        res = model.chat(
            messages=[message.message.model_dump()],
            model_id=message.model_id,
        )
        elapsed = time.time() - start_time

        # Log response
        response_data = {"response": res}
        log_response(
            current_user.username,
            "test",
            {"message": message.message.model_dump(), "model_id": message.model_id},
            response_data,
            elapsed,
        )

        return response_data
    except Exception as e:
        logger.error(f"Error in test endpoint: {str(e)}")
        logger.debug(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


# 角色扮演聊天接口
@router.post("/chat")
async def agent_chat(param: RoleParam, current_user=Depends(get_current_active_user)):
    logger.info(f"Chat request received from {current_user.username}")
    logger.info(
        f"Role: {param.role_name}, Model: {param.model_id}, Stream: {param.stream}"
    )

    role_file_path = os.path.join(DEFAULT_ROLE_PATH, param.role_name + ".yaml")
    logger.debug(f"Loading role from {role_file_path}")

    try:
        with open(role_file_path, "r") as f:
            role_config = yaml.safe_load(f)
        logger.debug(f"Role config loaded successfully")

        start_time = time.time()
        logger.info(f"Initializing RoleAgent for {param.role_name}")
        agent = RoleAgent(dict(role_config), model_id=param.model_id)

        if param.stream:
            logger.info("Starting streaming response")
            response = agent.chat_stream(param.message)

            async def stream_generator():
                chunks_count = 0
                full_response = ""
                for chunk in response:
                    chunks_count += 1
                    chunk_text = str(chunk.text if hasattr(chunk, "text") else chunk)
                    full_response += chunk_text

                    if chunks_count % 10 == 0:
                        logger.debug(f"Streamed {chunks_count} chunks so far")
                    chunk_dict = (
                        chunk.dict() if hasattr(chunk, "dict") else {"text": chunk_text}
                    )
                    yield f"data: {json.dumps(chunk_dict)}\n\n"

                elapsed = time.time() - start_time
                logger.info(
                    f"Stream completed: {chunks_count} chunks in {elapsed:.2f}s"
                )

                # Log the full response at the end of streaming
                log_response(
                    current_user.username,
                    "chat (stream)",
                    {
                        "role": param.role_name,
                        "message": param.message,
                        "model_id": param.model_id,
                    },
                    {"response": full_response},
                    elapsed,
                )

            return StreamingResponse(stream_generator(), media_type="text/event-stream")
        else:
            logger.info("Processing non-streaming chat request")
            res = agent.chat(param.message, stream=param.stream)
            elapsed = time.time() - start_time

            # Log response
            response_data = {"response": res}
            log_response(
                current_user.username,
                "chat",
                {
                    "role": param.role_name,
                    "message": param.message,
                    "model_id": param.model_id,
                },
                response_data,
                elapsed,
            )

            return response_data
    except FileNotFoundError as e:
        logger.error(f"Role file not found: {role_file_path}")
        raise HTTPException(
            status_code=404, detail=f"Role '{param.role_name}' not found"
        )
    except Exception as e:
        logger.error(f"Error in chat endpoint: {str(e)}")
        logger.debug(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


# 角色对话接口
@router.post("/ata")
async def agent_to_agent_chat(
    param: ConversationParam, current_user=Depends(get_current_active_user)
):
    logger.info(f"Agent-to-agent chat request from {current_user.username}")
    logger.info(f"Active role: {param.active_role}, Passive role: {param.passive_role}")
    logger.info(f"Memory space: {DEFAULT_MEMORY_SPACE}, Model: {param.model_id}")

    role_dict = {}
    # 扫描 configs/roles 目录获取所有配置文件
    logger.debug("Loading role configurations")
    for file_name in os.listdir(DEFAULT_ROLE_PATH):
        if not file_name.endswith(".yaml"):
            continue

        file_path = os.path.join(DEFAULT_ROLE_PATH, file_name)
        with open(file_path, "r", encoding="utf-8") as f:
            role_name = file_name.split(".")[0]
            role_dict[role_name] = yaml.safe_load(f)
            logger.debug(f"Loaded role: {role_name}")

    if param.topic is None or param.topic == "":
        logger.info("No topic provided, using default topic")
        with open(DEFAULT_TOPIC_PROMPT, "r", encoding="utf-8") as f:
            topic_dict = yaml.safe_load(f)
            topic = topic_dict["topic"]
    else:
        topic = param.topic
        logger.info(f"Using provided topic: {topic[:50]}...")

    try:
        start_time = time.time()
        logger.info("Initializing GTG conversation")
        ata = GTGConversation(
            active_role=dict(role_dict[param.active_role]),
            passive_role=dict(role_dict[param.passive_role]),
            topic=topic,
            memory_space=DEFAULT_MEMORY_SPACE,
            model_id=param.model_id,
        )
        logger.info("GTG conversation initialized successfully")

        async def stream_generator():
            chunks_count = 0
            events_count = 0
            full_conversation = []

            for chunk in ata.chat_stream():
                if "event" in chunk:
                    events_count += 1
                    logger.debug(f"Event received: {chunk}")
                    full_conversation.append(chunk)
                    yield f"event: {chunk}\n\n"

                # Safely process data chunks
                if "data" in chunk:
                    chunks_count += 1
                    if chunks_count % 20 == 0:
                        logger.debug(f"Streamed {chunks_count} data chunks so far")
                        # Use safe serialization to avoid circular references

                    logger.debug(f"Data received: {chunk}")
                    full_conversation.append(chunk)
                    yield f"data: {chunk}\n\n"
                await asyncio.sleep(0)

            elapsed = time.time() - start_time
            logger.info(
                f"ATA stream completed: {chunks_count} chunks, {events_count} events in {elapsed:.2f}s"
            )

            # Log the complete conversation at the end
            log_response(
                current_user.username,
                "ata",
                {
                    "active_role": param.active_role,
                    "passive_role": param.passive_role,
                    "topic": topic[:100] + "..." if len(topic) > 100 else topic,
                },
                {"conversation": full_conversation},
                elapsed,
            )

        logger.info("Starting streaming response for ATA conversation")
        return StreamingResponse(stream_generator(), media_type="text/event-stream")
    except KeyError as e:
        logger.error(f"Role not found: {str(e)}")
        raise HTTPException(status_code=404, detail=f"Role '{str(e)}' not found")
    except Exception as e:
        logger.error(f"Error in agent_to_agent chat: {str(e)}")
        logger.debug(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


# 角色对话接口
@router.get("/reset_memory")
async def reset_memory(current_user=Depends(get_current_active_user)):
    logger.info(f"Reset memory request from {current_user.username}")
    logger.info(f"Memory space: {DEFAULT_MEMORY_SPACE}")
    logger.info(f"Clearing memory space: {DEFAULT_MEMORY_SPACE}")
    try:
        for root, dirs, files in os.walk(DEFAULT_MEMORY_SPACE):
            for file in files:
                file_path = os.path.join(root, file)
                os.remove(file_path)
                logger.debug(f"Deleted file: {file_path}")
        logger.info("Memory reset successfully")
        return {"message": "Memory reset successfully"}
    except FileNotFoundError as e:
        logger.error(f"File not found during memory reset: {str(e)}")
        raise HTTPException(status_code=404, detail=str(e))
    except PermissionError as e:
        logger.error(f"Permission denied during memory reset: {str(e)}")
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        logger.error(f"Error resetting memory: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
