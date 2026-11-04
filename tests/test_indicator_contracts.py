"""T1/T2：指标输出契约（技术指标闭集 / 基本面指标字典键）。"""

import pandas as pd
import pytest

from indicators.base.registry import IndicatorRegistry


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
