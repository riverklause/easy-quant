"""
能量潮(OBV)
将成交量与价格变化结合
"""

import pandas as pd
import numpy as np
from typing import Union, List, Dict
from ...base.base_indicator import TechnicalIndicator


class OBV(TechnicalIndicator):
    """能量潮指标，使用时不需要设置价格字段，默认价格字段为'close'，建议指标名为OBV"""

    def __init__(self, price_field: str = 'close'):
        """
        初始化能量潮指标

        Args:
            price_field: 价格字段名称，默认'close'
        """
        super().__init__(
            name="OBV",
            description="能量潮指标",
            data_fields=[price_field, 'volume'],
            output_fields=['obv'],
            price_field=price_field
        )
        self.price_field = price_field

    def calculate(self,
                  data: Union[pd.DataFrame, pd.Series],
                  **kwargs) -> Union[pd.Series, pd.DataFrame]:
        """
        计算能量潮指标

        Args:
            data: 输入数据（预处理后），需要价格和成交量字段
            **kwargs: 计算参数

        Returns:
            OBV指标值
        """
        self.validate_data(data)

        if isinstance(data, pd.Series):
            raise ValueError("OBV需要价格和成交量字段，无法从Series中计算")

        try:
            df = data[self.data_fields].copy()
        except KeyError as e:
            missing = [f for f in self.data_fields if f not in data.columns]
            raise ValueError(f"数据中未找到必要字段: {missing}")

        if len(df) < 2:
            df['obv'] = df['volume']
            return df

        df['price_change'] = df[self.price_field].diff()

        df['obv_increment'] = np.where(df['price_change'] > 0, df['volume'],
                                      np.where(df['price_change'] < 0, -df['volume'], 0))

        df['obv'] = df['obv_increment'].cumsum()

        df.drop(columns=['price_change', 'obv_increment'], inplace=True)

        return df
