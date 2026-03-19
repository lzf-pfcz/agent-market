import { useState, useEffect } from 'react'
import { Users, Zap, Activity, Link, TrendingUp, Radio } from 'lucide-react'
import { agentApi } from '../hooks/useApi'
import type { PlatformStats } from '../types'

interface StatsBarProps {
  onlineCount: number
  wsConnected: boolean
}

export function StatsBar({ onlineCount, wsConnected }: StatsBarProps) {
  const [stats, setStats] = useState<PlatformStats>({
    total_agents: 0,
    online_agents: 0,
    active_sessions: 0,
    total_sessions: 0
  })

  useEffect(() => {
    const load = () => agentApi.stats().then(setStats).catch(() => {})
    load()
    const interval = setInterval(load, 5000)
    return () => clearInterval(interval)
  }, [])

  return (
    <div className="flex items-center gap-6 text-sm">
      <div className="flex items-center gap-2">
        <div className={`w-2 h-2 rounded-full ${wsConnected ? 'bg-green-400 animate-pulse' : 'bg-red-400'}`} />
        <span className={wsConnected ? 'text-green-400' : 'text-red-400'}>
          {wsConnected ? '实时监控中' : '连接断开'}
        </span>
      </div>
      <div className="flex items-center gap-1.5 text-slate-400">
        <Users size={14} />
        <span><span className="text-white font-medium">{stats.total_agents}</span> 个Agent</span>
      </div>
      <div className="flex items-center gap-1.5 text-slate-400">
        <Radio size={14} />
        <span><span className="text-green-400 font-medium">{onlineCount || stats.online_agents}</span> 在线</span>
      </div>
      <div className="flex items-center gap-1.5 text-slate-400">
        <Link size={14} />
        <span><span className="text-blue-400 font-medium">{stats.active_sessions}</span> 活跃会话</span>
      </div>
      <div className="flex items-center gap-1.5 text-slate-400">
        <TrendingUp size={14} />
        <span><span className="text-purple-400 font-medium">{stats.total_sessions}</span> 总会话</span>
      </div>
    </div>
  )
}
