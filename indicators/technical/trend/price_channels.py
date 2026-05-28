"""
价格通道(Price Channels)
基于最高价和最低价的价格通道
"""

import pandas as pd
import numpy as np
from typing import Union, List, Dict
from ...base.base_indicator import TechnicalIndicator


class PriceChannels(TechnicalIndicator):
    """价格通道，使用时不需要设置参数，默认周期为20，建议指标名为PriceChannels"""

    def __init__(self, period: int = 20):
        """
        初始化价格通道指标

        Args:
            period: 计算周期，默认20
        """
        super().__init__(
            name=f"PriceChannels_{period}",
            description=f"价格通道(周期={period})",
            data_fields=['high', 'low'],
            output_fields=['upper', 'lower'],
            period=period
        )
        self.period = period

    def calculate(self,
                  data: Union[pd.DataFrame, pd.Series],
                  **kwargs) -> Union[pd.Series, pd.DataFrame, Dict]:
        """
        计算价格通道

        Args:
            data: 输入数据（预处理后），必须包含high、low字段
            **kwargs: 计算参数

        Returns:
            价格通道指标值，包含upper、lower两个字段
        """
        self.validate_data(data)

        if isinstance(data, pd.Series):
            raise ValueError("Price Channels需要high、low两个字段，无法从Series中计算")

        try:
            df = data[self.data_fields].copy()
        except KeyError as e:
            missing = [f for f in self.data_fields if f not in data.columns]
            raise ValueError(f"数据中未找到必要字段: {missing}")

        df['upper'] = df['high'].rolling(window=self.period).max()

        df['lower'] = df['low'].rolling(window=self.period).min()

        return df
