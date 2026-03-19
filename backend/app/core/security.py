"""
安全模块 - 认证、授权、加密
Agent Marketplace V2 - 增强安全版本
"""
from datetime import datetime, timedelta
from typing import Optional, Set
from jose import JWTError, jwt, ExpiredSignatureError
from passlib.context import CryptContext
from app.core.config import settings
import secrets
import hashlib
import base64
import json
import logging

logger = logging.getLogger(__name__)

# 密码加密上下文
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# 内存存储（开发环境）
# 生产环境应使用 Redis，详见 get_token_blacklist() 和 get_rate_limiter()
_token_blacklist: Set[str] = set()


# ==================== Redis 集成 ====================

def _get_redis_client():
    """获取Redis客户端（如果配置了）"""
    try:
        import redis.asyncio as redis
        redis_url = settings.get_redis_url()
        if redis_url:
            return redis.from_url(redis_url, decode_responses=True)
    except Exception as e:
        logger.warning(f"Redis not available: {e}")
    return None


# ==================== Token 黑名单 ====================

async def add_to_blacklist(token: str, ttl: int = None) -> bool:
    """
    添加令牌到黑名单
    
    Args:
        token: 要撤销的令牌
        ttl: 过期时间（秒），默认使用令牌的剩余有效期
    """
    redis_client = _get_redis_client()
    
    if redis_client:
        try:
            # 使用令牌的剩余时间作为TTL
            if ttl is None:
                ttl = 60 * 60 * 24 * 7  # 默认7天
            
            await redis_client.setex(
                f"blacklist:{token[:64]}",  # 截断以节省空间
                ttl,
                "1"
            )
            logger.info(f"Token added to Redis blacklist")
            return True
        except Exception as e:
            logger.error(f"Failed to add token to Redis blacklist: {e}")
    
    # 降级到内存存储
    _token_blacklist.add(token)
    return True


async def is_token_blacklisted(token: str) -> bool:
    """检查令牌是否已撤销"""
    redis_client = _get_redis_client()
    
    if redis_client:
        try:
            result = await redis_client.exists(f"blacklist:{token[:64]}")
            return result > 0
        except Exception as e:
            logger.error(f"Failed to check Redis blacklist: {e}")
    
    # 降级到内存存储
    return token in _token_blacklist


def revoke_token(token: str) -> bool:
    """
    撤销令牌（同步版本，兼容旧代码）
    
    注意：生产环境应使用异步版本 add_to_blacklist()
    """
    _token_blacklist.add(token)
    return True


def is_token_revoked(token: str) -> bool:
    """检查令牌是否已撤销（同步版本）"""
    return token in _token_blacklist


# ==================== 密码相关 ====================

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """密码哈希"""
    return pwd_context.hash(password)


# ==================== JWT令牌 ====================

def create_access_token(
    data: dict, 
    expires_delta: Optional[timedelta] = None,
    token_type: str = "access"
) -> str:
    """
    创建访问令牌
    
    Args:
        data: 要编码的数据
        expires_delta: 过期时间增量
        token_type: 令牌类型 (access | refresh)
    """
    to_encode = data.copy()
    
    # 根据类型设置不同的过期时间
    if token_type == "refresh":
        expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    else:
        expire = datetime.utcnow() + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    
    to_encode.update({
        "exp": expire,
        "type": token_type,
        "iat": datetime.utcnow()
    })
    
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_token_pair(agent_id: str) -> dict:
    """
    创建令牌对 (access + refresh)
    
    Returns:
        {"access_token": "...", "refresh_token": "...", "expires_in": ...}
    """
    access_token = create_access_token(
        {"sub": agent_id, "type": "access"},
        token_type="access"
    )
    
    refresh_token = create_access_token(
        {"sub": agent_id, "type": "refresh"},
        token_type="refresh"
    )
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "Bearer",
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    }


async def decode_token_async(token: str) -> Optional[dict]:
    """异步解码令牌（支持Redis黑名单）"""
    try:
        payload = jwt.decode(
            token, 
            settings.SECRET_KEY, 
            algorithms=[settings.ALGORITHM]
        )
        
        # 异步检查黑名单
        if await is_token_blacklisted(token):
            logger.warning(f"Token in blacklist: {token[:20]}...")
            return None
        
        return payload
        
    except ExpiredSignatureError:
        logger.warning("Token expired")
        return None
    except JWTError as e:
        logger.warning(f"Token decode error: {e}")
        return None


