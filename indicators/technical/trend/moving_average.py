"""
移动平均线指标
实现简单移动平均线(SMA)、指数移动平均线(EMA)等趋势指标
"""

import pandas as pd
import numpy as np
from typing import Union, List, Dict, Optional
from ...base.base_indicator import TechnicalIndicator


class SMA(TechnicalIndicator):
    """简单移动平均线，使用时需要指定计算周期，价格字段一般为close,建议指标名为SMA_周期"""

    def __init__(self, period: int = 20, price_field: str = 'close'):
        """
        初始化简单移动平均线

        Args:
            period: 计算周期
            price_field: 价格字段名称
        """
        super().__init__(
            name=f"SMA_{period}",
            description=f"简单移动平均线(周期={period})",
            data_fields=[price_field],
            output_fields=['sma'],
            period=period,
            price_field=price_field
        )
        self.period = period
        self.price_field = price_field

    def calculate(self,
                  data: Union[pd.DataFrame, pd.Series],
                  **kwargs) -> Union[pd.Series, pd.DataFrame]:
        """
        计算简单移动平均线

        Args:
            data: 输入数据（预处理后）
            **kwargs: 计算参数

        Returns:
            移动平均线值
        """
        self.validate_data(data)

        if isinstance(data, pd.Series):
            price_data = data.copy()
        else:
            try:
                price_data = data[self.price_field]
            except KeyError:
                raise ValueError(f"数据中未找到价格字段: {self.price_field}")

        sma = price_data.rolling(window=self.period, min_periods=1).mean()

        if isinstance(data, pd.Series):
            return sma
        else:
            result = data.copy()
            result['sma'] = sma
            return result


class EMA(TechnicalIndicator):
    """指数移动平均线，使用时需要指定计算周期,价格字段一般为close,建议指标名为EMA_周期"""

    def __init__(self, period: int = 20, price_field: str = 'close'):
        """
        初始化指数移动平均线

        Args:
            period: 计算周期
            price_field: 价格字段名称
        """
        super().__init__(
            name=f"EMA_{period}",
            description=f"指数移动平均线(周期={period})",
            data_fields=[price_field],
            output_fields=['ema'],
            period=period,
            price_field=price_field
        )
        self.period = period
        self.price_field = price_field

    def calculate(self,
                  data: Union[pd.DataFrame, pd.Series],
                  **kwargs) -> Union[pd.Series, pd.DataFrame]:
        """
        计算指数移动平均线

        Args:
            data: 输入数据（预处理后）
            **kwargs: 计算参数

        Returns:
            指数移动平均线值
        """
        self.validate_data(data)

        if isinstance(data, pd.Series):
            price_data = data.copy()
        else:
            try:
                price_data = data[self.price_field]
            except KeyError:
                raise ValueError(f"数据中未找到价格字段: {self.price_field}")

        ema = price_data.ewm(span=self.period, adjust=False).mean()

        if isinstance(data, pd.Series):
            return ema
        else:
            result = data.copy()
            result['ema'] = ema
            return result


class MACD(TechnicalIndicator):
    """移动平均收敛散度指标，使用时一般不需要指定价格字段、快线、慢线和信号线周期，
    使用时建议指标名为MACD，如有修改建议指标名为MACD_快线周期_慢线周期_信号线周期_价格字段"""

    def __init__(self,
                 fast_period: int = 12,
                 slow_period: int = 26,
                 signal_period: int = 9,
                 price_field: str = 'close'):
        """
        初始化MACD指标

        Args:
            fast_period: 快线周期
            slow_period: 慢线周期
            signal_period: 信号线周期
            price_field: 价格字段名称
        """
        super().__init__(
            name="MACD",
            description=f"移动平均收敛散度指标(快线={fast_period}, 慢线={slow_period}, 信号线={signal_period})",
            data_fields=[price_field],
            output_fields=['macd', 'signal', 'histogram'],
            fast_period=fast_period,
            slow_period=slow_period,
            signal_period=signal_period,
            price_field=price_field
        )
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.signal_period = signal_period
        self.price_field = price_field

    def calculate(self,
                  data: Union[pd.DataFrame, pd.Series],
                  **kwargs) -> Union[pd.Series, pd.DataFrame, Dict]:
        """
        计算MACD指标

        Args:
            data: 输入数据（预处理后）
            **kwargs: 计算参数

        Returns:
            MACD指标值（包含MACD线、信号线、柱状图）
        """
        self.validate_data(data)

        if isinstance(data, pd.Series):
            price_data = data.copy()
        else:
            try:
                price_data = data[self.price_field]
            except KeyError:
                raise ValueError(f"数据中未找到价格字段: {self.price_field}")

        ema_fast = price_data.ewm(span=self.fast_period, adjust=False).mean()
        ema_slow = price_data.ewm(span=self.slow_period, adjust=False).mean()

        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=self.signal_period, adjust=False).mean()
        histogram = (macd_line - signal_line) * 2

        if isinstance(data, pd.Series):
            return pd.DataFrame({
                'macd': macd_line,
                'signal': signal_line,
                'histogram': histogram
            })
        else:
            result = data.copy()
            result['macd'] = macd_line
            result['signal'] = signal_line
            result['histogram'] = histogram
            return result
