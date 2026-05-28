"""
商品通道指数(CCI)
衡量价格偏离统计平均值的程度
"""

import pandas as pd
import numpy as np
from typing import Union, List, Dict
from ...base.base_indicator import TechnicalIndicator


class CCI(TechnicalIndicator):
    """商品通道指数,使用时一般不需要指定计算周期,默认14,建议指标名为CCI"""

    def __init__(self, period: int = 14):
        """
        初始化商品通道指数

        Args:
            period: 计算周期，默认14
        """
        super().__init__(
            name=f"CCI_{period}",
            description=f"商品通道指数(周期={period})",
            data_fields=['high', 'low', 'close'],
            output_fields=['cci'],
            period=period
        )
        self.period = period

    def calculate(self,
                  data: Union[pd.DataFrame, pd.Series],
                  **kwargs) -> Union[pd.Series, pd.DataFrame]:
        """
        计算商品通道指数

        Args:
            data: 输入数据（预处理后），必须包含high、low、close字段
            **kwargs: 计算参数

        Returns:
            CCI指标值
        """
        self.validate_data(data)

        if isinstance(data, pd.Series):
            raise ValueError("CCI需要high、low、close三个字段，无法从Series中计算")

        try:
            df = data[self.data_fields].copy()
        except KeyError as e:
            missing = [f for f in self.data_fields if f not in data.columns]
            raise ValueError(f"数据中未找到必要字段: {missing}")

        df['tp'] = (df['high'] + df['low'] + df['close']) / 3

        df['tp_sma'] = df['tp'].rolling(window=self.period).mean()

        df['md'] = df['tp'].rolling(window=self.period).apply(
            lambda x: abs(x - x.mean()).mean()
        )

        df['cci'] = (df['tp'] - df['tp_sma']) / (0.015 * df['md'])

        df.drop(columns=['tp', 'tp_sma', 'md'], inplace=True)

        return df
