"""
RSI条件
"""

from screener.filter_condition import TechnicalCondition


class RSICondition(TechnicalCondition):
    """RSI条件基类"""

    def __init__(self, name: str, period: int = 14):
        super().__init__(name=name, indicator_name='rsi')
        self.period = period

    def _calculate_indicator(self, data):
        from indicators.technical.momentum.rsi import RSI
        result = RSI(period=self.period).calculate(data)
        if hasattr(result, 'iloc'):
            value = result['rsi'].iloc[-1]
            return value
        return result


class RSIOversold(RSICondition):
    """RSI超卖 (<30)"""
    def __init__(self, period: int = 14):
        super().__init__(name='RSI_Oversold', period=period)

    def evaluate(self, data):
        value = self._calculate_indicator(data)
        if value is None:
            return False
        return value < 30


class RSIOverbought(RSICondition):
    """RSI超买 (>70)"""
    def __init__(self, period: int = 14):
        super().__init__(name='RSI_Overbought', period=period)

    def evaluate(self, data):
        value = self._calculate_indicator(data)
        if value is None:
            return False
        return value > 70


class RSINormal(RSICondition):
    """RSI中性 (30-70)"""
    def __init__(self, period: int = 14):
        super().__init__(name='RSI_Normal', period=period)

    def evaluate(self, data):
        value = self._calculate_indicator(data)
        if value is None:
            return False
        return 30 <= value <= 70
