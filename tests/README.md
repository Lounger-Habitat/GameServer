# GameServer 测试指南

本目录包含 GameServer 项目的测试文件。本指南将介绍如何使用 uv 工具设置测试环境并运行测试。

## 测试结构

测试目录结构如下：

```
tests/
  ├── __init__.py
  ├── test_api_games.py     # 游戏API端点测试
  ├── test_api_players.py   # 玩家API端点测试
  └── test_websocket.py     # WebSocket端点测试
```

## 测试环境设置

本项目使用 [uv](https://github.com/astral-sh/uv) 进行依赖管理和虚拟环境管理。uv 是一个快速的 Python 包安装器和解析器，它可以替代传统的 pip 和 virtualenv。

### 安装 uv

如果您尚未安装 uv，可以按照以下步骤安装：

```bash
# 使用 curl 安装
curl -sSf https://astral.sh/uv/install.sh | sh

# 或使用 pip 安装
pip install uv
```

### 创建虚拟环境并安装依赖

```bash
# 在项目根目录下创建虚拟环境并安装依赖
uv venv
uv pip install -e .
```

## 运行测试

### 运行所有测试

```bash
# 在项目根目录下运行所有测试
uv run pytest
```

### 运行特定测试文件

```bash
# 运行特定的测试文件
uv run pytest tests/test_api_games.py
uv run pytest tests/test_api_players.py
uv run pytest tests/test_websocket.py
```

### 运行特定测试函数

```bash
# 运行特定的测试函数
uv run pytest tests/test_api_games.py::test_get_games
```

### 生成测试覆盖率报告

```bash
# 安装 pytest-cov 插件
uv pip install pytest-cov

# 生成测试覆盖率报告
uv run pytest --cov=gameserver tests/

# 生成 HTML 格式的详细覆盖率报告
uv run pytest --cov=gameserver --cov-report=html tests/
```

## 编写新测试

### API 测试

使用 FastAPI 的 TestClient 编写 API 测试。示例：

```python
from fastapi.testclient import TestClient
from gameserver.main import app

client = TestClient(app)

def test_new_endpoint():
    response = client.get("/api/new-endpoint")
    assert response.status_code == 200
    data = response.json()
    # 添加更多断言...
```

### WebSocket 测试

使用 TestClient 的 websocket_connect 方法编写 WebSocket 测试。示例：

```python
import json
from fastapi.testclient import TestClient
from gameserver.main import app

client = TestClient(app)

def test_new_websocket_feature():
    with client.websocket_connect("/ws") as websocket:
        websocket.send_text(json.dumps({"type": "new_event", "data": {...}}))
        data = websocket.receive_text()
        response = json.loads(data)
        # 添加断言...
```

## 调试测试

使用 `-v` 参数获取更详细的测试输出：

```bash
uv run pytest -v
```

使用 `--pdb` 参数在测试失败时进入调试器：

```bash
uv run pytest --pdb
```

## 持续集成

在 CI 环境中，可以使用以下命令安装依赖并运行测试：

```bash
uv pip install -e .
uv run pytest
```

---

如有任何问题或建议，请联系项目维护者。