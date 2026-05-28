"""
随机指标KDJ(Stochastic Oscillator)
衡量收盘价在一定周期内价格范围中的位置
"""

import pandas as pd
import numpy as np
from typing import Union, List, Dict
from ...base.base_indicator import TechnicalIndicator


class KDJ(TechnicalIndicator):
    """随机指标KDJ，使用时一般不需要指定周期，默认9,3,3,建议指标名为KDJ"""

    def __init__(self, k_period: int = 9, d_period: int = 3, smooth_period: int = 3):
        """
        初始化随机指标

        Args:
            k_period: %K周期，默认9
            d_period: %D周期，默认3
            smooth_period: %K平滑周期，默认3
        """
        super().__init__(
            name=f"KDJ_{k_period}_{d_period}_{smooth_period}",
            description=f"随机指标KDJ(K={k_period}, D={d_period}, Smooth={smooth_period})",
            data_fields=['high', 'low', 'close'],
            output_fields=['k', 'd', 'j'],
            k_period=k_period,
            d_period=d_period,
            smooth_period=smooth_period
        )
        self.k_period = k_period
        self.d_period = d_period
        self.smooth_period = smooth_period

    def calculate(self,
                  data: Union[pd.DataFrame, pd.Series],
                  **kwargs) -> Union[pd.Series, pd.DataFrame]:
        """
        计算随机指标

        Args:
            data: 输入数据（预处理后），必须包含high、low、close字段
            **kwargs: 计算参数

        Returns:
            随机指标值，包含k(%K)和d(%D)两个字段
        """
        self.validate_data(data)

        if isinstance(data, pd.Series):
            raise ValueError("KDJ需要high、low、close三个字段，无法从Series中计算")

        try:
            df = data[self.data_fields].copy()
        except KeyError as e:
            missing = [f for f in self.data_fields if f not in data.columns]
            raise ValueError(f"数据中未找到必要字段: {missing}")

        high_minus_low = df['high'].rolling(window=self.k_period).max() - df['low'].rolling(window=self.k_period).min()
        close_minus_low = df['close'] - df['low'].rolling(window=self.k_period).min()

        df['raw_k'] = 100 * (close_minus_low / high_minus_low)

        df['k'] = df['raw_k'].rolling(window=self.smooth_period).mean()

        df['d'] = df['k'].rolling(window=self.d_period).mean()

        df['j'] = 3 * df['k'] - 2 * df['d']

        df.drop(columns=['raw_k'], inplace=True)

        return df
