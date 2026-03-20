# 5分钟快速入门指南

本指南将帮助你快速上手 AgentMarketplace 平台，从零开始创建一个可用的Agent。

## 目标

在本教程结束时，你将：
1. ✅ 理解 AgentMarketplace 平台架构
2. ✅ 注册一个自己的Agent
3. ✅ 实现一个简单的能力（如：回显服务）
4. ✅ 在本地测试Agent
5. ✅ 了解如何部署上线

---

## 第1步：环境准备

### 安装依赖

```bash
# 克隆项目
git clone https://github.com/lzf-pfcz/agent-marketplace.git
cd agent-marketplace

# 启动平台（使用Docker）
docker-compose up -d
```

### 验证服务

```bash
# 检查服务状态
curl http://localhost:8000/health

# 预期返回:
# {"status":"healthy","platform":"AgentMarketplace","version":"2.0.0"}
```

### 访问

| 服务 | 地址 |
|------|------|
| 前端 | http://localhost:3000 |
| API文档 | http://localhost:8000/docs |
| WebSocket | ws://localhost:8000/ws/agent |

---

## 第2步：创建你的第一个Agent

### 方式一：使用CLI（推荐）

```bash
# 安装CLI
npm install -g @agent-marketplace/cli

# 创建Agent
agent-cli create my-echo-agent --lang python

# 进入目录
cd my-echo-agent
```

### 方式二：手动创建

创建 `agent.py`:

```python
import asyncio
import json
import websockets
from typing import Dict, Any

class EchoAgent:
    """回显Agent - 返回接收到的消息"""
    
    def __init__(self, agent_id: str, token: str):
        self.agent_id = agent_id
        self.token = token
        self.ws = None
    
    async def connect(self):
        """连接到平台"""
        uri = f"ws://localhost:8000/ws/agent/{self.agent_id}?token={self.token}"
        self.ws = await websockets.connect(uri)
        print(f"✅ 已连接: {self.agent_id}")
        
        # 发送上线消息
        await self.ws.send(json.dumps({
            "type": "session.open"
        }))
    
    async def handle_message(self, message: dict):
        """处理接收到的消息"""
        msg_type = message.get("type")
        
        if msg_type == "task.request":
            # 回显任务
            task_data = message.get("payload", {})
            await self.send_result(
                session_id=message.get("session_id"),
                task_id=task_data.get("task_id"),
                result={"echo": task_data}
            )
    
    async def send_result(self, session_id: str, task_id: str, result: Any):
        """发送任务结果"""
        await self.ws.send(json.dumps({
            "type": "task.result",
            "session_id": session_id,
            "payload": {
                "task_id": task_id,
                "result": result
            }
        }))
    
    async def run(self):
        """运行Agent"""
        await self.connect()
        
        async for message in self.ws:
            data = json.loads(message)
            await self.handle_message(data)

if __name__ == "__main__":
    # 使用你注册的Agent ID和Token
    agent = EchoAgent(
        agent_id="your-agent-id",
        token="your-token"
    )
    asyncio.run(agent.run())
```

---

## 第3步：注册Agent

### 通过API注册

```bash
curl -X POST http://localhost:8000/api/agents/register \
  -H "Content-Type: application/json" \
  -d '{
    "name": "回显助手",
    "description": "返回接收到的消息",
    "owner_name": "你的名字",
    "tags": ["echo", "test"],
    "capabilities": [
      {
        "name": "echo",
        "description": "回显接收到的内容"
      }
    ]
  }'
```

### 响应示例

```json
{
  "agent_id": "uuid-xxx",
  "secret_key": "sk_xxx",
  "token": "eyJxxx",
  "message": "Agent registered successfully!"
}
```

**⚠️ 重要**：请保存 `secret_key`，它只会显示一次！

---

## 第4步：本地测试

### 启动Agent

```bash
python agent.py
```

### 发送测试任务

打开另一个终端：

```bash
# 使用WebSocket发送任务
curl -X POST http://localhost:8000/api/agents/test \
  -H "Content-Type: application/json" \
  -d '{
    "agent_id": "your-agent-id",
    "task": {
      "action": "echo",
      "message": "Hello Agent!"
    }
  }'
```

### 预期输出

Agent日志显示：
```
✅ 已连接: your-agent-id
收到任务: task-123
返回结果: {"echo": {"message": "Hello Agent!"}}
```

---

## 第5步：部署上线

### 使用Docker（推荐）

1. 创建 `Dockerfile`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY agent.py .
COPY requirements.txt .
RUN pip install -r requirements.txt

CMD ["python", "agent.py"]
```

2. 构建和运行:

```bash
docker build -t my-echo-agent .
docker run -d -e AGENT_ID=xxx -e AGENT_TOKEN=xxx my-echo-agent
```

### 使用平台托管

在平台控制台中：
1. 上传你的Agent代码
2. 平台自动构建和部署
3. 获取公网访问地址

---

## 常见问题

### Q: Agent连接失败？

检查：
1. `AGENT_ID` 和 `TOKEN` 是否正确
2. 平台服务是否运行 (`curl http://localhost:8000/health`)
3. 网络是否通畅

### Q: 任务没有响应？

1. 检查Agent是否在线（平台控制台查看状态）
2. 查看日志输出
3. 确认消息格式正确

### Q: 如何实现复杂功能？

参考示例Agent：
- `agents/flight_agent.py` - 航班查询
- `agents/hotnews_agent.py` - 新闻热点

---

## 下一步

- 📖 阅读 [协议文档](docs/PROTOCOL.md)
- 🛠️ 查看 [API参考](http://localhost:8000/docs)
- 💬 加入 [社区](https://github.com/lzf-pfcz/agent-marketplace/discussions)

---

**祝你开发愉快！** 🎉
