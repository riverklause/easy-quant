"""
成交量条件
"""

from screener.filter_condition import TechnicalCondition


class VolumeCondition(TechnicalCondition):
    """成交量条件基类"""
    def __init__(self, name: str, period: int = 20, multiplier: float = 1.5):
        super().__init__(name=name, indicator_name='volume')
        self.period = period
        self.multiplier = multiplier

    def _calculate_indicator(self, data):
        from indicators.technical.trend.moving_average import SMA
        volume = data['volume']
        sma = SMA(period=self.period).calculate(volume)
        if sma.empty:
            return None
        current_vol = volume.iloc[-1]
        avg_value = sma.iloc[-1]
        if avg_value is None or avg_value == 0:
            return None
        return current_vol / avg_value


class VolumeSpike(VolumeCondition):
    """放量 (成交量>1.5倍均量)"""
    def __init__(self, period: int = 20, multiplier: float = 1.5):
        super().__init__(name=f'VolumeSpike_{multiplier}x', period=period, multiplier=multiplier)

    def evaluate(self, data):
        ratio = self._calculate_indicator(data)
        if ratio is None:
            return False
        return ratio > self.multiplier


class VolumeShrink(VolumeCondition):
    """缩量 (成交量<0.5倍均量)"""
    def __init__(self, period: int = 20, multiplier: float = 0.5):
        super().__init__(name=f'VolumeShrink_{multiplier}x', period=period, multiplier=multiplier)

    def evaluate(self, data):
        ratio = self._calculate_indicator(data)
        if ratio is None:
            return False
        return ratio < self.multiplier
