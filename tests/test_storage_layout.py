"""存储路径布局契约灯：路径规则唯一来源是 LocalStorageManager，不允许回退成扁平布局。"""

import pandas as pd

from data.storage.local_storage import LocalStorageManager


def _storage(tmp_path):
    return LocalStorageManager(
        data_dir=str(tmp_path), cache_dir=str(tmp_path / "cache")
    )


def test_LS1_meta_layout(tmp_path):
    storage = _storage(tmp_path)

    assert storage.build_meta_path("StockList") == tmp_path / "meta" / "StockList.parquet"
    assert storage.build_meta_path("AlertConfig") == tmp_path / "meta" / "AlertConfig.parquet"


def test_LS1_data_layout(tmp_path):
    storage = _storage(tmp_path)

    assert storage.build_path(
        category="historical", symbol="US.AAPL", source="yfinance", period="daily"
    ) == tmp_path / "historical" / "yfinance" / "US_AAPL_daily.parquet"

    assert storage.build_path(
        category="realtime",
        symbol="US.AAPL",
        source="futu",
        period="quote",
        start_date="2025-09-07",
        end_date="2025-09-07",
    ) == tmp_path / "realtime" / "quote" / "futu" / "US_AAPL_realtime_quote_2025-09-07_2025-09-07.parquet"

    assert storage.build_path(
        category="screener",
        symbol="US.AAPL",
        source="yfinance",
        period="daily",
        start_date="2024-01-01",
        end_date="2024-12-31",
    ) == tmp_path / "screener" / "yfinance" / "US_AAPL_daily_2024-01-01_2024-12-31.parquet"

    assert storage.build_path(
        category="backtest",
        symbol="US.AAPL",
        source="yfinance",
        period="daily",
        start_date="2024-01-01",
        end_date="2024-12-31",
    ) == tmp_path / "backtest" / "yfinance" / "US_AAPL_daily_2024-01-01_2024-12-31.parquet"


def test_LS1_read_write_use_the_same_layout(tmp_path):
    """save_data/load_data 的 data_type 入口必须落到 build_path 的同一路径。"""
    storage = _storage(tmp_path)
    frame = pd.DataFrame(
        {"close": [1.0]}, index=pd.DatetimeIndex(["2024-01-01"], name="time_key")
    )

    assert storage.save_data(
        frame,
        symbol="US.AAPL",
        data_type="historical_daily",
        source="yfinance",
    )

    assert (
        tmp_path / "historical" / "yfinance" / "US_AAPL_daily.parquet"
    ).exists()

    loaded = storage.load_data(
        symbol="US.AAPL",
        data_type="historical_daily",
        source="yfinance",
        load_if_expired=True,
    )

    assert loaded is not None
    assert list(loaded["close"]) == [1.0]
