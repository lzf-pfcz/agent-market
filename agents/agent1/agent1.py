"""
agent1: 航空公司订票智能体
演示如何接入AgentMarketplace平台，提供机票查询和预订服务
"""
import asyncio
import json
import hashlib
import uuid
import random
import logging
import aiohttp
import websockets
from datetime import datetime, timedelta
from typing import Optional

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [agent1/AirBooking] %(levelname)s - %(message)s"
)
logger = logging.getLogger("agent1")

# 平台配置
PLATFORM_URL = "http://localhost:8000"
WS_BASE_URL = "ws://localhost:8000"

# Agent配置
AGENT_CONFIG = {
    "name": "航空订票助手",
    "description": "我可以查询和预订机票，支持国内外航线，提供实时航班信息和座位预订服务",
    "owner_name": "天空航空公司",
    "avatar": "✈️",
    "tags": ["travel", "booking", "flight", "airline"],
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
                    "cabin_class": {"type": "string", "enum": ["economy", "business", "first"]}
                },
                "required": ["from_city", "to_city", "date"]
            },
            "output_schema": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "flight_no": {"type": "string"},
                        "departure_time": {"type": "string"},
                        "arrival_time": {"type": "string"},
                        "price": {"type": "number"},
                        "seats_available": {"type": "integer"}
                    }
                }
            }
        },
        {
            "name": "book_flight",
            "description": "预订指定航班的机票",
            "input_schema": {
                "type": "object",
                "properties": {
                    "flight_no": {"type": "string"},
                    "passenger_name": {"type": "string"},
                    "cabin_class": {"type": "string"},
                    "date": {"type": "string"}
                },
                "required": ["flight_no", "passenger_name", "date"]
            },
            "output_schema": {
                "type": "object",
                "properties": {
                    "order_id": {"type": "string"},
                    "seat_no": {"type": "string"},
                    "total_price": {"type": "number"},
                    "status": {"type": "string"}
                }
            }
        }
    ]
}

# 模拟航班数据库
FLIGHT_DATABASE = {
    ("北京", "上海"): [
        {"flight_no": "CA1234", "departure": "07:00", "arrival": "09:10", "base_price": 680, "airline": "国航"},
        {"flight_no": "MU5678", "departure": "09:30", "arrival": "11:45", "base_price": 750, "airline": "东航"},
        {"flight_no": "FM9012", "departure": "12:00", "arrival": "14:15", "base_price": 590, "airline": "上航"},
        {"flight_no": "HO3456", "departure": "16:30", "arrival": "18:45", "base_price": 620, "airline": "吉祥"},
        {"flight_no": "CZ7890", "departure": "20:00", "arrival": "22:10", "base_price": 560, "airline": "南航"},
    ],
    ("上海", "北京"): [
        {"flight_no": "CA4321", "departure": "08:00", "arrival": "10:15", "base_price": 670, "airline": "国航"},
        {"flight_no": "MU8765", "departure": "11:00", "arrival": "13:20", "base_price": 730, "airline": "东航"},
        {"flight_no": "FM2109", "departure": "15:30", "arrival": "17:45", "base_price": 580, "airline": "上航"},
    ],
    ("北京", "广州"): [
        {"flight_no": "CZ3001", "departure": "08:30", "arrival": "11:45", "base_price": 980, "airline": "南航"},
        {"flight_no": "CA5678", "departure": "13:00", "arrival": "16:20", "base_price": 1050, "airline": "国航"},
        {"flight_no": "3U8888", "departure": "19:00", "arrival": "22:15", "base_price": 850, "airline": "四川航空"},
    ],
    ("广州", "北京"): [
        {"flight_no": "CZ3002", "departure": "09:00", "arrival": "12:20", "base_price": 960, "airline": "南航"},
        {"flight_no": "CA5679", "departure": "14:00", "arrival": "17:15", "base_price": 1020, "airline": "国航"},
    ],
}


def search_flights(from_city: str, to_city: str, date: str, cabin_class: str = "economy") -> list:
    """模拟航班查询"""
    key = (from_city, to_city)
    flights = FLIGHT_DATABASE.get(key, [])

    cabin_multiplier = {"economy": 1.0, "business": 2.8, "first": 5.0}.get(cabin_class, 1.0)

    result = []
    for f in flights:
        seats = random.randint(3, 50)
        price = int(f["base_price"] * cabin_multiplier * random.uniform(0.85, 1.15))
        result.append({
            "flight_no": f["flight_no"],
            "airline": f["airline"],
            "from_city": from_city,
            "to_city": to_city,
            "date": date,
            "departure_time": f"{date} {f['departure']}",
            "arrival_time": f"{date} {f['arrival']}",
            "cabin_class": cabin_class,
            "price": price,
            "seats_available": seats,
            "duration": "约2小时15分钟"
        })

    return sorted(result, key=lambda x: x["price"])


