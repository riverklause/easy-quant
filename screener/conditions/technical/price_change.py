"""
涨跌幅条件
"""

from screener.filter_condition import TechnicalCondition


class PriceChange(TechnicalCondition):
    """涨跌幅条件基类"""
    def __init__(self, name: str, period: int = 1):
        super().__init__(name=name, indicator_name='price_change')
        self.period = period

    def _calculate_indicator(self, data):
        close = data['close']
        if len(close) < self.period + 1:
            return None
        current_price = close.iloc[-1]
        past_price = close.iloc[-self.period - 1]
        if past_price == 0:
            return None
        return (current_price - past_price) / past_price * 100


class PriceUp(PriceChange):
    """上涨"""
    def __init__(self, period: int = 1):
        super().__init__(name=f'PriceUp_{period}d', period=period)

    def evaluate(self, data):
        value = self._calculate_indicator(data)
        if value is None:
            return False
        return value > 0


class PriceDown(PriceChange):
    """下跌"""
    def __init__(self, period: int = 1):
        super().__init__(name=f'PriceDown_{period}d', period=period)

    def evaluate(self, data):
        value = self._calculate_indicator(data)
        if value is None:
            return False
        return value < 0


class PriceChangeExceed(PriceChange):
    """涨跌幅超过X%"""
    def __init__(self, period: int = 1, threshold: float = 5):
        super().__init__(name=f'PriceChangeExceed_{threshold}pct_{period}d', period=period)
        self.threshold = threshold

    def evaluate(self, data):
        value = self._calculate_indicator(data)
        if value is None:
            return False
        return abs(value) > self.threshold
