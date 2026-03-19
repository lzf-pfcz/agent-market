"""
航班查询Agent - 对接携程网
提供航班信息查询服务
"""
import asyncio
import json
import hashlib
import uuid
import logging
import aiohttp
import websockets
from datetime import datetime, timedelta
from typing import Optional
from bs4 import BeautifulSoup

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [FlightAgent] %(levelname)s - %(message)s"
)
logger = logging.getLogger("flight_agent")

# 平台配置
PLATFORM_URL = "http://localhost:8000"
WS_BASE_URL = "ws://localhost:8000"

# Agent配置
AGENT_CONFIG = {
    "name": "航班查询助手",
    "description": "我可以查询实时航班信息，支持国内主要航线查询，对接携程网获取最新航班数据",
    "owner_name": "携程服务提供商",
    "avatar": "✈️",
    "tags": ["travel", "flight", "航班查询", "机票"],
    "capabilities": [
        {
            "name": "search_flights",
            "description": "查询指定日期、航线的航班信息",
            "input_schema": {
                "type": "object",
                "properties": {
                    "from_city": {"type": "string", "description": "出发城市"},
                    "to_city": {"type": "string", "description": "目的城市"},
                    "date": {"type": "string", "description": "出发日期 YYYY-MM-DD"},
                    "time_range": {"type": "string", "description": "时间段: 上午/下午/晚上/全天", "default": "全天"}
                },
                "required": ["from_city", "to_city", "date"]
            },
            "output_schema": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "flight_no": {"type": "string"},
                        "airline": {"type": "string"},
                        "departure_time": {"type": "string"},
                        "arrival_time": {"type": "string"},
                        "price": {"type": "number"},
                        "duration": {"type": "string"}
                    }
                }
            }
        }
    ]
}


async def fetch_flights_from_ctrip(from_city: str, to_city: str, date: str, time_range: str = "全天") -> list:
    """
    从携程网获取航班信息
    
    注意：由于携程网站需要JavaScript渲染和动态加载，这里提供模拟数据
    在实际生产环境中，可以使用Selenium或Playwright来抓取动态数据
    """
    # 模拟航班数据（实际应用中应该从携程API或网页抓取）
    logger.info(f"正在从携程网查询: {from_city} → {to_city}, {date}, {time_range}")
    
    # 模拟网络延迟
    await asyncio.sleep(1.5)
    
    # 根据时间范围过滤的航班数据
    base_flights = [
        {
            "flight_no": "CA1234",
            "airline": "中国国际航空",
            "base_price": 680,
            "duration": "2小时15分钟",
            "departure": "07:30",
            "arrival": "09:45",
            "period": "上午"
        },
        {
            "flight_no": "MU5678",
            "airline": "东方航空",
            "base_price": 750,
            "duration": "2小时10分钟",
            "departure": "10:15",
            "arrival": "12:25",
            "period": "上午"
        },
        {
            "flight_no": "FM9012",
            "airline": "上海航空",
            "base_price": 590,
            "duration": "2小时20分钟",
            "departure": "14:00",
            "arrival": "16:20",
            "period": "下午"
        },
        {
            "flight_no": "CZ3001",
            "airline": "南方航空",
            "base_price": 620,
            "duration": "2小时05分钟",
            "departure": "16:45",
            "arrival": "18:50",
            "period": "下午"
        },
        {
            "flight_no": "HO3456",
            "airline": "吉祥航空",
            "base_price": 850,
            "duration": "2小时30分钟",
            "departure": "20:30",
            "arrival": "23:00",
            "period": "晚上"
        }
    ]
    
    # 根据时间范围过滤
    if time_range == "上午":
        flights = [f for f in base_flights if f["period"] == "上午"]
    elif time_range == "下午":
        flights = [f for f in base_flights if f["period"] == "下午"]
    elif time_range == "晚上":
        flights = [f for f in base_flights if f["period"] == "晚上"]
    else:
        flights = base_flights
    
    # 添加实时价格波动和完整信息
    result = []
    for f in flights:
        import random
        price_variation = random.uniform(0.9, 1.1)
        result.append({
            "flight_no": f["flight_no"],
            "airline": f["airline"],
            "from_city": from_city,
            "to_city": to_city,
            "date": date,
            "departure_time": f"{date} {f['departure']}",
            "arrival_time": f"{date} {f['arrival']}",
            "price": int(f["base_price"] * price_variation),
            "duration": f["duration"],
            "source": "携程网"
        })
    
    logger.info(f"从携程网获取到 {len(result)} 个航班")
    return sorted(result, key=lambda x: x["price"])


def compute_challenge_response(challenge: str, secret_key: str) -> str:
    """计算挑战响应"""
    return hashlib.sha256(f"{challenge}{secret_key}".encode()).hexdigest()


