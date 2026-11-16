"""交易日历能力层测试（CAL-01～CAL-30，CAL-16 属引擎集成，P1 覆盖）。

全部离线：fake client + 注入时钟，不依赖 OpenD。
"""

from __future__ import annotations

import json
import logging
import threading
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import pytest

from data.sources.futu_client import FutuAPIClient
from utils.trading_calendar import (
    CalendarFutureUnavailable,
    CalendarOutOfRange,
    CalendarRateLimited,
    CalendarUnavailable,
    RateLimiter,
    TradingCalendar,
    normalize_market,
    normalize_trading_days_payload,
)

HK = ZoneInfo("Asia/Hong_Kong")
NY = ZoneInfo("America/New_York")
SH = ZoneInfo("Asia/Shanghai")
FIXED_NOW = datetime(2026, 11, 16, 10, 0, tzinfo=HK)
FIXTURES = Path(__file__).parent / "fixtures"


class Clock:
    def __init__(self, now: datetime = FIXED_NOW) -> None:
        self.now = now

    def __call__(self) -> datetime:
        return self.now

    def advance(self, **kwargs) -> None:
        self.now += timedelta(**kwargs)


class NoopLimiter:
    def acquire(self) -> None:
        pass


class FakeClient:
    def __init__(
        self,
        days: dict[str, set[date]],
        types: dict[date, str] | None = None,
        delay: float = 0.0,
    ) -> None:
        self.days = {normalize_market(key): set(value) for key, value in days.items()}
        self.types = types or {}
        self.calls: list[tuple[str, date, date]] = []
        self.error: Exception | None = None
        self.delay = delay

    def get_trading_days(self, market: str, start: str, end: str) -> pd.DataFrame:
        mkt = normalize_market(market)
        start_day, end_day = date.fromisoformat(start), date.fromisoformat(end)
        self.calls.append((mkt, start_day, end_day))
        if self.delay:
            time.sleep(self.delay)
        if self.error:
            raise self.error
        days = sorted(day for day in self.days.get(mkt, set()) if start_day <= day <= end_day)
        return pd.DataFrame(
            {
                "date": [day.isoformat() for day in days],
                "session_type": [self.types.get(day, "WHOLE") for day in days],
            }
        )


def weekdays(start: str | date, end: str | date) -> set[date]:
    start_day = date.fromisoformat(start) if isinstance(start, str) else start
    end_day = date.fromisoformat(end) if isinstance(end, str) else end
    return {day for day in pd.date_range(start_day, end_day).date if day.weekday() < 5}


def make_cal(tmp_path: Path, client=None, clock: Clock | None = None, **kwargs) -> TradingCalendar:
    return TradingCalendar(
        client=client,
        cache_dir=tmp_path / "cache",
        overrides_dir=tmp_path / "calendars",
        now_provider=clock or Clock(),
        rate_limiter=NoopLimiter(),
        retry_backoff=(),
        **kwargs,
    )


def read_meta(tmp_path: Path, market: str = "HK") -> dict:
    with open(tmp_path / "cache" / f"{market}.meta.json", "r", encoding="utf-8") as handle:
        return json.load(handle)


def write_override(tmp_path: Path, market: str, text: str) -> None:
    folder = tmp_path / "calendars" / market
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "overrides.csv").write_text(text, encoding="utf-8")


# --------------------------------------------------------------------------- #
# CAL-01 / 02 / 03 解析与市场归一
# --------------------------------------------------------------------------- #
def test_CAL_01_parse_list_dict():
    payload = [
        {"time": "2026-11-03", "trade_date_type": "WHOLE"},
        {"time": "2026-11-04", "trade_date_type": "MORNING"},
        {"time": "2026-11-02", "trade_date_type": "MORNING"},
        {"time": "2026-11-02", "trade_date_type": "WHOLE"},
    ]
    frame = normalize_trading_days_payload(payload, "HK")
    assert frame["date"].dt.strftime("%Y-%m-%d").tolist() == [
        "2026-11-02",
        "2026-11-03",
        "2026-11-04",
    ]
    assert frame["session_type"].tolist() == ["WHOLE", "WHOLE", "MORNING"]


