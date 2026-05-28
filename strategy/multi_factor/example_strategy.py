"""
示例多因子策略
展示如何使用多因子策略框架实现一个简单的多因子策略
专注于策略规则定义，不负责因子计算
"""

from typing import List, Dict, Any
import pandas as pd
import numpy as np
from strategy.multi_factor.multi_factor_strategy import MultiFactorStrategy


class SimpleValueMomentumStrategy(MultiFactorStrategy):
    """
    简单的价值动量多因子策略
    结合价值因子（PE、PB）和动量因子（20日收益率）
    专注于策略规则定义，不负责因子计算
    """
    
    def __init__(self, 
                 name: str = "SimpleValueMomentum",
                 top_n: int = 50,
                 lookback_period: int = 252,
                 rebalance_frequency: str = 'monthly'):
        """
        初始化简单价值动量多因子策略
        
        Args:
            name: 策略名称
            top_n: 选股数量
            lookback_period: 回测期数
            rebalance_frequency: 调仓频率
        """
        # 定义因子权重（价值因子60%，动量因子40%）
        factor_weights = {
            'pe_ratio': -0.3,   # PE越低越好，所以权重为负
            'pb_ratio': -0.3,   # PB越低越好，所以权重为负
            'return_20d': 0.4   # 动量越高越好，所以权重为正
        }
        
        # 调用父类构造函数
        super().__init__(
            name=name,
            factor_names=list(factor_weights.keys()),
            factor_weights=factor_weights,
            top_n=top_n,
            lookback_period=lookback_period,
            rebalance_frequency=rebalance_frequency
        )
    
    def define_rules(self, **kwargs):
        """
        定义策略规则
        
        Args:
            **kwargs: 规则参数
        """
        # 定义选股规则：选择综合评分最高的top_n只股票
        print(f"🔄 策略 '{self.name}' 规则定义完成")
        print(f"   - 因子权重: {self.factor_weights}")
        print(f"   - 选股数量: {self.top_n}")
        print(f"   - 调仓频率: {self.rebalance_frequency}")
    
    def run_strategy(self, factors_data: Dict[str, pd.DataFrame]) -> List[str]:
        """
        运行策略，生成选股结果
        
        Args:
            factors_data: 因子数据字典，key为股票代码，value为包含因子值的DataFrame
            
        Returns:
            选中的股票代码列表
        """
        # 生成综合评分（应用规则）
        scores = self.generate_scores(factors_data)
        
        # 选股
        selected_stocks = self.select_stocks(scores)
        
        return selected_stocks


class FamaFrenchThreeFactorStrategy(MultiFactorStrategy):
    """
    Fama-French三因子策略
    结合市场因子、市值因子和价值因子
    """
    
    def __init__(self, 
                 name: str = "FamaFrenchThreeFactor",
                 top_n: int = 50,
                 lookback_period: int = 252,
                 rebalance_frequency: str = 'monthly'):
        """
        初始化Fama-French三因子策略
        
        Args:
            name: 策略名称
            top_n: 选股数量
            lookback_period: 回测期数
            rebalance_frequency: 调仓频率
        """
        # 定义因子权重
        factor_weights = {
            'market_beta': 0.3,
            'size_factor': 0.3,   # 小市值溢价，所以权重为正
            'value_factor': 0.4   # 价值溢价，所以权重为正
        }
        
        # 调用父类构造函数
        super().__init__(
            name=name,
            factor_names=list(factor_weights.keys()),
            factor_weights=factor_weights,
            top_n=top_n,
            lookback_period=lookback_period,
            rebalance_frequency=rebalance_frequency
        )
    
    def calculate_factors(self, stock_data: Dict[str, pd.DataFrame]) -> Dict[str, pd.DataFrame]:
        """
        计算Fama-French三因子
        
        Args:
            stock_data: 股票数据字典
            
        Returns:
            包含因子值的股票数据字典
        """
        enhanced_data = {}
        
        # 计算市值因子需要所有股票的市值数据
        all_market_caps = []
        for symbol, data in stock_data.items():
            if 'market_cap' in data.columns:
                all_market_caps.append(data['market_cap'].iloc[-1])
        
        if all_market_caps:
            # 计算市值中位数
            median_market_cap = pd.Series(all_market_caps).median()
        else:
            median_market_cap = 0
        
        for symbol, data in stock_data.items():
            df = data.copy()
            
            # 计算市场beta（简化版本）
            if 'return' in df.columns and 'market_return' in df.columns:
                df['market_beta'] = df['return'].corr(df['market_return'])
            else:
                df['market_beta'] = 1.0
            
            # 计算市值因子（SMB - 小市值溢价）
            if 'market_cap' in df.columns:
                # 小市值股票获得正的size_factor
                df['size_factor'] = -np.log(df['market_cap']) / median_market_cap
            else:
                df['size_factor'] = 0
            
            # 计算价值因子（HML - 价值溢价）
            if 'pe_ratio' in df.columns:
                # 低PE股票获得正的value_factor
                df['value_factor'] = -df['pe_ratio']
            else:
                df['value_factor'] = 0
            
            enhanced_data[symbol] = df
        
        return enhanced_data
