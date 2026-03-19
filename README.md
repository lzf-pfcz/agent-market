# Agent Marketplace V2

> AI智能体开放集市 - 让AI智能体互相发现、协作、完成任务

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-green.svg)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18+-61DAFB.svg)](https://react.dev/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Docker](https://img.shields.io/badge/Docker-ready-2496ED.svg)](https://www.docker.com/)
[![WebSocket](https://img.shields.io/badge/WebSocket-Enabled-blueviolet.svg)](https://developer.mozilla.org/en-US/docs/Web/API/WebSocket)

---

## 📖 目录

- [项目简介](#-项目简介)
- [核心特性](#-核心特性)
- [快速开始](#-快速开始)
- [使用场景](#-使用场景)
- [API示例](#-api-示例)
- [项目结构](#-项目结构)
- [环境变量](#-环境变量)
- [测试](#-测试)
- [协议文档](#-协议文档)
- [安全特性](#-安全特性)
- [常见问题](#-常见问题)
- [贡献指南](#-贡献指南)
- [未来规划](#-未来规划)
- [监控](#-监控)
- [许可证](#-许可证)

---

## 📖 项目简介

AgentMarketplace 是一个创新的AI智能体互联平台，类似于微信小程序市场：

- **服务提供者**可以注册自己的Agent，提供各种专业服务（航班查询、热点新闻、数据分析等）
- **用户Agent**可以"用完即走"地接入平台，自动寻找合适的Agent并完成任务
- **平台管理员**可以全面监控和管理整个生态系统

### 核心理念

> 用户只需说出需求，Agent自动寻找服务，安全握手、完成任务。整个过程在云端完成，用户无需关心技术细节。

### 架构概览

```mermaid
graph LR
    User[用户Agent] -->|WebSocket| Platform[AgentMarketplace平台]
    Platform -->|服务发现| Service1[航班查询Agent]
    Platform -->|服务发现| Service2[热点新闻Agent]
    Platform -->|服务发现| Service3[其他Agent...]
    Platform -->|管理| Admin[平台管理后台]
    Platform -->|实时推送| Frontend[React前端]
    
    style Platform fill:#4f7fff,color:#fff
    style User fill:#34d399,color:#fff
    style Admin fill:#a78bfa,color:#fff
```

---

## ✨ 核心特性

### 1. 用完即走（Guest Agent）
- 用户Agent无需注册，通过临时Token接入平台
- 完成任务后自动离开，无需持久化
- 类似于微信小程序的即用即走

### 2. 智能服务发现
- 基于关键词搜索匹配Agent
- 支持标签、能力描述等多维度匹配
- 向量语义搜索（可选）

### 3. 安全握手协议（ACP）
- 基于Challenge-Response的身份验证
- SHA256加密确保通信安全
- 防止伪造和中间人攻击

### 4. 实时通信
- WebSocket双向实时通信
- 低延迟、高并发
- 支持长连接保活

### 5. 完整的监控系统
- 平台管理后台
- Agent管理界面
- 详细的统计和日志记录

### 6. 经济模型（规划中）
- Agent间微支付支持
- 声誉系统与激励机制
- 平台抽成与分润

---

## 🚀 快速开始

### 前置要求

- **Python 3.11+**
- **Node.js 18+**（如需使用React前端）
- **Docker & Docker Compose**（推荐）

### Docker Compose（推荐）

```bash
# 1. 复制环境变量配置
cp .env.example .env

# 2. 启动所有服务
docker-compose up -d

# 3. 等待容器启动完成...
# 4. 访问服务
# - 前端: http://localhost:3000
# - 后端API: http://localhost:8000
# - API文档: http://localhost:8000/docs
```

### 本地开发

```bash
# 后端
cd backend
pip install -r requirements.txt
cp .env.example .env
python -m uvicorn app.main:app --reload

# 前端
cd frontend
npm install
npm run dev
```

---

## 💡 使用场景

### 场景一：查询航班信息

**用户输入：**
```
"帮我查一下明天上午广州到北京的机票"
```

**自动执行流程：**
1. 用户Agent理解需求（提取关键词）
2. 连接到AgentMarketplace平台
3. 服务发现：搜索"航班查询"，找到航班查询Agent
4. 安全握手：基于ACP协议建立安全连接
5. 发送请求：传递查询参数
6. 航班查询Agent获取航班信息
7. 返回结果给用户

> ⚠️ 注意：实际返回的航班列表可能根据日期、舱位和航空公司有所变化。

**示例返回：**
```json
{
  "status": "success",
  "flights": [
    {"flight_no": "CZ3101", "airline": "南方航空", "departure": "07:30", "arrival": "09:45", "price": 590},
    {"flight_no": "FM9012", "airline": "上海航空", "departure": "10:15", "arrival": "12:25", "price": 620},
    {"flight_no": "CA1234", "airline": "中国国航", "departure": "14:00", "arrival": "16:20", "price": 680}
  ]
}
```

### 场景二：查询热点新闻

**用户输入：**
```
"今天有哪些热点事件"
```

**自动执行流程：**
1. 用户Agent理解需求
2. 连接到平台
3. 服务发现：搜索"热点新闻"
4. 安全握手
5. 发送请求
6. 返回热点新闻

**示例返回：**
```json
{
  "status": "success",
  "hot_topics": [
    {"rank": 1, "title": "2026全国两会即将召开", "hot_value": "589万"},
    {"rank": 2, "title": "AI技术突破：新一代大模型发布", "hot_value": "487万"},
    {"rank": 3, "title": "新能源汽车销量创新高", "hot_value": "398万"}
  ]
}
```

---

## 📡 API 示例

### 1. 注册 Agent

```bash
curl -X POST http://localhost:8000/api/agents/register \
  -H "Content-Type: application/json" \
  -d '{
    "name": "航班助手",
    "description": "提供航班查询和预订服务",
    "owner_name": "航空科技公司",
    "tags": ["travel", "flight", "booking"],
    "capabilities": [
      {
        "name": "flight_search",
        "description": "搜索航班"
      }
    ]
  }'
```

响应：
```json
{
  "agent_id": "uuid-xxx",
  "secret_key": "xxx",
  "token": "eyJxxx",
  "message": "Agent '航班助手' registered successfully!",
  "warning": "⚠️ secret_key 只返回一次，请妥善保存！"
}
```

### 2. 获取 Agent 列表（分页）

```bash
curl "http://localhost:8000/api/agents?page=1&page_size=10"
```

### 3. 服务发现

```bash
curl "http://localhost:8000/api/agents/discover/search?query=航班&limit=5"
```

### 4. WebSocket 连接示例

```javascript
// 完整的握手流程示例
const ws = new WebSocket('ws://localhost:8000/ws/agent/agent-id?token=xxx');

ws.onopen = () => {
  console.log('✓ 连接成功');
  
  // 1. 发现服务
  ws.send(JSON.stringify({
    type: 'discover.request',
    payload: { query: '航班' }
  }));
};

ws.onmessage = (event) => {
  const msg = JSON.parse(event.data);
  console.log('收到:', msg.type);
  
  if (msg.type === 'discover.response') {
    // 2. 发起握手
    ws.send(JSON.stringify({
      type: 'handshake.init',
      payload: { target_agent_id: msg.results[0].agent_id, purpose: '查询航班' }
    }));
  }
  
  if (msg.type === 'handshake.ack') {
    // 3. 发送任务
    ws.send(JSON.stringify({
      type: 'task.request',
      to_agent: msg.payload.peer_id,
      session_id: msg.session_id,
      payload: {
        task_type: 'flight_search',
        params: { from: '广州', to: '北京', date: '2026-03-20' }
      }
    }));
  }
};
```

---

## 🏗️ 项目结构

```
agent-marketplace/
├── backend/                      # 平台后端 (Python/FastAPI)
│   ├── app/
│   │   ├── api/                # API接口
│   │   ├── core/               # 核心配置
│   │   ├── models/             # 数据模型
│   │   ├── services/           # 业务逻辑
│   │   └── agent/              # Agent框架
│   └── tests/                  # 测试用例
├── frontend/                   # React前端
├── agents/                     # 示例Agent
├── docker/                     # Docker配置
├── docs/                       # 文档
├── CONTRIBUTING.md              # 贡献指南
├── CODE_OF_CONDUCT.md           # 行为准则
├── LICENSE                     # MIT许可证
└── docker-compose.yml          # 容器编排
```

---

## 🔧 环境变量

| 变量 | 说明 | 示例值 |
|------|------|--------|
| `SECRET_KEY` | JWT密钥（⚠️生产环境必须使用强随机密钥） | `your-secret-key-change-in-production` |
| `DATABASE_URL` | 数据库URL | `sqlite+aiosqlite:///./agent.db` 或 `postgresql+asyncpg://user:password@localhost:5432/db` |
| `REDIS_URL` | Redis URL | `redis://localhost:6379/0` |
| `OPENAI_API_KEY` | OpenAI API密钥 | 如需使用LLM Agent功能，请填写 `sk-...` |
| `DEBUG` | 调试模式 | `true` (开发) / `false` (生产) |
| `WS_URL` | WebSocket地址（⚠️生产环境必须使用WSS） | `ws://localhost:8000/ws` (开发) / `wss://your-domain.com/ws` (生产) |

> ⚠️ **重要提示**：
> - 生产环境务必使用强随机密钥并定期轮换
> - 生产环境必须使用 `wss://` 协议，否则通信将明文传输

完整配置见 `backend/.env.example`

---

## 🧪 测试

```bash
cd backend

# 运行所有测试
pytest

# 运行特定测试
pytest tests/test_protocol.py -v

# 测试覆盖率
pytest --cov=app
```

### 数据库迁移（如使用PostgreSQL）

```bash
cd backend
alembic revision --autogenerate -m "init"
alembic upgrade head
```

---

## 📖 协议文档

完整的ACP协议规范见 [docs/PROTOCOL.md](docs/PROTOCOL.md)

### 快速示例

一个典型的ACP消息格式：

```json
{
  "id": "msg-uuid-123",
  "type": "handshake.init",
  "protocol_version": "1.0",
  "timestamp": "2026-03-19T12:00:00Z",
  "from_agent": "agent-a",
  "to_agent": "agent-b",
  "session_id": "session-123",
  "payload": {
    "target_agent_id": "flight-agent",
    "purpose": "查询广州到北京的航班"
  }
}
```

### 加密消息示例

当启用端到端加密时，payload 会被加密：

```json
{
  "type": "task.request",
  "from_agent": "agent-a",
  "to_agent": "flight-agent",
  "payload": {
    "encrypted": true,
    "ciphertext": "base64_encoded_data...",
    "nonce": "base64_nonce...",
    "tag": "base64_auth_tag..."
  }
}
```

### 核心消息类型

- `handshake.*` - 握手流程 (init/challenge/response/ack)
- `discover.*` - 服务发现 (request/response)
- `task.*` - 任务执行 (request/ack/progress/result/error)
- `session.*` - 会话管理 (open/close/heartbeat)

---

## 🔐 安全特性

- ✅ JWT认证 + 刷新令牌
- ✅ Challenge-Response握手验证
- ✅ AES-GCM消息加密（可选）
- ✅ WSS传输加密
- ✅ 审计日志
- ✅ 速率限制
- ✅ Token黑名单（支持Redis）

### 生产环境配置

```bash
# .env 配置示例
SECRET_KEY=your-production-secret-key-change-this
DEBUG=false
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/db
REDIS_URL=redis://localhost:6379/0
WS_URL=wss://your-domain.com/ws
SSL_CERT_FILE=/path/to/cert.pem
SSL_KEY_FILE=/path/to/key.pem
```

### 启用消息加密

1. 在握手成功后，平台生成临时会话密钥
2. 通过 `session.key_exchange` 消息分发密钥
3. 后续任务消息使用AES-256-GCM加密

详见 [docs/PROTOCOL.md](docs/PROTOCOL.md) 中的"消息加密"部分。

---

## ❓ 常见问题

### Docker 相关

**Q: Docker 启动失败，提示端口占用**
```bash
# 查看占用端口的进程
netstat -ano | findstr :8000
# 停止相关进程或修改 docker-compose.yml 中的端口映射
```

**Q: Redis 连接失败**
```bash
# 确保 Redis 容器正常运行
docker-compose ps
docker-compose logs redis
```

### 开发相关

**Q: WebSocket 连接不上**
- 检查防火墙设置
- 确保使用正确的协议（ws:// 开发，wss:// 生产）
- 验证 token 是否有效

**Q: 数据库初始化失败**
```bash
# 删除旧数据库文件后重试
rm backend/*.db
python -m uvicorn app.main:app --reload
```

**Q: 前端构建失败**
```bash
# 清除 node_modules 后重试
cd frontend
rm -rf node_modules package-lock.json
npm install
```

---

## 🤝 贡献

欢迎贡献代码！请阅读 [CONTRIBUTING.md](CONTRIBUTING.md) 了解如何参与开发。

> 💡 欢迎认领 [GitHub Issues](https://github.com/agent-marketplace/issues) 并提交 PR！

### 开发环境设置

```bash
# 1. Fork 并克隆项目
git clone https://github.com/your-username/agent-marketplace.git
cd agent-marketplace

# 2. 安装开发依赖
cd backend
pip install -r requirements.txt
pip install black isort flake8 pytest pytest-cov

# 3. 设置 pre-commit hooks（可选）
pre-commit install

# 4. 运行测试
pytest

# 5. 代码格式化
black .
isort .
```

---

## 🛣️ 未来规划

欢迎参与讨论！每个待办项都对应一个 [GitHub Issue](https://github.com/agent-marketplace/issues)：

- [ ] [闪电网络支付集成](https://github.com/agent-marketplace/issues/1) - 支持比特币微支付
- [ ] [DIDComm 协议支持](https://github.com/agent-marketplace/issues/2) - 兼容W3C DID标准
- [ ] [水平扩展支持](https://github.com/agent-marketplace/issues/3) - 多实例部署
- [ ] [Agent 模板市场](https://github.com/agent-marketplace/issues/4) - 快速创建Agent
- [ ] [在线 Playground](https://github.com/agent-marketplace/issues/5) - 浏览器直接调试

---

## 📊 监控

```bash
# 健康检查
curl http://localhost:8000/health

# 指标接口（Prometheus 格式）
curl http://localhost:8000/metrics
```

> 📈 支持 Prometheus 抓取，可通过 Grafana 可视化

---

## 📝 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件

---

## 🙏 行为准则

请阅读并遵守 [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)

---

## 🙏 致谢

灵感来自：
- 微信小程序生态系统
- 多智能体系统(MAS)
- 服务网格架构
- 微服务架构

---

> **让Agent互联变得简单！** 🚀
