# 航班查询Agent模板

这是一个基础的航班查询Agent示例。

## 文件结构

```
flight-agent/
├── agent.py          # Agent主程序
├── requirements.txt  # Python依赖
├── .env              # 环境配置
├── Dockerfile        # Docker配置
└── README.md        # 说明文档
```

## 快速开始

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env 填入你的 Agent ID 和 Token

# 3. 运行
python agent.py
```

## 实现业务逻辑

在 `agent.py` 的 `handle_task` 方法中实现你的业务逻辑：

```python
async def handle_task(self, task_data: dict) -> dict:
    """处理任务"""
    action = task_data.get('action')
    
    if action == 'search_flight':
        # 查询航班
        from_city = task_data.get('from_city')
        to_city = task_data.get('to_city')
        date = task_data.get('date')
        
        # 调用实际API获取航班数据
        flights = self.search_flights(from_city, to_city, date)
        
        return {'flights': flights}
    
    return {'error': 'Unknown action'}
```

## 测试

```bash
# 本地测试
python agent.py

# 发送测试任务
curl -X POST http://localhost:8000/api/agents/<AGENT_ID>/test \
  -H "Content-Type: application/json" \
  -d '{"action": "search_flight", "from_city": "北京", "to_city": "上海", "date": "2026-03-21"}'
```

## Docker 部署

```bash
# 构建镜像
docker build -t flight-agent .

# 运行
docker run -d --name flight-agent \
  -e AGENT_ID=your-agent-id \
  -e AGENT_TOKEN=your-token \
  flight-agent
```
