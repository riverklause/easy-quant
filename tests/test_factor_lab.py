"""FL0-FL6：research 隔离 + 面板地基 + RankIC + 分档 + 适配器 + 尺度不变。"""

import logging
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from research.factor_lab import factors as _factors

_ROOT = Path(__file__).resolve().parent.parent


# ===== FL0：生产包隔离 =====

def test_FL0_production_does_not_import_research():
    """backtest/data/indicators/screener/strategy/web 里不得出现 import research。"""
    forbidden = ("import research", "from research")
    for pkg in ("backtest", "data", "indicators", "screener", "strategy", "web"):
        for path in (_ROOT / pkg).rglob("*.py"):
            src = path.read_text(encoding="utf-8")
            for token in forbidden:
                assert token not in src, f"{path}: 出现了 '{token}'"


# ===== FL1 / FL1b：面板地基 =====

def _stock_data(symbols=("A", "B", "C"), rows: int = 40):
    idx = pd.bdate_range("2024-01-01", periods=rows)
    return {
        sym: pd.DataFrame(
            {"close": [10.0 + k + i * 0.1 for i in range(rows)]},
            index=idx,
        )
        for k, sym in enumerate(symbols)
    }


def test_FL1_panel_is_causal():
    """momentum(t) 只用到 ≤t 的数据（与 T3 同范式）。"""
    from research.factor_lab.panel import momentum, to_panel

    data = _stock_data()
    full = momentum(to_panel(data, "close"), window=5)

    for t in (6, 20, 39):
        truncated = momentum(to_panel(data, "close").iloc[:t], window=5)
        pd.testing.assert_frame_equal(truncated, full.iloc[:t], check_names=False)


def test_FL1b_panel_aligns_symbols_on_date_union():
    """to_panel 按日期并集对齐、缺失显式保留为 NaN。"""
    from research.factor_lab.panel import to_panel

    data = _stock_data()
    data["A"] = data["A"].drop(data["A"].index[10])    # A 缺一天

    panel = to_panel(data, "close")

    assert list(panel.columns) == ["A", "B", "C"]
    assert panel.shape[0] == 40                         # 并集，不是交集
    assert pd.isna(panel.loc[data["B"].index[10], "A"])  # 缺失显式保留为 NaN


# ===== FL2：RankIC 的秩语义 =====

