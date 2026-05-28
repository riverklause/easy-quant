"""
多因子策略基类
专注于多因子策略规则定义，不负责因子计算
"""

from typing import List, Dict, Any, Union
import pandas as pd
import numpy as np
from strategy.base_strategy import BaseStrategy
from strategy.multi_factor.factor_combiner import FactorCombiner


class MultiFactorStrategy(BaseStrategy):
    """多因子策略基类"""
    
    def __init__(self, 
                 name: str,
                 factor_names: List[str],
                 factor_weights: Dict[str, float] = None,
                 lookback_period: int = 252,
                 top_n: int = 50,
                 rebalance_frequency: str = 'monthly'):
        """
        初始化多因子策略
        
        Args:
            name: 策略名称
            factor_names: 因子名称列表
            factor_weights: 因子权重字典
            lookback_period: 回测期数
            top_n: 选股数量
            rebalance_frequency: 调仓频率（daily, weekly, monthly）
        """
        # 调用父类初始化
        super().__init__(name)
        
        self.factor_names = factor_names
        self.factor_weights = factor_weights or {}
        self.lookback_period = lookback_period
        self.top_n = top_n
        self.rebalance_frequency = rebalance_frequency
        
        # 初始化因子组合器（只负责权重组合规则）
        self.combiner = FactorCombiner(factor_weights)
        
        # 更新策略参数
        self.update_params(
            factor_names=factor_names,
            factor_weights=factor_weights,
            lookback_period=lookback_period,
            top_n=top_n,
            rebalance_frequency=rebalance_frequency
        )
    
    def generate_scores(self, stock_data: Dict[str, pd.DataFrame]) -> pd.Series:
        """
        为所有股票生成综合评分
        
        Args:
            stock_data: 股票数据字典，key为股票代码，value为包含因子值的DataFrame
            
        Returns:
            股票综合评分Series，index为股票代码
        """
        scores = {}
        
        for symbol, data in stock_data.items():
            try:
                # 确保数据包含所有因子
                if all(factor in data.columns for factor in self.factor_names):
                    # 计算综合评分
                    score = self.combiner.combine_factors(
                        data.tail(self.lookback_period), 
                        self.factor_names
                    ).iloc[-1]
                    scores[symbol] = score
                else:
                    print(f"股票 {symbol} 缺少必要因子，跳过")
            except Exception as e:
                print(f"计算股票 {symbol} 评分失败: {e}")
                continue
        
        return pd.Series(scores)
    
    def select_stocks(self, scores: pd.Series) -> List[str]:
        """
        根据综合评分选股
        
        Args:
            scores: 股票综合评分Series
            
        Returns:
            选中的股票代码列表
        """
        # 按评分降序排序，选择前top_n只股票
        selected = scores.sort_values(ascending=False).head(self.top_n)
        return selected.index.tolist()
    
    def calculate_factor_contributions(self, 
                                     factor_data: pd.DataFrame,
                                     returns: pd.Series) -> Dict[str, float]:
        """
        计算各因子对策略收益的贡献
        
        Args:
            factor_data: 因子数据DataFrame
            returns: 股票收益率Series
            
        Returns:
            各因子的贡献度字典
        """
        contributions = {}
        
        # 标准化因子数据
        standardized_factors = factor_data[self.factor_names].apply(
            lambda x: (x - x.mean()) / x.std()
        )
        
        # 确保因子数据和收益率数据具有相同的索引
        # 使用共同的索引对齐数据
        common_index = standardized_factors.index.intersection(returns.index)
        if len(common_index) == 0:
            return contributions
        
        # 对齐数据
        aligned_factors = standardized_factors.loc[common_index]
        aligned_returns = returns.loc[common_index]
        
        # 计算因子暴露
        weights = self.combiner.get_weights()
        factor_exposures = aligned_factors.dot(pd.Series(weights))
        
        # 计算因子收益
        for factor in self.factor_names:
            # 计算单个因子的暴露
            factor_exposure = aligned_factors[factor]
            # 计算因子贡献
            contributions[factor] = np.cov(factor_exposure, aligned_returns)[0, 1] * weights.get(factor, 0)
        
        return contributions
    
    def evaluate_performance(self, 
                           portfolio_returns: pd.Series,
                           benchmark_returns: pd.Series = None) -> Dict[str, float]:
        """
        评估策略绩效
        
        Args:
            portfolio_returns: 组合收益率Series
            benchmark_returns: 基准收益率Series
            
        Returns:
            绩效指标字典
        """
        # 计算基本绩效指标
        performance = {
            'total_return': portfolio_returns.sum(),
            'annual_return': portfolio_returns.mean() * 252,
            'annual_volatility': portfolio_returns.std() * np.sqrt(252),
            'sharpe_ratio': (portfolio_returns.mean() / portfolio_returns.std()) * np.sqrt(252),
            'max_drawdown': self._calculate_max_drawdown(portfolio_returns),
        }
        
        # 计算信息比率（如果提供了基准）
        if benchmark_returns is not None:
            excess_returns = portfolio_returns - benchmark_returns
            performance['information_ratio'] = (excess_returns.mean() / excess_returns.std()) * np.sqrt(252)
            performance['alpha'] = excess_returns.mean() * 252
            performance['beta'] = np.cov(portfolio_returns, benchmark_returns)[0, 1] / benchmark_returns.var()
        
        return performance
    
    def _calculate_max_drawdown(self, returns: pd.Series) -> float:
        """
        计算最大回撤
        
        Args:
            returns: 收益率Series
            
        Returns:
            最大回撤
        """
        cumulative_returns = (1 + returns).cumprod()
        peak = cumulative_returns.expanding(min_periods=1).max()
        drawdown = (cumulative_returns / peak) - 1
        return drawdown.min()
    
    def set_factor_weights(self, factor_weights: Dict[str, float]):
        """
        设置因子权重
        
        Args:
            factor_weights: 因子权重字典
        """
        self.factor_weights = factor_weights
        self.combiner.set_weights(factor_weights)
    
    def get_factor_weights(self) -> Dict[str, float]:
        """
        获取当前因子权重
        
        Returns:
            当前因子权重字典
        """
        return self.factor_weights.copy()
    
    def rebalance(self, scores: pd.Series, current_portfolio: List[str] = None) -> Dict[str, float]:
        """
        调仓逻辑
        
        Args:
            scores: 股票综合评分Series
            current_portfolio: 当前持仓
            
        Returns:
            新的持仓权重字典
        """
        # 选择新的股票
        new_stocks = self.select_stocks(scores)
        
        # 计算持仓权重（等权重）
        weight = 1.0 / len(new_stocks)
        new_weights = {stock: weight for stock in new_stocks}
        
        return new_weights
    
    # BaseStrategy抽象方法实现
    def initialize(self, **kwargs):
        """
        初始化策略
        
        Args:
            **kwargs: 初始化参数
        """
        # 可以在这里进行额外的初始化操作
        print(f"🔄 策略 '{self.name}' 初始化完成")
    
    def generate_signals(self, factors_data: Dict[str, pd.DataFrame], **kwargs) -> List[Dict]:
        """
        生成交易信号
        
        Args:
            factors_data: 因子数据字典，key为股票代码，value为包含因子值的DataFrame
            **kwargs: 计算参数
            
        Returns:
            交易信号列表
        """
        if not isinstance(factors_data, dict):
            raise ValueError("输入数据必须是因子数据字典")
        
        signals = []
        
        try:
            # 验证因子数据是否包含所有所需因子
            missing_factors = []
            for symbol, data in factors_data.items():
                for factor in self.factor_names:
                    if factor not in data.columns:
                        missing_factors.append(f"{symbol}:{factor}")
            
            if missing_factors:
                raise ValueError(f"缺少必要因子: {missing_factors}")
            
            # 生成综合评分（应用规则）
            scores = self.generate_scores(factors_data)
            
            # 选股（应用规则）
            selected_stocks = self.select_stocks(scores)
            
            # 生成信号
            signal = {
                'type': 'SELECTION',
                'strategy_name': self.name,
                'timestamp': pd.Timestamp.now(),
                'selected_stocks': selected_stocks,
                'scores': scores.to_dict(),
                'signal_id': f"{self.name}_{pd.Timestamp.now().timestamp()}"
            }
            
            # 记录信号
            self.record_signal(signal)
            signals.append(signal)
            
        except Exception as e:
            print(f"❌ 策略 '{self.name}' 生成信号失败: {e}")
        
        return signals
    
    def update(self, factors_data: Dict[str, pd.DataFrame], **kwargs):
        """
        更新策略状态
        
        Args:
            factors_data: 因子数据字典
            **kwargs: 更新参数
        """
        # 更新策略参数
        if kwargs:
            self.update_params(**kwargs)
        
        # 更新因子权重
        if 'factor_weights' in kwargs:
            self.set_factor_weights(kwargs['factor_weights'])
        
        # 记录更新时间
        self.last_updated = pd.Timestamp.now()
