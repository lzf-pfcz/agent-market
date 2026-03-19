import { useState } from 'react'
import { X, Plus, Minus } from 'lucide-react'
import { agentApi } from '../hooks/useApi'

interface RegisterModalProps {
  onClose: () => void
  onSuccess: () => void
}

const PRESET_AGENTS = [
  {
    name: '智能客服助手',
    description: '提供7×24小时客户服务，支持问题解答、投诉处理和售后服务',
    owner_name: '客服中心',
    avatar: '💬',
    tags: ['customer-service', 'support', 'chat'],
    capabilities: [
      { name: 'answer_question', description: '回答用户问题', input_schema: {}, output_schema: {} },
      { name: 'handle_complaint', description: '处理投诉', input_schema: {}, output_schema: {} }
    ]
  },
  {
    name: '酒店预订助手',
    description: '查询并预订全球酒店，支持价格比较和特殊要求',
    owner_name: '连锁酒店集团',
    avatar: '🏨',
    tags: ['travel', 'hotel', 'booking'],
    capabilities: [
      { name: 'search_hotels', description: '搜索酒店', input_schema: {}, output_schema: {} },
      { name: 'book_hotel', description: '预订酒店', input_schema: {}, output_schema: {} }
    ]
  },
  {
    name: '天气预报Agent',
    description: '提供全球任意城市的实时天气和未来7天预报',
    owner_name: '气象服务公司',
    avatar: '⛅',
    tags: ['weather', 'forecast', 'data'],
    capabilities: [
      { name: 'get_weather', description: '获取天气', input_schema: {}, output_schema: {} }
    ]
  }
]

