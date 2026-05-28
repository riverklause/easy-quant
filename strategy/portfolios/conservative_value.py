"""
保守价值组合
专注于低估值、高股息股票的策略组合
"""

from typing import List, Dict, Optional
from . import BasePortfolio


class ConservativeValuePortfolio(BasePortfolio):
    """
    保守价值组合
    追求稳定收益，适合风险厌恶型投资者
    """
    
    def __init__(self):
        super().__init__(
            name="ConservativeValue",
            description="保守价值组合 - 追求稳定收益的价值型投资"
        )
        self._build_portfolio()
    
    def _build_portfolio(self):
        """构建组合配置"""
        
        # 策略1: 价值因子策略 - 低PE/PB
        self.add_strategy(
            strategy_id="value_factor_strategy",
            strategy_type="multi_factor",
            indicators=["pe_ratio", "pb_ratio", "dividend_yield"],
            params={
                "max_pe": 15,
                "max_pb": 2.0,
                "min_dividend_yield": 0.03,
                "top_n": 8,
                "position_size": 0.45
            },
            applicable_stocks=None
        )
        
        # 策略2: 低波动策略 - 降低风险
        self.add_strategy(
            strategy_id="low_volatility_strategy",
            strategy_type="technical",
            indicators=["atr", "std_channel", "bollinger_bands"],
            params={
                "atr_period": 14,
                "atr_multiplier": 1.5,
                "std_period": 20,
                "position_size": 0.30
            },
            applicable_stocks=None
        )
        
        # 策略3: 趋势跟踪策略 - 顺势而为
        self.add_strategy(
            strategy_id="trend_following_strategy",
            strategy_type="technical",
            indicators=["sma", "ema", "adx"],
            params={
                "sma_short": 20,
                "sma_long": 50,
                "adx_threshold": 25,
                "position_size": 0.25
            },
            applicable_stocks=None
        )
        
        # 设置组合参数
        self.params = {
            "rebalance_frequency": "monthly",
            "max_position_size": 0.45,
            "stop_loss": 0.05,
            "take_profit": 0.10,
            "risk_level": "low"
        }


def get_conservative_value_portfolio() -> ConservativeValuePortfolio:
    """
    获取保守价值组合实例
    
    Returns:
        ConservativeValuePortfolio 实例
    """
    return ConservativeValuePortfolio()