def _value_panel(rows: int = 20, n: int = 30, seed: int = 0,
                 lo: float = 0.0, hi: float = 1.0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range("2024-01-01", periods=rows)
    cols = [f"S{i}" for i in range(n)]
    return pd.DataFrame(rng.uniform(lo, hi, (rows, n)), index=idx, columns=cols)


def _price_panel(rows: int = 20, n: int = 30, seed: int = 0) -> pd.DataFrame:
    """价格必须为正，forward_returns 才有意义。"""
    return _value_panel(rows, n, seed, lo=10.0, hi=11.0)


def test_FL2_rank_ic_is_one_for_identical_ordering():
    """因子与标签完全同序 ⇒ RankIC 恒为 1；最后一根 bar 没有前瞻收益。"""
    from research.factor_lab.ic import rank_ic
    from research.factor_lab.labels import forward_returns

    fwd = forward_returns(_price_panel(), horizon=1)
    ic = rank_ic(fwd.copy(), fwd)

    assert len(ic) == len(fwd.index) - 1
    assert np.allclose(ic.to_numpy(), 1.0)


def test_FL2b_rank_ic_ignores_monotone_transforms():
    """单调变换不改变秩 ⇒ RankIC 不变；Pearson 会变（钉住"用的是秩"）。"""
    from research.factor_lab.ic import rank_ic
    from research.factor_lab.labels import forward_returns

    fwd = forward_returns(_price_panel(), horizon=1)
    factor = _value_panel(seed=7, lo=0.0, hi=3.0)      # 0~3，exp 后强烈非线性

    ic_raw = rank_ic(factor, fwd)
    ic_exp = rank_ic(factor.map(np.exp), fwd)
    pd.testing.assert_series_equal(ic_raw, ic_exp, check_names=False)

    pearson_raw = factor.corrwith(fwd, axis=1)
    pearson_exp = factor.map(np.exp).corrwith(fwd, axis=1)
    overlap = pearson_raw.dropna().index
    assert not np.allclose(pearson_raw[overlap], pearson_exp[overlap])


# ===== FL3：小截面丢弃必须可见，且按"成对有效样本"计数 =====

def test_FL3_small_cross_sections_are_dropped_and_counted(caplog):
    """只有 3 只股票、要求 ≥5 → 全部丢弃，且必须留下日志。"""
    from research.factor_lab.ic import rank_ic
    from research.factor_lab.labels import forward_returns

    fwd = forward_returns(_price_panel(rows=5, n=3), horizon=1)

    with caplog.at_level(logging.WARNING, logger="research.factor_lab.ic"):
        ic = rank_ic(fwd.copy(), fwd, min_stocks=5)

    assert ic.empty
    assert "丢弃 5 个截面" in caplog.text


def test_FL3b_threshold_counts_pairs_not_columns():
    """10 列，但某日只有 2 个成对有效样本：该日必须丢弃。"""
    from research.factor_lab.ic import rank_ic
    from research.factor_lab.labels import forward_returns

    fwd = forward_returns(_price_panel(rows=6, n=10), horizon=1)
    factor = _value_panel(rows=6, n=10, seed=3)
    idx = fwd.index
    factor.loc[idx[2], factor.columns[2:]] = np.nan     # 该日只剩 2 个有效

    ic = rank_ic(factor, fwd, min_stocks=5)

    assert len(ic) == 4                                 # 6 行 - 该日 - 末行无标签
    assert idx[2] not in ic.index


# ===== FL4：分档收益（单调性 + 复用 min_stocks 语义 + 并列确定性）=====

def test_FL4_quantiles_are_monotone_when_label_tracks_factor():
    """标签严格随因子递增 ⇒ 五档平均前瞻收益必须单调递增。"""
    from research.factor_lab.quantile import quantile_returns

    factor = _value_panel(rows=20, n=100, seed=11)
    fwd = factor * 0.001                       # 标签是该因子的单调函数

    q = quantile_returns(factor, fwd, n_groups=5)

    assert list(q.columns) == ["Q1", "Q2", "Q3", "Q4", "Q5"]
    assert (q["Q2"] > q["Q1"]).all()
    assert (q["Q3"] > q["Q2"]).all()
    assert (q["Q4"] > q["Q3"]).all()
    assert (q["Q5"] > q["Q4"]).all()
    assert (q["Q5"] - q["Q1"] > 0).all()       # 多空价差为正


def test_FL4b_quantile_reuses_min_stocks():
    """10 列但某日只有 2 个成对有效样本：该日整行丢弃（与 rank_ic 同一语义）。"""
    from research.factor_lab.quantile import quantile_returns

    factor = _value_panel(rows=6, n=10, seed=3)
    factor.loc[factor.index[2], factor.columns[2:]] = np.nan
    fwd = factor * 0.001                       # 继承 NaN ⇒ 成对有效样本 = 2

    q = quantile_returns(factor, fwd, n_groups=5, min_stocks=5)

    assert factor.index[2] not in q.index
    assert len(q) == 5                         # 6 行 - 被丢的那行


def test_FL4c_ties_are_split_deterministically():
    """全并列值 + method='first' 会按列顺序切五档，没有空档。"""
    from research.factor_lab.quantile import quantile_returns

    idx = pd.bdate_range("2024-01-01", periods=1)
    cols = [f"S{i}" for i in range(10)]
    factor = pd.DataFrame([[1.0] * 10], index=idx, columns=cols)
    fwd = pd.DataFrame([np.arange(10) * 0.01], index=idx, columns=cols)

    q = quantile_returns(factor, fwd, n_groups=5, min_stocks=5)
    assert list(q.columns) == ["Q1", "Q2", "Q3", "Q4", "Q5"]
    # "average" 会让所有值落同一档 → 其余四档 NaN，行被 dropna(how='all') 保留
    # 但列是 NaN；"first" 按顺序切成 2/2/2/2/2，五档都有值
    assert not q.isna().any().any()


# ===== FL5：适配器 + FL6：无量纲因子目录 + 尺度不变 =====

def _ohlcv_stock_data(symbols=("A", "B", "C"), rows: int = 40,
                      seed: int = 0) -> dict:
    """符合多数技术指标 data_fields 要求的 OHLCV 数据。"""
    rng = np.random.default_rng(seed)
    idx = pd.bdate_range("2024-01-01", periods=rows)
    frames = {}
    for k, sym in enumerate(symbols):
        drift = np.arange(rows) * 0.05 + k
        close = 10.0 + drift + rng.normal(0, 0.2, rows)
        high = close + np.abs(rng.normal(0, 0.1, rows))
        low = close - np.abs(rng.normal(0, 0.1, rows))
        vol = 1000 + np.abs(rng.normal(0, 200, rows))
        frames[sym] = pd.DataFrame({
            "open": close - 0.05, "high": high, "low": low,
            "close": close, "volume": vol,
        }, index=idx)
    return frames


def test_FL5_adapter_builds_wide_panel_and_is_causal():
    """adapter 不引入面板级未来数据；截断重算与全量切片一致（与 T3 同范式）。"""
    from indicators.technical.momentum.rsi import RSI
    from research.factor_lab.adapter import indicator_factor

    data = _ohlcv_stock_data()
    rsi = RSI(period=10)
    full = indicator_factor(data, rsi, "rsi")

    for t in (15, 30, 39):
        truncated = indicator_factor(
            {sym: df.iloc[:t] for sym, df in data.items()}, rsi, "rsi")
        pd.testing.assert_frame_equal(truncated, full.iloc[:t], check_names=False)


def test_FL5b_adapter_rejects_unknown_field():
    """field 不在 indicator.output_fields 里 → ValueError（T1 契约从测试变生产用）。"""
    from indicators.technical.momentum.rsi import RSI
    from research.factor_lab.adapter import indicator_factor

    with pytest.raises(ValueError, match="RSI_10"):
        indicator_factor(_ohlcv_stock_data(), RSI(period=10), "bogus")


_ALL_FACTORS = [getattr(_factors, name) for name in _factors.__all__]


@pytest.mark.parametrize("fn", _ALL_FACTORS, ids=lambda f: f.__name__)
def test_FL6_factors_are_scale_invariant(fn):
    """目录里每一个因子：价格整体乘 100 → 因子面板不变。

    参数化到 __all__，新增因子自动继承检查，不依赖作者记得补灯。
    """
    data = _ohlcv_stock_data()
    scaled = {sym: df.assign(high=df.high * 100, low=df.low * 100,
                              close=df.close * 100, open=df.open * 100)
              for sym, df in data.items()}

    orig, scaled_out = fn(data), fn(scaled)
    assert np.allclose(orig.fillna(0).to_numpy(),
                       scaled_out.fillna(0).to_numpy(), equal_nan=True), \
        f"{fn.__name__} 在价格乘 100 后变化了（违反尺度不变）"
