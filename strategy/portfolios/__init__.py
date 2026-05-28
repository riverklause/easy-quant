"""
策略组合模块
提供模块化的策略组合定义和管理
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
from strategy.strategy_portfolio import StrategyPortfolio


class BasePortfolio(StrategyPortfolio):
    """
    策略组合基类
    继承自 StrategyPortfolio，扩展模块化支持
    """
    
    def __init__(self, name: str, description: str = ""):
        """
        初始化策略组合
        
        Args:
            name: 组合名称
            description: 组合描述
        """
        super().__init__(name)
        self.description = description
        self.params = {}
    
    def get_info(self) -> Dict:
        """获取组合信息"""
        return {
            'name': self.name,
            'description': self.description,
            'strategy_count': len(self.strategy_configs),
            'global_strategies_count': len(self.global_strategies),
            'stock_specific_strategies_count': sum(len(s) for s in self.stock_strategy_map.values()),
            'covered_stocks': len(self.stock_strategy_map),
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }


def create_portfolio_from_config(config: Dict) -> BasePortfolio:
    """
    从配置创建策略组合
    
    Args:
        config: 组合配置字典
        
    Returns:
        BasePortfolio 实例
    """
    portfolio = BasePortfolio(config['name'], config.get('description', ''))
    portfolio.created_at = datetime.fromisoformat(config['created_at'])
    portfolio.updated_at = datetime.fromisoformat(config['updated_at'])
    portfolio.strategy_configs = config['strategy_configs']
    portfolio.stock_strategy_map = config['stock_strategy_map']
    portfolio.global_strategies = config['global_strategies']
    portfolio.params = config.get('params', {})
    return portfolio


# 导出预定义组合
from .aggressive_growth import AggressiveGrowthPortfolio, get_aggressive_growth_portfolio
from .conservative_value import ConservativeValuePortfolio, get_conservative_value_portfolio
from .balanced import BalancedPortfolio, get_balanced_portfolio

__all__ = [
    'BasePortfolio',
    'create_portfolio_from_config',
    'AggressiveGrowthPortfolio',
    'get_aggressive_growth_portfolio',
    'ConservativeValuePortfolio',
    'get_conservative_value_portfolio',
    'BalancedPortfolio',
    'get_balanced_portfolio',
]
