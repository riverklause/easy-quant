"""
指标计算基类
定义统一的指标接口规范
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Union
import pandas as pd
import numpy as np
from datetime import datetime


class BaseIndicator(ABC):
    """指标计算基类"""
    
    def __init__(self, 
                 name: str,
                 description: str = "",
                 version: str = "1.0.0",
                 **kwargs):
        """
        初始化指标
        
        Args:
            name: 指标名称
            description: 指标描述
            version: 指标版本
            **kwargs: 指标参数
        """
        self.name = name
        self.description = description
        self.version = version
        self.parameters = kwargs
        self._data_cache = {}
        self._last_calculation_time = None
        
    @abstractmethod
    def calculate(self, 
                  data: Union[pd.DataFrame, pd.Series, List[Dict]],
                  **kwargs) -> Union[pd.Series, pd.DataFrame, Dict]:
        """
        计算指标值
        
        Args:
            data: 输入数据，可以是DataFrame、Series或字典列表
            **kwargs: 计算参数
            
        Returns:
            指标计算结果
        """
        pass
    
    @abstractmethod
    def validate_data(self, data: Any) -> bool:
        """
        验证输入数据的有效性
        
        Args:
            data: 输入数据
            
        Returns:
            数据是否有效
        """
        pass
    
    def update(self, 
               new_data: Union[pd.DataFrame, pd.Series, Dict],
               **kwargs) -> Union[pd.Series, pd.DataFrame, Dict]:
        """
        增量更新指标值，部分指标可能不适用增量更新指标
        
        Args:
            new_data: 新增数据
            **kwargs: 更新参数
            
        Returns:
            更新后的指标值，默认是调用calculate方法重新计算
        """
        # 默认实现为重新计算
        return self.calculate(new_data, **kwargs)
    
    def get_info(self) -> Dict[str, Any]:
        """
        获取指标信息
        
        Returns:
            指标信息字典
        """
        return {
            'name': self.name,
            'description': self.description,
            'version': self.version,
            'parameters': self.parameters,
            'last_calculation_time': self._last_calculation_time
        }
    
    def reset(self):
        """重置指标状态"""
        self._data_cache.clear()
        self._last_calculation_time = None
    
    def __str__(self):
        """字符串表示"""
        return f"{self.name} (v{self.version})"
    
    def __repr__(self):
        """详细表示"""
        return f"{self.__class__.__name__}(name='{self.name}', parameters={self.parameters})"


class TechnicalIndicator(BaseIndicator):
    """技术指标基类"""
    
    def __init__(self, 
                 name: str,
                 data_fields: List[str],
                 output_fields: List[str],
                 **kwargs):
        """
        初始化技术指标
        
        Args:
            name: 指标名称
            data_fields: 需要的数据字段列表
            output_fields: 输出字段列表
            **kwargs: 指标参数
        """
        super().__init__(name, **kwargs)
        self.data_fields = data_fields
        self.output_fields = output_fields
        
    def validate_data(self, data: Any) -> bool:
        """验证技术指标数据"""
        if isinstance(data, pd.DataFrame):
            # 检查必需的字段是否存在
            missing_fields = [field for field in self.data_fields if field not in data.columns]
            if missing_fields:
                raise ValueError(f"缺少必需字段: {missing_fields}")
            return True
        elif isinstance(data, pd.Series):
            # 对于Series，不做检查默认认为是合法的
            return True
        elif isinstance(data, dict):
            # 明确拒绝单个字典输入
            raise TypeError(f"不支持的数据类型: {type(data)}。请使用 list[Dict] 格式输入数据。")
        elif isinstance(data, list) and all(isinstance(item, dict) for item in data):
            # 检查字典列表是否包含必需字段
            if len(data) > 0:
                missing_fields = [field for field in self.data_fields if field not in data[0]]
                if missing_fields:
                    raise ValueError(f"缺少必需字段: {missing_fields}")
            return True
        else:
            raise TypeError(f"不支持的数据类型: {type(data)}")


class StatisticalIndicator(BaseIndicator):
    """统计指标基类"""
    
    def __init__(self, name: str, **kwargs):
        """初始化统计指标"""
        super().__init__(name, **kwargs)
        
    def validate_data(self, data: Any) -> bool:
        """验证统计指标数据"""
        if isinstance(data, (pd.DataFrame, pd.Series)):
            return not data.empty
        else:
            raise TypeError(f"不支持的数据类型: {type(data)}")





# ---------------------- 因子相关基类 ----------------------

class BaseFactor(BaseIndicator):
    """因子基类，继承自BaseIndicator，扩展因子相关功能"""
    
    def __init__(self, 
                 name: str,
                 description: str,
                 data_fields: List[str],
                 output_fields: List[str],
                 factor_type: str,  # 因子类型：fundamental, technical, sentiment
                 **kwargs):
        """
        初始化因子
        
        Args:
            name: 因子名称
            description: 因子描述
            data_fields: 所需数据字段
            output_fields: 输出字段
            factor_type: 因子类型
            **kwargs: 其他参数
        """
        super().__init__(
            name=name,
            description=description,
            **kwargs
        )
        self.data_fields = data_fields
        self.output_fields = output_fields
        self.factor_type = factor_type
    
    def standardize(self, data: pd.Series) -> pd.Series:
        """
        因子标准化（Z-score）
        
        Args:
            data: 因子数据
            
        Returns:
            标准化后的因子数据
        """
        return (data - data.mean()) / data.std()
    
    def rank(self, data: pd.Series, ascending: bool = True) -> pd.Series:
        """
        因子排名
        
        Args:
            data: 因子数据
            ascending: 是否升序排列
            
        Returns:
            排名结果
        """
        return data.rank(ascending=ascending)
    
    def winsorize(self, data: pd.Series, lower_quantile: float = 0.01, upper_quantile: float = 0.99) -> pd.Series:
        """
        因子去极值（Winsorization）
        
        Args:
            data: 因子数据
            lower_quantile: 下分位数
            upper_quantile: 上分位数
            
        Returns:
            去极值后的因子数据
        """
        lower_bound = data.quantile(lower_quantile)
        upper_bound = data.quantile(upper_quantile)
        return data.clip(lower_bound, upper_bound)
    
    def neutralize(self, factor_data: pd.Series, industry_data: pd.Series) -> pd.Series:
        """
        因子行业中性化
        
        Args:
            factor_data: 因子数据
            industry_data: 行业分类数据
            
        Returns:
            行业中性化后的因子数据
        """
        # 使用线性回归去除行业影响
        df = pd.DataFrame({
            'factor': factor_data,
            'industry': industry_data
        })
        
        # 构建行业虚拟变量
        industry_dummies = pd.get_dummies(df['industry'], prefix='industry')
        X = industry_dummies
        y = df['factor']
        
        # 线性回归
        from sklearn.linear_model import LinearRegression
        model = LinearRegression()
        model.fit(X, y)
        
        # 计算残差作为中性化后的因子
        neutralized_factor = y - model.predict(X)
        
        return neutralized_factor


class TechnicalFactor(BaseFactor):
    """技术因子基类"""
    def __init__(self, name: str, description: str, data_fields: List[str], output_fields: List[str], **kwargs):
        super().__init__(
            name=name,
            description=description,
            data_fields=data_fields,
            output_fields=output_fields,
            factor_type='technical',
            **kwargs
        )


class FundamentalFactor(BaseFactor):
    """基本面因子基类"""
    def __init__(self, name: str, description: str, data_fields: List[str], output_fields: List[str], **kwargs):
        super().__init__(
            name=name,
            description=description,
            data_fields=data_fields,
            output_fields=output_fields,
            factor_type='fundamental',
            **kwargs
        )


class SentimentFactor(BaseFactor):
    """情绪因子基类"""
    def __init__(self, name: str, description: str, data_fields: List[str], output_fields: List[str], **kwargs):
        super().__init__(
            name=name,
            description=description,
            data_fields=data_fields,
            output_fields=output_fields,
            factor_type='sentiment',
            **kwargs
        )


class CompositeFactor(BaseFactor):
    """复合因子基类"""
    def __init__(self, name: str, description: str, data_fields: List[str], output_fields: List[str], **kwargs):
        super().__init__(
            name=name,
            description=description,
            data_fields=data_fields,
            output_fields=output_fields,
            factor_type='composite',
            **kwargs
        )
