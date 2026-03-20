# AgentMarketplace CLI

AgentMarketplace 命令行工具 - 快速创建和管理 Agent

## 安装

```bash
# 全局安装
npm install -g @agent-marketplace/cli

# 或使用 npx
npx agent-cli --help
```

## 命令

### create - 创建新 Agent

```bash
agent-cli create my-agent --lang python
agent-cli create my-agent --lang typescript
agent-cli create my-agent --lang javascript
```

### register - 注册 Agent

```bash
agent-cli register --name "航班助手" --description "提供航班查询"
```

### list - 列出已注册的 Agent

```bash
agent-cli list
```

### start - 启动 Agent

```bash
agent-cli start --agent-id <AGENT_ID>
```

### stop - 停止 Agent

```bash
agent-cli stop --agent-id <AGENT_ID>
```

## 选项

- `--help` 显示帮助
- `--version` 显示版本

## 示例

```bash
# 1. 创建新的航班查询 Agent
agent-cli create flight-agent --lang python

# 2. 进入目录
cd flight-agent

# 3. 修改 agent.py 实现业务逻辑

# 4. 注册到平台
agent-cli register

# 5. 启动 Agent
agent-cli start
```