def decode_token(token: str) -> Optional[dict]:
    """
    解码令牌（同步版本）
    
    注意：生产环境应使用异步版本 decode_token_async()
    """
    try:
        payload = jwt.decode(
            token, 
            settings.SECRET_KEY, 
            algorithms=[settings.ALGORITHM]
        )
        
        # 检查黑名单
        if token in _token_blacklist:
            logger.warning(f"Token in blacklist: {token[:20]}...")
            return None
        
        return payload
        
    except ExpiredSignatureError:
        logger.warning("Token expired")
        return None
    except JWTError as e:
        logger.warning(f"Token decode error: {e}")
        return None


def refresh_access_token(refresh_token: str) -> Optional[dict]:
    """
    刷新访问令牌
    
    Args:
        refresh_token: 刷新令牌
        
    Returns:
        新的令牌对 或 None
    """
    payload = decode_token(refresh_token)
    
    if not payload or payload.get("type") != "refresh":
        return None
    
    agent_id = payload.get("sub")
    if not agent_id:
        return None
    
    # 生成新令牌对
    return create_token_pair(agent_id)


# ==================== Agent认证 ====================

def generate_agent_token(agent_id: str) -> str:
    """生成Agent身份令牌"""
    return create_access_token({"sub": agent_id, "type": "agent"})


def verify_agent_token(token: str, expected_agent_id: str) -> bool:
    """
    验证Agent令牌
    
    Args:
        token: 待验证的令牌
        expected_agent_id: 期望的Agent ID
        
    Returns:
        是否有效
    """
    payload = decode_token(token)
    if not payload:
        return False
    
    # 验证类型和Agent ID
    if payload.get("type") != "agent":
        return False
    
    if payload.get("sub") != expected_agent_id:
        return False
    
    return True


# ==================== 握手挑战 ====================

def generate_challenge() -> str:
    """生成握手挑战码"""
    return secrets.token_hex(32)


def verify_challenge_response(challenge: str, agent_secret: str, response: str) -> bool:
    """验证握手挑战响应"""
    expected = hashlib.sha256(f"{challenge}{agent_secret}".encode()).hexdigest()
    return secrets.compare_digest(expected, response)


def compute_challenge_response(challenge: str, agent_secret: str) -> str:
    """计算挑战响应"""
    return hashlib.sha256(f"{challenge}{agent_secret}".encode()).hexdigest()


# ==================== 消息级加密 (AES-GCM) ====================

def generate_encryption_key() -> bytes:
    """生成加密密钥 (32 bytes for AES-256)"""
    return secrets.token_bytes(32)


def encrypt_message(plaintext: str, key: bytes) -> dict:
    """
    使用AES-GCM加密消息
    
    Args:
        plaintext: 明文
        key: 加密密钥 (32 bytes)
        
    Returns:
        {
            "ciphertext": "base64...",
            "nonce": "base64...",
            "tag": "base64..."
        }
    """
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    
    nonce = secrets.token_bytes(12)  # 96-bit nonce for GCM
    aesgcm = AESGCM(key)
    
    ciphertext = aesgcm.encrypt(nonce, plaintext.encode('utf-8'), None)
    
    # 分离 ciphertext 和 tag (最后16字节是tag)
    actual_ciphertext = ciphertext[:-16]
    tag = ciphertext[-16:]
    
    return {
        "ciphertext": base64.b64encode(actual_ciphertext).decode('utf-8'),
        "nonce": base64.b64encode(nonce).decode('utf-8'),
        "tag": base64.b64encode(tag).decode('utf-8')
    }


def decrypt_message(encrypted: dict, key: bytes) -> Optional[str]:
    """
    使用AES-GCM解密消息
    
    Args:
        encrypted: 加密的字典
        key: 解密密钥
        
    Returns:
        明文 或 None
    """
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    
    try:
        ciphertext = base64.b64decode(encrypted["ciphertext"])
        nonce = base64.b64decode(encrypted["nonce"])
        tag = base64.b64decode(encrypted["tag"])
        
        # 合并 ciphertext 和 tag
        ciphertext_with_tag = ciphertext + tag
        
        aesgcm = AESGCM(key)
        plaintext = aesgcm.decrypt(nonce, ciphertext_with_tag, None)
        
        return plaintext.decode('utf-8')
        
    except Exception as e:
        logger.error(f"Decryption failed: {e}")
        return None


