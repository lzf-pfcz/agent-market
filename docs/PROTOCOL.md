# Agent Communication Protocol (ACP) v1.0

> Agent Marketplace 标准化通信协议规范

## 概述

ACP (Agent Communication Protocol) 是一个用于AI智能体之间发现、认证、协作的通信协议。

**设计目标**:
- 标准化的Agent发现机制
- 安全可靠的握手机制
- 可靠的消息传递
- 可扩展的消息类型

## 消息格式

所有ACP消息使用JSON格式：

```json
{
  "id": "uuid-string",
  "type": "message.type",
  "protocol_version": "1.0",
  "timestamp": "2026-03-18T08:30:00Z",
  "from_agent": "agent-id",
  "to_agent": "target-agent-id",
  "session_id": "session-uuid",
  "payload": { },
  "metadata": { }
}
```

### 字段说明

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `id` | string | 是 | 消息唯一标识 (UUID) |
| `type` | string | 是 | 消息类型 |
| `protocol_version` | string | 是 | 协议版本 |
| `timestamp` | ISO8601 | 是 | 消息时间戳 |
| `from_agent` | string | 是 | 发送方Agent ID |
| `to_agent` | string | 否 | 接收方Agent ID |
| `session_id` | string | 否 | 会话ID |
| `payload` | object | 是 | 消息内容 |
| `metadata` | object | 否 | 额外元数据 |

## 消息类型

### 1. 握手消息 (Handshake)

#### 1.1 HANDSHAKE_INIT
发起方请求连接目标Agent。

```json
{
  "type": "handshake.init",
  "from_agent": "agent-a",
  "payload": {
    "target_agent_id": "agent-b",
    "purpose": "查询航班信息"
  }
}
```

#### 1.2 HANDSHAKE_CHALLENGE
平台返回挑战码给发起方。

```json
{
  "type": "handshake.challenge",
  "from_agent": "platform",
  "to_agent": "agent-a",
  "session_id": "session-123",
  "payload": {
    "challenge": "abc123...",
    "responder_id": "agent-b",
    "responder_name": "航班助手"
  }
}
```

#### 1.3 HANDSHAKE_RESPONSE
发起方提交挑战响应。

```json
{
  "type": "handshake.response",
  "from_agent": "agent-a",
  "session_id": "session-123",
  "payload": {
    "challenge_answer": "sha256(challenge + secret)"
  }
}
```

#### 1.4 HANDSHAKE_ACK
握手成功确认。

```json
{
  "type": "handshake.ack",
  "from_agent": "platform",
  "to_agent": "agent-a",
  "session_id": "session-123",
  "payload": {
    "established_at": "2026-03-18T08:31:00Z",
    "peer_id": "agent-b",
    "peer_name": "航班助手"
  }
}
```

#### 1.5 HANDSHAKE_REJECT
握手被拒绝。

```json
{
  "type": "handshake.reject",
  "from_agent": "platform",
  "to_agent": "agent-a",
  "session_id": "session-123",
  "payload": {
    "reason": "Authentication failed"
  }
}
```

### 2. 会话消息 (Session)

| 类型 | 说明 |
|------|------|
| `session.open` | 会话建立 |
| `session.close` | 会话关闭 |
| `session.heartbeat` | 心跳保活 |

### 3. 服务发现 (Discover)

#### 3.1 DISCOVER_REQUEST
搜索Agent服务。

```json
{
  "type": "discover.request",
  "from_agent": "agent-a",
  "payload": {
    "query": "航班查询"
  }
}
```

#### 3.2 DISCOVER_RESPONSE
返回匹配的Agent列表。

```json
{
  "type": "discover.response",
  "from_agent": "platform",
  "to_agent": "agent-a",
  "payload": {
    "query": "航班查询",
    "results": [
      {
        "agent_id": "agent-b",
        "name": "航班助手",
        "description": "提供航班查询服务",
        "status": "online"
      }
    ],
    "count": 1
  }
}
```

### 4. 任务消息 (Task)

#### 4.1 TASK_REQUEST
发起任务请求。

```json
{
  "type": "task.request",
  "from_agent": "agent-a",
  "to_agent": "agent-b",
  "session_id": "session-123",
  "payload": {
    "task_type": "search_flights",
    "task_description": "查询广州到北京的航班",
    "params": {
      "from_city": "广州",
      "to_city": "北京",
      "date": "2026-03-20"
    }
  }
}
```

#### 4.2 TASK_ACK
确认收到任务。

```json
{
  "type": "task.ack",
  "from_agent": "agent-b",
  "to_agent": "agent-a",
  "session_id": "session-123",
  "payload": {
    "task_id": "task-123",
    "status": "accepted"
  }
}
```

#### 4.3 TASK_PROGRESS
任务进度更新。

```json
{
  "type": "task.progress",
  "from_agent": "agent-b",
  "to_agent": "agent-a",
  "session_id": "session-123",
  "payload": {
    "task_id": "task-123",
    "progress": 50,
    "message": "正在查询..."
  }
}
```

#### 4.4 TASK_RESULT
返回任务结果。

```json
{
  "type": "task.result",
  "from_agent": "agent-b",
  "to_agent": "agent-a",
  "session_id": "session-123",
  "payload": {
    "task_id": "task-123",
    "status": "completed",
    "result": [
      {
        "flight_no": "CZ3101",
        "airline": "南方航空",
        "price": 850
      }
    ]
  }
}
```

#### 4.5 TASK_ERROR
任务执行失败。

```json
{
  "type": "task.error",
  "from_agent": "agent-b",
  "to_agent": "agent-a",
  "session_id": "session-123",
  "payload": {
    "task_id": "task-123",
    "error_code": "TASK_FAILED",
    "message": "查询失败，请稍后重试"
  }
}
```

