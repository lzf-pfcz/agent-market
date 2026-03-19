import type { Agent } from '../types'
import { Cpu, Tag, Star, BarChart2 } from 'lucide-react'
import clsx from 'clsx'

interface AgentCardProps {
  agent: Agent
  onClick?: () => void
  highlight?: boolean
}

const STATUS_CONFIG = {
  online: { dot: 'status-dot-online', text: 'text-green-400', label: '在线' },
  offline: { dot: 'status-dot-offline', text: 'text-slate-500', label: '离线' },
  busy: { dot: 'status-dot-busy', text: 'text-yellow-400', label: '忙碌' },
}

export function AgentCard({ agent, onClick, highlight }: AgentCardProps) {
  const status = STATUS_CONFIG[agent.status] || STATUS_CONFIG.offline
  const successRate = agent.total_calls > 0
    ? Math.round((agent.success_calls / agent.total_calls) * 100)
    : null

  return (
    <div
      className={clsx(
        'glass agent-card-glow rounded-xl p-5 cursor-pointer transition-all duration-300',
        highlight && 'border-blue-500/50 shadow-blue-500/20 shadow-lg'
      )}
      onClick={onClick}
    >
      {/* Header */}
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-3">
          <div className="text-3xl w-12 h-12 flex items-center justify-center rounded-xl bg-dark-600 border border-white/5">
            {agent.avatar || '🤖'}
          </div>
          <div>
            <h3 className="font-semibold text-white text-base leading-tight">{agent.name}</h3>
            <p className="text-xs text-slate-500 mt-0.5">{agent.owner_name}</p>
          </div>
        </div>
        <div className="flex items-center gap-1.5 mt-1">
          <div className={clsx('w-1.5 h-1.5 rounded-full', status.dot)} />
          <span className={clsx('text-xs font-medium', status.text)}>{status.label}</span>
        </div>
      </div>

      {/* Description */}
      <p className="text-sm text-slate-400 mb-3 line-clamp-2 leading-relaxed">{agent.description}</p>

      {/* Tags */}
      {agent.tags.length > 0 && (
        <div className="flex flex-wrap gap-1.5 mb-3">
          {agent.tags.slice(0, 4).map(tag => (
            <span
              key={tag}
              className="text-xs px-2 py-0.5 rounded-full bg-blue-500/10 text-blue-400 border border-blue-500/20"
            >
              {tag}
            </span>
          ))}
          {agent.tags.length > 4 && (
            <span className="text-xs px-2 py-0.5 rounded-full bg-slate-700 text-slate-400">
              +{agent.tags.length - 4}
            </span>
          )}
        </div>
      )}

      {/* Capabilities count */}
      <div className="flex items-center justify-between pt-3 border-t border-white/5">
        <div className="flex items-center gap-1.5 text-xs text-slate-500">
          <Cpu size={12} />
          <span>{agent.capabilities.length} 项能力</span>
        </div>
        {successRate !== null && (
          <div className="flex items-center gap-1.5 text-xs text-slate-500">
            <BarChart2 size={12} />
            <span>{successRate}% 成功率</span>
          </div>
        )}
        <div className="text-xs text-slate-600">
          {agent.total_calls > 0 ? `${agent.total_calls} 次调用` : '暂无记录'}
        </div>
      </div>
    </div>
  )
}
