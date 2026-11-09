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


def _write_legacy(symbol, source, adj_close, tmp_path):
    """直接落盘一个旧格式文件（绕过 save_data），模拟历史遗留数据。"""
    storage = _storage(tmp_path)
    frame = pd.DataFrame(
        {
            "close": [10.0, 11.0],
            "volume": [100, 200],
            "adj_close": adj_close,
        },
        index=pd.DatetimeIndex(["2024-01-01", "2024-01-02"], name="time_key"),
    )
    path = storage.build_path(category="historical", symbol=symbol, source=source)
    path.parent.mkdir(parents=True, exist_ok=True)
    frame.to_parquet(path)
    return storage, path


def test_LS4_load_turns_zero_adj_close_into_nan(tmp_path):
    """旧文件用 0 占位：读出来必须是 NaN，不能把"未知"当成"复权价为零"。"""
    storage, _ = _write_legacy("US.AAPL", "futu", [0, 0], tmp_path)

    loaded = storage.load_data(
        symbol="US.AAPL", data_type="historical_daily", source="futu"
    )

    assert loaded is not None
    assert loaded["adj_close"].isna().all(), (
        f"0 未归一：{loaded['adj_close'].tolist()}"
    )
    assert list(loaded["close"]) == [10.0, 11.0]


def test_LS4b_normalization_is_read_only_and_keeps_real_values(tmp_path):
    """归一化只作用于返回值：真值原样保留，磁盘文件不被改写。"""
    # 真值（含单个 NaN）不得被动
    storage, path = _write_legacy(
        "US.AAPL", "yfinance", [9.5, float("nan")], tmp_path
    )
    loaded = storage.load_data(
        symbol="US.AAPL", data_type="historical_daily", source="yfinance"
    )
    assert loaded["adj_close"].iloc[0] == 9.5
    assert pd.isna(loaded["adj_close"].iloc[1])

    # 旧文件读完后仍是 0：兜底在读时，不静默"修复"历史文件
    storage, path = _write_legacy("US.MSFT", "futu", [0, 0], tmp_path)
    storage.load_data(
        symbol="US.MSFT", data_type="historical_daily", source="futu"
    )
    assert (pd.read_parquet(path)["adj_close"] == 0).all(), "磁盘文件被改写了"
