"""数据源频率回归：pandas 3 已移除 'M'，monthly 必须走 'ME'。"""

import asyncio

from backtest.datafeed.historical_datafeed import HistoricalDataFeed


def test_monthly_frequency_produces_bars():
    feed = HistoricalDataFeed(data_manager=None)
    bars = asyncio.run(
        feed.get_data(["X"], "2021-01-01", "2021-12-31", "monthly")
    )

    assert list(bars) == ["X"]
    assert len(bars["X"]) == 12
