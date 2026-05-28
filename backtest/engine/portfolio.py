"""
组合管理器
负责模拟持仓管理、收益计算和现金管理
"""

from typing import Dict, List, Optional
from datetime import datetime
from dataclasses import dataclass, field
import pandas as pd
import numpy as np


@dataclass
class Position:
    """持仓信息"""
    symbol: str
    quantity: int
    avg_price: float
    entry_date: datetime
    
    def market_value(self, current_price: float) -> float:
        """当前市值"""
        return self.quantity * current_price
    
    def profit(self, current_price: float) -> float:
        """浮动盈亏"""
        return (current_price - self.avg_price) * self.quantity


@dataclass
class PortfolioSnapshot:
    """组合快照"""
    date: datetime
    cash: float
    positions: Dict[str, Position]
    total_value: float
    daily_return: float


class Portfolio:
    """
    组合管理器
    职责：
    1. 持仓管理（买入、卖出、清仓）
    2. 收益计算
    3. 现金管理
    4. 历史记录
    """
    
    def __init__(self, 
                 initial_capital: float,
                 commission_rate: float = 0.001,
                 slippage: float = 0.0):
        """
        初始化组合管理器
        
        Args:
            initial_capital: 初始资金
            commission_rate: 佣金费率（默认0.1%）
            slippage: 滑点（默认0）
        """
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.commission_rate = commission_rate
        self.slippage = slippage
        
        self.positions: Dict[str, Position] = {}
        self.history: List[PortfolioSnapshot] = []
        self.trade_history: List[Dict] = []
        
        self._total_commission = 0.0
    
    def buy(self, 
            symbol: str, 
            quantity: int, 
            price: float, 
            date: datetime,
            adjust_price: bool = True) -> bool:
        """
        买入股票
        
        Args:
            symbol: 股票代码
            quantity: 买入数量
            price: 价格
            date: 交易日期
            adjust_price: 是否考虑滑点
            
        Returns:
            是否买入成功
        """
        if quantity <= 0:
            return False
        
        exec_price = price * (1 + self.slippage) if adjust_price else price
        cost = quantity * exec_price
        commission = cost * self.commission_rate
        total_cost = cost + commission
        
        if total_cost > self.cash:
            return False
        
        self.cash -= total_cost
        self._total_commission += commission
        
        if symbol in self.positions:
            pos = self.positions[symbol]
            total_quantity = pos.quantity + quantity
            total_cost_basis = pos.avg_price * pos.quantity + cost
            pos.quantity = total_quantity
            pos.avg_price = total_cost_basis / total_quantity
        else:
            self.positions[symbol] = Position(
                symbol=symbol,
                quantity=quantity,
                avg_price=exec_price,
                entry_date=date
            )
        
        self.trade_history.append({
            'date': date,
            'symbol': symbol,
            'action': 'BUY',
            'quantity': quantity,
            'price': exec_price,
            'commission': commission,
            'total_cost': total_cost
        })
        
        return True
    
    def sell(self, 
             symbol: str, 
             quantity: int, 
             price: float, 
             date: datetime,
             adjust_price: bool = True) -> bool:
        """
        卖出股票
        
        Args:
            symbol: 股票代码
            quantity: 卖出数量
            price: 价格
            date: 交易日期
            adjust_price: 是否考虑滑点
            
        Returns:
            是否卖出成功
        """
        if symbol not in self.positions:
            return False
        
        pos = self.positions[symbol]
        if quantity > pos.quantity:
            quantity = pos.quantity
        
        if quantity <= 0:
            return False
        
        exec_price = price * (1 - self.slippage) if adjust_price else price
        proceeds = quantity * exec_price
        commission = proceeds * self.commission_rate
        net_proceeds = proceeds - commission
        
        self.cash += net_proceeds
        self._total_commission += commission
        
        pos.quantity -= quantity
        if pos.quantity == 0:
            del self.positions[symbol]
        
        self.trade_history.append({
            'date': date,
            'symbol': symbol,
            'action': 'SELL',
            'quantity': quantity,
            'price': exec_price,
            'commission': commission,
            'net_proceeds': net_proceeds,
            'profit': (exec_price - pos.avg_price) * quantity if symbol in self.positions else 0
        })
        
        return True
    
    def get_position(self, symbol: str) -> Optional[Position]:
        """
        获取持仓
        
        Args:
            symbol: 股票代码
            
        Returns:
            持仓信息，如果不存在返回None
        """
        return self.positions.get(symbol)
    
    def get_positions_value(self, current_prices: Dict[str, float]) -> float:
        """
        获取持仓市值
        
        Args:
            current_prices: 当前价格字典
            
        Returns:
            持仓总市值
        """
        total = 0.0
        for symbol, pos in self.positions.items():
            if symbol in current_prices:
                total += pos.market_value(current_prices[symbol])
        return total
    
    def get_total_value(self, current_prices: Dict[str, float]) -> float:
        """
        获取总资产
        
        Args:
            current_prices: 当前价格字典
            
        Returns:
            总资产（现金+持仓市值）
        """
        return self.cash + self.get_positions_value(current_prices)
    
    def get_total_return(self, current_prices: Dict[str, float]) -> float:
        """
        获取总收益率
        
        Args:
            current_prices: 当前价格字典
            
        Returns:
            总收益率
        """
        current_value = self.get_total_value(current_prices)
        return (current_value - self.initial_capital) / self.initial_capital
    
    def record_snapshot(self, date: datetime, current_prices: Dict[str, float], prev_value: float = None):
        """
        记录组合快照
        
        Args:
            date: 日期
            current_prices: 当前价格
            prev_value: 昨日收盘总资产
        """
        total_value = self.get_total_value(current_prices)
        
        if prev_value and prev_value > 0:
            daily_return = (total_value - prev_value) / prev_value
        else:
            daily_return = 0.0
        
        snapshot = PortfolioSnapshot(
            date=date,
            cash=self.cash,
            positions=self.positions.copy(),
            total_value=total_value,
            daily_return=daily_return
        )
        self.history.append(snapshot)
        
        return snapshot
    
    def get_returns_series(self) -> pd.Series:
        """
        获取收益率序列
        
        Returns:
            收益率Series
        """
        if not self.history:
            return pd.Series(dtype=float)
        
        returns = [snapshot.daily_return for snapshot in self.history]
        dates = [snapshot.date for snapshot in self.history]
        
        return pd.Series(returns, index=pd.DatetimeIndex(dates), name='returns')
    
    def get_equity_curve(self) -> pd.DataFrame:
        """
        获取权益曲线
        
        Returns:
            包含日期、权益、收益率的DataFrame
        """
        if not self.history:
            return pd.DataFrame()
        
        data = []
        for snapshot in self.history:
            data.append({
                'date': snapshot.date,
                'equity': snapshot.total_value,
                'cash': snapshot.cash,
                'positions_value': snapshot.total_value - snapshot.cash,
                'daily_return': snapshot.daily_return
            })
        
        df = pd.DataFrame(data)
        df.set_index('date', inplace=True)
        
        return df
    
    def get_trade_history(self) -> pd.DataFrame:
        """
        获取交易历史
        
        Returns:
            交易历史DataFrame
        """
        if not self.trade_history:
            return pd.DataFrame()
        
        df = pd.DataFrame(self.trade_history)
        if not df.empty:
            df.set_index('date', inplace=True)
        
        return df
    
    def get_statistics(self) -> Dict:
        """
        获取组合统计信息
        
        Returns:
            统计信息字典
        """
        return {
            'initial_capital': self.initial_capital,
            'current_cash': self.cash,
            'total_positions_value': sum(
                pos.quantity * pos.avg_price 
                for pos in self.positions.values()
            ),
            'total_commission': self._total_commission,
            'total_trades': len(self.trade_history),
            'current_positions': len(self.positions)
        }
    
    def reset(self):
        """重置组合到初始状态"""
        self.cash = self.initial_capital
        self.positions.clear()
        self.history.clear()
        self.trade_history.clear()
        self._total_commission = 0.0
