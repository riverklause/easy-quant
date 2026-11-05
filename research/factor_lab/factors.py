"""无量纲因子目录。

目录原则：**这里只放无量纲因子**——价格整体乘 100，因子面板不变
（尺度不变性）。裸 SMA、裸 MACD、裸 ATR 这类价格量纲的不放进来，
要先做 close/sma-1、hist/close、atr/close 之类归一化才能进。

入口函数签名统一 `fn(stock_data: Dict[str, pd.DataFrame]) -> pd.DataFrame`
（宽表，index=date, columns=symbol），供 FL6 尺度不变灯与后续
rank_ic / quantile_returns 直接消费。

FL6 参数化到 `__all__`：新增因子自动继承尺度不变检查，
不依赖作者记得补灯。

目录原则之二：**相关 > 0.85 视为同一因子**，只留一个。实测（10 只港股日线）
bias / bollinger_pb / cci / kdj_k / macd_hist_pct / rsi / wr 两两 0.59~0.87，
同属"价格在近期区间里的位置"家族；ADX 最大 |0.17|、ATR% 最大 |0.06|，
是目前唯二接近正交的维度。同族因子堆在目录里会让 meanIC 表把
同一件事重复测量多次，等权合成时还会互相抵消。
"""

from typing import Dict

import pandas as pd

from .adapter import indicator_factor
from .panel import to_panel


__all__ = [
    "adx_factor", "atr_pct_factor", "bias_factor", "bollinger_pb_factor",
    "cci_factor", "kdj_k_factor", "macd_hist_pct_factor", "rsi_factor", "wr_factor",
]

# 按"相关 > 0.85 视为同一因子"剪枝后的子集：每个维度只留一个代表。
# 保留 __all__ 全部（照旧受 FL6 参数化检查），这里只是报告/合成时的默认输入。
ACTIVE = ["adx_factor", "atr_pct_factor", "bias_factor", "rsi_factor"]


# ---- 直接无量纲（output_fields 里是 0–100 / −100–0 等范围量）---------

def rsi_factor(stock_data: Dict[str, pd.DataFrame], period: int = 14) -> pd.DataFrame:
    """RSI（0–100，直接无量纲）。"""
    from indicators.technical.momentum.rsi import RSI
    return indicator_factor(stock_data, RSI(period=period), "rsi")


def cci_factor(stock_data: Dict[str, pd.DataFrame], period: int = 14) -> pd.DataFrame:
    """CCI（无量纲振荡器）。"""
    from indicators.technical.momentum.cci import CCI
    return indicator_factor(stock_data, CCI(period=period), "cci")


def wr_factor(stock_data: Dict[str, pd.DataFrame], period: int = 14) -> pd.DataFrame:
    """Williams %R（−100–0，无量纲）。"""
    from indicators.technical.momentum.williams_r import WilliamsR
    return indicator_factor(stock_data, WilliamsR(period=period), "wr")


def kdj_k_factor(stock_data: Dict[str, pd.DataFrame],
                 k_period: int = 9,
                 d_period: int = 3,
                 smooth_period: int = 3) -> pd.DataFrame:
    """KDJ 的 %K（0–100，无量纲）。"""
    from indicators.technical.momentum.kdj import KDJ
    kdj = KDJ(k_period=k_period, d_period=d_period, smooth_period=smooth_period)
    return indicator_factor(stock_data, kdj, "k")


def adx_factor(stock_data: Dict[str, pd.DataFrame], period: int = 14) -> pd.DataFrame:
    """ADX（0–100，趋势强度，无量纲）。"""
    from indicators.technical.trend.adx import ADX
    return indicator_factor(stock_data, ADX(period=period), "adx")


# ---- 需归一化（指标本身是价格量纲）------------------------------------

def atr_pct_factor(stock_data: Dict[str, pd.DataFrame], period: int = 14) -> pd.DataFrame:
    """ATR / close（无量纲价格波动率）。"""
    from indicators.technical.volatility.atr import ATR
    atr = indicator_factor(stock_data, ATR(period=period), "atr")
    return atr / to_panel(stock_data, "close")


def bias_factor(stock_data: Dict[str, pd.DataFrame], period: int = 20) -> pd.DataFrame:
    """close / SMA − 1（无量纲乖离率）。"""
    from indicators.technical.trend.moving_average import SMA
    sma = indicator_factor(stock_data, SMA(period=period), "sma")
    return to_panel(stock_data, "close") / sma - 1


def bollinger_pb_factor(stock_data: Dict[str, pd.DataFrame],
                        period: int = 20) -> pd.DataFrame:
    """%B = (close − lower) / (upper − lower)，范围 0–1 之外可延伸。"""
    from indicators.technical.volatility.bollinger_bands import BollingerBands
    ind = BollingerBands(period=period)
    lower = indicator_factor(stock_data, ind, "bb_lower")
    upper = indicator_factor(stock_data, ind, "bb_upper")
    return (to_panel(stock_data, "close") - lower) / (upper - lower)


def macd_hist_pct_factor(stock_data: Dict[str, pd.DataFrame],
                         fast: int = 12, slow: int = 26,
                         signal: int = 9) -> pd.DataFrame:
    """MACD 柱 / close（价格量纲，必须归一化）。"""
    from indicators.technical.trend.moving_average import MACD
    hist = indicator_factor(stock_data,
                            MACD(fast_period=fast, slow_period=slow,
                                 signal_period=signal),
                            "histogram")
    return hist / to_panel(stock_data, "close")
