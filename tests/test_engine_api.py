"""M1/M2：run 与 run_async 必须行为一致（同一实现的两个入口）。"""

import asyncio

import pandas as pd

from backtest.datafeed.historical_datafeed import HistoricalDataFeed
from backtest.engine.backtest_engine import BacktestEngine
from strategy.technical_strategy import TechnicalStrategy


class _BuyOnce(TechnicalStrategy):
    """每根 bar 都要求 BUY；有持仓后不再成交，所以结果恒为一笔。"""

    def __init__(self):
        super().__init__("m")
        self.required_indicators = []

    def apply_rules(self, indicators_data, **kwargs):
        return [{"type": "BUY"}]


class _SpyFeed(HistoricalDataFeed):
    def __init__(self):
        super().__init__(data_manager=None)
        self.calls = 0

    async def get_data(self, symbols, start_date, end_date, frequency="daily"):
        self.calls += 1
        return {symbol: _bars() for symbol in symbols}


def _bars(rows: int = 30) -> pd.DataFrame:
    idx = pd.bdate_range("2024-01-01", periods=rows)
    close = [10.0 + i * 0.1 for i in range(rows)]
    return pd.DataFrame({
        "open": close,
        "high": [c + 0.1 for c in close],
        "low": [c - 0.1 for c in close],
        "close": close,
        "volume": [1000] * rows,
    }, index=idx)


def _engine() -> BacktestEngine:
    return BacktestEngine(strategy=_BuyOnce(), datafeed=_SpyFeed(),
                          initial_capital=1_000_000)


def test_M1_run_and_run_async_agree():
    """同步入口与异步入口在同一 fixture 上必须产出同一结果。"""
    a, b = _engine(), _engine()

    r1 = a.run("2024-01-01", "2024-03-01", symbols=["X"])
    r2 = asyncio.run(b.run_async("2024-01-01", "2024-03-01", symbols=["X"]))

    assert r1.execution_failures == r2.execution_failures
    assert r1.data_source == r2.data_source
    assert r1.trades.equals(r2.trades)
    assert r1.equity_curve.equals(r2.equity_curve)


def test_M2_async_resolves_default_symbols():
    """symbols=None 时两条入口都要回落到默认标的，而不是把 None 传下去。"""
    engine = _engine()
    result = asyncio.run(engine.run_async("2024-01-01", "2024-03-01", symbols=None))

    assert "AAPL" in engine.get_data()
    assert len(result.equity_curve) > 0
