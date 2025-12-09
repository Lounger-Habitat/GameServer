"""Response API 路由（OpenAI Response API 预留）"""
from fastapi import APIRouter

router = APIRouter()


@router.get("/")
async def response_root():
    """Response API 根端点"""
    return {
        "message": "OpenAI Response API",
        "status": "预留模块，待实现",
        "note": "此模块将实现 OpenAI 的 Response API 功能"
    }


@router.get("/status")
async def get_status():
    """获取状态"""
    return {
        "status": "ok",
        "service": "response_api",
        "ready": False,
        "message": "Response API 模块已启用，功能待实现"
    }


@router.post("/create")
async def create_response():
    """创建响应（占位符）"""
    return {
        "message": "Response API 创建端点",
        "status": "not_implemented",
        "note": "待 OpenAI Response API 规范明确后实现"
    }
