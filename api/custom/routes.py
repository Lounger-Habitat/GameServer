"""自定义 API 路由"""
from datetime import datetime
from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class CustomRequest(BaseModel):
    """自定义请求"""
    name: str
    message: Optional[str] = None


class CustomResponse(BaseModel):
    """自定义响应"""
    success: bool
    data: dict
    timestamp: str


@router.get("/")
async def custom_root():
    """自定义 API 根端点"""
    return {
        "message": "Custom API",
        "version": "1.0",
        "description": "自定义 API 端点集合"
    }


@router.get("/hello")
async def hello(name: str = "World"):
    """问候端点"""
    return CustomResponse(
        success=True,
        data={
            "greeting": f"Hello, {name}!",
            "message": "欢迎使用自定义 API"
        },
        timestamp=datetime.now().isoformat()
    )


@router.get("/info")
async def get_info():
    """获取服务信息"""
    return CustomResponse(
        success=True,
        data={
            "service": "Custom API Server",
            "version": "0.1.0",
            "features": [
                "RESTful API",
                "WebSocket Support",
                "Modular Architecture"
            ]
        },
        timestamp=datetime.now().isoformat()
    )


@router.post("/echo")
async def echo(request: CustomRequest):
    """回显端点"""
    return CustomResponse(
        success=True,
        data={
            "received": request.model_dump(),
            "echo": f"收到来自 {request.name} 的消息: {request.message or '(无消息)'}"
        },
        timestamp=datetime.now().isoformat()
    )