class _QuoteCtx:
    def __init__(self, ret: int, payload) -> None:
        self.ret = ret
        self.payload = payload
        self.calls = []

    def request_trading_days(self, market, start=None, end=None):
        self.calls.append((market, start, end))
        return self.ret, self.payload


def test_CAL_02_dataframe_compat_and_errors():
    client = FutuAPIClient({})
    with pytest.raises(ConnectionError):
        client.get_trading_days("HK", "2026-11-02", "2026-11-03")

    client.connected = True
    client.quote_ctx = _QuoteCtx(
        0,
        pd.DataFrame(
            {
                "time": ["2026-11-03", "2026-11-02"],
                "trade_date_type": ["WHOLE", "MORNING"],
            }
        ),
    )
    frame = client.get_trading_days("HK", "2026-11-02", "2026-11-03")
    assert frame["session_type"].tolist() == ["MORNING", "WHOLE"]

    client.quote_ctx = _QuoteCtx(-1, "RET_ERROR")
    with pytest.raises(RuntimeError):
        client.get_trading_days("HK", "2026-11-02", "2026-11-03")

    # A 股走 TradeDateMarket.CN（没有 SH/SZ）
    client.quote_ctx = _QuoteCtx(
        0, [{"time": "2026-11-02", "trade_date_type": "WHOLE"}]
    )
    client.get_trading_days("SH", "2026-11-02", "2026-11-02")
    assert client.quote_ctx.calls[-1][0] == "CN"


def test_CAL_03_market_alias_and_timestamp(tmp_path):
    assert normalize_market("SH") == "CN"
    assert normalize_market("SZ.000001") == "CN"
    assert normalize_market("HK.00700") == "HK"

    client = FakeClient({"HK": weekdays("2025-11-17", "2026-11-16")})
    cal = make_cal(tmp_path, client)
    cal.get_trading_days("HK", end=pd.Timestamp("2026-11-16"))
    assert client.calls[-1][2] == date(2026, 11, 16)


# --------------------------------------------------------------------------- #
# CAL-04 / 05 缓存与 TTL
# --------------------------------------------------------------------------- #
def test_CAL_04_cache_hit_cross_instance_and_corrupt(tmp_path):
    client = FakeClient({"HK": weekdays("2026-11-02", "2026-11-06")})
    first = make_cal(tmp_path, client)
    assert len(first.get_trading_days("HK", "2026-11-02", "2026-11-06")) == 5
    assert len(client.calls) == 1

    second = make_cal(tmp_path, client)
    assert len(second.get_trading_days("HK", "2026-11-02", "2026-11-06")) == 5
    assert len(client.calls) == 1

    (tmp_path / "cache" / "HK.parquet").write_bytes(b"broken")
    third = make_cal(tmp_path, client)
    assert len(third.get_trading_days("HK", "2026-11-02", "2026-11-06")) == 5
    assert len(client.calls) == 2


def test_CAL_05_ttl_and_force_refresh(tmp_path):
    client = FakeClient({"HK": weekdays("2026-11-02", "2026-11-06")})
    clock = Clock()
    cal = make_cal(tmp_path, client, clock)
    cal.get_trading_days("HK", "2026-11-02", "2026-11-06")
    assert len(client.calls) == 1

    clock.advance(hours=1)
    cal.get_trading_days("HK", "2026-11-02", "2026-11-06")
    assert len(client.calls) == 1

    clock.advance(hours=13)
    cal.get_trading_days("HK", "2026-11-02", "2026-11-06")
    assert len(client.calls) == 2

    cal.get_trading_days("HK", "2026-11-02", "2026-11-06", refresh=True)
    assert len(client.calls) == 3


