"""Agent related API endpoints."""

import yaml
import os
import sys

from typing import List
from enum import Enum

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse

from pydantic import BaseModel, Field

from gameserver.models.user import User
from gameserver.utils.auth import get_current_active_user

from mlong import Model
from mlong import user, system
from mlong import RoleAgent
from mlong import GTGConversation
# from mlong import VectorStore


STORAGE_BASE_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "storage")
DEFAULT_MEMORY_SPACE = os.path.join(STORAGE_BASE_PATH, "memory")
DEFAULT_ROLE_PATH = os.path.join(STORAGE_BASE_PATH, "configs", "roles")
DEFAULT_TOPIC_PROMPT = os.path.join(STORAGE_BASE_PATH, "configs", "topics", "ds_chat_v3.yaml")

router = APIRouter()


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
    model_id: ModelID = ModelID.DEEPSEEK_REASONER
    temperature: float = 0
    max_tokens: int = 8192
    stream: bool = False


class RoleParam(BaseModel):
    role_name: str
    message: str
    model_id: ModelID = ModelID.DEEPSEEK_REASONER
    stream: bool = False


class ConversationParam(BaseModel):
    active_role: str
    passive_role: str
    topic: str
    memory_space: str = "memory"
    model_id: ModelID = ModelID.DEEPSEEK_REASONER

@router.post("/test")
async def test(message:TestMessage, current_user = Depends(get_current_active_user)):
    model = Model()
    res = model.chat(
        messages=[message.message.model_dump()],
        model_id=message.model_id,
    )
    return {"response": res}

# 角色扮演聊天接口
@router.post("/chat")
async def agent_chat(param: RoleParam, current_user = Depends(get_current_active_user)):
    # 不再检查权限
    role_file_path = os.path.join(DEFAULT_ROLE_PATH, param.role_name + ".yaml")
    with open(role_file_path, "r") as f:
        role_config = yaml.safe_load(f)
    try:
        agent = RoleAgent(dict(role_config), model_id=param.model_id)
        if param.stream:
            # 流式响应需要在前端处理
            response = agent.chat_stream(param.message)

            # 创建一个生成器函数来处理流式响应
            async def stream_generator():
                # 对流式响应进行处理
                for chunk in response:
                    # 如果是 ChatStreamResponse 对象，需要将其转换为字典
                    chunk_dict = (
                        chunk.dict() if hasattr(chunk, "dict") else {"text": str(chunk)}
                    )
                    yield f"data: {chunk_dict}\n\n"

            return StreamingResponse(stream_generator(), media_type="text/event-stream")
        else:
            # 非流式响应
            res = agent.chat(param.message, stream=param.stream)
            return {"response": res}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# 角色对话接口
@router.post("/ata")
async def agent_to_agent_chat(param: ConversationParam, current_user = Depends(get_current_active_user)):
    # 不再检查权限
    role_dict = {}
    # 扫描 configs/roles 目录获取所有配置文件
    for file_name in os.listdir(DEFAULT_ROLE_PATH):
        file_path = os.path.join(DEFAULT_ROLE_PATH, file_name)
        with open(file_path, "r", encoding="utf-8") as f:
            role_dict[file_name.split(".")[0]] = yaml.safe_load(f)

    if param.topic is None or param.topic == "":
        with open(DEFAULT_TOPIC_PROMPT, "r", encoding="utf-8") as f:
            topic_dict = yaml.safe_load(f)
            topic = topic_dict["topic"]
    else:
        topic = param.topic

        # try:
    ata = GTGConversation(
        active_role=dict(role_dict[param.active_role]),
        passive_role=dict(role_dict[param.passive_role]),
        topic=topic,
        memory_space=os.path.join(DEFAULT_MEMORY_SPACE, param.memory_space),
        model_id=param.model_id,
    )

    async def stream_generator():
        for chunk in ata.chat_stream():
            if "event" in chunk:
                yield f"event: {chunk}\n\n"
            if "data" in chunk:
                yield f"data: {chunk}\n\n"

    return StreamingResponse(stream_generator(), media_type="text/event-stream")
    # except Exception as e:
    #     raise HTTPException(status_code=500, detail=str(e))
