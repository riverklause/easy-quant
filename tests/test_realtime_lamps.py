"""R1/R2：实时循环的指标失败隔离与熔断（不依赖 pytest-asyncio）。"""

import asyncio

import pandas as pd
import pytest

from indicators.base.errors import IndicatorCalculationError
from strategy.strategy_executor import StrategyExecutor
from strategy.technical_strategy import TechnicalStrategy


class _Recorder(TechnicalStrategy):
    """记录哪些 symbol 进入了策略评估。"""

    def __init__(self):
        super().__init__("rec")
        self.required_indicators = ["sma_5"]        # 字符串声明：跳过装配
        self.seen = set()

    def generate_signals(self, indicators_data, **kwargs):
        self.seen.update(indicators_data.keys())
        return []


class _DataManager:
    def __init__(self, symbols):
        self.symbols = list(symbols)

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
