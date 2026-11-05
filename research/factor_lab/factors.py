"""无量纲因子目录。

目录原则：**这里只放无量纲因子**——价格整体乘 100，因子面板不变
（尺度不变性）。裸 SMA、裸 MACD、裸 ATR 这类价格量纲的不放进来，
要先做 close/sma-1、hist/close、atr/close 之类归一化才能进。

入口函数签名统一 `fn(stock_data: Dict[str, pd.DataFrame]) -> pd.DataFrame`
（宽表，index=date, columns=symbol），供 FL6 尺度不变灯与后续
rank_ic / quantile_returns 直接消费。
"""

import pandas as pd

from .adapter import indicator_factor


# ---- 直接无量纲（output_fields 里是 0–100 / −100–0 等范围量）---------

def rsi_factor(stock_data: Dict[str, pd.DataFrame], period: int = 14) -> pd.DataFrame:
    """RSI（0–100，直接无量纲）。"""
    from indicators.technical.momentum.rsi import RSI
    return indicator_factor(stock_data, RSI(period=period), "rsi")


# ---- 需归一化（指标本身是价格量纲）------------------------------------

def atr_pct_factor(stock_data: Dict[str, pd.DataFrame], period: int = 14) -> pd.DataFrame:
    """ATR / close（无量纲价格波动率）。"""
    from indicators.technical.volatility.atr import ATR
    atr = indicator_factor(stock_data, ATR(period=period), "atr")
    close = pd.DataFrame({sym: df["close"] for sym, df in stock_data.items()}).sort_index()
    return atr / close


def bias_factor(stock_data: Dict[str, pd.DataFrame], period: int = 20) -> pd.DataFrame:
    """close / SMA − 1（无量纲乖离率）。"""
    from indicators.technical.trend.moving_average import SMA
    sma = indicator_factor(stock_data, SMA(period=period), "sma")
    close = pd.DataFrame({sym: df["close"] for sym, df in stock_data.items()}).sort_index()
    return close / sma - 1


def bollinger_pb_factor(stock_data: Dict[str, pd.DataFrame],
                        period: int = 20) -> pd.DataFrame:
    """%B = (close − lower) / (upper − lower)，范围 0–1 之外可延伸。"""
    from indicators.technical.volatility.bollinger_bands import BollingerBands
    ind = BollingerBands(period=period)
    lower = indicator_factor(stock_data, ind, "bb_lower")
    upper = indicator_factor(stock_data, ind, "bb_upper")
    close = pd.DataFrame({sym: df["close"] for sym, df in stock_data.items()}).sort_index()
    return (close - lower) / (upper - lower)
