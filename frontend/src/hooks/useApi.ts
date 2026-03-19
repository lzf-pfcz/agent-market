import axios from 'axios'
import type { Agent, Session, ActivityLog, PlatformStats } from '../types'

const api = axios.create({
  baseURL: 'http://localhost:8000',
  timeout: 10000,
})

export const agentApi = {
  list: (params?: { search?: string; tag?: string; status?: string }) =>
    api.get<Agent[]>('/api/agents/', { params }).then(r => r.data),

  get: (id: string) =>
    api.get<Agent>(`/api/agents/${id}`).then(r => r.data),

  register: (data: {
    name: string
    description: string
    owner_name: string
    avatar?: string
    tags: string[]
    capabilities: any[]
    is_public: boolean
  }) => api.post('/api/agents/register', data).then(r => r.data),

  discover: (query: string) =>
    api.get('/api/agents/discover/search', { params: { query } }).then(r => r.data),

  stats: () =>
    api.get<PlatformStats>('/api/agents/stats/overview').then(r => r.data),
}

export const sessionApi = {
  list: () =>
    api.get<Session[]>('/sessions/list').then(r => r.data),
}

export const activityApi = {
  logs: (limit = 50) =>
    api.get<ActivityLog[]>('/activity/logs', { params: { limit } }).then(r => r.data),
}

export default api
