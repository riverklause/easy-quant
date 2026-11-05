"""T1/T2：指标输出契约（技术指标闭集 / 基本面指标字典键）。

CL1/CL2：历史缓存按指标 ID 精确匹配，注销后必须清空。
"""

import pandas as pd
import pytest

from indicators.base.calculator import IndicatorCalculator
from indicators.base.registry import IndicatorRegistry
from indicators.technical.trend.moving_average import SMA


def _bars(n: int = 60) -> pd.DataFrame:
    idx = pd.bdate_range("2024-01-01", periods=n)
    close = [10.0 + i * 0.1 for i in range(n)]
    return pd.DataFrame({
        "open": close,
        "high": [c + 0.1 for c in close],
        "low": [c - 0.1 for c in close],
        "close": close,
        "volume": [1000 + i for i in range(n)],
    }, index=idx)


def _registry() -> IndicatorRegistry:
    reg = IndicatorRegistry()
    reg.load_indicators_from_package("indicators.technical")
    return reg


def _technical_instances():
    reg = _registry()
    items = []
    for name in reg.get_available_indicators():
        inst = reg.create_indicator(name)
        if ".fundamental." in type(inst).__module__:
            continue                      # 另一类契约，见 T2
        items.append(pytest.param(inst, id=name))
    return items


@pytest.mark.parametrize("indicator", _technical_instances())
def test_T1_technical_output_is_closed(indicator):
    df = _bars()
    result = indicator.calculate(df.copy())

    assert isinstance(result, pd.DataFrame), (
        f"{indicator.name} 对 DataFrame 输入返回了 {type(result).__name__}"
    )
    assert set(result.columns) == set(indicator.output_fields), (
        f"{indicator.name} 输出列 {sorted(result.columns)} != {indicator.output_fields}"
    )
    assert not (set(result.columns) & set(df.columns)), (
        f"{indicator.name} 回显了输入列"
    )


def _first_look_ahead_bar(indicator) -> int | None:
    """返回第一个“前缀计算 != 全量计算的前缀”的 t；因果指标返回 None。"""
    df = _bars()
    full = indicator.calculate(df.copy())

    for t in (10, 20, 40):
        partial = indicator.calculate(df.iloc[:t].copy())
        try:
            pd.testing.assert_frame_equal(
                partial,
                full.iloc[:t].loc[partial.index],
                check_names=False,
                rtol=1e-9,
            )
        except AssertionError:
            return t
    return None


@pytest.mark.parametrize("indicator", _technical_instances())
def test_T3_indicator_is_causal(indicator):
    """T3 因果性：t 时刻的指标值只能依赖 t 及之前的数据。

    L8 把引擎改成“全历史预计算 + 按 bar 切片”，这条灯是那次优化的安全网：
    任何用了全序列统计量（居中窗口、全量 z-score）的指标都会在这里红。
    """
    assert _first_look_ahead_bar(indicator) is None, (
        f"{indicator.name} 在某个 t 用到了未来数据"
    )


class _LookAheadIndicator:
    """T3 灵敏度自检用的反例：拿全序列最大值做归一化，必然泄漏未来。"""

    name = "LookAhead"

    @staticmethod
    def calculate(data: pd.DataFrame) -> pd.DataFrame:
        return pd.DataFrame({"z": data["close"] / data["close"].max()}, index=data.index)


def test_T3_detects_a_look_ahead_indicator():
    """自检：T3 的 oracle 不是摆设——故意泄漏未来的实现必须被判红。"""
    assert _first_look_ahead_bar(_LookAheadIndicator()) == 10


def test_T2_fundamental_output_is_declared_dict():
    reg = _registry()
    row = {
        "current_assets": 100.0, "current_liabilities": 40.0, "total_assets": 200.0,
        "retained_earnings": 30.0, "ebit": 20.0, "market_cap": 500.0,
        "total_liabilities": 60.0, "revenue": 300.0,
        "net_income": 25.0, "shareholders_equity": 140.0,
    }
    for name in ("AltmanZScore", "DupontAnalysis"):
        inst = reg.create_indicator(name)
        out = inst.calculate([dict(row)])
        assert set(out) == set(inst.output_fields), name


def _panel(symbol: str = "X", n: int = 60) -> pd.DataFrame:
    """构造 calculator 期望的 [time_key, code] MultiIndex 面板。"""
    bars = _bars(n)
    bars.index.name = "time_key"
    bars["code"] = symbol
    return bars.set_index("code", append=True)


def test_CL1_history_lookup_is_exact():
    """CL1：history 模式按指标 ID 精确取数，"sma_5" 不能命中 "sma_50"。"""
    calc = IndicatorCalculator()
    calc.register_indicator(SMA(period=5), "sma_5")
    calc.register_indicator(SMA(period=50), "sma_50")

    # 故意让 sma_50 先入缓存（字典插入序），旧的子串匹配会最先命中它
    calc.batch_calculate(_panel(), ["sma_50", "sma_5"], cache_mode="history")

    got = calc.get_indicator("X", "sma_5", cache_mode="history")
    assert got is not None
    assert got["sma"].iloc[-1] == pytest.approx(
        SMA(period=5).calculate(_panel())["sma"].iloc[-1]
    )


def test_CL2_unregister_clears_history_cache():
    """CL2：注销指标后，该指标的历史缓存必须被清掉。"""
    calc = IndicatorCalculator()
    calc.register_indicator(SMA(period=5), "sma_5")
    calc.batch_calculate(_panel(), ["sma_5"], cache_mode="history")

    assert calc._cache
    calc.unregister_indicator("sma_5")
    assert calc._cache == {}
