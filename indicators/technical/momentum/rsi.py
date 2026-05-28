"""
相对强弱指标(RSI)
衡量证券价格上涨和下跌的力度
"""

import pandas as pd
import numpy as np
from typing import Union, List, Dict
from ...base.base_indicator import TechnicalIndicator


class RSI(TechnicalIndicator):
    """相对强弱指标，使用时需要指定计算周期，价格字段一般为close,建议指标名为RSI_周期"""

    def __init__(self, period: int = 14, price_field: str = 'close'):
        """
        初始化相对强弱指标

        Args:
            period: 计算周期
            price_field: 价格字段名称
        """
        super().__init__(
            name=f"RSI_{period}",
            description=f"相对强弱指标(周期={period})",
            data_fields=[price_field], #注意由于只要一个价格字段，所以要列表化
            output_fields=['rsi'],
            period=period,
            price_field=price_field
        )
        self.period = period
        self.price_field = price_field # 注意由于只要一个价格字段，
        # 所以不使用父类的data_fields，改用字符串的price_field后续计算只用pd.Series

    def calculate(self,
                  data: Union[pd.DataFrame, pd.Series],
                  **kwargs) -> Union[pd.Series, pd.DataFrame]:
        """
        计算相对强弱指标

        Args:
            data: 输入数据（预处理后）
            **kwargs: 计算参数

        Returns:
            RSI指标值
        """
        self.validate_data(data)

        if isinstance(data, pd.Series):
            price_data = data
        else:
            try:
                price_data = data[self.price_field] #得到的是pd.Series
            except KeyError:
                raise ValueError(f"数据中未找到价格字段: {self.price_field}")

        delta = price_data.diff()

        gain = (delta.where(delta > 0, 0)).rolling(window=self.period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=self.period).mean()

        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))

        if isinstance(data, pd.Series):
            return rsi
        else:
            result = data.copy()
            result['rsi'] = rsi
            return result