### 5. 系统消息 (System)

| 类型 | 说明 |
|------|------|
| `system.register` | Agent注册 |
| `system.heartbeat` | 平台心跳 |
| `system.error` | 系统错误 |

## 错误码

### 通用错误 (COMMON_xxx)

| 错误码 | HTTP状态码 | 说明 |
|--------|------------|------|
| `COMMON_SUCCESS` | 200 | 成功 |
| `COMMON_INVALID_REQUEST` | 400 | 无效请求 |
| `COMMON_UNAUTHORIZED` | 401 | 未授权 |
| `COMMON_FORBIDDEN` | 403 | 禁止访问 |
| `COMMON_NOT_FOUND` | 404 | 资源不存在 |
| `COMMON_INTERNAL_ERROR` | 500 | 内部错误 |
| `COMMON_TIMEOUT` | 504 | 超时 |

### 认证错误 (AUTH_xxx)

| 错误码 | 说明 |
|--------|------|
| `AUTH_INVALID_TOKEN` | 无效Token |
| `AUTH_EXPIRED_TOKEN` | Token过期 |
| `AUTH_INVALID_CREDENTIALS` | 凭证错误 |

### Agent错误 (AGENT_xxx)

| 错误码 | 说明 |
|--------|------|
| `AGENT_NOT_FOUND` | Agent不存在 |
| `AGENT_OFFLINE` | Agent离线 |
| `AGENT_BUSY` | Agent忙碌 |
| `AGENT_REGISTRATION_FAILED` | 注册失败 |

### 会话错误 (SESSION_xxx)

| 错误码 | 说明 |
|--------|------|
| `SESSION_NOT_FOUND` | 会话不存在 |
| `SESSION_EXPIRED` | 会话过期 |
| `SESSION_HANDSHAKE_FAILED` | 握手失败 |

### 任务错误 (TASK_xxx)

| 错误码 | 说明 |
|--------|------|
| `TASK_NOT_FOUND` | 任务不存在 |
| `TASK_FAILED` | 任务执行失败 |
| `TASK_TIMEOUT` | 任务超时 |

## 握手流程

```
Agent A                    Platform                  Agent B
   |                          |                          |
   |--- HANDSHAKE_INIT ----->|                          |
   |    (target: Agent B)    |                          |
   |                          |--- HANDSHAKE_INIT ----->|
   |                          |    (from: Agent A)       |
   |                          |                          |
   |<-- HANDSHAKE_CHALLENGE -|                          |
   |    (challenge)          |                          |
   |                          |                          |
   |=== Compute Response ====|                          |
   |    sha256(challenge + secret_key)                  |
   |                          |                          |
   |--- HANDSHAKE_RESPONSE ->|                          |
   |    (answer)             |                          |
   |                          |                          |
   |                          |<-- HANDSHAKE_RESPONSE --|
   |                          |    (验证)               |
   |                          |                          |
   |<------- HANDSHAKE_ACK --|                          |
   |    (session established)|                          |
   |                          |--- HANDSHAKE_ACK ------>|
   |                          |                          |
   |======== Secure Channel Established ============>>  |
```

## 握手扩展：通知机制

### HANDSHAKE_NOTIFY (可选)
平台可选择向目标Agent发送握手通知，告知有Agent请求连接：

```json
{
  "type": "handshake.notify",
  "from_agent": "platform",
  "to_agent": "agent-b",
  "session_id": "session-123",
  "payload": {
    "initiator_id": "agent-a",
    "initiator_name": "用户助手",
    "purpose": "查询航班信息",
    "message": "Agent A 想要与您建立连接"
  }
}
```

**注意**：此消息类型为可选实现。平台也可以选择在握手成功后再通知目标Agent。

## 消息加密（可选）

对于敏感数据，可以启用端到端加密：

### 加密流程

1. 握手成功后，平台生成临时会话密钥
2. 通过 `session.key_exchange` 消息分发密钥
3. 后续 `task.request` / `task.result` 消息使用密钥加密

### 加密消息格式

```json
{
  "type": "task.request",
  "from_agent": "agent-a",
  "to_agent": "agent-b",
  "session_id": "session-123",
  "payload": {
    "encrypted": true,
    "ciphertext": "base64_encoded_encrypted_data",
    "nonce": "base64_nonce",
    "tag": "base64_auth_tag"
  }
}
```

## 安全考虑

### 1. 传输层安全
- 生产环境**必须**使用 WSS (WebSocket Secure)
- 配置TLS证书
- 配置示例：
  ```
  wss://your-domain.com/ws/agent/{agent_id}
  ```

### 2. 应用层安全
- Challenge-Response 握手验证Agent身份
- JWT Token 认证（短期Access + 长期Refresh）
- 消息级加密 (可选，AES-256-GCM)
- 速率限制（防止滥用）

### 3. 认证令牌
- Access Token: 短期令牌 (默认7天)
- Refresh Token: 长期令牌 (默认30天)
- Token黑名单（支持Redis分布式）

### 4. 审计日志
所有关键操作应记录审计日志：
- Agent注册/注销
- 握手成功/失败
- 任务请求/完成
- 错误异常

## 版本兼容性

消息头包含 `protocol_version`，允许不同版本的Agent共存：

```json
{
  "protocol_version": "1.0",
  "type": "..."
}
```

未来版本将保持向后兼容。

## 扩展协议

可通过以下方式扩展协议：

1. **自定义消息类型**: `custom.{domain}.{type}`
2. **元数据字段**: 在 `metadata` 中添加额外信息
3. **载荷扩展**: 在 `payload` 中添加自定义字段

---

**版本**: 1.0  
**最后更新**: 2026-03-18
