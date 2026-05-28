"""
抛物线转向指标(Parabolic SAR)
用于判断趋势反转点
"""

import pandas as pd
import numpy as np
from typing import Union, List, Dict
from ...base.base_indicator import TechnicalIndicator


class ParabolicSAR(TechnicalIndicator):
    """抛物线转向指标，使用时不需要设置参数，建议指标名为SAR"""

    def __init__(self, af: float = 0.02, max_af: float = 0.2):
        """
        初始化抛物线转向指标

        Args:
            af: 加速因子，默认0.02
            max_af: 最大加速因子，默认0.2
        """
        super().__init__(
            name=f"ParabolicSAR_{af}_{max_af}",
            description=f"抛物线转向指标(AF={af}, MaxAF={max_af})",
            data_fields=['high', 'low', 'close'],
            output_fields=['sar'],
            af=af,
            max_af=max_af
        )
        self.af = af
        self.max_af = max_af

    def calculate(self,
                  data: Union[pd.DataFrame, pd.Series],
                  **kwargs) -> Union[pd.Series, pd.DataFrame, Dict]:
        """
        计算抛物线转向指标

        Args:
            data: 输入数据（预处理后），必须包含high、low、close字段
            **kwargs: 计算参数

        Returns:
            Parabolic SAR指标值
        """
        self.validate_data(data)

        if isinstance(data, pd.Series):
            raise ValueError("Parabolic SAR需要high、low、close三个字段，无法从Series中计算")

        try:
            df = data[self.data_fields].copy()
        except KeyError as e:
            missing = [f for f in self.data_fields if f not in data.columns]
            raise ValueError(f"数据中未找到必要字段: {missing}")

        if len(df) < 2:
            df['sar'] = df['close']
            return df

        sar = np.zeros(len(df))
        trend = np.zeros(len(df), dtype=int)
        af = np.full(len(df), self.af)
        ep = np.zeros(len(df))

        if df['close'].iloc[1] > df['close'].iloc[0]:
            trend[0] = 1
            sar[0] = df['low'].iloc[0]
            ep[0] = df['high'].iloc[1]
        else:
            trend[0] = -1
            sar[0] = df['high'].iloc[0]
            ep[0] = df['low'].iloc[1]

        for i in range(1, len(df)):
            sar[i] = sar[i-1] + af[i-1] * (ep[i-1] - sar[i-1])

            if trend[i-1] == 1:
                sar[i] = min(sar[i], df['low'].iloc[i-1])
                if i > 1:
                    sar[i] = min(sar[i], df['low'].iloc[i-2])

                if df['low'].iloc[i] <= sar[i]:
                    trend[i] = -1
                    sar[i] = ep[i-1]
                    ep[i] = df['low'].iloc[i]
                    af[i] = self.af
                else:
                    trend[i] = 1
                    if df['high'].iloc[i] > ep[i-1]:
                        ep[i] = df['high'].iloc[i]
                        af[i] = min(af[i-1] + self.af, self.max_af)
                    else:
                        ep[i] = ep[i-1]
                        af[i] = af[i-1]
            else:
                sar[i] = max(sar[i], df['high'].iloc[i-1])
                if i > 1:
                    sar[i] = max(sar[i], df['high'].iloc[i-2])

                if df['high'].iloc[i] >= sar[i]:
                    trend[i] = 1
                    sar[i] = ep[i-1]
                    ep[i] = df['high'].iloc[i]
                    af[i] = self.af
                else:
                    trend[i] = -1
                    if df['low'].iloc[i] < ep[i-1]:
                        ep[i] = df['low'].iloc[i]
                        af[i] = min(af[i-1] + self.af, self.max_af)
                    else:
                        ep[i] = ep[i-1]
                        af[i] = af[i-1]

        df['sar'] = sar

        return df
