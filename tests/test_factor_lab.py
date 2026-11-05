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


# ===== FL7：IC 汇总 + 衰减 =====

def test_FL7_ic_summary_pins_ddof1_and_ir():
    """精确值钉住 ddof=1 与 IR 定义（ddof=0 会让 IR 差 20%+）。"""
    from research.factor_lab.ic import ic_summary

    s = ic_summary(pd.Series([0.1, -0.05, 0.2]))

    assert s.n == 3
    assert s.mean == pytest.approx(0.25 / 3)
    assert s.std == pytest.approx((0.03166666666666667 / 2) ** 0.5)   # ddof=1
    assert s.ir == pytest.approx(s.mean / s.std)
    assert s.positive_ratio == pytest.approx(2 / 3)
    assert s.t_stat == pytest.approx(s.ir * 3 ** 0.5)


def test_FL7c_ic_summary_on_empty_series():
    """空序列不抛异常：n=0，其余为 NaN。"""
    from research.factor_lab.ic import ic_summary

    s = ic_summary(pd.Series(dtype=float))

    assert s.n == 0
    assert np.isnan(s.mean) and np.isnan(s.ir)


def test_FL7b_ic_decay_is_strictly_monotone_for_an_iid_predictor():
    """因子 = 次日收益：h=1 时 IC=1，h 越大 IC≈1/√h，必须**严格**下降。

    合成数据里因子故意使用未来收益——它是"完美预测器"基准，不是研究用法。
    """
    from research.factor_lab.decay import ic_decay

    rng = np.random.default_rng(0)
    idx = pd.bdate_range("2024-01-01", periods=60)
    cols = [f"S{i}" for i in range(30)]
    ret = pd.DataFrame(rng.normal(0, 0.01, (60, 30)), index=idx, columns=cols)
    close = (1 + ret).cumprod()
    factor = close.pct_change().shift(-1)          # 次日收益

    decay = ic_decay(factor, close, horizons=(1, 2, 5, 10))

    assert list(decay.index) == [1, 2, 5, 10]
    assert decay.loc[1, "mean_ic"] == pytest.approx(1.0)
    assert (decay["mean_ic"].diff().dropna() < 0).all()   # 严格下降
    assert decay["n"].is_monotonic_decreasing             # 样本随 horizon 变少


# ===== FL8：因子相关性矩阵（逐日截面 Spearman 再取均值）=====

def test_FL8_correlation_is_rank_based_and_symmetric():
    """单调变换不改相关性（Pearson 会改）；f 与 -f 必须恰好 -1；矩阵对称、对角为 1。"""
    from research.factor_lab.cross_section import factor_correlation

    f = _value_panel(rows=12, n=20, seed=1)          # 0~1，立方后强烈非线性
    panels = {"f": f, "g": f.map(lambda x: x ** 3), "h": -f}

    r = factor_correlation(panels)

    assert list(r.matrix.columns) == ["f", "g", "h"]
    assert r.matrix.loc["f", "g"] == pytest.approx(1.0)
    assert r.matrix.loc["f", "h"] == pytest.approx(-1.0)
    assert np.allclose(np.diag(r.matrix.to_numpy()), 1.0)
    pd.testing.assert_frame_equal(r.matrix, r.matrix.T)

    # 钉住"用的是秩"：同样的数据按 Pearson 算明显小于 1
    pearson = f.corrwith(panels["g"], axis=1).mean()
    assert pearson < 0.99


def test_FL8b_correlation_averages_each_date_not_the_pooled_panel():
    """两天符号相反：逐日相关再取均值 = 0，把两天堆起来算会得到别的数。

    直接对面板求相关会把时间维度混进来——这正是这条灯要钉住的事。
    """
    from research.factor_lab.cross_section import factor_correlation

    idx = pd.bdate_range("2024-01-01", periods=3)
    cols = [f"S{i}" for i in range(6)]
    f = pd.DataFrame([[1.0, 2, 3, 4, 5, 6]] * 3, index=idx, columns=cols)
    g = pd.DataFrame([[2.0, 4, 6, 8, 10, 12],
                      [12.0, 10, 8, 6, 4, 2],
                      [1.0, 2, 4, 3, 6, 5]], index=idx, columns=cols)

    r = factor_correlation({"f": f, "g": g})
    expected = (1.0 - 1.0 + 15.5 / 17.5) / 3          # 第三日秩相关 = 15.5/17.5

    assert r.n.loc["f", "g"] == 3
    assert r.matrix.loc["f", "g"] == pytest.approx(expected)

    pooled = pd.concat([f.stack(), g.stack()], axis=1).corr(method="spearman")
    assert not r.matrix.loc["f", "g"] == pytest.approx(pooled.iloc[0, 1])


def test_FL8c_correlation_reuses_min_stocks_per_date():
    """某日只剩 2 个成对有效样本 ⇒ 该日不进平均，n 也随之少 1。"""
    from research.factor_lab.cross_section import factor_correlation

    f = _value_panel(rows=6, n=10, seed=3)
    g = _value_panel(rows=6, n=10, seed=4)
    f.loc[f.index[2], f.columns[2:]] = np.nan          # 该日只剩 2 个成对样本

    r = factor_correlation({"f": f, "g": g}, min_stocks=5)

    assert r.n.loc["f", "g"] == 5                      # 6 行 - 被丢的那行
    assert r.n.loc["g", "f"] == 5                      # 对称
    assert r.n.loc["f", "f"] == 5


# ===== FL9：秩必须在成对支撑集上取 =====

def _asymmetric_support_panels():
    """A 有 6 个有效值 [1..6]；B 只在 S0/S2/S5 有效，且在交集上严格反向。"""
    idx = pd.bdate_range("2024-01-01", periods=1)
    cols = [f"S{i}" for i in range(6)]
    a = pd.DataFrame([[1.0, 2.0, 3.0, 4.0, 5.0, 6.0]], index=idx, columns=cols)
    b = pd.DataFrame([[30.0, np.nan, 20.0, np.nan, np.nan, 10.0]],
                     index=idx, columns=cols)
    return a, b


def test_FL9_rank_ic_ranks_on_paired_support():
    """各面板自身取秩 → A 在交集上是 [1,3,6]，得到 −0.9934；
    在交集上取秩 → [1,2,3]，正确结果是 −1.0。"""
    from research.factor_lab.ic import rank_ic

    a, b = _asymmetric_support_panels()
    ic = rank_ic(a, b, min_stocks=3)

    assert len(ic) == 1
    assert ic.iloc[0] == pytest.approx(-1.0)


def test_FL9b_factor_correlation_uses_the_same_definition():
    """相关性矩阵与 rank_ic 必须共用同一个秩定义。"""
    from research.factor_lab.cross_section import factor_correlation

    a, b = _asymmetric_support_panels()
    result = factor_correlation({"A": a, "B": b}, min_stocks=3)

    assert result.matrix.loc["A", "B"] == pytest.approx(-1.0)
