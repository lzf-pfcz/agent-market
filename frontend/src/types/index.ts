// Agent类型定义
export interface AgentCapability {
  name: string
  description: string
  input_schema?: Record<string, any>
  output_schema?: Record<string, any>
  examples?: any[]
}

export interface Agent {
  id: string
  name: string
  description: string
  owner_name: string
  avatar?: string
  tags: string[]
  capabilities: AgentCapability[]
  status: 'online' | 'offline' | 'busy'
  is_public: boolean
  total_calls: number
  success_calls: number
  created_at: string
}

export interface Session {
  id: string
  initiator_id: string
  responder_id: string
  status: 'pending' | 'established' | 'closed' | 'failed'
  created_at: string | null
  established_at: string | null
  closed_at: string | null
}

export interface ActivityLog {
  id: number
  event_type: string
  agent_id: string | null
  target_agent_id: string | null
  description: string
  metadata: Record<string, any> | null
  created_at: string | null
}

export interface PlatformStats {
  total_agents: number
  online_agents: number
  active_sessions: number
  total_sessions: number
}

// WebSocket事件类型
export interface PlatformEvent {
  event: string
  data: Record<string, any>
}
