"""
平均趋向指数(ADX)
用于衡量趋势强度，不指示方向
"""

import pandas as pd
import numpy as np
from typing import Union, List, Dict
from ...base.base_indicator import TechnicalIndicator


class ADX(TechnicalIndicator):
    """平均趋向指数，使用时需要指定计算周期,建议指标名为ADX_周期"""

    def __init__(self, period: int = 14):
        """
        初始化平均趋向指数

        Args:
            period: 计算周期
        """
        super().__init__(
            name=f"ADX_{period}",
            description=f"平均趋向指数(周期={period})",
            data_fields=['high', 'low', 'close'],
            output_fields=['adx', 'plus_di', 'minus_di'],
            period=period
        )
        self.period = period

    def calculate(self,
                  data: Union[pd.DataFrame, pd.Series],
                  **kwargs) -> Union[pd.Series, pd.DataFrame, Dict]:
        """
        计算平均趋向指数

        Args:
            data: 输入数据（预处理后），必须包含high、low、close字段
            **kwargs: 计算参数

        Returns:
            ADX指标值，包含adx、plus_di、minus_di三个字段
        """
        self.validate_data(data)

        if isinstance(data, pd.Series):
            raise ValueError("ADX需要high、low、close三个字段，无法从Series中计算")

        try:
            df = data[self.data_fields].copy()
        except KeyError as e:
            missing = [f for f in self.data_fields if f not in data.columns]
            raise ValueError(f"数据中未找到必要字段: {missing}")

        df['tr1'] = df['high'] - df['low']
        df['tr2'] = abs(df['high'] - df['close'].shift(1))
        df['tr3'] = abs(df['low'] - df['close'].shift(1))
        df['tr'] = df[['tr1', 'tr2', 'tr3']].max(axis=1)

        df['plus_dm'] = np.where((df['high'] - df['high'].shift(1)) > (df['low'].shift(1) - df['low']),
                                np.maximum(df['high'] - df['high'].shift(1), 0), 0)
        df['minus_dm'] = np.where((df['low'].shift(1) - df['low']) > (df['high'] - df['high'].shift(1)),
                                 np.maximum(df['low'].shift(1) - df['low'], 0), 0)

        df['tr_ema'] = df['tr'].ewm(span=self.period, adjust=False).mean()
        df['plus_dm_ema'] = df['plus_dm'].ewm(span=self.period, adjust=False).mean()
        df['minus_dm_ema'] = df['minus_dm'].ewm(span=self.period, adjust=False).mean()

        df['plus_di'] = (df['plus_dm_ema'] / df['tr_ema']) * 100
        df['minus_di'] = (df['minus_dm_ema'] / df['tr_ema']) * 100

        df['dx'] = (abs(df['plus_di'] - df['minus_di']) / (df['plus_di'] + df['minus_di'])) * 100

        df['adx'] = df['dx'].ewm(span=self.period, adjust=False).mean()

        df.drop(columns=['tr1', 'tr2', 'tr3', 'tr', 'plus_dm', 'minus_dm',
            'tr_ema', 'plus_dm_ema', 'minus_dm_ema', 'dx'], inplace=True)

        return df
