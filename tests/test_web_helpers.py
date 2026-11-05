"""W1-W3：web 页面的数据辅助函数（不启动 Dash 运行时）。

路径常量在 import 时就算好了，所以测试用 monkeypatch 改模块属性，
把输入钉在 tmp_path，而不是依赖本机 data_dir。
"""

import logging

import pandas as pd


def _write_stock_list(path, rows):
    pd.DataFrame(rows, columns=["code", "name"]).to_parquet(path, index=False)


def test_W1_stock_list_display_handles_missing_and_present(monkeypatch, tmp_path):
    from web.pages import control_stock

    target = tmp_path / "StockList.parquet"
    monkeypatch.setattr(control_stock, "STOCK_LIST_FILE", target)

    # 文件缺失：返回提示组件，不抛
    placeholder = control_stock.get_stock_list_display()
    assert "暂无" in str(placeholder.children)

    # 文件存在：按 code 升序，Checklist 的 options 与数据一致
    _write_stock_list(target, [{"code": "US.AAPL", "name": "Apple"},
                               {"code": "HK.00700", "name": "腾讯"}])
    comp = control_stock.get_stock_list_display()
    options = comp.children[0].options
    assert [o["value"] for o in options] == ["HK.00700", "US.AAPL"]


def test_W2_screener_config_roundtrip(monkeypatch, tmp_path):
    from web.pages import control_strategy

    monkeypatch.setattr(
        control_strategy,
        "SCREENER_CONFIG_FILE",
        tmp_path / "ScreenerConfig.parquet",
    )

    assert control_strategy.get_screener_configs() == []

    control_strategy.save_screener_config({"name": "rsi", "threshold": 30})
    control_strategy.save_screener_config({"name": "macd", "threshold": 0})

    got = control_strategy.get_screener_configs()
    assert [c["name"] for c in got] == ["rsi", "macd"]


def test_W3_corrupt_stock_list_is_logged(monkeypatch, tmp_path, caplog):
    """文件损坏不能静默显示“暂无”：必须留下一条错误日志。"""
    from web.pages import control_stock

    target = tmp_path / "StockList.parquet"
    target.write_bytes(b"not a parquet")
    monkeypatch.setattr(control_stock, "STOCK_LIST_FILE", target)

    with caplog.at_level(logging.ERROR, logger="web.pages.control_stock"):
        comp = control_stock.get_stock_list_display()

    assert "暂无" in str(comp.children)
    assert "读取关注列表失败" in caplog.text
