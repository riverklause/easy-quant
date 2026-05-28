"""
订单执行器
负责订单的创建、匹配和执行
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, field
from abc import ABC, abstractmethod


class OrderType(Enum):
    """订单类型"""
    MARKET = "MARKET"           # 市价单
    LIMIT = "LIMIT"             # 限价单
    STOP = "STOP"               # 止损单
    STOP_LIMIT = "STOP_LIMIT"   # 止损限价单


class OrderSide(Enum):
    """订单方向"""
    BUY = "BUY"
    SELL = "SELL"


class OrderStatus(Enum):
    """订单状态"""
    PENDING = "PENDING"         # 待成交
    FILLED = "FILLED"          # 已成交
    PARTIAL = "PARTIAL"        # 部分成交
    CANCELLED = "CANCELLED"    # 已取消
    REJECTED = "REJECTED"      # 已拒绝


@dataclass
class Order:
    """
    订单
    """
    symbol: str
    side: OrderSide
    order_type: OrderType
    quantity: int
    price: Optional[float] = None
    stop_price: Optional[float] = None
    
    timestamp: datetime = field(default_factory=datetime.now)
    status: OrderStatus = OrderStatus.PENDING
    filled_quantity: int = 0
    filled_price: Optional[float] = None
    filled_time: Optional[datetime] = None
    order_id: str = field(default_factory=lambda: f"ORDER_{datetime.now().timestamp()}")
    
    def __post_init__(self):
        if self.order_type == OrderType.MARKET and self.price is not None:
            self.price = None
    
    def is_filled(self) -> bool:
        """是否完全成交"""
        return self.status in [OrderStatus.FILLED, OrderStatus.CANCELLED, OrderStatus.REJECTED]
    
    def is_active(self) -> bool:
        """是否活跃订单"""
        return self.status == OrderStatus.PENDING


class OrderExecutor(ABC):
    """
    订单执行器抽象基类
    定义订单执行的接口
    """
    
    @abstractmethod
    def execute_order(self, order: Order, current_price: float, 
                      current_time: datetime) -> Order:
        """
        执行订单
        
        Args:
            order: 订单
            current_price: 当前价格
            current_time: 当前时间
            
        Returns:
            执行后的订单
        """
        pass
    
    @abstractmethod
    def can_fill_order(self, order: Order, current_price: float) -> bool:
        """
        判断订单是否可以成交
        
        Args:
            order: 订单
            current_price: 当前价格
            
        Returns:
            是否可以成交
        """
        pass


class SimpleOrderExecutor(OrderExecutor):
    """
    简单订单执行器
    实现简单的订单执行逻辑
    """
    
    def __init__(self, slippage: float = 0.0, commission_rate: float = 0.001):
        """
        初始化订单执行器
        
        Args:
            slippage: 滑点比例
            commission_rate: 佣金费率
        """
        self.slippage = slippage
        self.commission_rate = commission_rate
        
        self.pending_orders: List[Order] = []
        self.filled_orders: List[Order] = []
        self.order_history: List[Order] = []
    
    def create_market_order(self, symbol: str, side: OrderSide, 
                           quantity: int) -> Order:
        """
        创建市价单
        
        Args:
            symbol: 股票代码
            side: 买卖方向
            quantity: 数量
            
        Returns:
            订单
        """
        order = Order(
            symbol=symbol,
            side=side,
            order_type=OrderType.MARKET,
            quantity=quantity
        )
        self.pending_orders.append(order)
        return order
    
    def create_limit_order(self, symbol: str, side: OrderSide,
                           quantity: int, limit_price: float) -> Order:
        """
        创建限价单
        
        Args:
            symbol: 股票代码
            side: 买卖方向
            quantity: 数量
            limit_price: 限价
            
        Returns:
            订单
        """
        order = Order(
            symbol=symbol,
            side=side,
            order_type=OrderType.LIMIT,
            quantity=quantity,
            price=limit_price
        )
        self.pending_orders.append(order)
        return order
    
    def create_stop_order(self, symbol: str, side: OrderSide,
                         quantity: int, stop_price: float) -> Order:
        """
        创建止损单
        
        Args:
            symbol: 股票代码
            side: 买卖方向
            quantity: 数量
            stop_price: 止损价格
            
        Returns:
            订单
        """
        order = Order(
            symbol=symbol,
            side=side,
            order_type=OrderType.STOP,
            quantity=quantity,
            stop_price=stop_price
        )
        self.pending_orders.append(order)
        return order
    
    def cancel_order(self, order_id: str) -> bool:
        """
        取消订单
        
        Args:
            order_id: 订单ID
            
        Returns:
            是否成功取消
        """
        for order in self.pending_orders:
            if order.order_id == order_id:
                order.status = OrderStatus.CANCELLED
                self.order_history.append(order)
                return True
        return False
    
    def can_fill_order(self, order: Order, current_price: float) -> bool:
        """
        判断订单是否可以成交
        
        Args:
            order: 订单
            current_price: 当前价格
            
        Returns:
            是否可以成交
        """
        if order.order_type == OrderType.MARKET:
            return True
        
        elif order.order_type == OrderType.LIMIT:
            if order.side == OrderSide.BUY:
                return current_price <= order.price
            else:
                return current_price >= order.price
        
        elif order.order_type == OrderType.STOP:
            if order.side == OrderSide.BUY:
                return current_price >= order.stop_price
            else:
                return current_price <= order.stop_price
        
        return False
    
    def execute_order(self, order: Order, current_price: float,
                      current_time: datetime) -> Order:
        """
        执行订单
        
        Args:
            order: 订单
            current_price: 当前价格
            current_time: 当前时间
            
        Returns:
            执行后的订单
        """
        if not self.can_fill_order(order, current_price):
            return order
        
        if order.side == OrderSide.BUY:
            filled_price = current_price * (1 + self.slippage)
        else:
            filled_price = current_price * (1 - self.slippage)
        
        order.filled_quantity = order.quantity
        order.filled_price = filled_price
        order.filled_time = current_time
        order.status = OrderStatus.FILLED
        
        if order in self.pending_orders:
            self.pending_orders.remove(order)
        
        self.filled_orders.append(order)
        self.order_history.append(order)
        
        return order
    
    def process_pending_orders(self, symbol: str, current_price: float,
                               current_time: datetime) -> List[Order]:
        """
        处理待成交订单
        
        Args:
            symbol: 股票代码
            current_price: 当前价格
            current_time: 当前时间
            
        Returns:
            成交的订单列表
        """
        filled_orders = []
        
        for order in self.pending_orders[:]:
            if order.symbol == symbol and order.is_active():
                self.execute_order(order, current_price, current_time)
                filled_orders.append(order)
        
        return filled_orders
    
    def get_pending_orders(self, symbol: str = None) -> List[Order]:
        """
        获取待成交订单
        
        Args:
            symbol: 股票代码过滤（可选）
            
        Returns:
            订单列表
        """
        if symbol:
            return [o for o in self.pending_orders if o.symbol == symbol and o.is_active()]
        return [o for o in self.pending_orders if o.is_active()]
    
    def get_filled_orders(self, symbol: str = None) -> List[Order]:
        """
        获取已成交订单
        
        Args:
            symbol: 股票代码过滤（可选）
            
        Returns:
            订单列表
        """
        if symbol:
            return [o for o in self.filled_orders if o.symbol == symbol]
        return self.filled_orders.copy()
    
    def get_order_statistics(self) -> Dict[str, Any]:
        """
        获取订单统计
        
        Returns:
            统计信息
        """
        return {
            'total_orders': len(self.order_history),
            'pending_orders': len(self.pending_orders),
            'filled_orders': len(self.filled_orders),
            'buy_orders': len([o for o in self.filled_orders if o.side == OrderSide.BUY]),
            'sell_orders': len([o for o in self.filled_orders if o.side == OrderSide.SELL]),
        }
    
    def reset(self):
        """重置执行器"""
        self.pending_orders.clear()
        self.filled_orders.clear()
        self.order_history.clear()
