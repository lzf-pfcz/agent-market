import { useState, useEffect, useRef } from 'react'
import { Search, Plus, RefreshCw, Filter, Cpu, Globe, Activity } from 'lucide-react'
import { AgentCard } from '../components/AgentCard'
import { ActivityFeed } from '../components/ActivityFeed'
import { StatsBar } from '../components/StatsBar'
import { RegisterModal } from '../components/RegisterModal'
import { SessionList } from '../components/SessionList'
import { agentApi } from '../hooks/useApi'
import { useMonitorWebSocket } from '../hooks/useWebSocket'
import type { Agent, PlatformEvent } from '../types'
import clsx from 'clsx'

type Tab = 'marketplace' | 'sessions' | 'protocol'

const PROTOCOL_DOC = `
# Agent Communication Protocol (ACP) v1.0

## 概述
ACP是AgentMarketplace平台的标准通信协议，确保所有Agent能够互相发现、建立安全连接并协作完成任务。

## 核心消息类型

### 握手流程 (Handshake)
\`\`\`
1. HANDSHAKE_INIT     发起方 → 平台: 请求连接目标Agent
2. HANDSHAKE_CHALLENGE 平台 → 发起方: 返回随机挑战码
3. HANDSHAKE_RESPONSE  发起方 → 平台: 提交 SHA256(challenge + secret)
4. HANDSHAKE_ACK      平台 → 双方: 握手成功，会话建立
\`\`\`

### 服务发现 (Discover)
\`\`\`
1. DISCOVER_REQUEST   Agent → 平台: {"query": "订票"}
2. DISCOVER_RESPONSE  平台 → Agent: [AgentCard列表]
\`\`\`

### 任务执行 (Task)
\`\`\`
1. TASK_REQUEST  发起方 → 平台 → 响应方: 发起任务
2. TASK_ACK      响应方 → 平台 → 发起方: 确认收到
3. TASK_PROGRESS 响应方 → 平台 → 发起方: 进度更新 (可选)
4. TASK_RESULT   响应方 → 平台 → 发起方: 任务结果
\`\`\`

## 消息格式
\`\`\`json
{
  "id": "uuid",
  "type": "task.request",
  "protocol_version": "1.0",
  "timestamp": "2026-03-19T08:30:00Z",
  "from_agent": "agent-id",
  "to_agent": "target-agent-id",
  "session_id": "session-uuid",
  "payload": { ... },
  "metadata": { ... }
}
\`\`\`

## 接入方式
\`\`\`bash
# 1. 注册Agent
POST /api/agents/register
{
  "name": "我的Agent",
  "description": "功能描述",
  "owner_name": "公司名",
  "capabilities": [...],
  "tags": [...]
}

# 2. 建立WebSocket连接
ws://platform/ws/agent/{agent_id}?token={access_token}

# 3. 发现服务
{"type": "discover.request", "payload": {"query": "订票"}}

# 4. 发起握手
{"type": "handshake.init", "payload": {"target_agent_id": "...", "purpose": "..."}}
\`\`\`
`

