# GameServer

一个使用FastAPI构建的游戏后台服务，提供RESTful API和WebSocket接口。

## 功能特点

- RESTful API接口
- WebSocket实时通信
- 使用uv进行依赖管理
- 完整的测试套件

## 安装

确保你已安装Python 3.13.2或更高版本和uv。

```bash
# 克隆仓库
git clone <repository-url>
cd GameServer

# 使用uv安装依赖
uv sync
```

暂行编辑模式单独安装 agent 依赖

```bash
# 下载依赖
cd ~/Workspace
git clone https://github.com/GCYYfun/MengLong

# 然后使用可编辑模式安装 MengLong
cd ~/Workspace/MengLong
uv pip install -e .

# 返回 GameServer 目录
cd ~/Workspace/GameServer
```

## 运行服务

```bash
# 启动服务器
uv run fastapi dev gameserver/main.py # 部署替换为 fastapi run 
```

服务将在 http://localhost:8000 上运行。



## API文档

启动服务后，可以访问以下URL查看API文档：

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## WebSocket

WebSocket接口可通过 ws://localhost:8000/ws 访问。

## 测试

```bash
# 运行测试
uv run -m pytest
```

## 项目结构

```
gameserver/
├── __init__.py
├── main.py           # 应用入口
├── api/              # RESTful API路由
├── ws/               # WebSocket处理
├── models/           # 数据模型
├── services/         # 业务逻辑
└── utils/            # 工具函数
tests/                # 测试目录
```