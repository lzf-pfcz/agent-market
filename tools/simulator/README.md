# Agent 模拟器

本地测试工具 - 模拟平台和其他Agent进行端到端测试

## 功能

- 模拟其他Agent响应
- 发送握手请求
- 发送任务请求
- 验证响应格式
- 查看完整交互日志

## 安装

```bash
cd tools/simulator
pip install -r requirements.txt
```

## 使用方法

### 基本使用

```bash
# 启动模拟器
python simulator.py

# 模拟发送任务给目标Agent
python simulator.py send-task --target flight-agent-001 --payload '{"from":"北京","to":"上海"}'
```

### 交互模式

```bash
python simulator.py interactive
```

## 命令

### send-task - 发送任务

```bash
python simulator.py send-task \
  --target agent-id \
  --payload '{"action":"echo","message":"Hello"}' \
  --platform-url ws://localhost:8000/ws/agent
```

### handshake - 握手

```bash
python simulator.py handshake \
  --initiator my-agent \
  --responder target-agent \
  --platform-url ws://localhost:8000
```

### discover - 发现服务

```bash
python simulator.py discover \
  --query "航班" \
  --platform-url http://localhost:8000
```

## 测试脚本示例

创建 `test_script.py`:

```python
from simulator import AgentSimulator

async def test_flight_agent():
    """测试航班查询Agent"""
    sim = AgentSimulator(platform_url="ws://localhost:8000")
    
    # 1. 发现服务
    agents = await sim.discover("航班")
    print(f"发现Agent: {agents}")
    
    # 2. 发起握手
    session = await sim.handshake("test-agent", agents[0]["agent_id"])
    print(f"会话建立: {session}")
    
    # 3. 发送任务
    result = await sim.send_task(
        session_id=session["session_id"],
        target_agent=agents[0]["agent_id"],
        payload={
            "action": "search_flight",
            "from_city": "北京",
            "to_city": "上海",
            "date": "2026-03-21"
        }
    )
    print(f"结果: {result}")
    
    # 4. 关闭会话
    await sim.close_session(session["session_id"])

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_flight_agent())
```

## 日志输出

```
[2026-03-20 10:00:00] [INFO] 模拟器启动
[2026-03-20 10:00:01] [INFO] 发现服务: query=航班
[2026-03-20 10:00:01] [INFO] 发现结果: [flight-agent-001]
[2026-03-20 10:00:02] [INFO] 发起握手: test-agent -> flight-agent-001
[2026-03-20 10:00:02] [INFO] 握手成功: session-abc123
[2026-03-20 10:00:03] [INFO] 发送任务: task-xyz789
[2026-03-20 10:00:03] [INFO] 收到响应: {flights: [...]}
[2026-03-20 10:00:04] [INFO] 测试通过!
```

## 断言验证

```python
from simulator import assert_response

# 验证响应格式
assert_response(result, {
    "status": "success",
    "flights": lambda x: len(x) > 0
})

# 验证响应时间
assert result["latency_ms"] < 1000

# 验证字段存在
assert "flight_no" in result["flights"][0]
```
