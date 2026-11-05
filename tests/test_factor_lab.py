"""FL0-FL1b：research 包隔离 + 因子面板因果性。

FL0（保护性）：生产包（backtest/data/indicators/screener/strategy/web）
不得 import research；今天即绿，写进来是为了防将来有人在生产代码里
顺手从 research 抄东西。

FL1 / FL1b（因果 + 对齐）：因子面板是所有 IC / 分档的地基，一旦泄漏
未来数据，IC 会好看得离谱且不可察觉。FL1 钉"t 列只依赖 ≤t 的数据"，
与 T3 同范式；FL1b 钉"并集对齐、缺失显式保留为 NaN"。
"""

from pathlib import Path

import pandas as pd
import pytest

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
