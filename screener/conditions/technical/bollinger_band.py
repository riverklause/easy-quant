"""
布林带条件
"""

from screener.filter_condition import TechnicalCondition


class BollingerBandCondition(TechnicalCondition):
    """布林带条件基类"""
    def __init__(self, name: str, position: str, period: int = 20, std_dev: float = 2.0):
        super().__init__(name=name, indicator_name='bollinger')
        self.position = position
        self.period = period
        self.std_dev = std_dev

    def _calculate_indicator(self, data):
        from indicators.technical.volatility.bollinger_bands import BollingerBands
        bb = BollingerBands(period=self.period, std_dev=self.std_dev)
        result = bb.calculate(data)
        if not hasattr(result, 'iloc'):
            return None
        return {
            'price': data['close'].iloc[-1],
            'bb_upper': result['bb_upper'].iloc[-1],
            'bb_lower': result['bb_lower'].iloc[-1]
        }


class PriceAtBBUpper(BollingerBandCondition):
    """价格触及布林上轨"""
    def __init__(self, period: int = 20, std_dev: float = 2.0):
        super().__init__(name='BB_Upper', position='upper', period=period, std_dev=std_dev)

    def evaluate(self, data):
        values = self._calculate_indicator(data)
        if values is None:
            return False
        if values['bb_upper'] is None:
            return False
        return values['price'] >= values['bb_upper']


class PriceAtBBLower(BollingerBandCondition):
    """价格触及布林下轨"""
    def __init__(self, period: int = 20, std_dev: float = 2.0):
        super().__init__(name='BB_Lower', position='lower', period=period, std_dev=std_dev)

    def evaluate(self, data):
        values = self._calculate_indicator(data)
        if values is None:
            return False
        if values['bb_lower'] is None:
            return False
        return values['price'] <= values['bb_lower']
