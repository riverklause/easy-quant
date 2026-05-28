"""
过滤条件基类
"""

from abc import ABC, abstractmethod
from typing import Any, Dict


class FilterCondition(ABC):
    """过滤条件基类"""

    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    def evaluate(self, data: Any) -> bool:
        """评估数据是否符合条件"""
        pass


class TechnicalCondition(FilterCondition):
    """技术指标条件基类"""

    def __init__(self, name: str, indicator_name: str = ''):
        super().__init__(name)
        self.indicator_name = indicator_name

    def _calculate_indicator(self, data):
        """计算技术指标值"""
        pass