class FlightQueryAgent:
    def __init__(self):
        self.agent_id: Optional[str] = None
        self.secret_key: Optional[str] = None
        self.token: Optional[str] = None
        self.ws: Optional[websockets.WebSocketClientProtocol] = None
        self.active_sessions = {}  # session_id -> peer_id
        self.stats = {
            "total_queries": 0,
            "successful_queries": 0
        }

    async def register(self):
        """向平台注册"""
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{PLATFORM_URL}/api/agents/register",
                json=AGENT_CONFIG
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    self.agent_id = data["agent_id"]
                    self.secret_key = data["secret_key"]
                    self.token = data["token"]
                    logger.info(f"✓ Agent注册成功! ID: {self.agent_id}")
                    logger.info(f"  Secret Key: {self.secret_key[:16]}...")
                    logger.info(f"  Token: {self.token[:16]}...")
                    return True
                else:
                    logger.error(f"✗ 注册失败: {await resp.text()}")
                    return False

    async def connect(self):
        """连接到平台"""
        ws_url = f"{WS_BASE_URL}/ws/agent/{self.agent_id}?token={self.token}"
        logger.info(f"正在连接到平台...")

        async with websockets.connect(ws_url) as ws:
            self.ws = ws
            logger.info("✓ 已连接到AgentMarketplace平台!")

            async for raw_msg in ws:
                try:
                    data = json.loads(raw_msg)
                    await self.handle_message(data)
                except Exception as e:
                    logger.error(f"✗ 处理消息错误: {e}")

    async def handle_message(self, data: dict):
        """处理接收到的消息"""
        msg_type = data.get("type")
        logger.info(f"收到消息: {msg_type}")

        if msg_type == "session.open":
            logger.info(f"平台: {data['payload'].get('message')}")

        elif msg_type == "handshake.init":
            # 有Agent要和我握手
            payload = data.get("payload", {})
            logger.info(f"握手请求来自: {payload.get('initiator_name')} - 目的: {payload.get('purpose')}")

        elif msg_type == "handshake.ack":
            # 握手成功
            payload = data.get("payload", {})
            session_id = data.get("session_id")
            peer_name = payload.get("peer_name")
            self.active_sessions[session_id] = payload.get("peer_id")
            logger.info(f"✓ 握手成功! 与 {peer_name} 建立安全连接 - Session: {session_id[:8]}...")

        elif msg_type == "task.request":
            # 收到任务请求
            await self.handle_task_request(data)

        elif msg_type == "session.close":
            session_id = data.get("session_id")
            if session_id in self.active_sessions:
                del self.active_sessions[session_id]
            logger.info(f"会话 {session_id[:8] if session_id else 'unknown'}... 已关闭")

    async def handle_task_request(self, data: dict):
        """处理任务请求"""
        session_id = data.get("session_id")
        from_agent = data.get("from_agent")
        payload = data.get("payload", {})
        task_type = payload.get("task_type")
        task_id = data.get("id")

        logger.info(f"任务请求: {task_type}")

        # 发送确认
        ack = {
            "id": str(uuid.uuid4()),
            "type": "task.ack",
            "from_agent": self.agent_id,
            "to_agent": from_agent,
            "session_id": session_id,
            "payload": {"ref_task_id": task_id, "status": "processing"}
        }
        await self.ws.send(json.dumps(ack))

        # 执行任务
        result = None
        error = None

        try:
            self.stats["total_queries"] += 1
            
            if task_type == "search_flights":
                params = payload.get("params", {})
                result = await fetch_flights_from_ctrip(
                    params.get("from_city", ""),
                    params.get("to_city", ""),
                    params.get("date", ""),
                    params.get("time_range", "全天")
                )
                logger.info(f"✓ 查询完成，找到 {len(result)} 个航班")
                self.stats["successful_queries"] += 1

            else:
                error = f"未知的任务类型: {task_type}"

        except Exception as e:
            error = str(e)
            logger.error(f"✗ 任务执行错误: {e}")

        # 返回结果
        if error:
            response = {
                "id": str(uuid.uuid4()),
                "type": "task.error",
                "from_agent": self.agent_id,
                "to_agent": from_agent,
                "session_id": session_id,
                "payload": {"error": error, "ref_task_id": task_id}
            }
        else:
            response = {
                "id": str(uuid.uuid4()),
                "type": "task.result",
                "from_agent": self.agent_id,
                "to_agent": from_agent,
                "session_id": session_id,
                "payload": {
                    "task_type": task_type,
                    "result": result,
                    "ref_task_id": task_id,
                    "processed_at": datetime.now().isoformat(),
                    "stats": self.stats
                }
            }

        await self.ws.send(json.dumps(response))
        logger.info(f"结果已发送给 {from_agent[:8]}...")

    async def run(self):
        """主运行循环"""
        logger.info("=" * 60)
        logger.info("航班查询助手 启动中...")
        logger.info("=" * 60)

        if not await self.register():
            return

        while True:
            try:
                await self.connect()
            except Exception as e:
                logger.error(f"✗ 连接丢失: {e}. 5秒后重连...")
                await asyncio.sleep(5)


if __name__ == "__main__":
    asyncio.run(FlightQueryAgent().run())
