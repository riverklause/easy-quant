"""ADJ0-ADJ3：adj_close 列语义（源真值保留 / 缺列补 NaN / 不改入参）与 NET1 网络真值灯。"""

import asyncio
import os

import pandas as pd
import pytest


def _fake_download(ticker: str, n: int = 3) -> pd.DataFrame:
    """模拟 yf.download(group_by='ticker') 的返回：列是 (ticker, field) 多级索引。"""
    idx = pd.bdate_range("2024-05-01", periods=n)
    fields = ["Open", "High", "Low", "Close", "Adj Close", "Volume"]
    cols = pd.MultiIndex.from_product([[ticker], fields])
    values = [[10.0, 11.0, 9.0, 10.0, 9.0, 100.0]] * n
    return pd.DataFrame(values, index=idx, columns=cols)


def test_ADJ0_yfinance_batch_keeps_source_adj_close(monkeypatch):
    from data.sources import yfinance_client as mod

    client = mod.YFinanceClient(config={"yfinance_proxy": None})
    ticker = client._convert_symbol("HK.00700")

    monkeypatch.setattr(mod.yf, "download", lambda *a, **k: _fake_download(ticker))

    got = asyncio.run(
        client.get_batch_data(["HK.00700"], "2024-05-01", "2024-06-01")
    )

    assert "adj_close" in got.columns
    assert (got["adj_close"] == 9.0).all(), f"被覆盖成 {got['adj_close'].tolist()}"


def test_ADJ1_source_column_wins():
    """源给了真值就原样保留，helper 不得改写。"""
    from data.sources.adj_close import with_adj_close

    df = pd.DataFrame({"close": [10.0], "adj_close": [9.5]})
    assert with_adj_close(df)["adj_close"].iloc[0] == 9.5


def test_ADJ2_missing_column_is_nan_not_zero():
    """缺列补 NaN：0 会被当成"复权价为零"，NaN 才是"未知"。"""
    from data.sources.adj_close import with_adj_close

    got = with_adj_close(pd.DataFrame({"close": [10.0]}))
    assert got["adj_close"].isna().all(), "缺列必须补 NaN，不能是 0"


def test_ADJ3_does_not_mutate_input():
    """helper 不得就地修改入参，避免污染上游缓存。"""
    from data.sources.adj_close import with_adj_close

    df = pd.DataFrame({"close": [10.0]})
    with_adj_close(df)
    assert "adj_close" not in df.columns


@pytest.mark.skipif(
    os.getenv("NET_TESTS") != "1", reason="需代理+网络：NET_TESTS=1 运行"
)
def test_NET1_yfinance_adj_close_is_really_adjusted():
    """网络真值灯：确认 Yahoo 的 Adj Close 与 Close 不同，才配叫复权价。"""
    import yfinance as yf

    from utils.settings import settings

    proxy = settings.data.yfinance.get("yfinance_proxy")
    if proxy:
        yf.config.network.proxy = proxy

    df = yf.download(
        "KO", start="2024-05-01", end="2024-06-01",
        auto_adjust=False, progress=False, threads=False,
    )
    assert len(df) > 0, "下载为空（限流或代理未配置）"

    close = df["Close"]["KO"]
    adj = df["Adj Close"]["KO"]
    assert (adj - close).abs().max() > 0, (
        "Adj Close 与 Close 相同 → 该列不是复权价，不能写进 adj_close"
    )