# --------------------------------------------------------------------------- #
# CAL-06 / 07 / 08 窗口边界
# --------------------------------------------------------------------------- #
def test_CAL_06_boundary_year_coverage_only_window(tmp_path):
    client = FakeClient({"HK": weekdays("2016-11-16", "2017-02-10")})
    cal = make_cal(tmp_path, client)
    cal.get_trading_days("HK", "2016-11-16", "2017-01-31")

    meta = read_meta(tmp_path)
    assert meta["covered_intervals"][0]["start"] == "2016-11-16"

    before = len(client.calls)
    cal.get_trading_days("HK", "2017-02-01", "2017-02-10")
    assert len(client.calls) == before + 1


def test_CAL_07_ten_year_window_read_cache_else_out_of_range(tmp_path):
    client = FakeClient({"HK": weekdays("2016-11-16", "2016-12-31")})
    clock = Clock()
    cal = make_cal(tmp_path, client, clock)
    cal.get_trading_days("HK", "2016-11-16", "2016-12-31")

    clock.advance(days=365)  # 2027-11-16，窗口起点移到 2017-11-16
    before = len(client.calls)
    assert len(cal.get_trading_days("HK", "2016-12-01", "2016-12-31")) > 0
    assert len(client.calls) == before

    with pytest.raises(CalendarOutOfRange):
        cal.get_trading_days("HK", "2016-01-01", "2016-01-31")


def test_CAL_08_future_end_clamped(tmp_path, caplog):
    client = FakeClient({"HK": weekdays("2026-12-01", "2026-12-31")})
    cal = make_cal(tmp_path, client)

    with caplog.at_level(logging.WARNING, logger="utils.trading_calendar"):
        days = cal.get_trading_days("HK", "2026-12-01", "2027-03-01")

    assert len(days) > 0
    assert all(day.year == 2026 for day in days)
    assert client.calls[-1][2] == date(2026, 12, 31)
    assert any("夹取" in record.message for record in caplog.records)


# --------------------------------------------------------------------------- #
# CAL-09 / 10 / 11 / 12 跨年、限流、重试、single-flight
# --------------------------------------------------------------------------- #
def test_CAL_09_next_trading_day_cross_year_raises(tmp_path):
    client = FakeClient({"HK": weekdays("2026-12-01", "2026-12-31")})
    cal = make_cal(tmp_path, client)
    cal.get_trading_days("HK", "2026-12-01", "2026-12-31")
    with pytest.raises(CalendarFutureUnavailable):
        cal.next_trading_day("2026-12-31", "HK")


class _FakeTime:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.now += seconds


def test_CAL_10_rate_limiter_window():
    fake = _FakeTime()
    limiter = RateLimiter(min_interval=1.1, max_calls=25, window=30.0, clock=fake, sleep=fake.sleep)
    stamps = []
    for _ in range(40):
        limiter.acquire()
        stamps.append(fake.now)

    for stamp in stamps:
        assert sum(1 for item in stamps if stamp <= item < stamp + 30.0) <= 25
    assert all(b - a >= 1.1 - 1e-9 for a, b in zip(stamps, stamps[1:]))


def test_CAL_11_retry_only_rate_limit(tmp_path):
    client = FakeClient({"HK": weekdays("2026-11-02", "2026-11-06")})
    client.error = RuntimeError("frequency limit reached")
    cal = TradingCalendar(
        client=client,
        cache_dir=tmp_path / "cache",
        overrides_dir=tmp_path / "calendars",
        now_provider=Clock(),
        rate_limiter=NoopLimiter(),
        retry_backoff=(0, 0),
    )
    with pytest.raises(CalendarRateLimited):
        cal.get_trading_days("HK", "2026-11-02", "2026-11-06")
    assert len(client.calls) == 3

    other = FakeClient({"HK": weekdays("2026-11-02", "2026-11-06")})
    other.error = RuntimeError("boom")
    cal2 = TradingCalendar(
        client=other,
        cache_dir=tmp_path / "cache2",
        overrides_dir=tmp_path / "calendars",
        now_provider=Clock(),
        rate_limiter=NoopLimiter(),
        retry_backoff=(0, 0),
    )
    with pytest.raises(CalendarUnavailable):
        cal2.get_trading_days("HK", "2026-11-02", "2026-11-06")
    assert len(other.calls) == 1


