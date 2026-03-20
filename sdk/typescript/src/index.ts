/**
 * AgentMarketplace TypeScript SDK
 * 让开发者快速接入AI智能体平台
 * 
 * 使用示例:
 * ```typescript
 * import { Agent } from '@agent-marketplace/sdk';
 * 
 * const agent = new Agent({
 *   name: '航班助手',
 *   description: '提供航班查询服务',
 *   platformUrl: 'ws://localhost:8000/ws/agent'
 * });
 * 
 * agent.on('task', async (task) => {
 *   console.log('收到任务:', task);
 *   return { result: '任务已完成' };
 * });
 * 
 * await agent.connect();
 * ```
 */

import WebSocket from 'ws';

// ==================== 类型定义 ====================

export interface AgentConfig {
  /** Agent名称 */
  name: string;
  /** Agent描述 */
  description: string;
  /** 平台WebSocket地址 */
  platformUrl: string;
  /** 平台API地址 */
  apiUrl?: string;
  /** Agent ID (注册后获得) */
  agentId?: string;
  /** 认证Token */
  token?: string;
  /** 重连间隔(毫秒) */
  reconnectInterval?: number;
  /** 心跳间隔(毫秒) */
  heartbeatInterval?: number;
  /** 日志级别 */
  logLevel?: 'debug' | 'info' | 'warn' | 'error';
}

export interface Capability {
  name: string;
  description: string;
  inputSchema?: Record<string, any>;
  outputSchema?: Record<string, any>;
}

export interface Task {
  taskId: string;
  sessionId: string;
  fromAgent: string;
  payload: Record<string, any>;
}

export interface TaskResult {
  taskId: string;
  status: 'success' | 'error' | 'progress';
  result?: any;
  error?: string;
  progress?: number;
}

export interface RegisterResult {
  agentId: string;
  secretKey: string;
  token: string;
}

// ==================== 消息类型 ====================

export enum MessageType {
  // 会话
  SESSION_OPEN = 'session.open',
  SESSION_CLOSE = 'session.close',
  SESSION_HEARTBEAT = 'session.heartbeat',
  
  // 握手
  HANDSHAKE_INIT = 'handshake.init',
  HANDSHAKE_CHALLENGE = 'handshake.challenge',
  HANDSHAKE_RESPONSE = 'handshake.response',
  HANDSHAKE_ACK = 'handshake.ack',
  HANDSHAKE_REJECT = 'handshake.reject',
  
  // 发现
  DISCOVER_REQUEST = 'discover.request',
  DISCOVER_RESPONSE = 'discover.response',
  
  // 任务
  TASK_REQUEST = 'task.request',
  TASK_ACK = 'task.ack',
  TASK_PROGRESS = 'task.progress',
  TASK_RESULT = 'task.result',
  TASK_ERROR = 'task.error',
  
  // 系统
  SYSTEM_ERROR = 'system.error',
}

export interface ACPMessage {
  id?: string;
  type: string;
  protocol_version?: string;
  timestamp?: string;
  from_agent?: string;
  to_agent?: string;
  session_id?: string;
  payload?: Record<string, any>;
  metadata?: Record<string, any>;
}

// ==================== Agent 类 ====================

export class Agent {
  private config: Required<AgentConfig>;
  private ws: WebSocket | null = null;
  private connected: boolean = false;
  private sessionId: string | null = null;
  private reconnectTimer: NodeJS.Timeout | null = null;
  private heartbeatTimer: NodeJS.Timeout | null = null;
  private taskHandlers: Map<string, (task: Task) => Promise<any>> = new Map();
  private messageHandlers: Map<string, (msg: ACPMessage) => void> = new Map();
  
  constructor(config: AgentConfig) {
    this.config = {
      name: config.name,
      description: config.description,
      platformUrl: config.platformUrl,
      apiUrl: config.apiUrl || 'http://localhost:8000',
      agentId: config.agentId || '',
      token: config.token || '',
      reconnectInterval: config.reconnectInterval || 5000,
      heartbeatInterval: config.heartbeatInterval || 30000,
      logLevel: config.logLevel || 'info',
    };
  }
  
