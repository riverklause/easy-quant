"""S1/S2：选股器暴露条件失败 + Stochastic 指标可评估。

S1 红因：StockScreener._filter_single / _filter_group 两处
`except Exception: pass` 把编程错误伪装成市场结论。
修法：保留"一个条件坏了不拖垮其它"，但必须计数 + logger.exception，
并提供 fail_fast 开关。

S2 红因：screener/conditions/technical/stochastic.py 从不存在的
indicators/technical/momentum/stochastic.py import Stochastic，
每次 evaluate() 都抛 ImportError。修法：复用 KDJ（已满足 T1 契约、
output_fields=['k','d','j']），%K 即随机指标。
"""

import pandas as pd
import pytest

from screener.filter_condition import FilterCondition
from screener.stock_screener import StockScreener


# ===== 共享测试夹具 =====

def _bars(n=30):
    index = pd.bdate_range("2024-01-01", periods=n)
    close = [10.0 + i for i in range(n)]
    return pd.DataFrame(
        {
            "open": close,
            "high": [c + 0.5 for c in close],
            "low": [c - 0.5 for c in close],
            "close": close,
            "volume": [1000] * n,
        },
        index=index,
    )


class _Boom(FilterCondition):
    """故意在 evaluate 里抛 RuntimeError 的条件。"""
    def __init__(self, name="boom"):
        super().__init__(name=name)

    def evaluate(self, data):
        raise RuntimeError("坏了")


class _AlwaysPass(FilterCondition):
    def __init__(self, name="ok"):
        super().__init__(name=name)

    def evaluate(self, data):
        return True


# ===== S1 =====

def test_S1_condition_failure_is_counted():
    """选股器必须暴露条件失败，而不是静默吞掉。"""
    from screener.conditions.technical.rsi import RSIOversold

    screener = StockScreener()
    screener.add_condition(_Boom())          # 条件级 RuntimeError
    screener.add_condition(RSIOversold())   # 正常条件

    results = screener.screen({"X": _bars()})

    assert screener.condition_errors == {"boom": 1}, \
        f"condition_errors 应为 boom:1，实际 {getattr(screener, 'condition_errors', '<不存在>')}"
    # 一个坏条件不拖垮其它（RSIOversold 在单调上行里全是 False，
    # 但至少要在结果里出现，而不是消失）
    assert "RSI_Oversold" in results


def test_S1_fail_fast_raises_instead_of_swallowing():
    """fail_fast=True 时，坏条件应直接抛错，用于测试/CI。"""
    screener = StockScreener(fail_fast=True)
    screener.add_condition(_Boom())

    with pytest.raises(RuntimeError, match="坏了"):
        screener.screen({"X": _bars()})


# ===== S2 =====

def test_S2_stochastic_overbought_on_uptrend():
    """单调上行序列 → KDJ 的 %K 应接近 100 → StochasticOverbought 通过。"""
    from screener.conditions.technical.stochastic import StochasticOverbought

    cond = StochasticOverbought(k_period=9)
    assert cond.evaluate(_bars()) is True


def test_S2_stochastic_oversold_on_downtrend():
    """单调下行序列 → KDJ 的 %K 应接近 0 → StochasticOversold 通过。"""
    from screener.conditions.technical.stochastic import StochasticOversold

    index = pd.bdate_range("2024-01-01", periods=30)
    close = [10.0 - i for i in range(30)]    # 单调下行
    bars = pd.DataFrame(
        {
            "open": close,
            "high": [c + 0.5 for c in close],
            "low": [c - 0.5 for c in close],
            "close": close,
            "volume": [1000] * 30,
        },
        index=index,
    )

    cond = StochasticOversold(k_period=9)
    assert cond.evaluate(bars) is True