export function RegisterModal({ onClose, onSuccess }: RegisterModalProps) {
  const [form, setForm] = useState({
    name: '',
    description: '',
    owner_name: '',
    avatar: '🤖',
    tags: [''],
    capabilities: [{ name: '', description: '' }],
    is_public: true,
  })
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<any>(null)
  const [error, setError] = useState('')

  const fillPreset = (preset: typeof PRESET_AGENTS[0]) => {
    setForm({
      ...preset,
      tags: preset.tags,
      capabilities: preset.capabilities,
      is_public: true
    })
  }

  const handleSubmit = async () => {
    if (!form.name || !form.description || !form.owner_name) {
      setError('请填写必填字段')
      return
    }
    setLoading(true)
    setError('')
    try {
      const data = {
        ...form,
        tags: form.tags.filter(t => t.trim()),
        capabilities: form.capabilities.filter(c => c.name.trim()),
      }
      const res = await agentApi.register(data)
      setResult(res)
    } catch (e: any) {
      setError(e.response?.data?.detail || '注册失败，请检查后端服务')
    } finally {
      setLoading(false)
    }
  }

  if (result) {
    return (
      <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
        <div className="glass rounded-2xl p-6 w-full max-w-md">
          <div className="text-center">
            <div className="text-5xl mb-4">🎉</div>
            <h3 className="text-xl font-bold text-white mb-2">注册成功！</h3>
            <p className="text-slate-400 text-sm mb-6">请保存以下凭证，用于Agent连接平台</p>
          </div>
          <div className="space-y-3 mb-6">
            <div className="bg-dark-700 rounded-lg p-3">
              <p className="text-xs text-slate-500 mb-1">Agent ID</p>
              <p className="text-green-400 font-mono text-sm break-all">{result.agent_id}</p>
            </div>
            <div className="bg-dark-700 rounded-lg p-3">
              <p className="text-xs text-slate-500 mb-1">Secret Key</p>
              <p className="text-yellow-400 font-mono text-sm break-all">{result.secret_key}</p>
            </div>
            <div className="bg-dark-700 rounded-lg p-3">
              <p className="text-xs text-slate-500 mb-1">Access Token</p>
              <p className="text-blue-400 font-mono text-xs break-all">{result.token.slice(0, 60)}...</p>
            </div>
          </div>
          <button
            onClick={() => { onSuccess(); onClose() }}
            className="w-full py-2.5 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors"
          >
            完成
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <div className="glass rounded-2xl w-full max-w-2xl max-h-[90vh] overflow-y-auto">
        <div className="sticky top-0 glass flex items-center justify-between p-5 border-b border-white/10">
          <h2 className="text-lg font-bold text-white">注册新 Agent</h2>
          <button onClick={onClose} className="text-slate-400 hover:text-white transition-colors">
            <X size={20} />
          </button>
        </div>

        <div className="p-5 space-y-5">
          {/* 预设模板 */}
          <div>
            <p className="text-sm text-slate-400 mb-2">快速填入模板：</p>
            <div className="flex flex-wrap gap-2">
              {PRESET_AGENTS.map(p => (
                <button
                  key={p.name}
                  onClick={() => fillPreset(p)}
                  className="text-xs px-3 py-1.5 rounded-lg bg-blue-500/10 text-blue-400 border border-blue-500/20 hover:bg-blue-500/20 transition-colors"
                >
                  {p.avatar} {p.name}
                </button>
              ))}
            </div>
          </div>

          {error && (
            <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-3 text-red-400 text-sm">
              {error}
            </div>
          )}

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs text-slate-400 mb-1.5">Agent名称 *</label>
              <input
                value={form.name}
                onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
                placeholder="如: 航空订票助手"
                className="w-full bg-dark-700 border border-white/10 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-600 focus:outline-none focus:border-blue-500/50"
              />
            </div>
            <div>
              <label className="block text-xs text-slate-400 mb-1.5">所有者 *</label>
              <input
                value={form.owner_name}
                onChange={e => setForm(f => ({ ...f, owner_name: e.target.value }))}
                placeholder="公司/个人名称"
                className="w-full bg-dark-700 border border-white/10 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-600 focus:outline-none focus:border-blue-500/50"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs text-slate-400 mb-1.5">功能描述 * (Agent的"招牌")</label>
            <textarea
              value={form.description}
              onChange={e => setForm(f => ({ ...f, description: e.target.value }))}
              placeholder="描述这个Agent能做什么..."
              rows={3}
              className="w-full bg-dark-700 border border-white/10 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-600 focus:outline-none focus:border-blue-500/50 resize-none"
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs text-slate-400 mb-1.5">头像 Emoji</label>
              <input
                value={form.avatar}
                onChange={e => setForm(f => ({ ...f, avatar: e.target.value }))}
                placeholder="🤖"
                className="w-full bg-dark-700 border border-white/10 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-600 focus:outline-none focus:border-blue-500/50"
              />
            </div>
            <div className="flex items-end pb-0.5">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={form.is_public}
                  onChange={e => setForm(f => ({ ...f, is_public: e.target.checked }))}
                  className="w-4 h-4 rounded"
                />
                <span className="text-sm text-slate-300">公开发布到集市</span>
              </label>
            </div>
          </div>

          {/* 标签 */}
          <div>
            <label className="block text-xs text-slate-400 mb-1.5">服务标签</label>
            <div className="space-y-2">
              {form.tags.map((tag, i) => (
                <div key={i} className="flex gap-2">
                  <input
                    value={tag}
                    onChange={e => {
                      const tags = [...form.tags]
                      tags[i] = e.target.value
                      setForm(f => ({ ...f, tags }))
                    }}
                    placeholder="如: booking, travel"
                    className="flex-1 bg-dark-700 border border-white/10 rounded-lg px-3 py-2 text-sm text-white placeholder-slate-600 focus:outline-none focus:border-blue-500/50"
                  />
                  <button
                    onClick={() => setForm(f => ({ ...f, tags: f.tags.filter((_, j) => j !== i) }))}
                    className="p-2 text-slate-500 hover:text-red-400 transition-colors"
                  >
                    <Minus size={14} />
                  </button>
                </div>
              ))}
              <button
                onClick={() => setForm(f => ({ ...f, tags: [...f.tags, ''] }))}
                className="flex items-center gap-1 text-xs text-blue-400 hover:text-blue-300 transition-colors"
              >
                <Plus size={12} /> 添加标签
              </button>
            </div>
          </div>

          {/* 能力 */}
          <div>
            <label className="block text-xs text-slate-400 mb-1.5">服务能力</label>
            <div className="space-y-3">
              {form.capabilities.map((cap, i) => (
                <div key={i} className="bg-dark-700/50 rounded-lg p-3 border border-white/5">
                  <div className="flex gap-2 mb-2">
                    <input
                      value={cap.name}
                      onChange={e => {
                        const caps = [...form.capabilities]
                        caps[i] = { ...caps[i], name: e.target.value }
                        setForm(f => ({ ...f, capabilities: caps }))
                      }}
                      placeholder="能力标识符 (如: book_flight)"
                      className="flex-1 bg-dark-800 border border-white/10 rounded-lg px-3 py-1.5 text-sm text-white placeholder-slate-600 focus:outline-none focus:border-blue-500/50"
                    />
                    <button
                      onClick={() => setForm(f => ({ ...f, capabilities: f.capabilities.filter((_, j) => j !== i) }))}
                      className="p-1.5 text-slate-500 hover:text-red-400 transition-colors"
                    >
                      <Minus size={14} />
                    </button>
                  </div>
                  <input
                    value={cap.description}
                    onChange={e => {
                      const caps = [...form.capabilities]
                      caps[i] = { ...caps[i], description: e.target.value }
                      setForm(f => ({ ...f, capabilities: caps }))
                    }}
                    placeholder="能力描述"
                    className="w-full bg-dark-800 border border-white/10 rounded-lg px-3 py-1.5 text-sm text-white placeholder-slate-600 focus:outline-none focus:border-blue-500/50"
                  />
                </div>
              ))}
              <button
                onClick={() => setForm(f => ({ ...f, capabilities: [...f.capabilities, { name: '', description: '' }] }))}
                className="flex items-center gap-1 text-xs text-blue-400 hover:text-blue-300 transition-colors"
              >
                <Plus size={12} /> 添加能力
              </button>
            </div>
          </div>
        </div>

        <div className="sticky bottom-0 glass p-4 border-t border-white/10 flex gap-3">
          <button
            onClick={onClose}
            className="flex-1 py-2.5 border border-white/10 text-slate-400 rounded-lg hover:text-white transition-colors"
          >
            取消
          </button>
          <button
            onClick={handleSubmit}
            disabled={loading}
            className="flex-1 py-2.5 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-600/50 text-white rounded-lg transition-colors font-medium"
          >
            {loading ? '注册中...' : '注册到集市'}
          </button>
        </div>
      </div>
    </div>
  )
}
