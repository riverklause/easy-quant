"""
平均真实波幅(ATR)
衡量价格波动性
"""

import pandas as pd
import numpy as np
from typing import Union, List, Dict
from ...base.base_indicator import TechnicalIndicator


class ATR(TechnicalIndicator):
    """平均真实波幅（ATR），使用时不需要指定周期，默认14,建议指标名为ATR"""

    def __init__(self, period: int = 14):
        """
        初始化平均真实波幅

        Args:
            period: 计算周期，默认14
        """
        super().__init__(
            name=f"ATR_{period}",
            description=f"平均真实波幅(周期={period})",
            data_fields=['high', 'low', 'close'],
            output_fields=['atr'],
            period=period
        )
        self.period = period

    def calculate(self,
                  data: Union[pd.DataFrame, pd.Series],
                  **kwargs) -> Union[pd.Series, pd.DataFrame]:
        """
        计算平均真实波幅

        Args:
            data: 输入数据（预处理后），必须包含high、low、close字段
            **kwargs: 计算参数

        Returns:
            ATR指标值
        """
        self.validate_data(data)

        if isinstance(data, pd.Series):
            raise ValueError("ATR需要high、low、close三个字段，无法从Series中计算")

        try:
            df = data[self.data_fields].copy()
        except KeyError as e:
            missing = [f for f in self.data_fields if f not in data.columns]
            raise ValueError(f"数据中未找到必要字段: {missing}")

        df['tr1'] = df['high'] - df['low']
        df['tr2'] = abs(df['high'] - df['close'].shift(1))
        df['tr3'] = abs(df['low'] - df['close'].shift(1))
        df['tr'] = df[['tr1', 'tr2', 'tr3']].max(axis=1)

        df['atr'] = df['tr'].ewm(span=self.period, adjust=False).mean()

        df.drop(columns=['tr1', 'tr2', 'tr3', 'tr'], inplace=True)

        return df
