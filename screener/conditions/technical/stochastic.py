"""
随机指标条件
"""

from screener.filter_condition import TechnicalCondition


class StochasticCondition(TechnicalCondition):
    """随机指标条件基类"""
    def __init__(self, name: str, k_period: int = 14):
        super().__init__(name=name, indicator_name='stochastic')
        self.k_period = k_period

    def _calculate_indicator(self, data):
        from indicators.technical.momentum.stochastic import Stochastic
        stoch = Stochastic(period=self.k_period)
        result = stoch.calculate(data)
        if hasattr(result, 'iloc'):
            value = result.iloc[-1]
            return value
        return result


class StochasticOversold(StochasticCondition):
    """随机指标超卖 (<20)"""
    def __init__(self, k_period: int = 14):
        super().__init__(name='Stochastic_Oversold', k_period=k_period)
        self.threshold = 20

    def evaluate(self, data):
        value = self._calculate_indicator(data)
        if value is None:
            return False
        return value < 20


class StochasticOverbought(StochasticCondition):
    """随机指标超买 (>80)"""
    def __init__(self, k_period: int = 14):
        super().__init__(name='Stochastic_Overbought', k_period=k_period)
        self.threshold = 80

    def evaluate(self, data):
        value = self._calculate_indicator(data)
        if value is None:
            return False
        return value > 80
