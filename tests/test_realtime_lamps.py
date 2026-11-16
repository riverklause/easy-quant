"""R1/R2/P4：实时循环的指标失败隔离、熔断与交易日门控（不依赖 pytest-asyncio）。"""

import asyncio
from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd
import pytest

from indicators.base.errors import IndicatorCalculationError
from strategy.strategy_executor import StrategyExecutor
from strategy.technical_strategy import TechnicalStrategy
from utils.trading_calendar import CalendarFutureUnavailable


class _Recorder(TechnicalStrategy):
    """记录哪些 symbol 进入了策略评估。"""

    def __init__(self):
        super().__init__("rec")
        self.required_indicators = ["sma_5"]        # 字符串声明：跳过装配
        self.seen = set()

    def generate_signals(self, indicators_data, **kwargs):
        self.seen.update(indicators_data.keys())
        return []


class _Calendar:
    """测试替身：默认全市场全天可交易。"""

    def __init__(self, closed_markets=()):
        self.closed_markets = set(closed_markets)

    def is_trading_day(self, moment, market):
        return True

    def is_trading_time(self, moment, market):
        return market not in self.closed_markets


class _BrokenCalendar:
    def __init__(self, exc):
        self.exc = exc

    def is_trading_day(self, moment, market):
        raise self.exc

    def is_trading_time(self, moment, market):
        raise self.exc


class _DataManager:
    def __init__(self, symbols, calendar=None):
        self.symbols = list(symbols)
        self._calendar = calendar or _Calendar()

    def get_trading_calendar(self):
        return self._calendar

    def get_realtime_data(self, data_type, symbol):
        if symbol not in self.symbols:
            return pd.DataFrame()
        idx = pd.bdate_range("2024-01-01", periods=20)
        df = pd.DataFrame({
            "open": [10.0] * 20, "high": [10.1] * 20,
            "low": [9.9] * 20, "close": [10.0] * 20, "volume": [1000] * 20,
        }, index=idx)
        df.attrs["symbol"] = symbol
        return df


class _FakeCalculator:
    def __init__(self, bad_symbols):
        self.bad = set(bad_symbols)
        self.indicators = {}
        self.cache = {}

    def batch_calculate(self, data, indicator_ids, **kwargs):
        if data.attrs.get("symbol") in self.bad:
            raise IndicatorCalculationError(f"boom: {data.attrs.get('symbol')}")
        return {"unknown": {iid: pd.Series([1.0]) for iid in indicator_ids}}

    def get_indicator(self, symbol, indicator_id, cache_mode="realtime"):
        return self.cache.get((symbol, indicator_id))


def test_R1_failed_symbol_never_reaches_strategy():
    calc = _FakeCalculator(bad_symbols={"A"})
    calc.cache[("A", "sma_5")] = pd.Series([9.9])   # 陈旧值：必须被排除
    calc.cache[("B", "sma_5")] = pd.Series([10.0])
    executor = StrategyExecutor(calculator=calc)
    strategy = _Recorder()

    failed = executor._realtime_tick(
        _DataManager(["A", "B"]), ["A", "B"], {"s": strategy}
    )

    assert failed == {"A"}
    assert executor.realtime_stats["indicator_errors"] == 1
    assert strategy.seen == {"B"}, "A 的陈旧指标被拿去出信号了"


def test_R2_circuit_breaker_stops_after_consecutive_failures():
    executor = StrategyExecutor(calculator=_FakeCalculator(bad_symbols={"A"}))
    executor.max_consecutive_failures = 2
    executor._realtime_interval = 0
    executor._realtime_running = True

    asyncio.run(asyncio.wait_for(
        executor._realtime_loop(_DataManager(["A"]), ["A"], {"s": _Recorder()}),
        timeout=5,
    ))

    assert executor.realtime_stats["ticks"] == 2, "熔断没有在连续失败后停止"
    assert executor.is_realtime_running() is False
    assert "连续" in (executor.realtime_stats["stopped_reason"] or "")


def test_R4_cancel_propagates():
    executor = StrategyExecutor(calculator=_FakeCalculator(bad_symbols=set()))
    executor._realtime_interval = 0
    executor._realtime_running = True

    async def scenario():
        task = asyncio.create_task(
            executor._realtime_loop(_DataManager(["A"]), ["A"], {"s": _Recorder()})
        )
        await asyncio.sleep(0)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        return task.cancelled()

    assert asyncio.run(scenario()) is True
    assert executor.realtime_stats["stopped_reason"] == "循环退出"


def test_R4b_stop_mode_records_reason():
    executor = StrategyExecutor(calculator=_FakeCalculator(bad_symbols=set()))
    executor._realtime_running = True

    executor.stop_realtime_mode()

    assert executor.is_realtime_running() is False
    assert executor.realtime_stats["stopped_reason"] == "用户取消"


