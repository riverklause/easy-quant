"""
技术指标过滤条件
"""

from screener.conditions.technical.rsi import RSIOversold, RSIOverbought, RSINormal
from screener.conditions.technical.macd import MACDGoldenCross, MACDDeathCross
from screener.conditions.technical.moving_average import PriceAboveMA, PriceBelowMA, GoldenCrossMA, DeathCrossMA
from screener.conditions.technical.volume import VolumeSpike, VolumeShrink
from screener.conditions.technical.price_change import PriceUp, PriceDown, PriceChangeExceed
from screener.conditions.technical.bollinger_band import PriceAtBBUpper, PriceAtBBLower
from screener.conditions.technical.stochastic import StochasticOversold, StochasticOverbought
from screener.conditions.technical.adx import StrongTrend, WeakTrend

__all__ = [
    'RSIOversold',
    'RSIOverbought',
    'RSINormal',
    'MACDGoldenCross',
    'MACDDeathCross',
    'PriceAboveMA',
    'PriceBelowMA',
    'GoldenCrossMA',
    'DeathCrossMA',
    'VolumeSpike',
    'VolumeShrink',
    'PriceUp',
    'PriceDown',
    'PriceChangeExceed',
    'PriceAtBBUpper',
    'PriceAtBBLower',
    'StochasticOversold',
    'StochasticOverbought',
    'StrongTrend',
    'WeakTrend'
]
