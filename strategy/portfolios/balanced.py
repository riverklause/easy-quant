"""
平衡型组合
结合成长和价值策略的平衡投资组合
"""

from typing import List, Dict, Optional
from . import BasePortfolio


class BalancedPortfolio(BasePortfolio):
    """
    平衡型组合
    在成长和价值之间寻求平衡
    """
    
    def __init__(self):
        super().__init__(
            name="Balanced",
            description="平衡型组合 - 成长与价值兼顾"
        )
        self._build_portfolio()
    
    def _build_portfolio(self):
        """构建组合配置"""
        
        # 策略1: 价值因子策略
        self.add_strategy(
            strategy_id="value_strategy",
            strategy_type="multi_factor",
            indicators=["pe_ratio", "pb_ratio", "dividend_yield"],
            params={
                "max_pe": 20,
                "max_pb": 3.0,
                "min_dividend_yield": 0.02,
                "top_n": 6,
                "position_size": 0.30
            },
            applicable_stocks=None
        )
        
        # 策略2: 动量因子策略
        self.add_strategy(
            strategy_id="momentum_strategy",
            strategy_type="multi_factor",
            indicators=["return_20d", "return_60d"],
            params={
                "momentum_threshold": 0.03,
                "top_n": 6,
                "position_size": 0.30
            },
            applicable_stocks=None
        )
        
        # 策略3: 质量因子策略
        self.add_strategy(
            strategy_id="quality_strategy",
            strategy_type="multi_factor",
            indicators=["roe", "debt_ratio", "profit_margin"],
            params={
                "min_roe": 0.15,
                "max_debt_ratio": 0.5,
                "min_profit_margin": 0.1,
                "top_n": 5,
                "position_size": 0.25
            },
            applicable_stocks=None
        )
        
        # 策略4: 技术趋势策略
        self.add_strategy(
            strategy_id="technical_trend_strategy",
            strategy_type="technical",
            indicators=["sma", "macd", "rsi"],
            params={
                "sma_short": 20,
                "sma_long": 60,
                "rsi_oversold": 35,
                "rsi_overbought": 65,
                "position_size": 0.15
            },
            applicable_stocks=None
        )
        
        # 设置组合参数
        self.params = {
            "rebalance_frequency": "biweekly",
            "max_position_size": 0.35,
            "stop_loss": 0.07,
            "take_profit": 0.15,
            "risk_level": "medium"
        }


def get_balanced_portfolio() -> BalancedPortfolio:
    """
    获取平衡型组合实例
    
    Returns:
        BalancedPortfolio 实例
    """
    return BalancedPortfolio()
