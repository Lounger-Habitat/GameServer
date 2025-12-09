"""模块化 API Server 主入口"""
from core.app import create_app
from config import settings

# 打印启动信息
print("=" * 60)
print("🚀 启动模块化 API Server")
print("=" * 60)

# 创建应用实例（供 fastapi dev/run 使用）
app = create_app()

print(f"\n📡 服务器配置:")
print(f"   - Host: {settings.server.host}")
print(f"   - Port: {settings.server.port}")
print(f"\n📚 API 文档: http://localhost:{settings.server.port}/docs")
print("=" * 60)
print()

