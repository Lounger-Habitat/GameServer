"""FastAPI 应用工厂"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi import Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from utils.config import settings
# 获取鉴权依赖项（用于保护其他路由）
from api.auth.dependencies import verify_api_key

def create_app() -> FastAPI:
    """创建并配置 FastAPI 应用"""
    app = FastAPI(
        title="MengLong API Server",
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
    
    # 注册统计中间件
    if settings.statistics.enabled:
        from api.statistics.middleware import StatisticsMiddleware
        app.add_middleware(StatisticsMiddleware)
        print("✅ 统计中间件已注册")

    # 动态注册路由
    register_routes(app)

    return app


def register_routes(app: FastAPI) -> None:
    """根据配置动态注册路由"""
    
    # Auth API（始终启用，用于 Key 管理）
    from api.auth.routes import router as auth_router
    app.include_router(auth_router, prefix="/auth", tags=["Authentication"])
    if settings.auth.enabled:
        print("✅ API Key 鉴权已启用")
    else:
        print("⚠️  API Key 鉴权已禁用")
    


    
    # OpenAI 兼容 API
    if settings.modules.enable_openai_api:
        from api.openai.routes import router as openai_router
        app.include_router(
            openai_router, 
            prefix="/v1", 
            tags=["OpenAI Compatible"],
            dependencies=[Depends(verify_api_key)]
        )
        print("✅ OpenAI Compatible API 已启用")
    
    # Response API
    if settings.modules.enable_response_api:
        from api.response.routes import router as response_router
        app.include_router(
            response_router, 
            prefix="/response", 
            tags=["Response API"],
            dependencies=[Depends(verify_api_key)]
        )
        print("✅ Response API 已启用")
    
    # 朦胧 API
    if settings.modules.enable_menglong_api:
        from api.menglong.routes import router as menglong_router
        app.include_router(
            menglong_router, 
            prefix="/menglong", 
            tags=["MengLong API"],
            dependencies=[Depends(verify_api_key)]
        )
        print("✅ MengLong API 已启用")
    
    # Agent API
    if settings.modules.enable_agent_api:
        from api.agent.routes import router as agent_router
        app.include_router(
            agent_router,
            prefix="/agent",
            tags=["Agent API"],
            dependencies=[Depends(verify_api_key)]
        )
        print("✅ Agent API 已启用")
    
    # WebSocket
    if settings.modules.enable_websocket:
        from ws.starprotocol import router as ws_router
        app.include_router(ws_router, tags=["WebSocket"])
        print("✅ WebSocket 已启用")
        
        # Monitor API（新的规范化 API）
        from ws.monitor_api import router as monitor_router
        app.include_router(monitor_router, tags=["Monitor"])
        print("✅ Monitor API 已启用")
    
    # 统计 API
    if settings.statistics.enabled:
        from api.statistics.routes import router as stats_router
        app.include_router(
            stats_router,
            prefix="/statistics",
            tags=["Statistics"],
            dependencies=[Depends(verify_api_key)]
        )
        print("✅ 统计 API 已启用")
    
    # 静态文件服务（用于监控页面）
    try:
        app.mount("/static", StaticFiles(directory="static"), name="static")
        print("✅ 静态文件服务已启用")
    except Exception as e:
        print(f"⚠️  静态文件服务启用失败: {e}")
    
    # 监控页面端点
    @app.get("/monitor", tags=["System"])
    async def monitor_page():
        """重定向到 Star Protocol 监控页面"""
        return RedirectResponse(url="/static/monitor.html")

    # 健康检查端点
    @app.get("/health", tags=["System"])
    async def health_check():
        """健康检查"""
        return {
            "status": "healthy",
            "auth_enabled": settings.auth.enabled,
            "modules": {
                "openai_api": settings.modules.enable_openai_api,
                "response_api": settings.modules.enable_response_api,
                "menglong_api": settings.modules.enable_menglong_api,
                "agent_api": settings.modules.enable_agent_api,
                "websocket": settings.modules.enable_websocket,
                "statistics": settings.statistics.enabled,
            }
        }
