"""ADJ0：yfinance 批量结果里的 Adj Close 不能被 0 覆盖。

先红：yfinance_client 在 _process_dataframe 已把 'Adj Close' 映射成 'adj_close'，
随后又执行 result['adj_close'] = 0，把源返回的真实复权值抹掉。
"""

import asyncio

import pandas as pd


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
