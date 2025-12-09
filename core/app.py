"""FastAPI 应用工厂"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings


def create_app() -> FastAPI:
    """创建并配置 FastAPI 应用"""
    app = FastAPI(
        title="Modular API Server",
        description="支持 RESTful API 和 WebSocket 的模块化服务器",
        version="0.1.0",
    )

    # 配置 CORS
    if settings.cors.enabled:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors.allow_origins,
            allow_credentials=settings.cors.allow_credentials,
            allow_methods=settings.cors.allow_methods,
            allow_headers=settings.cors.allow_headers,
        )

    # 动态注册路由
    register_routes(app)

    return app


def register_routes(app: FastAPI) -> None:
    """根据配置动态注册路由"""
    
    # OpenAI 兼容 API
    if settings.modules.enable_openai_api:
        from api.openai.routes import router as openai_router
        app.include_router(openai_router, prefix="/v1", tags=["OpenAI Compatible"])
        print("✅ OpenAI Compatible API 已启用")
    
    # Response API
    if settings.modules.enable_response_api:
        from api.response.routes import router as response_router
        app.include_router(response_router, prefix="/response", tags=["Response API"])
        print("✅ Response API 已启用")
    
    # 自定义 API
    if settings.modules.enable_custom_api:
        from api.custom.routes import router as custom_router
        app.include_router(custom_router, prefix="/custom", tags=["Custom API"])
        print("✅ Custom API 已启用")
    
    # WebSocket
    if settings.modules.enable_websocket:
        from ws.starprotocol import router as ws_router
        app.include_router(ws_router, tags=["WebSocket"])
        print("✅ WebSocket 已启用")

    # 健康检查端点
    @app.get("/health", tags=["System"])
    async def health_check():
        """健康检查"""
        return {
            "status": "healthy",
            "modules": {
                "openai_api": settings.modules.enable_openai_api,
                "response_api": settings.modules.enable_response_api,
                "custom_api": settings.modules.enable_custom_api,
                "websocket": settings.modules.enable_websocket,
            }
        }
