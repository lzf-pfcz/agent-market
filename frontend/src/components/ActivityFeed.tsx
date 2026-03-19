import { useEffect, useRef } from 'react'
import type { PlatformEvent } from '../types'
import clsx from 'clsx'

interface ActivityFeedProps {
  events: (PlatformEvent & { ts: string })[]
}

const EVENT_ICONS: Record<string, string> = {
  'agent.online': '🟢',
  'agent.offline': '🔴',
  'handshake': '🤝',
  'task': '⚡',
  'activity': '📝',
}

const EVENT_COLORS: Record<string, string> = {
  'agent.online': 'text-green-400',
  'agent.offline': 'text-red-400',
  'handshake': 'text-blue-400',
  'task': 'text-yellow-400',
  'activity': 'text-slate-300',
}

function getEventDescription(event: PlatformEvent): string {
  const { data } = event
  switch (event.event) {
    case 'agent.online': return `${data.name} 已上线`
    case 'agent.offline': return `${data.name} 已下线`
    case 'handshake':
      if (data.status === 'initiating') return `${data.initiator} → ${data.responder}: 发起握手`
      if (data.status === 'established') return `${data.initiator} ↔ ${data.responder}: 握手成功！安全通道建立`
      if (data.status === 'rejected') return `${data.initiator} × ${data.responder}: 握手被拒绝`
      return `握手状态: ${data.status}`
    case 'task':
      if (data.task_type === 'request') return `${data.from} → ${data.to}: ${data.detail}`
      if (data.task_type === 'result') return `${data.from} → ${data.to}: 任务完成`
      return `${data.from} → ${data.to}: ${data.detail}`
    case 'activity': return data.description || ''
    default: return JSON.stringify(data).slice(0, 60)
  }
}

export function ActivityFeed({ events }: ActivityFeedProps) {
  const feedRef = useRef<HTMLDivElement>(null)

  return (
    <div className="h-full flex flex-col">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-medium text-slate-300">实时活动流</h3>
        <span className="text-xs text-slate-600">{events.length} 条记录</span>
      </div>
      <div ref={feedRef} className="flex-1 overflow-y-auto space-y-1.5 pr-1">
        {events.length === 0 ? (
          <div className="text-center text-slate-600 text-sm py-8">
            等待平台事件...
          </div>
        ) : (
          events.map((event, i) => (
            <div
              key={i}
              className={clsx(
                'flex items-start gap-2 p-2 rounded-lg text-xs',
                'bg-white/2 hover:bg-white/4 transition-colors',
                i === 0 && 'session-arrow'
              )}
            >
              <span className="text-base leading-none mt-0.5 flex-shrink-0">
                {EVENT_ICONS[event.event] || '📌'}
              </span>
              <div className="flex-1 min-w-0">
                <p className={clsx('leading-relaxed', EVENT_COLORS[event.event] || 'text-slate-300')}>
                  {getEventDescription(event)}
                </p>
              </div>
              <span className="text-slate-600 flex-shrink-0">{event.ts}</span>
            </div>
          ))
        )}
      </div>
    </div>
  )
}