  // ==================== 公共方法 ====================
  
  /**
   * 连接到平台
   */
  async connect(): Promise<void> {
    if (this.connected) {
      this.warn('已经连接');
      return;
    }
    
    if (!this.config.agentId || !this.config.token) {
      throw new Error('请先注册Agent并获取 agentId 和 token');
    }
    
    return new Promise((resolve, reject) => {
      const url = `${this.config.platformUrl}/${this.config.agentId}?token=${this.config.token}`;
      this.info(`连接到: ${url}`);
      
      this.ws = new WebSocket(url);
      
      this.ws.on('open', () => {
        this.connected = true;
        this.info('✓ 连接成功');
        this.startHeartbeat();
        resolve();
      });
      
      this.ws.on('message', (data) => {
        this.handleMessage(data.toString());
      });
      
      this.ws.on('close', () => {
        this.connected = false;
        this.info('连接已关闭');
        this.stopHeartbeat();
        this.scheduleReconnect();
      });
      
      this.ws.on('error', (error) => {
        this.error('连接错误:', error.message);
        reject(error);
      });
    });
  }
  
  /**
   * 断开连接
   */
  disconnect(): void {
    this.stopReconnect();
    this.stopHeartbeat();
    
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    this.connected = false;
  }
  
  /**
   * 注册Agent到平台
   */
  async register(): Promise<RegisterResult> {
    const url = `${this.config.apiUrl}/api/agents/register`;
    this.info(`注册Agent: ${this.config.name}`);
    
    const response = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        name: this.config.name,
        description: this.config.description,
        owner_name: this.config.name, // 可改为实际所有者名
        tags: [],
        capabilities: []
      })
    });
    
    if (!response.ok) {
      throw new Error(`注册失败: ${response.statusText}`);
    }
    
    const result: RegisterResult = await response.json();
    
    this.config.agentId = result.agentId;
    this.config.token = result.token;
    
    this.info(`✓ 注册成功! AgentID: ${result.agentId}`);
    this.info(`⚠️ 请保存 secretKey: ${result.secretKey.substring(0, 8)}... (仅显示一次)`);
    
    return result;
  }
  
  /**
   * 发送任务结果
   */
  async sendResult(sessionId: string, taskId: string, result: any): Promise<void> {
    const msg: ACPMessage = {
      type: MessageType.TASK_RESULT,
      from_agent: this.config.agentId,
      session_id: sessionId,
      payload: {
        task_id: taskId,
        result
      }
    };
    
    await this.send(msg);
  }
  
  /**
   * 发送任务进度
   */
  async sendProgress(sessionId: string, taskId: string, progress: number, message?: string): Promise<void> {
    const msg: ACPMessage = {
      type: MessageType.TASK_PROGRESS,
      from_agent: this.config.agentId,
      session_id: sessionId,
      payload: {
        task_id: taskId,
        progress,
        message
      }
    };
    
    await this.send(msg);
  }
  
  /**
   * 发送错误
   */
  async sendError(sessionId: string, taskId: string, error: string): Promise<void> {
    const msg: ACPMessage = {
      type: MessageType.TASK_ERROR,
      from_agent: this.config.agentId,
      session_id: sessionId,
      payload: {
        task_id: taskId,
        error
      }
    };
    
    await this.send(msg);
  }
  
  // ==================== 事件处理 ====================
  
  /**
   * 注册任务处理器
   */
  onTask(handler: (task: Task) => Promise<any>): void {
    this.taskHandlers.set('default', handler);
  }
  
  /**
   * 注册消息处理器
   */
  on(type: string, handler: (msg: ACPMessage) => void): void {
    this.messageHandlers.set(type, handler);
  }
  
  /**
   * 移除消息处理器
   */
  off(type: string): void {
    this.messageHandlers.delete(type);
  }
  
  // ==================== 私有方法 ====================
  
  private async send(msg: ACPMessage): Promise<void> {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      throw new Error('未连接');
    }
    
    msg.id = msg.id || this.generateId();
    msg.protocol_version = msg.protocol_version || '1.0';
    msg.timestamp = msg.timestamp || new Date().toISOString();
    msg.from_agent = msg.from_agent || this.config.agentId;
    
    this.ws.send(JSON.stringify(msg));
  }
  
  private handleMessage(data: string): void {
    try {
      const msg: ACPMessage = JSON.parse(data);
      this.debug(`收到消息: ${msg.type}`);
      
      // 触发消息事件
      const handler = this.messageHandlers.get(msg.type);
      if (handler) {
        handler(msg);
      }
      
      // 处理任务请求
      if (msg.type === MessageType.TASK_REQUEST) {
        this.handleTask(msg);
      }
      
      // 处理会话打开
      if (msg.type === MessageType.SESSION_OPEN) {
        this.sessionId = msg.payload?.session_id || null;
        this.info('✓ 会话已建立');
      }
      
      // 处理错误
      if (msg.type === MessageType.SYSTEM_ERROR) {
        this.error('系统错误:', msg.payload);
      }
      
    } catch (e) {
      this.error('解析消息失败:', e);
    }
  }
  
  private async handleTask(msg: ACPMessage): Promise<void> {
    const task: Task = {
      taskId: msg.payload?.task_id || '',
      sessionId: msg.session_id || '',
      fromAgent: msg.from_agent || '',
      payload: msg.payload || {}
    };
    
    this.info(`收到任务: ${task.taskId}`);
    
    // 发送确认
    await this.send({
      type: MessageType.TASK_ACK,
      session_id: task.sessionId,
      payload: { task_id: task.taskId, status: 'accepted' }
    });
    
    // 执行任务处理
    const handler = this.taskHandlers.get('default');
    if (handler) {
      try {
        const result = await handler(task);
        await this.sendResult(task.sessionId, task.taskId, result);
        this.info(`任务完成: ${task.taskId}`);
      } catch (e: any) {
        await this.sendError(task.sessionId, task.taskId, e.message);
        this.error(`任务失败: ${task.taskId}`, e.message);
      }
    } else {
      await this.sendError(task.sessionId, task.taskId, '未注册任务处理器');
    }
  }
  
  private startHeartbeat(): void {
    this.heartbeatTimer = setInterval(async () => {
      if (this.connected) {
        await this.send({
          type: MessageType.SESSION_HEARTBEAT,
          from_agent: this.config.agentId
        });
        this.debug('心跳');
      }
    }, this.config.heartbeatInterval);
  }
  
  private stopHeartbeat(): void {
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer);
      this.heartbeatTimer = null;
    }
  }
  
  private scheduleReconnect(): void {
    if (this.reconnectTimer) return;
    
    this.info(`将在 ${this.config.reconnectInterval}ms 后重连...`);
    this.reconnectTimer = setTimeout(async () => {
      this.reconnectTimer = null;
      try {
        await this.connect();
      } catch (e) {
        // 连接失败会自动重试
      }
    }, this.config.reconnectInterval);
  }
  
  private stopReconnect(): void {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
  }
  
  private generateId(): string {
    return `${Date.now()}-${Math.random().toString(36).substring(2, 11)}`;
  }
  
  // ==================== 日志 ====================
  
  private log(level: string, ...args: any[]): void {
    const prefix = `[${new Date().toISOString()}] [${level.toUpperCase()}]`;
    console[level as keyof Console](prefix, ...args);
  }
  
  private debug(...args: any[]): void {
    if (this.config.logLevel === 'debug') this.log('debug', ...args);
  }
  
  private info(...args: any[]): void {
    if (['debug', 'info'].includes(this.config.logLevel)) this.log('info', ...args);
  }
  
  private warn(...args: any[]): void {
    if (['debug', 'info', 'warn'].includes(this.config.logLevel)) this.log('warn', ...args);
  }
  
  private error(...args: any[]): void {
    this.log('error', ...args);
  }
}

export default Agent;
