"""P4-1/P4-2：Web 日历运行时预热与盘前刷新。"""

import threading
import time
from datetime import date, datetime
from zoneinfo import ZoneInfo

from utils.trading_calendar import CalendarUnavailable
from web.calendar_runtime import CalendarRuntime

HK = ZoneInfo("Asia/Hong_Kong")
NY = ZoneInfo("America/New_York")


class _Manager:
    def __init__(self, calendar):
        self._calendar = calendar

    def get_trading_calendar(self):
        return self._calendar


class _Calendar:
    def __init__(self, fail_markets=(), holidays=()):
        self.fail_markets = set(fail_markets)
        self.holidays = set(holidays)
        self.warm_calls = []
        self.refresh_calls = []
        self.last_source = "cache"

    def get_trading_days(self, market, start, end):
        if market in self.fail_markets:
            raise CalendarUnavailable(f"{market} 不可用")
        self.warm_calls.append((market, start, end))
        return []

    def is_trading_day(self, day, market):
        return day not in self.holidays

    def refresh(self, market, start, end):
        self.refresh_calls.append((market, start, end))
        return []


def test_P4_warm_uses_current_natural_year_and_fail_soft():
    calendar = _Calendar(fail_markets={"HK"})
    runtime = CalendarRuntime(markets=("HK", "US", "CN"))

    results = runtime.warm_once(
        _Manager(calendar), now=datetime(2026, 11, 16, 10, 0, tzinfo=HK)
    )

    assert results["HK"]["ok"] is False
    assert "不可用" in results["HK"]["error"]
    assert results["US"]["ok"] is True
    assert results["US"]["source"] == "cache"
    assert results["CN"]["ok"] is True
    assert calendar.warm_calls == [
        ("US", date(2026, 1, 1), date(2026, 12, 31)),
        ("CN", date(2026, 1, 1), date(2026, 12, 31)),
    ]


def test_P4_warm_without_calendar_accessor_records_error():
    runtime = CalendarRuntime(markets=("US",))

    results = runtime.warm_once(object(), now=datetime(2026, 11, 16, 10, 0, tzinfo=HK))

    assert results["US"]["ok"] is False
    assert "get_trading_calendar" in results["US"]["error"]


def test_P4_calendar_resolved_once_across_warm_and_refresh_threads():
    """warm/refresh 两个后台线程必须共用同一份日历，避免并发创建两个实例。"""
    calendar = _Calendar()

    class _SlowManager:
        def __init__(self):
            self.calls = 0
            self.lock = threading.Lock()

        def get_trading_calendar(self):
            with self.lock:
                self.calls += 1
            time.sleep(0.05)
            return calendar

    manager = _SlowManager()
    runtime = CalendarRuntime(markets=("US",))

    def warm():
        runtime.warm_once(manager, now=datetime(2026, 11, 16, 10, 0, tzinfo=HK))

    def refresh():
        runtime.maybe_refresh(manager, now=datetime(2026, 11, 16, 9, 15, tzinfo=NY))

    threads = [threading.Thread(target=warm), threading.Thread(target=refresh)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert manager.calls == 1


def test_P4_preopen_refresh_runs_once_per_market_per_day():
    calendar = _Calendar()
    runtime = CalendarRuntime(markets=("US",))
    manager = _Manager(calendar)

    first = runtime.maybe_refresh(
        manager, now=datetime(2026, 11, 16, 9, 15, tzinfo=NY)
    )
    assert first["US"]["ok"] is True
    assert calendar.refresh_calls == [
        ("US", date(2026, 11, 16), date(2026, 11, 16))
    ]

    # 同一天窗口内再次轮询：不再刷新，也不重复请求
    runtime.maybe_refresh(manager, now=datetime(2026, 11, 16, 9, 20, tzinfo=NY))
    assert len(calendar.refresh_calls) == 1

    # 次日窗口内：允许再次刷新
    runtime.maybe_refresh(manager, now=datetime(2026, 11, 17, 9, 15, tzinfo=NY))
    assert len(calendar.refresh_calls) == 2


def test_P4_preopen_refresh_window_and_holiday_skip():
    calendar = _Calendar(holidays={date(2026, 11, 16)})
    runtime = CalendarRuntime(markets=("US",))
    manager = _Manager(calendar)

    # 09:30 是右开边界，不刷新
    assert runtime.maybe_refresh(
        manager, now=datetime(2026, 11, 16, 9, 30, tzinfo=NY)
    ) == {}
    # 周六不刷新
    assert runtime.maybe_refresh(
        manager, now=datetime(2026, 11, 14, 9, 15, tzinfo=NY)
    ) == {}

    # 交易日窗口内但当天休市：记录成功（休市），不调用 refresh
    result = runtime.maybe_refresh(
        manager, now=datetime(2026, 11, 16, 9, 0, tzinfo=NY)
    )
    assert result["US"]["ok"] is True
    assert result["US"]["note"] == "休市"
    assert calendar.refresh_calls == []


def test_P4_failed_refresh_is_not_retried_same_day():
    class _BrokenCalendar(_Calendar):
        def __init__(self):
            super().__init__()
            self.day_checks = 0

        def is_trading_day(self, day, market):
            self.day_checks += 1
            raise CalendarUnavailable("futu 未连接")

    calendar = _BrokenCalendar()
    runtime = CalendarRuntime(markets=("US",))
    manager = _Manager(calendar)

    first = runtime.maybe_refresh(
        manager, now=datetime(2026, 11, 16, 9, 5, tzinfo=NY)
    )
    assert first["US"]["ok"] is False
    assert "未连接" in first["US"]["error"]

    runtime.maybe_refresh(manager, now=datetime(2026, 11, 16, 9, 10, tzinfo=NY))
    assert calendar.day_checks == 1, "同一天失败后不应再次请求日历"
