"""
布林带指标
实现布林带技术分析指标，用于衡量价格波动范围
"""

import pandas as pd
import numpy as np
from typing import Union, List, Dict
from ...base.base_indicator import TechnicalIndicator


class BollingerBands(TechnicalIndicator):
    """布林带指标，使用时不需要指定周期，建议指标名为BOLL"""

    def __init__(self, period: int = 20, std_dev: float = 2.0, price_field: str = 'close'):
        """
        初始化布林带指标

        Args:
            period: 计算周期
            std_dev: 标准差倍数
            price_field: 价格字段名称
        """
        super().__init__(
            name=f"BollingerBands_{period}",
            description=f"布林带指标(周期={period}, 标准差={std_dev})",
            data_fields=[price_field],
            output_fields=['bb_middle', 'bb_upper', 'bb_lower'],
            period=period,
            std_dev=std_dev,
            price_field=price_field
        )
        self.period = period
        self.std_dev = std_dev
        self.price_field = price_field

    def calculate(self,
                  data: Union[pd.DataFrame, pd.Series],
                  **kwargs) -> Union[pd.Series, pd.DataFrame]:
        """
        计算布林带指标

        Args:
            data: 输入数据（预处理后）
            **kwargs: 计算参数

        Returns:
            布林带指标值（包含中轨、上轨、下轨）
        """
        self.validate_data(data)

        if isinstance(data, pd.Series):
            price_data = data
        else:
            try:
                price_data = data[self.price_field]
            except KeyError:
                raise ValueError(f"数据中未找到价格字段: {self.price_field}")

        middle_band = price_data.rolling(window=self.period).mean()

        std = price_data.rolling(window=self.period).std()

        upper_band = middle_band + (self.std_dev * std)
        lower_band = middle_band - (self.std_dev * std)

        if isinstance(data, pd.Series):
            return pd.DataFrame({
                'bb_middle': middle_band,
                'bb_upper': upper_band,
                'bb_lower': lower_band
            })
        else:
            result = data.copy()
            result['bb_middle'] = middle_band
            result['bb_upper'] = upper_band
            result['bb_lower'] = lower_band
            return result