def test_CAL_12_single_flight_same_range(tmp_path):
    client = FakeClient({"HK": weekdays("2026-11-02", "2026-11-06")}, delay=0.05)
    cal = make_cal(tmp_path, client)

    def worker():
        cal.get_trading_days("HK", "2026-11-02", "2026-11-06")

    threads = [threading.Thread(target=worker) for _ in range(4)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert len(client.calls) == 1


# --------------------------------------------------------------------------- #
# CAL-13 / 14 / 15 时区与时段
# --------------------------------------------------------------------------- #
def test_CAL_13_session_date_timezone(tmp_path):
    cal = make_cal(tmp_path, FakeClient({}))
    instant = datetime(2026, 11, 16, 2, 0, tzinfo=timezone.utc)
    assert cal.session_date(instant, "US") == date(2026, 11, 15)
    assert cal.session_date(instant, "HK") == date(2026, 11, 16)


def test_CAL_14_sessions_and_overrides(tmp_path):
    client = FakeClient(
        {
            "HK": {date(2024, 12, 24)},
            "US": {date(2026, 11, 27)},
            "CN": {date(2026, 11, 16)},
        },
        types={date(2024, 12, 24): "MORNING"},
    )
    write_override(tmp_path, "US", "date,close_time,source,note\n2026-11-27,13:00,manual,early\n")
    cal = make_cal(tmp_path, client)

    assert cal.is_trading_time(datetime(2024, 12, 24, 11, 0, tzinfo=HK), "HK") is True
    assert cal.is_trading_time(datetime(2024, 12, 24, 14, 0, tzinfo=HK), "HK") is False

    assert cal.is_trading_time(datetime(2026, 11, 27, 12, 0, tzinfo=NY), "US") is True
    assert cal.is_trading_time(datetime(2026, 11, 27, 13, 30, tzinfo=NY), "US") is False

    assert cal.is_trading_time(datetime(2026, 11, 16, 12, 0, tzinfo=SH), "CN") is False
    assert cal.is_trading_time(datetime(2026, 11, 16, 14, 0, tzinfo=SH), "CN") is True


def test_CAL_15_override_only_close_time(tmp_path):
    client = FakeClient({"HK": weekdays("2024-12-23", "2024-12-24")})
    write_override(
        tmp_path,
        "HK",
        "date,close_time,source,note,session_type\n2024-12-24,15:00,manual,early,MORNING\n",
    )
    cal = make_cal(tmp_path, client)
    frame = cal.get_calendar_frame("HK", "2024-12-24", "2024-12-24")
    assert frame["session_type"].tolist() == ["WHOLE"]
    assert frame["close_time"].tolist() == ["15:00"]
    assert cal.is_trading_time(datetime(2024, 12, 24, 14, 0, tzinfo=HK), "HK") is True
    assert cal.is_trading_time(datetime(2024, 12, 24, 15, 30, tzinfo=HK), "HK") is False


# --------------------------------------------------------------------------- #
# CAL-17 已知日期 fixture
# --------------------------------------------------------------------------- #
def test_CAL_17_hk_2024_fixture(tmp_path):
    fixture = json.loads((FIXTURES / "hk_2024_holidays.json").read_text(encoding="utf-8"))
    holidays = {date.fromisoformat(item) for item in fixture["holidays"]}
    half_days = {date.fromisoformat(key): value for key, value in fixture["half_days"].items()}
    days = weekdays("2024-01-01", "2024-12-31") - holidays

    cal = make_cal(tmp_path, FakeClient({"HK": days}, types=half_days))
    assert cal.is_trading_day("2024-01-01", "HK") is False
    assert cal.is_trading_day("2024-01-02", "HK") is True
    assert cal.is_trading_day("2024-02-12", "HK") is False
    assert cal.is_trading_day("2024-12-25", "HK") is False
    assert cal.get_session_type("2024-12-24", "HK") == "MORNING"
    assert cal.is_trading_time(datetime(2024, 12, 24, 11, 0, tzinfo=HK), "HK") is True
    assert cal.is_trading_time(datetime(2024, 12, 24, 15, 0, tzinfo=HK), "HK") is False


# --------------------------------------------------------------------------- #
# CAL-18 并发写 coverage
# --------------------------------------------------------------------------- #
def test_CAL_18_concurrent_writes_keep_coverage(tmp_path):
    client = FakeClient({"HK": weekdays("2026-01-01", "2026-02-28")}, delay=0.02)
    first = make_cal(tmp_path, client)
    second = make_cal(tmp_path, client)

    threads = [
        threading.Thread(target=lambda: first.prewarm("HK", "2026-01-01", "2026-01-31")),
        threading.Thread(target=lambda: second.prewarm("HK", "2026-02-01", "2026-02-28")),
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    meta = read_meta(tmp_path)
    starts = [item["start"] for item in meta["covered_intervals"]]
    ends = [item["end"] for item in meta["covered_intervals"]]
    assert min(starts) == "2026-01-01"
    # prewarm 的强制区间与缺口取并集，请求覆盖到 2/28（周六）；weekend 不参与覆盖判定
    assert max(ends) == "2026-02-28"


# --------------------------------------------------------------------------- #
# CAL-19 / 20 / 21 未覆盖与回退
# --------------------------------------------------------------------------- #
def test_CAL_19_uncovered_raises_weekend_exception(tmp_path):
    cal = make_cal(tmp_path, None)
    with pytest.raises(CalendarUnavailable):
        cal.is_trading_day("2026-11-16", "HK")
    with pytest.raises(CalendarUnavailable):
        cal.get_session_type("2026-11-16", "HK")
    assert cal.is_trading_day("2026-11-14", "HK") is False
    assert cal.get_session_type("2026-11-14", "HK") is None


def test_CAL_20_history_out_of_range_vs_future_clamp(tmp_path, caplog):
    client = FakeClient({"HK": weekdays("2026-12-01", "2026-12-31")})
    cal = make_cal(tmp_path, client)

    with pytest.raises(CalendarOutOfRange):
        cal.get_trading_days("HK", "2010-01-01", "2010-01-31")
    assert client.calls == []

    with caplog.at_level(logging.WARNING, logger="utils.trading_calendar"):
        days = cal.get_trading_days("HK", "2026-12-01", "2027-01-05")
    assert all(day.year == 2026 for day in days)
    assert any("夹取" in record.message for record in caplog.records)


def test_CAL_21_fallback_to_stale_cache(tmp_path, caplog):
    client = FakeClient({"HK": weekdays("2026-11-02", "2026-11-06")})
    clock = Clock()
    cal = make_cal(tmp_path, client, clock)
    cal.get_trading_days("HK", "2026-11-02", "2026-11-06")

    clock.advance(hours=13)
    client.error = ConnectionError("OpenD down")
    with caplog.at_level(logging.WARNING, logger="utils.trading_calendar"):
        days = cal.get_trading_days("HK", "2026-11-02", "2026-11-06")

    assert len(days) == 5
    assert cal.cache_stale is True
    assert cal.last_source == "cache"
    assert any("回退旧缓存" in record.message for record in caplog.records)


# --------------------------------------------------------------------------- #
# CAL-22 / 23 / 24 未发布与窗口错误优先级
# --------------------------------------------------------------------------- #
def test_CAL_22_unpublished_tail_converges(tmp_path, caplog):
    client = FakeClient({"HK": weekdays("2026-01-01", "2026-11-13")})
    cal = make_cal(tmp_path, client)

    with caplog.at_level(logging.WARNING, logger="utils.trading_calendar"):
        days = cal.get_trading_days("HK", "2026-01-01", "2026-12-31")

    assert len(days) > 0
    assert days[-1].date() == date(2026, 11, 13)
    assert len(client.calls) == 1
    assert read_meta(tmp_path)["covered_intervals"][-1]["end"] == "2026-11-13"

    with pytest.raises(CalendarFutureUnavailable):
        cal.is_trading_day("2026-11-16", "HK")
    assert len(client.calls) == 1
    assert cal.is_trading_day("2026-11-14", "HK") is False


def test_CAL_23_previous_trading_day_out_of_range(tmp_path):
    cal = make_cal(tmp_path, FakeClient({"HK": weekdays("2024-01-01", "2024-12-31")}))
    with pytest.raises(CalendarOutOfRange):
        cal.previous_trading_day("2016-11-16", "HK")


def test_CAL_24_history_error_wins(tmp_path):
    client = FakeClient({"HK": weekdays("2026-12-01", "2026-12-31")})
    cal = make_cal(tmp_path, client)
    with pytest.raises(CalendarOutOfRange):
        cal.get_trading_days("HK", "2010-01-01", "2027-01-31")
    assert client.calls == []


# --------------------------------------------------------------------------- #
# CAL-25 / 26 入参与 override 校验
# --------------------------------------------------------------------------- #
def test_CAL_25_naive_and_aware_midnight(tmp_path):
    cal = make_cal(tmp_path, FakeClient({"HK": weekdays("2026-11-16", "2026-11-16")}))
    with pytest.raises(ValueError):
        cal.get_session_type(datetime(2026, 11, 16, 15, 0), "HK")

    aware_midnight = pd.Timestamp("2026-11-16 00:00", tz="UTC")
    assert cal.session_date(aware_midnight, "US") == date(2026, 11, 15)
    assert cal.session_date(aware_midnight, "HK") == date(2026, 11, 16)


def test_CAL_26_override_validation(tmp_path, caplog):
    client = FakeClient(
        {
            "US": {date(2026, 11, 26), date(2026, 11, 27)},
            "HK": {date(2024, 12, 24)},
        },
        types={date(2024, 12, 24): "MORNING"},
    )
    write_override(
        tmp_path,
        "US",
        "date,close_time,source,note\n"
        "2026-11-27,13:00,manual,early\n"
        "2026-11-27,12:00,manual,dup\n"
        "2026-11-28,13:00,manual,sat\n"
        "2026-12-25,13:00,manual,holiday\n"
        "2026-11-26,25:00,manual,bad\n",
    )
    write_override(tmp_path, "HK", "date,close_time,source,note\n2024-12-24,11:30,manual,half\n")
    cal = make_cal(tmp_path, client)

    with caplog.at_level(logging.WARNING, logger="utils.trading_calendar"):
        frame = cal.get_calendar_frame("US", "2026-11-26", "2026-11-27")
        hk_frame = cal.get_calendar_frame("HK", "2024-12-24", "2024-12-24")

    assert frame.loc[frame["date"].dt.date == date(2026, 11, 27), "close_time"].iloc[0] == "13:00"
    assert hk_frame["close_time"].tolist() == ["11:30"]
    messages = " ".join(record.message for record in caplog.records)
    assert "重复" in messages or "非交易日" in messages or "不在" in messages


# --------------------------------------------------------------------------- #
# CAL-27 / 28 / 29 / 30 严格失败、已发布分支、负缓存、纯周末
# --------------------------------------------------------------------------- #
def test_CAL_27_no_calendar_no_business_day_fallback(tmp_path):
    cal = make_cal(tmp_path, None)
    with pytest.raises(CalendarUnavailable):
        cal.get_trading_days("HK", "2026-11-02", "2026-11-06")


def test_CAL_28_published_branch_covers_tail(tmp_path):
    days = weekdays("2026-12-01", "2026-12-31") - {date(2026, 12, 28)}
    client = FakeClient({"HK": days})
    cal = make_cal(tmp_path, client)
    cal.get_trading_days("HK", "2026-12-01", "2026-12-31")

    assert read_meta(tmp_path)["covered_intervals"][-1]["end"] == "2026-12-31"
    before = len(client.calls)
    assert cal.is_trading_day("2026-12-28", "HK") is False
    assert len(client.calls) == before


def test_CAL_29_future_negative_cache(tmp_path):
    client = FakeClient({"HK": weekdays("2026-01-01", "2026-11-13")})
    clock = Clock()
    cal = make_cal(tmp_path, client, clock)
    cal.get_trading_days("HK", "2026-01-01", "2026-12-31")
    calls = len(client.calls)

    clock.advance(hours=1)
    with pytest.raises(CalendarFutureUnavailable):
        cal.is_trading_day("2026-11-17", "HK")
    assert len(client.calls) == calls

    # 推进 12 小时（仍在同一天，23:00）：总 13 小时 > future_probe_ttl，触发重新探测
    clock.advance(hours=12)
    with pytest.raises(CalendarFutureUnavailable):
        cal.is_trading_day("2026-11-17", "HK")
    assert len(client.calls) == calls + 1

    with pytest.raises(CalendarFutureUnavailable):
        cal.is_trading_day("2026-11-17", "HK", refresh=True)
    assert len(client.calls) == calls + 2


def test_CAL_30_weekend_only_range(tmp_path):
    client = FakeClient({"HK": weekdays("2026-11-01", "2026-11-30")})
    cal = make_cal(tmp_path, client)
    days = cal.get_trading_days("HK", "2026-11-14", "2026-11-15")
    assert len(days) == 0
    assert client.calls == []


# --------------------------------------------------------------------------- #
# CAL-31～35 review 补充：refresh 并集、限流回退、未来无缓存、
# 历史空返回复核
# --------------------------------------------------------------------------- #
def test_CAL_31_refresh_refetches_covered_prefix(tmp_path):
    client = FakeClient({"HK": weekdays("2026-01-01", "2026-12-31")})
    cal = make_cal(tmp_path, client)
    cal.get_trading_days("HK", "2026-01-01", "2026-06-30")

    before = len(client.calls)
    cal.get_trading_days("HK", "2026-01-01", "2026-12-31", refresh=True)
    assert len(client.calls) == before + 1
    # 强制区间与缺口取并集，已覆盖的 1–6 月也要重取
    assert client.calls[-1][1:] == (date(2026, 1, 1), date(2026, 12, 31))


def test_CAL_32_rate_limited_falls_back_to_cache(tmp_path, caplog):
    client = FakeClient({"HK": weekdays("2026-11-02", "2026-11-06")})
    clock = Clock()
    cal = make_cal(tmp_path, client, clock)
    cal.get_trading_days("HK", "2026-11-02", "2026-11-06")

    clock.advance(hours=13)
    client.error = RuntimeError("frequency limit reached")
    with caplog.at_level(logging.WARNING, logger="utils.trading_calendar"):
        days = cal.get_trading_days("HK", "2026-11-02", "2026-11-06")

    assert len(days) == 5
    assert cal.cache_stale is True
    assert any("回退旧缓存" in record.message for record in caplog.records)


def test_CAL_33_future_without_cache_raises_future_unavailable(tmp_path):
    client = FakeClient({})
    cal = make_cal(tmp_path, client)

    with pytest.raises(CalendarFutureUnavailable):
        cal.is_trading_day("2026-11-17", "HK")
    assert len(client.calls) == 1

    # 同一实例会命中刚写入的负缓存；refresh 绕过它，才能真正钉住最终分支
    # 里「allow_partial=True 也不返回空」这一条
    with pytest.raises(CalendarFutureUnavailable):
        cal.get_trading_days("HK", "2026-11-17", "2026-11-20", refresh=True)
    assert len(client.calls) == 2


def test_CAL_34_historical_empty_rechecked(tmp_path):
    client = FakeClient({"HK": {date(2024, 1, 3)}})
    cal = make_cal(tmp_path, client)

    assert cal.is_trading_day("2024-01-02", "HK") is False
    assert client.calls[0][1:] == (date(2024, 1, 2), date(2024, 1, 2))
    # 空返回后用所在自然年复核，确认非空才写「整段休市」coverage
    assert client.calls[1][1:] == (date(2024, 1, 1), date(2024, 12, 31))
    assert read_meta(tmp_path)["covered_intervals"][0]["start"] == "2024-01-02"


def test_CAL_35_historical_empty_unresolved_raises(tmp_path):
    client = FakeClient({})
    cal = make_cal(tmp_path, client)

    with pytest.raises(CalendarUnavailable):
        cal.is_trading_day("2024-01-02", "HK")
    assert not (tmp_path / "cache" / "HK.meta.json").exists()


def test_CAL_36_partial_cache_fetches_history_gap(tmp_path):
    # 只有 1 月缓存时，请求全年不能把 2–11 月当成「未来未发布」
    client = FakeClient({"HK": weekdays("2026-01-01", "2026-12-31")})
    cal = make_cal(tmp_path, client)
    assert len(cal.get_trading_days("HK", "2026-01-01", "2026-01-30")) == 22

    before = len(client.calls)
    days = cal.get_trading_days("HK", "2026-01-01", "2026-12-31")
    assert len(client.calls) == before + 1
    assert client.calls[-1][1] == date(2026, 2, 2)  # 第一个缺失工作日
    assert len(days) == len(weekdays("2026-01-01", "2026-12-31"))


def test_CAL_37_stale_refreshes_covered_prefix_with_gap(tmp_path):
    # 1–6 月过期 + 7–12 月缺失：不能只补缺口而沿用过期前缀
    client = FakeClient({"HK": weekdays("2026-01-01", "2026-12-31")})
    clock = Clock()
    cal = make_cal(tmp_path, client, clock)
    cal.get_trading_days("HK", "2026-01-01", "2026-06-30")

    clock.advance(hours=13)
    before = len(client.calls)
    cal.get_trading_days("HK", "2026-01-01", "2026-12-31")
    assert len(client.calls) == before + 1
    assert client.calls[-1][1:] == (date(2026, 1, 1), date(2026, 12, 31))


def test_CAL_38_rate_limiter_threads_reserve_slots():
    limiter = RateLimiter(min_interval=0.05, max_calls=25, window=30.0)
    barrier = threading.Barrier(5)
    stamps: list[float] = []
    guard = threading.Lock()

    def worker() -> None:
        barrier.wait()
        limiter.acquire()
        with guard:
            stamps.append(time.monotonic())

    threads = [threading.Thread(target=worker) for _ in range(5)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    stamps.sort()
    assert len(stamps) == 5
    gaps = [later - earlier for earlier, later in zip(stamps, stamps[1:])]
    assert min(gaps) >= 0.04


class ScriptedClient:
    """按调用顺序返回预置结果，用于构造「窄请求空、宽请求有数据」。"""

    def __init__(self, responses: list[pd.DataFrame]) -> None:
        self.responses = list(responses)
        self.calls: list[tuple[str, date, date]] = []

    def get_trading_days(self, market: str, start: str, end: str) -> pd.DataFrame:
        self.calls.append(
            (normalize_market(market), date.fromisoformat(start), date.fromisoformat(end))
        )
        return self.responses.pop(0)


def _frame(*days: str) -> pd.DataFrame:
    return pd.DataFrame({"date": list(days), "session_type": ["WHOLE"] * len(days)})


def test_CAL_39_historical_empty_wide_hit_fills_rows(tmp_path):
    # 宽请求在 chunk 内命中行时，应补进 frame 而不是丢弃
    client = ScriptedClient([_frame(), _frame("2024-01-02", "2024-01-03")])
    cal = make_cal(tmp_path, client)

    days = cal.get_trading_days("HK", "2024-01-02", "2024-01-03")
    assert days.strftime("%Y-%m-%d").tolist() == ["2024-01-02", "2024-01-03"]
    assert len(client.calls) == 2


def test_CAL_40_weekend_calendar_frame_no_request(tmp_path):
    client = FakeClient({"HK": weekdays("2026-01-01", "2026-12-31")})
    cal = make_cal(tmp_path, client)

    frame = cal.get_calendar_frame("HK", "2026-11-14", "2026-11-15")
    assert frame.empty
    assert client.calls == []