def wrap_encrypted_payload(payload: dict, key: bytes) -> str:
    """包装加密的有效载荷"""
    plaintext = json.dumps(payload)
    encrypted = encrypt_message(plaintext, key)
    return json.dumps(encrypted)


def unwrap_encrypted_payload(encrypted_json: str, key: bytes) -> Optional[dict]:
    """解包加密的有效载荷"""
    try:
        encrypted = json.loads(encrypted_json)
        plaintext = decrypt_message(encrypted, key)
        if plaintext:
            return json.loads(plaintext)
    except Exception as e:
        logger.error(f"Unwrap failed: {e}")
    return None


# ==================== TLS/WSS配置 ====================

def get_ws_protocol() -> str:
    """
    获取WebSocket协议
    
    生产环境应使用 WSS (WebSocket Secure)
    """
    if settings.WS_URL.startswith("wss://"):
        return "wss://"
    elif settings.WS_URL.startswith("ws://"):
        # 生产环境警告
        if not settings.DEBUG:
            logger.warning("Using unencrypted WS in production! Set WS_URL to wss://")
        return "ws://"
    return "ws://"


def get_ssl_config() -> Optional[dict]:
    """获取SSL/TLS配置"""
    if settings.SSL_CERT_FILE and settings.SSL_KEY_FILE:
        return {
            "certfile": settings.SSL_CERT_FILE,
            "keyfile": settings.SSL_KEY_FILE
        }
    return None


# ==================== 审计日志 ====================

def create_audit_log(
    event: str,
    agent_id: str,
    action: str,
    result: str,
    details: Optional[dict] = None
) -> dict:
    """
    创建审计日志条目
    
    Args:
        event: 事件类型
        agent_id: Agent ID
        action: 操作
        result: 结果 (success/failure)
        details: 额外详情
    """
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "event": event,
        "agent_id": agent_id,
        "action": action,
        "result": result,
        "details": details or {}
    }


# ==================== 速率限制 ====================

class RateLimiter:
    """
    速率限制器
    
    支持内存和Redis两种存储方式
    """
    
    def __init__(self):
        self._requests: dict = {}
        self._redis_client = None
    
    def _get_redis(self):
        """获取Redis客户端"""
        if self._redis_client is None:
            self._redis_client = _get_redis_client()
        return self._redis_client
    
    async def is_allowed_async(self, key: str, max_requests: int, window_seconds: int) -> bool:
        """异步检查请求是否允许"""
        redis_client = self._get_redis()
        
        if redis_client:
            try:
                # 使用 Redis 有序集合实现滑动窗口
                now = datetime.utcnow().timestamp()
                window_start = now - window_seconds
                redis_key = f"ratelimit:{key}"
                
                # 移除窗口外的请求
                await redis_client.zremrangebyscore(redis_key, 0, window_start)
                
                # 检查当前请求数
                current_count = await redis_client.zcard(redis_key)
                if current_count >= max_requests:
                    return False
                
                # 添加新请求
                await redis_client.zadd(redis_key, {str(now): now})
                await redis_client.expire(redis_key, window_seconds)
                return True
            except Exception as e:
                logger.error(f"Redis rate limit error: {e}")
        
        # 降级到内存存储
        return self._is_allowed_memory(key, max_requests, window_seconds)
    
    def _is_allowed_memory(self, key: str, max_requests: int, window_seconds: int) -> bool:
        """内存速率限制"""
        now = datetime.utcnow()
        window_start = now - timedelta(seconds=window_seconds)
        
        if key not in self._requests:
            self._requests[key] = []
        
        # 清理过期请求
        self._requests[key] = [
            t for t in self._requests[key] if t > window_start
        ]
        
        # 检查限制
        if len(self._requests[key]) >= max_requests:
            return False
        
        # 记录新请求
        self._requests[key].append(now)
        return True
    
    def is_allowed(self, key: str, max_requests: int, window_seconds: int) -> bool:
        """同步版本（内存）"""
        return self._is_allowed_memory(key, max_requests, window_seconds)


# 全局限流器
rate_limiter = RateLimiter()
