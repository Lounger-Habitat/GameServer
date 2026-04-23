"""模块化 API Server 主入口"""

from core.app import create_app
from utils.config import settings

import logging
import sys

logging.basicConfig(
    level=logging.INFO,  # 如果需要更详细的信息，可以改为 logging.DEBUG
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[logging.StreamHandler(sys.stdout)],
)

# 打印启动信息
print("=" * 60)
print("🚀 启动模块化 API Server")
print("=" * 60)

# 创建应用实例（供 fastapi dev/run 使用）
app = create_app()

print("📡 服务器配置:")
print(f"   - Host: {settings.server.host}")
print(f"   - Port: {settings.server.port}")
print(f"📚 API 文档: http://localhost:{settings.server.port}/docs")
print("=" * 60)
print()
