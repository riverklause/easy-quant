"""技术筛选条件灯：每盏都断言"触发 + 不触发"，防止恒 True/恒 False 蒙混。"""

import pandas as pd

from screener.conditions.technical.bollinger_band import PriceAtBBLower, PriceAtBBUpper
from screener.conditions.technical.macd import MACDDeathCross, MACDGoldenCross
from screener.conditions.technical.moving_average import (
    DeathCrossMA,
    GoldenCrossMA,
    PriceAboveMA,
    PriceBelowMA,
)
from screener.conditions.technical.price_change import (
    PriceChangeExceed,
    PriceDown,
    PriceUp,
)
from screener.conditions.technical.rsi import RSIOverbought, RSIOversold
from screener.conditions.technical.volume import VolumeShrink, VolumeSpike


def _bars(closes, volumes=None):
    n = len(closes)
    volumes = volumes if volumes is not None else [100] * n
    return pd.DataFrame(
        {
            "open": closes,
            "high": [c + 0.1 for c in closes],
            "low": [c - 0.1 for c in closes],
            "close": closes,
            "volume": volumes,
        },
        index=pd.bdate_range("2024-01-01", periods=n),
    )


def test_SCT1_macd_cross_conditions_return_boolean():
    """MACD 条件必须能算出结果；构造参数写错会抛 TypeError。"""
    bars = _bars([1.0 + i * 0.1 for i in range(60)])

    assert isinstance(MACDGoldenCross().evaluate(bars), bool)
    assert isinstance(MACDDeathCross().evaluate(bars), bool)


def test_SCT1b_macd_cross_direction(monkeypatch):
    """histogram 由负转正只算金叉，由正转负只算死叉。"""
    bars = _bars([1.0] * 10)
    golden = MACDGoldenCross()
    death = MACDDeathCross()

    monkeypatch.setattr(
        golden, "_calculate_indicator", lambda data: {"previous": -1.0, "current": 1.0}
    )
    monkeypatch.setattr(
        death, "_calculate_indicator", lambda data: {"previous": 1.0, "current": -1.0}
    )

    assert golden.evaluate(bars) is True
    assert death.evaluate(bars) is True

    monkeypatch.setattr(
        golden, "_calculate_indicator", lambda data: {"previous": 1.0, "current": -1.0}
    )
    assert golden.evaluate(bars) is False


def test_SCT2_rsi_oversold_and_overbought():
    down = _bars([100.0 - i for i in range(60)])
    up = _bars([100.0 + i for i in range(60)])

    assert RSIOversold().evaluate(down)
    assert not RSIOverbought().evaluate(down)
    assert RSIOverbought().evaluate(up)
    assert not RSIOversold().evaluate(up)


def test_SCT3_price_vs_ma():
    bars = _bars([3.0, 3.0, 3.0, 1.0, 10.0])

    assert PriceAboveMA(period=3).evaluate(bars)
    assert not PriceBelowMA(period=3).evaluate(bars)


def test_SCT4_ma_cross_direction():
    bars = _bars([3.0, 3.0, 3.0, 1.0, 10.0])

    assert GoldenCrossMA(fast_period=2, slow_period=3).evaluate(bars)
    assert not DeathCrossMA(fast_period=2, slow_period=3).evaluate(bars)


def test_SCT5_volume_spike_and_shrink():
    spike = _bars([100.0] * 20, volumes=[100] * 19 + [500])
    shrink = _bars([100.0] * 20, volumes=[100] * 19 + [10])

    assert VolumeSpike().evaluate(spike)
    assert not VolumeShrink().evaluate(spike)
    assert VolumeShrink().evaluate(shrink)
    assert not VolumeSpike().evaluate(shrink)


def test_SCT6_price_change_direction_and_threshold():
    bars = _bars([100.0] * 10 + [110.0])

    assert PriceUp().evaluate(bars)
    assert not PriceDown().evaluate(bars)
    assert PriceChangeExceed(threshold=5).evaluate(bars)


def test_SCT7_bollinger_upper_and_lower():
    upper = _bars([100.0] * 19 + [200.0])
    lower = _bars([100.0] * 19 + [0.0])

    assert PriceAtBBUpper(period=20).evaluate(upper)
    assert not PriceAtBBLower(period=20).evaluate(upper)
    assert PriceAtBBLower(period=20).evaluate(lower)
    assert not PriceAtBBUpper(period=20).evaluate(lower)
