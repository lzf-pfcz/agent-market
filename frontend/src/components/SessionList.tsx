import { useState, useEffect } from 'react'
import { sessionApi } from '../hooks/useApi'
import type { Session } from '../types'
import { ArrowRight, CheckCircle, XCircle, Clock, RefreshCw } from 'lucide-react'
import clsx from 'clsx'

const STATUS_CONFIG = {
  pending: { icon: Clock, color: 'text-yellow-400', bg: 'bg-yellow-400/10', label: '待建立' },
  established: { icon: CheckCircle, color: 'text-green-400', bg: 'bg-green-400/10', label: '已建立' },
  closed: { icon: CheckCircle, color: 'text-slate-400', bg: 'bg-slate-400/10', label: '已关闭' },
  failed: { icon: XCircle, color: 'text-red-400', bg: 'bg-red-400/10', label: '失败' },
}

export function SessionList() {
  const [sessions, setSessions] = useState<Session[]>([])
  const [loading, setLoading] = useState(true)

  const load = () => {
    setLoading(true)
    sessionApi.list()
      .then(setSessions)
      .catch(() => {})
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    load()
    const interval = setInterval(load, 5000)
    return () => clearInterval(interval)
  }, [])

  const formatTime = (t: string | null) => {
    if (!t) return '-'
    return new Date(t).toLocaleString('zh-CN', { 
      month: 'numeric', day: 'numeric',
      hour: '2-digit', minute: '2-digit', second: '2-digit'
    })
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-base font-semibold text-white">握手会话记录</h2>
        <button onClick={load} className="text-slate-400 hover:text-white transition-colors">
          <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
        </button>
      </div>

      {sessions.length === 0 ? (
        <div className="text-center py-12 text-slate-600">
          <p className="text-4xl mb-3">🤝</p>
          <p>还没有Agent之间的握手记录</p>
          <p className="text-sm mt-1">当Agent连接到平台并相互握手时，这里会显示记录</p>
        </div>
      ) : (
        <div className="space-y-3">
          {sessions.map(session => {
            const config = STATUS_CONFIG[session.status] || STATUS_CONFIG.pending
            const Icon = config.icon
            return (
              <div key={session.id} className="glass rounded-xl p-4">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-3">
                    <code className="text-xs text-slate-600 font-mono">{session.id.slice(0, 8)}...</code>
                    <span className={clsx('flex items-center gap-1 text-xs px-2 py-0.5 rounded-full', config.color, config.bg)}>
                      <Icon size={10} />
                      {config.label}
                    </span>
                  </div>
                  <span className="text-xs text-slate-600">{formatTime(session.created_at)}</span>
                </div>
                <div className="flex items-center gap-2 text-sm">
                  <code className="text-blue-400 font-mono text-xs">{session.initiator_id.slice(0, 12)}...</code>
                  <ArrowRight size={14} className="text-slate-600" />
                  <code className="text-purple-400 font-mono text-xs">{session.responder_id.slice(0, 12)}...</code>
                </div>
                {session.established_at && (
                  <p className="text-xs text-slate-600 mt-1">
                    建立时间: {formatTime(session.established_at)}
                    {session.closed_at && ` | 关闭: ${formatTime(session.closed_at)}`}
                  </p>
                )}
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
