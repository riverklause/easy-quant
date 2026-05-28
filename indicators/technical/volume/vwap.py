"""
成交量加权平均价(VWAP)
用于日内交易的重要参考指标
"""

import pandas as pd
import numpy as np
from typing import Union, List, Dict
from ...base.base_indicator import TechnicalIndicator


class VWAP(TechnicalIndicator):
    """成交量加权平均价指标，日内交易用，建议指标名为VWAP"""

    def __init__(self):
        """
        初始化成交量加权平均价指标
        """
        super().__init__(
            name="VWAP",
            description="成交量加权平均价指标",
            data_fields=['high', 'low', 'close', 'volume'],
            output_fields=['vwap'],
        )

    def calculate(self,
                  data: Union[pd.DataFrame, pd.Series],
                  **kwargs) -> Union[pd.Series, pd.DataFrame]:
        """
        计算成交量加权平均价

        Args:
            data: 输入数据（预处理后），需要high、low、close和volume四个字段
            **kwargs: 计算参数

        Returns:
            VWAP指标值
        """
        self.validate_data(data)

        if isinstance(data, pd.Series):
            raise ValueError("VWAP需要high、low、close和volume四个字段，无法从Series中计算")

        try:
            df = data[self.data_fields].copy()
        except KeyError as e:
            missing = [f for f in self.data_fields if f not in data.columns]
            raise ValueError(f"数据中未找到必要字段: {missing}")

        df['tp'] = (df['high'] + df['low'] + df['close']) / 3

        df['cum_volume'] = df['volume'].cumsum()

        df['tp_volume'] = df['tp'] * df['volume']

        df['cum_tp_volume'] = df['tp_volume'].cumsum()

        df['vwap'] = df['cum_tp_volume'] / df['cum_volume']

        df.drop(columns=['tp', 'cum_volume', 'tp_volume', 'cum_tp_volume'], inplace=True)

        return df
