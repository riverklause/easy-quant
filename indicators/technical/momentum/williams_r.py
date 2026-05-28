"""
威廉指标(Williams %R)
超买超卖指标
"""

import pandas as pd
import numpy as np
from typing import Union, List, Dict
from ...base.base_indicator import TechnicalIndicator


class WilliamsR(TechnicalIndicator):
    """威廉指标（WMSR），使用时不需要指定周期，默认14,建议指标名为WMSR"""

    def __init__(self, period: int = 14, price_field: list = ['high', 'low', 'close']):
        """
        初始化威廉指标

        Args:
            period: 计算周期，默认14
        """
        super().__init__(
            name=f"WilliamsR_{period}",
            description=f"威廉指标(周期={period})",
            data_fields=price_field,
            output_fields=['wr'],
            period=period
        )
        self.period = period

    def calculate(self,
                  data: Union[pd.DataFrame, pd.Series],
                  **kwargs) -> Union[pd.Series, pd.DataFrame]:
        """
        计算威廉指标

        Args:
            data: 输入数据（预处理后），必须包含high、low、close字段
            **kwargs: 计算参数

        Returns:
            Williams %R指标值
        """
        self.validate_data(data)

        if isinstance(data, pd.Series):
            raise ValueError("Williams %R需要high、low、close三个字段，无法从Series中计算")

        try:
            df = data[self.data_fields].copy()
        except KeyError as e:
            missing = [f for f in self.data_fields if f not in data.columns]
            raise ValueError(f"数据中未找到必要字段: {missing}")

        highest_high = df['high'].rolling(window=self.period).max()
        lowest_low = df['low'].rolling(window=self.period).min()

        df['wr'] = (highest_high - df['close']) / (highest_high - lowest_low) * -100

        return df
