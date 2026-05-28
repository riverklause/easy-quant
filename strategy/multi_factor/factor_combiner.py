"""
因子组合器
负责因子的标准化、加权、排名和综合评分
"""

from typing import List, Dict, Any
import pandas as pd


class FactorCombiner:
    """因子组合器，负责因子的标准化、加权和综合评分"""
    
    def __init__(self, 
                 factor_weights: Dict[str, float] = None,
                 standardization: bool = True,
                 winsorize: bool = True,
                 lower_quantile: float = 0.01,
                 upper_quantile: float = 0.99):
        """
        初始化因子组合器
        
        Args:
            factor_weights: 因子权重字典，默认等权重
            standardization: 是否进行因子标准化
            winsorize: 是否进行因子去极值
            lower_quantile: 去极值下分位数
            upper_quantile: 去极值上分位数
        """
        self.factor_weights = factor_weights or {}
        self.standardization = standardization
        self.winsorize = winsorize
        self.lower_quantile = lower_quantile
        self.upper_quantile = upper_quantile
    
    def combine_factors(self, 
                       factor_data: pd.DataFrame,
                       factor_names: List[str]) -> pd.Series:
        """
        组合多个因子，生成综合评分
        
        Args:
            factor_data: 包含多个因子值的DataFrame
            factor_names: 要组合的因子名称列表
            
        Returns:
            综合评分Series
        """
        # 1. 复制数据，避免修改原始数据
        processed_data = factor_data[factor_names].copy()
        
        # 2. 因子去极值
        if self.winsorize:
            for factor in factor_names:
                processed_data[factor] = self._winsorize(processed_data[factor])
        
        # 3. 因子标准化
        if self.standardization:
            for factor in factor_names:
                processed_data[factor] = self._standardize(processed_data[factor])
        
        # 4. 因子加权
        weights = self._get_weights(factor_names)
        
        # 5. 计算综合评分
        scores = processed_data.dot(pd.Series(weights))
        
        return scores
    
    def _winsorize(self, data: pd.Series) -> pd.Series:
        """
        因子去极值
        
        Args:
            data: 因子数据
            
        Returns:
            去极值后的因子数据
        """
        lower_bound = data.quantile(self.lower_quantile)
        upper_bound = data.quantile(self.upper_quantile)
        return data.clip(lower_bound, upper_bound)
    
    def _standardize(self, data: pd.Series) -> pd.Series:
        """
        因子标准化
        
        Args:
            data: 因子数据
            
        Returns:
            标准化后的因子数据
        """
        return (data - data.mean()) / data.std()
    
    def _get_weights(self, factor_names: List[str]) -> Dict[str, float]:
        """
        获取因子权重
        
        Args:
            factor_names: 因子名称列表
            
        Returns:
            因子权重字典
        """
        if not self.factor_weights:
            # 默认等权重
            weight = 1.0 / len(factor_names)
            return {name: weight for name in factor_names}
        else:
            # 检查所有因子是否都有权重，否则使用等权重填充
            weights = self.factor_weights.copy()
            for factor in factor_names:
                if factor not in weights:
                    weights[factor] = 1.0 / len(factor_names)
            return weights
    
    def rank_factors(self, scores: pd.Series, ascending: bool = False) -> pd.Series:
        """
        对综合评分进行排名
        
        Args:
            scores: 综合评分Series
            ascending: 是否升序排列
            
        Returns:
            排名结果
        """
        return scores.rank(ascending=ascending)
    
    def select_top_n(self, scores: pd.Series, top_n: int) -> List[str]:
        """
        根据综合评分选择top N个股票
        
        Args:
            scores: 综合评分Series
            top_n: 选股数量
            
        Returns:
            选中的股票代码列表
        """
        # 按评分降序排序，选择前top_n只股票
        selected = scores.sort_values(ascending=False).head(top_n)
        return selected.index.tolist()
    
    def set_weights(self, factor_weights: Dict[str, float]):
        """
        设置因子权重
        
        Args:
            factor_weights: 因子权重字典
        """
        self.factor_weights = factor_weights
    
    def get_weights(self) -> Dict[str, float]:
        """
        获取当前因子权重
        
        Returns:
            当前因子权重字典
        """
        return self.factor_weights.copy()
