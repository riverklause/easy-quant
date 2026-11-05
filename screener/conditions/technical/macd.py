"""
MACD金叉/死叉条件
"""

from screener.filter_condition import TechnicalCondition


class MACDCross(TechnicalCondition):
    """MACD交叉基类"""

    def __init__(self, name: str, cross_type: str, fast: int = 12, slow: int = 26, signal: int = 9):
        super().__init__(name=name, indicator_name='macd')
        self.cross_type = cross_type
        self.fast = fast
        self.slow = slow
        self.signal = signal

    def _calculate_indicator(self, data):
        from indicators.technical.trend.moving_average import MACD
        result = MACD(fast_period=self.fast, slow_period=self.slow,
                      signal_period=self.signal).calculate(data)
        histogram = result['histogram'].dropna()
        if len(histogram) < 2:
            return None
        return {
            'current': float(histogram.iloc[-1]),
            'previous': float(histogram.iloc[-2])
        }

    def evaluate(self, data):
        values = self._calculate_indicator(data)
        if values is None:
            return False
        current = values['current']
        previous = values['previous']
        if self.cross_type == 'golden':
            return previous < 0 and current > 0
        else:
            return previous > 0 and current < 0


class MACDGoldenCross(MACDCross):
    """MACD金叉"""
    def __init__(self, fast: int = 12, slow: int = 26, signal: int = 9):
        super().__init__(name='MACD_Golden', cross_type='golden', fast=fast, slow=slow, signal=signal)


class MACDDeathCross(MACDCross):
    """MACD死叉"""
    def __init__(self, fast: int = 12, slow: int = 26, signal: int = 9):
        super().__init__(name='MACD_Death', cross_type='death', fast=fast, slow=slow, signal=signal)
