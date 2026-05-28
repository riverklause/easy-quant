"""
激进成长组合
专注于高成长性股票的策略组合
"""

from typing import List, Dict, Optional
from . import BasePortfolio


class AggressiveGrowthPortfolio(BasePortfolio):
    """
    激进成长组合
    追求高收益，适合风险承受能力强的投资者
    """
    
    def __init__(self):
        super().__init__(
            name="AggressiveGrowth",
            description="激进成长组合 - 追求高收益的成长型投资"
        )
        self._build_portfolio()
    
    def _build_portfolio(self):
        """构建组合配置"""
        
        # 策略1: 动量策略 - 捕捉强势股
        self.add_strategy(
            strategy_id="momentum_strategy",
            strategy_type="technical",
            indicators=["rsi", "macd", "atr"],
            params={
                "rsi_period": 14,
                "rsi_oversold": 35,
                "macd_fast": 12,
                "macd_slow": 26,
                "macd_signal": 9,
                "atr_multiplier": 2.0,
                "position_size": 0.4
            },
            applicable_stocks=None  # 全局策略
        )
        
        # 策略2: 成长股筛选 - 高动量因子
        self.add_strategy(
            strategy_id="growth_factor_strategy",
            strategy_type="multi_factor",
            indicators=["return_20d", "return_60d", "volume_ratio"],
            params={
                "momentum_threshold": 0.05,
                "volume_threshold": 1.5,
                "top_n": 5,
                "position_size": 0.35
            },
            applicable_stocks=None
        )
        
        # 策略3: 突破策略 - 捕捉突破行情
        self.add_strategy(
            strategy_id="breakout_strategy",
            strategy_type="technical",
            indicators=["price_channels", "volume_ma"],
            params={
                "channel_period": 20,
                "volume_ma_period": 20,
                "volume_threshold": 2.0,
                "position_size": 0.25
            },
            applicable_stocks=None
        )
        
        # 设置组合参数
        self.params = {
            "rebalance_frequency": "weekly",
            "max_position_size": 0.4,
            "stop_loss": 0.08,
            "take_profit": 0.20,
            "risk_level": "high"
        }


def get_aggressive_growth_portfolio() -> AggressiveGrowthPortfolio:
    """
    获取激进成长组合实例
    
    Returns:
        AggressiveGrowthPortfolio 实例
    """
    return AggressiveGrowthPortfolio()
