"""
agent2: 个人出行助理智能体
演示如何主动发现服务、发起握手、协作完成任务
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

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [agent2/PersonalAssist] %(levelname)s - %(message)s"
)
logger = logging.getLogger("agent2")

PLATFORM_URL = "http://localhost:8000"
WS_BASE_URL = "ws://localhost:8000"

AGENT_CONFIG = {
    "name": "个人出行助理",
    "description": "我是您的专属出行助理，能够帮您搜索、比价和预订交通、住宿等出行服务",
    "owner_name": "用户: 张伟",
    "avatar": "🧑‍💼",
    "tags": ["personal", "travel", "assistant"],
    "capabilities": [
        {
            "name": "plan_trip",
            "description": "根据用户需求规划出行方案",
            "input_schema": {
                "type": "object",
                "properties": {
                    "from_city": {"type": "string"},
                    "to_city": {"type": "string"},
                    "date": {"type": "string"},
                    "preferences": {"type": "object"}
                }
            }
        }
    ]
}


def compute_challenge_response(challenge: str, secret_key: str) -> str:
    return hashlib.sha256(f"{challenge}{secret_key}".encode()).hexdigest()


class PersonalAssistantAgent:
    def __init__(self):
        self.agent_id: Optional[str] = None
        self.secret_key: Optional[str] = None
        self.token: Optional[str] = None
        self.ws: Optional[websockets.WebSocketClientProtocol] = None

        # 状态机
        self.pending_tasks = {}         # task_id -> future
        self.pending_handshakes = {}    # session_id -> challenge_future
        self.active_sessions = {}       # session_id -> peer_agent_id
        self.session_by_peer = {}       # peer_id -> session_id

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
                    return True
                else:
                    logger.error(f"Registration failed: {await resp.text()}")
                    return False

    async def discover_service(self, query: str) -> list:
        """发现服务 - 通过WebSocket向平台发送发现请求"""
        future = asyncio.get_event_loop().create_future()
        discover_id = str(uuid.uuid4())

        msg = {
            "id": discover_id,
            "type": "discover.request",
            "from_agent": self.agent_id,
            "payload": {"query": query}
        }

        self.pending_tasks[discover_id] = future
        await self.ws.send(json.dumps(msg))

        try:
            result = await asyncio.wait_for(future, timeout=10.0)
            return result
        except asyncio.TimeoutError:
            logger.error("Service discovery timeout")
            return []
        finally:
            self.pending_tasks.pop(discover_id, None)

    async def handshake_with(self, target_id: str, purpose: str) -> Optional[str]:
        """与目标Agent握手"""
        logger.info(f"Initiating handshake with {target_id[:8]}...")

        # 发起握手
        init_msg = {
            "id": str(uuid.uuid4()),
            "type": "handshake.init",
            "from_agent": self.agent_id,
            "payload": {
                "target_agent_id": target_id,
                "purpose": purpose
            }
        }
        await self.ws.send(json.dumps(init_msg))

        # 等待挑战码
        challenge_future = asyncio.get_event_loop().create_future()
        self.pending_handshakes["__waiting__" + target_id] = challenge_future

        try:
            challenge_data = await asyncio.wait_for(challenge_future, timeout=15.0)
        except asyncio.TimeoutError:
            logger.error("Handshake challenge timeout")
            return None
        finally:
            self.pending_handshakes.pop("__waiting__" + target_id, None)

        # 计算挑战响应
        session_id = challenge_data["session_id"]
        challenge = challenge_data["challenge"]
        answer = compute_challenge_response(challenge, self.secret_key)

        response_msg = {
            "id": str(uuid.uuid4()),
            "type": "handshake.response",
            "from_agent": self.agent_id,
            "session_id": session_id,
            "payload": {
                "challenge_answer": answer,
                "session_id": session_id
            }
        }
        await self.ws.send(json.dumps(response_msg))

        # 等待握手确认
        ack_future = asyncio.get_event_loop().create_future()
        self.pending_handshakes[session_id] = ack_future

        try:
            await asyncio.wait_for(ack_future, timeout=15.0)
            logger.info(f"✅ Handshake established! Session: {session_id[:8]}...")
            return session_id
        except asyncio.TimeoutError:
            logger.error("Handshake ACK timeout")
            return None
        finally:
            self.pending_handshakes.pop(session_id, None)

    async def call_service(self, session_id: str, target_id: str, task_type: str, params: dict, description: str) -> Optional[dict]:
        """调用远端Agent服务"""
        task_id = str(uuid.uuid4())
        future = asyncio.get_event_loop().create_future()
        self.pending_tasks[task_id] = future

        request_msg = {
            "id": task_id,
            "type": "task.request",
            "from_agent": self.agent_id,
            "to_agent": target_id,
            "session_id": session_id,
            "payload": {
                "task_type": task_type,
                "task_description": description,
                "params": params
            }
        }
        await self.ws.send(json.dumps(request_msg))
        logger.info(f"Task sent: {task_type}")

        try:
            result = await asyncio.wait_for(future, timeout=30.0)
            return result
        except asyncio.TimeoutError:
            logger.error(f"Task {task_type} timeout")
            return None
        finally:
            self.pending_tasks.pop(task_id, None)

    async def close_session(self, session_id: str, reason: str = "Task completed"):
        """礼貌地关闭会话"""
        close_msg = {
            "id": str(uuid.uuid4()),
            "type": "session.close",
            "from_agent": self.agent_id,
            "session_id": session_id,
            "payload": {"reason": reason}
        }
        await self.ws.send(json.dumps(close_msg))
        if session_id in self.active_sessions:
            del self.active_sessions[session_id]

    async def book_flight_for_user(self, from_city: str, to_city: str, date: str, cabin: str = "economy"):
        """
        完整的机票预订流程：
        1. 发现 -> 2. 握手 -> 3. 查询 -> 4. 预订 -> 5. 关闭
        """
        logger.info("=" * 60)
        logger.info(f"开始机票预订任务: {from_city} -> {to_city}, {date}")
        logger.info("=" * 60)

        # Step 1: 服务发现
        logger.info("\n📡 Step 1: 搜索订票服务...")
        agents = await self.discover_service("订票 机票")
        online_agents = [a for a in agents if a.get("status") == "online"]

        if not online_agents:
            logger.warning("未找到在线的订票服务，尝试搜索 flight...")
            agents = await self.discover_service("flight booking")
            online_agents = [a for a in agents if a.get("status") == "online"]

        if not online_agents:
            logger.error("❌ 未找到可用的订票服务!")
            return None

        target = online_agents[0]
        logger.info(f"✅ 找到订票服务: {target['name']} (ID: {target['agent_id'][:8]}...)")

        # Step 2: 握手
        logger.info(f"\n🤝 Step 2: 与 {target['name']} 发起握手...")
        await asyncio.sleep(0.5)
        session_id = await self.handshake_with(
            target["agent_id"],
            f"我需要预订从{from_city}到{to_city}的机票"
        )

        if not session_id:
            logger.error("❌ 握手失败!")
            return None

        logger.info(f"✅ 安全通道已建立!")

        # Step 3: 查询航班
        logger.info(f"\n🔍 Step 3: 查询 {date} {from_city}→{to_city} 的航班...")
        await asyncio.sleep(0.5)
        search_result = await self.call_service(
            session_id, target["agent_id"],
            "search_flights",
            {"from_city": from_city, "to_city": to_city, "date": date, "cabin_class": cabin},
            f"查询{from_city}到{to_city}{date}的{cabin}舱航班"
        )

        if not search_result or not search_result.get("result"):
            logger.error("❌ 航班查询失败!")
            await self.close_session(session_id, "Query failed")
            return None

        flights = search_result["result"]
        logger.info(f"✅ 找到 {len(flights)} 个航班:")
        for i, f in enumerate(flights[:3]):
            logger.info(f"   [{i+1}] {f['flight_no']} {f['departure_time'][-5:]}→{f['arrival_time'][-5:]} ¥{f['price']} ({f['seats_available']}座位)")

        best_flight = flights[0]
        logger.info(f"\n💡 为您选择最优航班: {best_flight['flight_no']} ¥{best_flight['price']}")

        # Step 4: 预订机票
        logger.info(f"\n📝 Step 4: 预订航班 {best_flight['flight_no']}...")
        await asyncio.sleep(0.5)
        booking_result = await self.call_service(
            session_id, target["agent_id"],
            "book_flight",
            {
                "flight_no": best_flight["flight_no"],
                "passenger_name": "张伟",
                "cabin_class": cabin,
                "date": date
            },
            f"预订{best_flight['flight_no']}航班{cabin}舱"
        )

        if not booking_result or not booking_result.get("result"):
            logger.error("❌ 预订失败!")
            await self.close_session(session_id, "Booking failed")
            return None

        order = booking_result["result"]
        logger.info(f"✅ 机票预订成功!")
        logger.info(f"   订单号: {order['order_id']}")
        logger.info(f"   航班: {order['flight_no']}")
        logger.info(f"   座位: {order['seat_no']}")
        logger.info(f"   总价: ¥{order['total_price']}")

        # Step 5: 礼貌关闭会话
        logger.info(f"\n👋 Step 5: 任务完成，礼貌地关闭会话...")
        await asyncio.sleep(0.5)
        await self.close_session(session_id, "Thank you! Task completed successfully.")

        logger.info("\n" + "=" * 60)
        logger.info("✈️  机票已订好！向用户汇报结果...")
        logger.info(f"   您好！已为您订好机票：")
        logger.info(f"   {from_city} → {to_city}")
        logger.info(f"   {order['flight_no']} | {date}")
        logger.info(f"   座位: {order['seat_no']} | 总价: ¥{order['total_price']}")
        logger.info(f"   订单号: {order['order_id']}")
        logger.info("=" * 60)

        return order

    async def handle_message(self, data: dict):
        """处理接收到的消息"""
        msg_type = data.get("type")
        msg_id = data.get("id")

        if msg_type == "session.open":
            logger.info(f"Connected! {data['payload'].get('message')}")
            # 上线后等待2秒，然后执行演示任务
            asyncio.create_task(self.run_demo())

        elif msg_type == "discover.response":
            results = data["payload"].get("results", [])
            if msg_id and msg_id in self.pending_tasks:
                future = self.pending_tasks[msg_id]
                if not future.done():
                    future.set_result(results)

        elif msg_type == "handshake.challenge":
            payload = data.get("payload", {})
            target_id = payload.get("responder_id", "")
            key = "__waiting__" + target_id
            if key in self.pending_handshakes:
                future = self.pending_handshakes[key]
                if not future.done():
                    future.set_result(payload)

        elif msg_type == "handshake.ack":
            session_id = data.get("session_id")
            payload = data.get("payload", {})
            peer_id = payload.get("peer_id")
            self.active_sessions[session_id] = peer_id
            if session_id and session_id in self.pending_handshakes:
                future = self.pending_handshakes[session_id]
                if not future.done():
                    future.set_result(True)

        elif msg_type == "handshake.reject":
            session_id = data.get("session_id")
            if session_id and session_id in self.pending_handshakes:
                future = self.pending_handshakes[session_id]
                if not future.done():
                    future.set_exception(Exception("Handshake rejected"))

        elif msg_type in ["task.result", "task.error"]:
            payload = data.get("payload", {})
            ref_id = payload.get("ref_task_id")
            if ref_id and ref_id in self.pending_tasks:
                future = self.pending_tasks[ref_id]
                if not future.done():
                    if msg_type == "task.result":
                        future.set_result(payload)
                    else:
                        future.set_result(None)

        elif msg_type == "task.ack":
            logger.info("Task acknowledged by remote agent, processing...")

    async def run_demo(self):
        """等待片刻后执行演示场景"""
        await asyncio.sleep(3)
        logger.info("\n🎬 开始演示场景: 用户说 '帮我订一张明天从北京到上海的机票'")

        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        await self.book_flight_for_user("北京", "上海", tomorrow, "economy")

    async def run(self):
        """主运行循环"""
        logger.info("=" * 50)
        logger.info("个人出行助理 (agent2) 启动中...")
        logger.info("=" * 50)

        if not await self.register():
            return

        ws_url = f"{WS_BASE_URL}/ws/agent/{self.agent_id}?token={self.token}"
        logger.info("Connecting to platform...")

        async with websockets.connect(ws_url) as ws:
            self.ws = ws
            logger.info("Connected!")

            async for raw_msg in ws:
                try:
                    data = json.loads(raw_msg)
                    await self.handle_message(data)
                except Exception as e:
                    logger.error(f"Error: {e}")


if __name__ == "__main__":
    asyncio.run(PersonalAssistantAgent().run())
