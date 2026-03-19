"""
经济模型与结算服务
支持微支付、声誉系统、激励机制
"""
import json
import time
import logging
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from enum import Enum

logger = logging.getLogger(__name__)


class Currency(str, Enum):
    """支持的货币类型"""
    USD = "USD"
    CNY = "CNY"
    TOKEN = "TOKEN"  # 平台积分代币
    SATOSHI = "SATOSHI"  # 比特币闪电网络


class TransactionStatus(str, Enum):
    """交易状态"""
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"


@dataclass
class Transaction:
    """交易记录"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    from_agent_id: str = ""
    to_agent_id: str = ""
    amount: float = 0.0
    currency: Currency = Currency.TOKEN
    status: TransactionStatus = TransactionStatus.PENDING
    service_type: str = ""  # 任务类型
    session_id: str = ""
    created_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "from_agent_id": self.from_agent_id,
            "to_agent_id": self.to_agent_id,
            "amount": self.amount,
            "currency": self.currency.value,
            "status": self.status.value,
            "service_type": self.service_type,
            "session_id": self.session_id,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
            "metadata": self.metadata
        }


@dataclass
class AgentWallet:
    """Agent钱包"""
    agent_id: str
    balance: float = 0.0
    currency: Currency = Currency.TOKEN
    locked: float = 0.0  # 锁定的金额（如押金、未完成交易）
    reputation_score: float = 100.0  # 声誉分数 (0-100)
    total_transactions: int = 0
    
    def available_balance(self) -> float:
        return max(0, self.balance - self.locked)


@dataclass
class PricingRule:
    """定价规则"""
    service_type: str
    base_price: float = 1.0
    price_per_call: float = 0.0
    price_per_token: float = 0.0  # 按Token计费
    currency: Currency = Currency.TOKEN
    min_price: float = 0.01
    max_price: float = 1000.0


class PaymentProvider(ABC):
    """支付提供商接口"""
    
    @abstractmethod
    async def create_transaction(self, tx: Transaction) -> bool:
        """创建交易"""
        pass
    
    @abstractmethod
    async def execute_transaction(self, tx_id: str) -> bool:
        """执行交易"""
        pass
    
    @abstractmethod
    async def refund_transaction(self, tx_id: str) -> bool:
        """退款"""
        pass
    
    @abstractmethod
    async def get_balance(self, agent_id: str) -> float:
        """获取余额"""
        pass


class TokenPaymentProvider(PaymentProvider):
    """平台积分支付提供商"""
    
    def __init__(self):
        self._wallets: Dict[str, AgentWallet] = {}
        self._transactions: Dict[str, Transaction] = {}
    
    def get_wallet(self, agent_id: str) -> AgentWallet:
        """获取或创建钱包"""
        if agent_id not in self._wallets:
            self._wallets[agent_id] = AgentWallet(agent_id=agent_id)
        return self._wallets[agent_id]
    
    async def deposit(self, agent_id: str, amount: float) -> bool:
        """充值"""
        wallet = self.get_wallet(agent_id)
        wallet.balance += amount
        logger.info(f"Deposit: {agent_id} +{amount}")
        return True
    
    async def create_transaction(self, tx: Transaction) -> bool:
        """创建交易"""
        # 检查余额
        wallet = self.get_wallet(tx.from_agent_id)
        if wallet.available_balance() < tx.amount:
            logger.warning(f"Insufficient balance: {tx.from_agent_id}")
            return False
        
        # 锁定金额
        wallet.locked += tx.amount
        tx.status = TransactionStatus.PENDING
        self._transactions[tx.id] = tx
        
        return True
    
    async def execute_transaction(self, tx_id: str) -> bool:
        """执行交易"""
        tx = self._transactions.get(tx_id)
        if not tx or tx.status != TransactionStatus.PENDING:
            return False
        
        # 转账
        from_wallet = self.get_wallet(tx.from_agent_id)
        to_wallet = self.get_wallet(tx.to_agent_id)
        
        # 扣除锁定金额
        from_wallet.locked -= tx.amount
        from_wallet.balance -= tx.amount
        
        # 计算平台抽成
        platform_fee = tx.amount * 0.05  # 5% 平台费
        agent_receive = tx.amount - platform_fee
        
        # 加到接收方
        to_wallet.balance += agent_receive
        
        # 更新状态
        tx.status = TransactionStatus.COMPLETED
        tx.completed_at = time.time()
        
        # 更新统计
        from_wallet.total_transactions += 1
        to_wallet.total_transactions += 1
        
        logger.info(f"Transaction completed: {tx.from_agent_id} -> {tx.to_agent_id}: {tx.amount}")
        return True
    
    async def refund_transaction(self, tx_id: str) -> bool:
        """退款"""
        tx = self._transactions.get(tx_id)
        if not tx or tx.status != TransactionStatus.PENDING:
            return False
        
        # 解锁金额
        from_wallet = self.get_wallet(tx.from_agent_id)
        from_wallet.locked -= tx.amount
        
        tx.status = TransactionStatus.REFUNDED
        return True
    
    async def get_balance(self, agent_id: str) -> float:
        """获取余额"""
        wallet = self.get_wallet(agent_id)
        return wallet.available_balance()


class ReputationSystem:
    """
    声誉系统
    
    根据Agent的表现计算声誉分数
    """
    
    def __init__(self):
        self._scores: Dict[str, float] = {}  # agent_id -> score
        self._reviews: Dict[str, List[Dict]] = {}  # agent_id -> reviews
    
    def get_score(self, agent_id: str) -> float:
        """获取声誉分数"""
        return self._scores.get(agent_id, 100.0)
    
    def update_score(self, agent_id: str, delta: float) -> float:
        """更新声誉分数"""
        current = self._scores.get(agent_id, 100.0)
        new_score = max(0, min(100, current + delta))
        self._scores[agent_id] = new_score
        return new_score
    
    def add_review(
        self,
        agent_id: str,
        reviewer_id: str,
        rating: int,  # 1-5
        comment: str = ""
    ) -> None:
        """添加评价"""
        if agent_id not in self._reviews:
            self._reviews[agent_id] = []
        
        self._reviews[agent_id].append({
            "reviewer_id": reviewer_id,
            "rating": rating,
            "comment": comment,
            "timestamp": time.time()
        })
        
        # 计算评分影响
        avg_rating = self._calculate_avg_rating(agent_id)
        # 评分3为基准，高于3加分，低于3减分
        delta = (avg_rating - 3) * 2
        self.update_score(agent_id, delta)
    
    def _calculate_avg_rating(self, agent_id: str) -> float:
        """计算平均评分"""
        reviews = self._reviews.get(agent_id, [])
        if not reviews:
            return 3.0
        return sum(r["rating"] for r in reviews) / len(reviews)
    
    def on_task_success(self, agent_id: str) -> None:
        """任务成功回调"""
        self.update_score(agent_id, 0.5)
    
    def on_task_failed(self, agent_id: str) -> None:
        """任务失败回调"""
        self.update_score(agent_id, -2.0)
    
    def get_leaderboard(self, top_n: int = 10) -> List[Dict]:
        """获取排行榜"""
        sorted_agents = sorted(
            self._scores.items(),
            key=lambda x: x[1],
            reverse=True
        )
        return [
            {"rank": i + 1, "agent_id": aid, "score": score}
            for i, (aid, score) in enumerate(sorted_agents[:top_n])
        ]


class IncentiveSystem:
    """
    激励系统
    
    提供奖励池和激励机制
    """
    
    def __init__(self):
        self._reward_pool: float = 0.0
        self._claimable_rewards: Dict[str, float] = {}
    
    def add_to_pool(self, amount: float) -> None:
        """添加奖励到池中"""
        self._reward_pool += amount
    
    def calculate_reward(
        self,
        agent_id: str,
        calls: int,
        success_rate: float,
        avg_rating: float
    ) -> float:
        """计算奖励"""
        # 综合公式: calls * 成功率 * 评分系数
        base = min(calls, 100) * 0.1
        success_bonus = success_rate * 0.5
        rating_bonus = (avg_rating / 5.0) * 0.4
        
        return base * (1 + success_bonus + rating_bonus)
    
    def claim_reward(self, agent_id: str) -> float:
        """领取奖励"""
        reward = self._claimable_rewards.get(agent_id, 0)
        if reward > 0:
            self._claimable_rewards[agent_id] = 0
        return reward


class EconomyService:
    """
    经济服务 - 整合支付、声誉、激励
    """
    
    def __init__(self, payment_provider: Optional[PaymentProvider] = None):
        self.payment = payment_provider or TokenPaymentProvider()
        self.reputation = ReputationSystem()
        self.incentive = IncentiveSystem()
    
    async def charge_for_service(
        self,
        from_agent_id: str,
        to_agent_id: str,
        service_type: str,
        session_id: str,
        amount: float
    ) -> Optional[str]:
        """
        为服务收费
        
        Returns:
            交易ID 或 None
        """
        tx = Transaction(
            from_agent_id=from_agent_id,
            to_agent_id=to_agent_id,
            amount=amount,
            currency=Currency.TOKEN,
            service_type=service_type,
            session_id=session_id
        )
        
        if await self.payment.create_transaction(tx):
            return tx.id
        return None
    
    async def complete_payment(self, tx_id: str, success: bool = True) -> bool:
        """完成支付"""
        if success:
            result = await self.payment.execute_transaction(tx_id)
            # 更新声誉
            if result:
                # 获取交易信息更新声誉
                pass
            return result
        else:
            return await self.payment.refund_transaction(tx_id)
    
    async def get_agent_status(self, agent_id: str) -> Dict:
        """获取Agent经济状态"""
        balance = await self.payment.get_balance(agent_id)
        score = self.reputation.get_score(agent_id)
        
        return {
            "agent_id": agent_id,
            "balance": balance,
            "reputation_score": score,
            "reputation_level": self._get_reputation_level(score)
        }
    
    def _get_reputation_level(self, score: float) -> str:
        """获取声誉等级"""
        if score >= 90:
            return "🌟 卓越"
        elif score >= 80:
            return "⭐ 优秀"
        elif score >= 70:
            return "👍 良好"
        elif score >= 60:
            return "😐 一般"
        else:
            return "⚠️ 较差"


# 全局经济服务实例
_economy_service: Optional[EconomyService] = None


def get_economy_service() -> EconomyService:
    """获取经济服务实例"""
    global _economy_service
    if _economy_service is None:
        _economy_service = EconomyService()
    return _economy_service