def book_flight(flight_no: str, passenger_name: str, cabin_class: str, date: str) -> dict:
    """模拟机票预订"""
    import string
    order_id = "ORD" + "".join(random.choices(string.ascii_uppercase + string.digits, k=8))
    row = random.randint(10, 35)
    col = random.choice(["A", "B", "C", "D", "E", "F"])
    seat_no = f"{row}{col}"

    cabin_multiplier = {"economy": 1.0, "business": 2.8, "first": 5.0}.get(cabin_class, 1.0)
    base_price = 680  # 默认价格
    for flights in FLIGHT_DATABASE.values():
        for f in flights:
            if f["flight_no"] == flight_no:
                base_price = f["base_price"]
                break

    total_price = int(base_price * cabin_multiplier)

    return {
        "order_id": order_id,
        "flight_no": flight_no,
        "passenger_name": passenger_name,
        "seat_no": seat_no,
        "cabin_class": cabin_class,
        "date": date,
        "total_price": total_price,
        "status": "confirmed",
        "booking_time": datetime.now().isoformat(),
        "message": f"订票成功！航班{flight_no}，座位{seat_no}，总价¥{total_price}"
    }


def compute_challenge_response(challenge: str, secret_key: str) -> str:
    return hashlib.sha256(f"{challenge}{secret_key}".encode()).hexdigest()


class AirBookingAgent:
    def __init__(self):
        self.agent_id: Optional[str] = None
        self.secret_key: Optional[str] = None
        self.token: Optional[str] = None
        self.ws: Optional[websockets.WebSocketClientProtocol] = None
        self.active_sessions = {}  # session_id -> peer_id

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
                    logger.info(f"Agent registered! ID: {self.agent_id}")
                    logger.info(f"Secret Key: {self.secret_key[:16]}...")
                    return True
                else:
                    logger.error(f"Registration failed: {await resp.text()}")
                    return False

    async def connect(self):
        """连接到平台"""
        ws_url = f"{WS_BASE_URL}/ws/agent/{self.agent_id}?token={self.token}"
        logger.info(f"Connecting to platform: {ws_url[:50]}...")

        async with websockets.connect(ws_url) as ws:
            self.ws = ws
            logger.info("Connected to AgentMarketplace platform!")

            async for raw_msg in ws:
                try:
                    data = json.loads(raw_msg)
                    await self.handle_message(data)
                except Exception as e:
                    logger.error(f"Error handling message: {e}")

    async def handle_message(self, data: dict):
        """处理接收到的消息"""
        msg_type = data.get("type")
        logger.info(f"Received: {msg_type}")

        if msg_type == "session.open":
            logger.info(f"Platform says: {data['payload'].get('message')}")

        elif msg_type == "handshake.init":
            # 有Agent要和我握手
            payload = data.get("payload", {})
            logger.info(f"Handshake from: {payload.get('initiator_name')} - Purpose: {payload.get('purpose')}")
            # 注意：握手验证由平台负责，我们只需等待ACK

        elif msg_type == "handshake.ack":
            # 握手成功
            payload = data.get("payload", {})
            session_id = data.get("session_id")
            peer_name = payload.get("peer_name")
            self.active_sessions[session_id] = payload.get("peer_id")
            logger.info(f"✅ Handshake established with {peer_name}! Session: {session_id[:8]}...")

        elif msg_type == "task.request":
            # 收到任务请求
            await self.handle_task_request(data)

        elif msg_type == "session.close":
            session_id = data.get("session_id")
            if session_id in self.active_sessions:
                del self.active_sessions[session_id]
            logger.info(f"Session {session_id[:8] if session_id else 'unknown'}... closed")

    async def handle_task_request(self, data: dict):
        """处理任务请求"""
        session_id = data.get("session_id")
        from_agent = data.get("from_agent")
        payload = data.get("payload", {})
        task_type = payload.get("task_type")
        task_id = data.get("id")

        logger.info(f"Task request: {task_type}")

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

        # 模拟处理延迟
        await asyncio.sleep(1.5)

        # 执行任务
        result = None
        error = None

        try:
            if task_type == "search_flights":
                params = payload.get("params", {})
                result = search_flights(
                    params.get("from_city", ""),
                    params.get("to_city", ""),
                    params.get("date", ""),
                    params.get("cabin_class", "economy")
                )
                logger.info(f"Found {len(result)} flights")

            elif task_type == "book_flight":
                params = payload.get("params", {})
                result = book_flight(
                    params.get("flight_no", ""),
                    params.get("passenger_name", "旅客"),
                    params.get("cabin_class", "economy"),
                    params.get("date", "")
                )
                logger.info(f"Booked: {result['order_id']}")

            else:
                error = f"Unknown task type: {task_type}"

        except Exception as e:
            error = str(e)

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
                    "processed_at": datetime.now().isoformat()
                }
            }

        await self.ws.send(json.dumps(response))
        logger.info(f"Task result sent to {from_agent[:8]}...")

    async def run(self):
        """主运行循环"""
        logger.info("=" * 50)
        logger.info("航空订票助手 (agent1) 启动中...")
        logger.info("=" * 50)

        if not await self.register():
            return

        while True:
            try:
                await self.connect()
            except Exception as e:
                logger.error(f"Connection lost: {e}. Reconnecting in 5s...")
                await asyncio.sleep(5)


if __name__ == "__main__":
    asyncio.run(AirBookingAgent().run())