def test_R3_task_exception_is_recorded():
    executor = StrategyExecutor(calculator=_FakeCalculator(bad_symbols=set()))

    async def boom():
        raise IndicatorCalculationError("装配失败")

    async def scenario():
        task = asyncio.create_task(boom())
        task.add_done_callback(executor._on_realtime_task_done)
        with pytest.raises(IndicatorCalculationError):
            await task
        await asyncio.sleep(0)        # 让 done callback 跑完

    asyncio.run(scenario())
    assert "装配失败" in (executor.realtime_stats["stopped_reason"] or "")


# --------------------------------------------------------------------------- #
# P4-3：交易日/时段门控
# --------------------------------------------------------------------------- #
def test_P4_gating_skips_closed_market_in_indicators_and_signals():
    calc = _FakeCalculator(bad_symbols=set())
    calc.cache[("US.AAPL", "sma_5")] = pd.Series([10.0])
    calc.cache[("HK.00700", "sma_5")] = pd.Series([9.0])  # 陈旧值，不得进信号
    executor = StrategyExecutor(calculator=calc)
    strategy = _Recorder()
    manager = _DataManager(
        ["US.AAPL", "HK.00700"], calendar=_Calendar(closed_markets={"HK"})
    )

    failed = executor._realtime_tick(
        manager,
        ["US.AAPL", "HK.00700"],
        {"s": strategy},
        now=datetime(2026, 11, 16, 10, 0, tzinfo=ZoneInfo("America/New_York")),
    )

    assert failed == set()
    assert strategy.seen == {"US.AAPL"}, "休市标的的旧指标被拿去出信号了"
    assert executor.realtime_stats["skipped_off_session"] == 1
    assert executor.realtime_stats["last_tick_skipped"] == 1


def test_P4_calendar_future_unavailable_stops_realtime_loop():
    executor = StrategyExecutor(calculator=_FakeCalculator(bad_symbols=set()))
    executor._realtime_interval = 0
    executor._realtime_running = True
    manager = _DataManager(
        ["US.AAPL"],
        calendar=_BrokenCalendar(CalendarFutureUnavailable("尚未发布")),
    )

    asyncio.run(asyncio.wait_for(
        executor._realtime_loop(manager, ["US.AAPL"], {"s": _Recorder()}),
        timeout=5,
    ))

    assert executor.is_realtime_running() is False
    assert "跨年日历未发布" in (executor.realtime_stats["stopped_reason"] or "")


def test_P4_missing_calendar_fails_closed():
    class _NoCalendarManager:
        def get_realtime_data(self, data_type, symbol):
            return pd.DataFrame()

    executor = StrategyExecutor(calculator=_FakeCalculator(bad_symbols=set()))
    executor._realtime_interval = 0
    executor._realtime_running = True

    asyncio.run(asyncio.wait_for(
        executor._realtime_loop(_NoCalendarManager(), ["A"], {"s": _Recorder()}),
        timeout=5,
    ))

    assert executor.is_realtime_running() is False
    assert "交易日历不可用" in (executor.realtime_stats["stopped_reason"] or "")


def test_P4_calendar_creation_exception_fails_closed():
    class _BoomManager:
        def get_trading_calendar(self):
            raise RuntimeError("settings broken")

    executor = StrategyExecutor(calculator=_FakeCalculator(bad_symbols=set()))
    executor._realtime_interval = 0
    executor._realtime_running = True

    asyncio.run(asyncio.wait_for(
        executor._realtime_loop(_BoomManager(), ["US.AAPL"], {"s": _Recorder()}),
        timeout=5,
    ))

    assert executor.is_realtime_running() is False
    reason = executor.realtime_stats["stopped_reason"] or ""
    assert "交易日历不可用" in reason
    assert "获取交易日历失败" in reason
    assert "settings broken" in reason


def test_P4_none_calendar_fails_closed():
    class _NoneManager:
        def get_trading_calendar(self):
            return None

    executor = StrategyExecutor(calculator=_FakeCalculator(bad_symbols=set()))
    executor._realtime_interval = 0
    executor._realtime_running = True

    asyncio.run(asyncio.wait_for(
        executor._realtime_loop(_NoneManager(), ["US.AAPL"], {"s": _Recorder()}),
        timeout=5,
    ))

    assert executor.is_realtime_running() is False
    assert "未初始化" in (executor.realtime_stats["stopped_reason"] or "")


def test_P4_status_sink_receives_realtime_stats():
    seen = []
    executor = StrategyExecutor(
        calculator=_FakeCalculator(bad_symbols=set()), status_sink=seen.append
    )
    executor.realtime_stats["skipped_off_session"] = 4
    executor.realtime_stats["last_tick_skipped"] = 2

    executor._publish_status()

    assert seen[-1]["skipped_off_session"] == 4
    assert seen[-1]["last_tick_skipped"] == 2
    assert seen[-1]["running"] is False
    assert seen[-1]["updated_at"]
