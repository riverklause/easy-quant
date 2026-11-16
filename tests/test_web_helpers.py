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


def test_W4_load_kline_data_normalizes_legacy_adj_close(monkeypatch, tmp_path):
    """K线页直接读 parquet，必须同样套用 adj_close 的 0→NaN 归一。"""
    from web.pages import indicators

    path = tmp_path / "US.AAPL_daily.parquet"
    pd.DataFrame(
        {"close": [10.0, 11.0], "volume": [100, 200], "adj_close": [0, 0]},
        index=pd.DatetimeIndex(["2024-01-01", "2024-01-02"], name="time_key"),
    ).to_parquet(path)

    class _FakeStorage:
        def build_path(self, *args, **kwargs):
            return path

    monkeypatch.setattr(indicators, "_storage", _FakeStorage())

    got = indicators.load_kline_data("US.AAPL")

    assert got["adj_close"].isna().all(), f"0 未归一：{got['adj_close'].tolist()}"
    assert list(got["close"]) == [10.0, 11.0]

def test_W5_corrupt_screener_result_is_logged(tmp_path, caplog):
    """坏 parquet 不能静默返回空表：必须留一条错误日志。"""
    from web.pages import screener

    path = tmp_path / "bad.parquet"
    path.write_bytes(b"not a parquet")

    with caplog.at_level(logging.ERROR, logger="web.pages.screener"):
        df = screener.load_screener_result(path)

    assert df.empty
    assert "读取选股结果失败" in caplog.text


def test_W6_corrupt_backtest_result_is_logged(tmp_path, caplog):
    """回测结果同理：空表可以返回，但不能无声。"""
    from web.pages import performance

    path = tmp_path / "bad.parquet"
    path.write_bytes(b"not a parquet")

    with caplog.at_level(logging.ERROR, logger="web.pages.performance"):
        df = performance.load_backtest_result(path)

    assert df.empty
    assert "读取回测结果失败" in caplog.text

def test_W8_calendar_status_shows_unavailable_instead_of_crashing(caplog):
    """四类日历异常都必须变成可见提示：不崩溃、不静默降级。"""
    import logging

    from web.calendar_status import build_calendar_status
    from utils.trading_calendar import (
        CalendarFutureUnavailable,
        CalendarRateLimited,
        CalendarUnavailable,
    )

    markets = (("HK", "港股"),)

    assert "尚未初始化" in str(build_calendar_status(None, markets=markets))

    class _RaisingCalendar:
        def __init__(self, exc):
            self.exc = exc

        def get_session_type(self, moment, market):
            raise self.exc

    for exc, expected in (
        (CalendarUnavailable("futu 未连接"), "交易日历不可用"),
        (CalendarRateLimited("请求超限"), "交易日历不可用"),
        (CalendarFutureUnavailable("跨年未发布"), "跨年日历未发布"),
    ):
        component = build_calendar_status(_RaisingCalendar(exc), markets=markets)
        assert expected in str(component)

    # 非日历异常同样不能把页面打崩，且要留下日志
    with caplog.at_level(logging.ERROR, logger="web.calendar_status"):
        component = build_calendar_status(
            _RaisingCalendar(RuntimeError("boom")), markets=markets
        )
    assert "交易日历不可用" in str(component)
    assert "交易日历状态检查失败" in caplog.text


def test_W9_calendar_status_renders_trading_and_closed_days():
    from web.calendar_status import build_calendar_status

    markets = (("HK", "港股"),)

    class _Calendar:
        def __init__(self, session_type="WHOLE", intraday=True):
            self.session_type = session_type
            self.intraday = intraday

        def get_session_type(self, moment, market):
            return self.session_type

        def is_trading_time(self, moment, market):
            return self.intraday

    assert "盘中" in str(build_calendar_status(_Calendar(), markets=markets))
    assert "非盘中" in str(
        build_calendar_status(_Calendar(intraday=False), markets=markets)
    )
    assert "今日休市" in str(
        build_calendar_status(_Calendar(session_type=None), markets=markets)
    )


def test_W10_runtime_status_renders_warm_refresh_and_realtime():
    """监控页运行时快照：成功/失败/未运行都要有明确文案。"""
    from web.calendar_status import build_runtime_status

    empty = str(build_runtime_status({}))
    assert "尚未执行" in empty
    assert "未运行" in empty

    snapshot = {
        "warm": {
            "HK": {"ok": True, "source": "cache", "error": None},
            "US": {"ok": False, "source": None, "error": "futu 超时"},
        },
        "refresh": {"US": {"ok": True, "error": None, "note": "休市"}},
        "realtime": {
            "running": True,
            "skipped_off_session": 7,
            "last_tick_skipped": 2,
            "stopped_reason": None,
            "updated_at": "2026-11-16T10:00:00+08:00",
        },
        "checked_at": "2026-11-16T10:00:30+08:00",
    }
    text = str(build_runtime_status(snapshot))
    assert "预热 成功（cache）" in text
    assert "预热 失败：futu 超时" in text
    assert "盘前刷新 成功（休市）" in text
    assert "累计跳过休市标的 7" in text
    assert "本轮跳过 2" in text
    assert "2026-11-16T10:00:30+08:00" in text


def test_W11_reloader_parent_does_not_start_calendar_runtime():
    from web.calendar_runtime import should_start_runtime

    assert should_start_runtime(True, {}) is False
    assert should_start_runtime(True, {"WERKZEUG_RUN_MAIN": "true"}) is True
    assert should_start_runtime(False, {}) is True


def test_W12_runtime_without_realtime_sink_shows_not_running():
    """P4 选 A：Web 没有实时 executor 时，监控明确显示未运行，不伪造计数。"""
    from web.calendar_runtime import CalendarRuntime
    from web.calendar_status import build_runtime_status

    text = str(build_runtime_status(CalendarRuntime().snapshot()))
    assert "未运行" in text
    assert "累计跳过" not in text


def test_W7_name_lookup_prefers_full_market_list(monkeypatch, tmp_path):
    """名称查全市场清单：只在 universe 外的代码也必须能显示。"""
    from web.pages import control_stock

    info = tmp_path / "StockBasicInfo.parquet"
    filtered = tmp_path / "StockBasicFiltered.parquet"
    pd.DataFrame({"code": ["HK.09988"], "name": ["阿里巴巴"]}).to_parquet(info, index=False)
    pd.DataFrame({"code": ["HK.00700"], "name": ["腾讯"]}).to_parquet(filtered, index=False)

    monkeypatch.setattr(control_stock, "STOCK_BASIC_INFO_FILE", info)
    monkeypatch.setattr(control_stock, "STOCK_BASIC_FILTERED_FILE", filtered)

    assert control_stock.show_stock_name("HK.09988") == "股票名称: 阿里巴巴"
    assert control_stock.show_stock_name("HK.00700") == "股票名称: 腾讯"
