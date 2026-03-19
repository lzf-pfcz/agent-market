"""
热榜总结Agent - 对接知乎
提供热点新闻查询服务
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
import random

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [HotNewsAgent] %(levelname)s - %(message)s"
)
logger = logging.getLogger("hotnews_agent")

# 平台配置
PLATFORM_URL = "http://localhost:8000"
WS_BASE_URL = "ws://localhost:8000"

# Agent配置
AGENT_CONFIG = {
    "name": "热点新闻助手",
    "description": "我可以查询知乎等平台的热点新闻，自动汇总前十条热点事件，提供实时热点追踪服务",
    "owner_name": "知乎服务提供商",
    "avatar": "🔥",
    "tags": ["news", "热点", "知乎", "热榜"],
    "capabilities": [
        {
            "name": "get_hot_topics",
            "description": "获取知乎等平台的热点新闻前十条",
            "input_schema": {
                "type": "object",
                "properties": {
                    "platform": {"type": "string", "description": "平台: 知乎/微博/百度", "default": "知乎"},
                    "category": {"type": "string", "description": "分类: 全部/科技/娱乐/体育", "default": "全部"}
                },
                "required": []
            },
            "output_schema": {
                "type": "object",
                "properties": {
                    "platform": {"type": "string"},
                    "timestamp": {"type": "string"},
                    "hot_topics": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "rank": {"type": "integer"},
                                "title": {"type": "string"},
                                "hot_value": {"type": "number"},
                                "summary": {"type": "string"}
                            }
                        }
                    }
                }
            }
        }
    ]
}


async def fetch_hot_topics_from_zhihu(platform: str = "知乎", category: str = "全部") -> dict:
    """
    从知乎等平台获取热点新闻
    
    注意：由于知乎等网站有反爬机制，这里提供模拟数据
    在实际生产环境中，可以使用官方API或合规的爬虫方案
    """
    logger.info(f"正在从{platform}查询热点新闻 - 分类: {category}")
    
    # 模拟网络延迟
    await asyncio.sleep(1.5)
    
    # 模拟热点数据（实际应用中应该从知乎API或网页抓取）
    hot_topics_data = {
        "全部": [
            {"title": "2026年全国两会即将召开", "hot_value": 5892341, "summary": "全国两会将审议多项重要议题"},
            {"title": "AI技术突破：新一代大模型发布", "hot_value": 4876234, "summary": "多家科技公司发布新一代AI大模型"},
            {"title": "新能源汽车销量创新高", "hot_value": 3987652, "summary": "3月份新能源汽车销量同比增长45%"},
            {"title": "国际经济形势分析", "hot_value": 2987654, "summary": "全球经济增长预期上调至3.2%"},
            {"title": "教育部发布新政策", "hot_value": 2543210, "summary": "义务教育阶段将新增人工智能课程"},
            {"title": "体育赛事精彩回顾", "hot_value": 2098765, "summary": "本周多项国际赛事精彩纷呈"},
            {"title": "科技创新成果展示", "hot_value": 1876543, "summary": "国家科技奖励大会在北京举行"},
            {"title": "环保新规实施", "hot_value": 1654321, "summary": "碳达峰碳中和新规正式实施"},
            {"title": "文化旅游新趋势", "hot_value": 1432109, "summary": "春季旅游市场迎来小高峰"},
            {"title": "健康生活指南", "hot_value": 1209876, "summary": "专家发布春季养生健康建议"}
        ],
        "科技": [
            {"title": "新一代芯片技术突破", "hot_value": 4567890, "summary": "国产3nm芯片技术取得重大突破"},
            {"title": "量子计算新进展", "hot_value": 3456789, "summary": "量子计算达到实用化新阶段"},
            {"title": "6G技术研发启动", "hot_value": 2987654, "summary": "6G技术研发正式拉开序幕"},
            {"title": "AI医疗应用", "hot_value": 2543210, "summary": "AI辅助诊断准确率大幅提升"},
            {"title": "太空探索新成果", "hot_value": 2098765, "summary": "火星探测器传回新发现"}
        ],
        "娱乐": [
            {"title": "春节档电影破纪录", "hot_value": 5678901, "summary": "2026年春节档票房创历史新高"},
            {"title": "热门剧集收官", "hot_value": 4567890, "summary": "多部热门剧集迎来大结局"},
            {"title": "音乐节巡演启动", "hot_value": 3456789, "summary": "全国音乐节巡演正式开始"},
            {"title": "明星公益行动", "hot_value": 2987654, "summary": "多位明星参与公益项目"},
            {"title": "电竞比赛夺冠", "hot_value": 2543210, "summary": "中国电竞战队夺得世界冠军"}
        ],
        "体育": [
            {"title": "世界杯预选赛", "hot_value": 4567890, "summary": "世界杯预选赛激战正酣"},
            {"title": "NBA季后赛", "hot_value": 3456789, "summary": "NBA季后赛精彩对决"},
            {"title": "羽毛球世锦赛", "hot_value": 2987654, "summary": "中国选手包揽多项冠军"},
            {"title": "马拉松赛事", "hot_value": 2543210, "summary": "全国马拉松赛事陆续开跑"},
            {"title": "奥运会备战", "hot_value": 2098765, "summary": "各国运动员备战奥运会"}
        ]
    }
    
    # 获取对应分类的数据
    topics = hot_topics_data.get(category, hot_topics_data["全部"])
    
    # 随机调整热度值（模拟实时变化）
    for topic in topics:
        variation = random.uniform(0.95, 1.05)
        topic["hot_value"] = int(topic["hot_value"] * variation)
    
    # 按热度排序
    topics = sorted(topics, key=lambda x: x["hot_value"], reverse=True)[:10]
    
    # 添加排名
    result = {
        "platform": platform,
        "category": category,
        "timestamp": datetime.now().isoformat(),
        "total_topics": len(topics),
        "hot_topics": [
            {
                "rank": i + 1,
                "title": topic["title"],
                "hot_value": topic["hot_value"],
                "summary": topic["summary"]
            }
            for i, topic in enumerate(topics)
        ]
    }
    
    logger.info(f"从{platform}获取到 {len(topics)} 条热点新闻")
    return result


def compute_challenge_response(challenge: str, secret_key: str) -> str:
    """计算挑战响应"""
    return hashlib.sha256(f"{challenge}{secret_key}".encode()).hexdigest()


class HotNewsAgent:
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
            
            if task_type == "get_hot_topics":
                params = payload.get("params", {})
                result = await fetch_hot_topics_from_zhihu(
                    params.get("platform", "知乎"),
                    params.get("category", "全部")
                )
                logger.info(f"✓ 查询完成，获取到 {result['total_topics']} 条热点新闻")
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
        logger.info("热点新闻助手 启动中...")
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
    asyncio.run(HotNewsAgent().run())
