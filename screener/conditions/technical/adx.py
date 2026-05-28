"""
ADX趋势指标条件
"""

from screener.filter_condition import TechnicalCondition


class ADXCondition(TechnicalCondition):
    """ADX条件基类"""
    def __init__(self, name: str, period: int = 14):
        super().__init__(name=name, indicator_name='adx')
        self.period = period

    def _calculate_indicator(self, data):
        from indicators.technical.trend.adx import ADX
        adx_indicator = ADX(period=self.period)
        result = adx_indicator.calculate(data)
        if hasattr(result, 'iloc'):
            value = result.iloc[-1]
            return value
        return result


class StrongTrend(ADXCondition):
    """强趋势 (ADX>25)"""
    def __init__(self, period: int = 14, threshold: float = 25):
        super().__init__(name=f'StrongTrend_ADX{threshold}', period=period)
        self.threshold = threshold

    def evaluate(self, data):
        value = self._calculate_indicator(data)
        if value is None:
            return False
        return value > self.threshold


class WeakTrend(ADXCondition):
    """弱趋势 (ADX<20)"""
    def __init__(self, period: int = 14, threshold: float = 20):
        super().__init__(name=f'WeakTrend_ADX{threshold}', period=period)
        self.threshold = threshold

    def evaluate(self, data):
        value = self._calculate_indicator(data)
        if value is None:
            return False
        return value < self.threshold