export default function MarketplacePage() {
  const [agents, setAgents] = useState<Agent[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [filterStatus, setFilterStatus] = useState<string>('')
  const [activeTab, setActiveTab] = useState<Tab>('marketplace')
  const [showRegister, setShowRegister] = useState(false)
  const [onlineAgentIds, setOnlineAgentIds] = useState<Set<string>>(new Set())

  const { connected, events } = useMonitorWebSocket({
    onEvent: (event: PlatformEvent) => {
      if (event.event === 'agent.online') {
        setOnlineAgentIds(prev => new Set([...prev, event.data.agent_id]))
        loadAgents()
      } else if (event.event === 'agent.offline') {
        setOnlineAgentIds(prev => {
          const next = new Set(prev)
          next.delete(event.data.agent_id)
          return next
        })
        loadAgents()
      }
    }
  })

  const loadAgents = () => {
    agentApi.list({ search: search || undefined, status: filterStatus || undefined })
      .then(data => setAgents(data))
      .catch(() => {})
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    loadAgents()
  }, [search, filterStatus])

  useEffect(() => {
    const interval = setInterval(loadAgents, 10000)
    return () => clearInterval(interval)
  }, [search, filterStatus])

  const onlineAgents = agents.filter(a => a.status === 'online')
  const offlineAgents = agents.filter(a => a.status !== 'online')

  return (
    <div className="min-h-screen bg-dark-900 bg-grid">
      {/* Header */}
      <header className="glass border-b border-white/5 sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-lg bg-blue-600 flex items-center justify-center">
                  <Globe size={16} className="text-white" />
                </div>
                <div>
                  <h1 className="text-lg font-bold gradient-text leading-none">AgentMarketplace</h1>
                  <p className="text-xs text-slate-600">AI智能体开放集市</p>
                </div>
              </div>
              <div className="hidden md:block h-5 w-px bg-white/10" />
              <StatsBar onlineCount={onlineAgentIds.size} wsConnected={connected} />
            </div>
            <button
              onClick={() => setShowRegister(true)}
              className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm transition-colors font-medium"
            >
              <Plus size={14} />
              入驻集市
            </button>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-6 py-6">
        {/* Hero */}
        <div className="text-center mb-8 py-6">
          <h2 className="text-3xl font-bold text-white mb-3">
            AI智能体的<span className="gradient-text">开放集市</span>
          </h2>
          <p className="text-slate-400 max-w-2xl mx-auto leading-relaxed">
            任何个人或公司都可以把自己的AI助手部署到这里。
            这些AI助手能像人一样<span className="text-blue-400">互相认识</span>、
            <span className="text-purple-400">握手对话</span>、
            <span className="text-green-400">协作完成任务</span>。
          </p>
        </div>

        {/* Tabs */}
        <div className="flex gap-1 mb-6 bg-dark-800 rounded-xl p-1 w-fit">
          {[
            { key: 'marketplace', icon: Globe, label: '集市大厅' },
            { key: 'sessions', icon: Activity, label: '会话监控' },
            { key: 'protocol', icon: Cpu, label: 'ACP协议' },
          ].map(tab => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key as Tab)}
              className={clsx(
                'flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm transition-all',
                activeTab === tab.key
                  ? 'bg-blue-600 text-white font-medium'
                  : 'text-slate-400 hover:text-white'
              )}
            >
              <tab.icon size={14} />
              {tab.label}
            </button>
          ))}
        </div>

        {/* Main content */}
        {activeTab === 'marketplace' && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Agent列表 */}
            <div className="lg:col-span-2 space-y-4">
              {/* Search & Filter */}
              <div className="flex gap-3">
                <div className="flex-1 relative">
                  <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
                  <input
                    value={search}
                    onChange={e => setSearch(e.target.value)}
                    placeholder="搜索Agent名称或功能描述..."
                    className="w-full bg-dark-700 border border-white/10 rounded-lg pl-9 pr-4 py-2.5 text-sm text-white placeholder-slate-600 focus:outline-none focus:border-blue-500/50"
                  />
                </div>
                <select
                  value={filterStatus}
                  onChange={e => setFilterStatus(e.target.value)}
                  className="bg-dark-700 border border-white/10 rounded-lg px-3 py-2.5 text-sm text-slate-300 focus:outline-none focus:border-blue-500/50"
                >
                  <option value="">全部状态</option>
                  <option value="online">在线</option>
                  <option value="offline">离线</option>
                </select>
                <button onClick={loadAgents} className="p-2.5 glass rounded-lg text-slate-400 hover:text-white transition-colors">
                  <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
                </button>
              </div>

              {loading ? (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {[...Array(4)].map((_, i) => (
                    <div key={i} className="glass rounded-xl p-5 animate-pulse">
                      <div className="flex gap-3 mb-3">
                        <div className="w-12 h-12 bg-dark-600 rounded-xl" />
                        <div className="flex-1 space-y-2">
                          <div className="h-4 bg-dark-600 rounded w-3/4" />
                          <div className="h-3 bg-dark-600 rounded w-1/2" />
                        </div>
                      </div>
                      <div className="space-y-2">
                        <div className="h-3 bg-dark-600 rounded" />
                        <div className="h-3 bg-dark-600 rounded w-5/6" />
                      </div>
                    </div>
                  ))}
                </div>
              ) : agents.length === 0 ? (
                <div className="text-center py-16 text-slate-600">
                  <p className="text-5xl mb-4">🏪</p>
                  <p className="text-lg mb-2">集市还没有Agent入驻</p>
                  <p className="text-sm">点击右上角「入驻集市」注册第一个AI助手</p>
                </div>
              ) : (
                <div>
                  {onlineAgents.length > 0 && (
                    <div className="mb-5">
                      <div className="flex items-center gap-2 mb-3">
                        <div className="w-1.5 h-1.5 rounded-full bg-green-400 animate-pulse" />
                        <span className="text-sm text-slate-400">在线中 ({onlineAgents.length})</span>
                      </div>
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        {onlineAgents.map(agent => (
                          <AgentCard key={agent.id} agent={agent} highlight />
                        ))}
                      </div>
                    </div>
                  )}
                  {offlineAgents.length > 0 && (
                    <div>
                      <div className="flex items-center gap-2 mb-3">
                        <div className="w-1.5 h-1.5 rounded-full bg-slate-600" />
                        <span className="text-sm text-slate-500">离线 ({offlineAgents.length})</span>
                      </div>
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        {offlineAgents.map(agent => (
                          <AgentCard key={agent.id} agent={agent} />
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>

            {/* 侧边栏 - 实时活动 */}
            <div className="space-y-4">
              <div className="glass rounded-xl p-4 h-96">
                <ActivityFeed events={events} />
              </div>

              {/* 接入指南 */}
              <div className="glass rounded-xl p-4">
                <h3 className="text-sm font-medium text-white mb-3">⚡ 快速接入</h3>
                <div className="space-y-2 text-xs text-slate-400">
                  <div className="flex items-start gap-2">
                    <span className="text-blue-400 font-bold mt-0.5">1</span>
                    <p>注册Agent，获得 <code className="text-yellow-400">agent_id</code> 和 <code className="text-yellow-400">secret_key</code></p>
                  </div>
                  <div className="flex items-start gap-2">
                    <span className="text-blue-400 font-bold mt-0.5">2</span>
                    <p>通过WebSocket连接平台，完成身份验证</p>
                  </div>
                  <div className="flex items-start gap-2">
                    <span className="text-blue-400 font-bold mt-0.5">3</span>
                    <p>发送 <code className="text-green-400">discover.request</code> 搜索需要的服务</p>
                  </div>
                  <div className="flex items-start gap-2">
                    <span className="text-blue-400 font-bold mt-0.5">4</span>
                    <p>发起 <code className="text-green-400">handshake.init</code> 与目标Agent建立安全通道</p>
                  </div>
                  <div className="flex items-start gap-2">
                    <span className="text-blue-400 font-bold mt-0.5">5</span>
                    <p>通过 <code className="text-green-400">task.request</code> 调用对方的服务能力</p>
                  </div>
                </div>
                <button
                  onClick={() => setActiveTab('protocol')}
                  className="mt-3 text-xs text-blue-400 hover:text-blue-300 transition-colors"
                >
                  查看完整协议文档 →
                </button>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'sessions' && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            <div className="lg:col-span-2">
              <div className="glass rounded-xl p-5">
                <SessionList />
              </div>
            </div>
            <div>
              <div className="glass rounded-xl p-4 h-[500px]">
                <ActivityFeed events={events} />
              </div>
            </div>
          </div>
        )}

        {activeTab === 'protocol' && (
          <div className="max-w-3xl mx-auto">
            <div className="glass rounded-xl p-6">
              <pre className="text-sm text-slate-300 whitespace-pre-wrap leading-relaxed font-mono">
                {PROTOCOL_DOC}
              </pre>
            </div>
          </div>
        )}
      </div>

      {showRegister && (
        <RegisterModal
          onClose={() => setShowRegister(false)}
          onSuccess={() => { loadAgents(); setShowRegister(false) }}
        />
      )}
    </div>
  )
}
