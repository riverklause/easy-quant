"""
移动平均线条件
"""

from screener.filter_condition import TechnicalCondition


class MACondition(TechnicalCondition):
    """移动平均线条件基类"""
    def __init__(self, name: str, period: int = 20):
        super().__init__(name=name, indicator_name=f'ma{period}')
        self.period = period

    def _calculate_indicator(self, data):
        from indicators.technical.trend.moving_average import SMA
        close = data['close']
        sma = SMA(period=self.period).calculate(close)
        if sma.empty:
            return None
        return sma.iloc[-1]


class PriceAboveMA(MACondition):
    """价格在MA之上"""
    def __init__(self, period: int = 20):
        name = f'PriceAboveMA{period}'
        super().__init__(name=name, period=period)

    def evaluate(self, data):
        ma_value = self._calculate_indicator(data)
        if ma_value is None or ma_value == 0:
            return False
        price = data['close'].iloc[-1]
        return price > ma_value


class PriceBelowMA(MACondition):
    """价格在MA之下"""
    def __init__(self, period: int = 20):
        name = f'PriceBelowMA{period}'
        super().__init__(name=name, period=period)

    def evaluate(self, data):
        ma_value = self._calculate_indicator(data)
        if ma_value is None or ma_value == 0:
            return False
        price = data['close'].iloc[-1]
        return price < ma_value


class CrossMA(TechnicalCondition):
    """均线交叉基类"""
    def __init__(self, name: str, fast_period: int = 5, slow_period: int = 20):
        super().__init__(name=name, indicator_name='cross')
        self.fast_period = fast_period
        self.slow_period = slow_period

    def _calculate_indicator(self, data):
        from indicators.technical.trend.moving_average import SMA
        close = data['close']
        fast_ma = SMA(period=self.fast_period).calculate(close)
        slow_ma = SMA(period=self.slow_period).calculate(close)
        if len(fast_ma) < 2 or len(slow_ma) < 2:
            return None
        return {
            'current_diff': fast_ma.iloc[-1] - slow_ma.iloc[-1],
            'prev_diff': fast_ma.iloc[-2] - slow_ma.iloc[-2]
        }


class GoldenCrossMA(CrossMA):
    """金叉 (短期MA上穿长期MA)"""
    def __init__(self, fast_period: int = 5, slow_period: int = 20):
        name = f'GoldenCrossMA_{fast_period}_{slow_period}'
        super().__init__(name=name, fast_period=fast_period, slow_period=slow_period)

    def evaluate(self, data):
        values = self._calculate_indicator(data)
        if values is None:
            return False
        return values['prev_diff'] < 0 and values['current_diff'] > 0


class DeathCrossMA(CrossMA):
    """死叉 (短期MA下穿长期MA)"""
    def __init__(self, fast_period: int = 5, slow_period: int = 20):
        name = f'DeathCrossMA_{fast_period}_{slow_period}'
        super().__init__(name=name, fast_period=fast_period, slow_period=slow_period)

    def evaluate(self, data):
        values = self._calculate_indicator(data)
        if values is None:
            return False
        return values['prev_diff'] > 0 and values['current_diff'] < 0
