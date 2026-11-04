"""
L1-L3b + L4b：撮合记账 / 卖出盈亏 / 费用语义 / 信号分支 / 循环作用域 / 指标接线

约定：
- L1、L2 直接打 Portfolio（纯单元，零网络），因为 _process_signal 无法指定数量
  （_execute_buy 的 quantity 由 initial_capital * 0.1 硬编码推导）。
- L3 打 BacktestEngine._execute_strategy，验证 :315-322 的 try 作用域。
- L4b 只验证“引擎喂给策略的是指标，不是 OHLC”；信号输出形状是另一盏灯。
- 所有期望值都是恒等式，不用 != 0 这类弱 oracle。
"""

from datetime import datetime

import pandas as pd
import pytest

from backtest.engine.backtest_engine import BacktestEngine, IndicatorCalculationError
from backtest.engine.portfolio import Portfolio
from backtest.datafeed.historical_datafeed import HistoricalDataFeed
from strategy.indicator_spec import IndicatorSpec
from strategy.technical_strategy import TechnicalStrategy

DATE = pd.Timestamp("2024-01-02")


def test_L1_buy_bookkeeping():
    """L1 买入记账：现金、持仓、均价。"""
    pf = Portfolio(initial_capital=1_000_000, commission_rate=0.0, slippage=0.0)

    assert pf.buy("X", 100, 10.0, DATE) is True

    assert pf.cash == 999_000.0
    pos = pf.get_position("X")
    assert pos is not None
    assert pos.quantity == 100
    assert pos.avg_price == 10.0
    assert len(pf.trade_history) == 1


def test_L2_sell_realizes_profit():
    """L2 卖出盈亏：清仓后 profit == (卖价-买价)*qty，现金回款正确。

    当前 portfolio.py:181 先 del 再判 `symbol in self.positions`，
    所以这里会红：profit 恒为 0。
    """
    pf = Portfolio(initial_capital=1_000_000, commission_rate=0.0, slippage=0.0)

    pf.buy("X", 100, 10.0, DATE)
    assert pf.sell("X", 100, 11.0, DATE) is True

    assert pf.get_position("X") is None
    assert pf.cash == 1_000_100.0
    assert pf.trade_history[-1]["profit"] == 100.0


def test_L2b_fee_semantics():
    """L2b 费用语义：零费 fixture 无法区分毛/净，这里用有费 fixture 钉住。

    红因（当前）：portfolio.py:181 先 del 再判 membership，profit 恒 0，
    所以毛/净的区分还没被验证就已经被 bug 掩盖。
    """
    pf = Portfolio(initial_capital=1_000_000, commission_rate=0.001, slippage=0.0)

    pf.buy("X", 100, 10.0, DATE)     # 成本 1000 + 费 1  → cash 998_999.0
    pf.sell("X", 100, 11.0, DATE)    # 回款 1100 - 费 1.1 → cash 1_000_097.9

    assert pf.trade_history[-1]["profit"] == pytest.approx(100.0)      # 毛
    assert pf.cash == pytest.approx(1_000_097.9)
    assert (pf.cash - 1_000_000) == pytest.approx(97.9)                # 累计净 = 毛 - 双边费


def test_L3a_both_signals_executed():
    """L3a 分支：同一天 BUY 后紧跟 SELL，两条都必须执行。

    当前 backtest_engine.py:441 对字符串调用 .get()，SELL 必抛；
    异常被 :321 的 try 吞掉，导致后续信号一起丢失。
    """
    engine = BacktestEngine(
        strategy=TechnicalStrategy("lamp"),
        initial_capital=1_000_000,
        commission_rate=0.001,
    )

    signals = [
        {"symbol": "X", "price": 10.0, "signal": "BUY"},
        {"symbol": "X", "price": 11.0, "signal": "SELL"},
    ]
    # 只替换"产生信号"这一步，隔离作用域问题，不引入指标/数据依赖
    engine._generate_signals = lambda strategy, date, prices: signals

    engine._execute_strategy(DATE, {"X": 10.0})

    assert [t["action"] for t in engine.portfolio.trade_history] == ["BUY", "SELL"], (
        "SELL 被吞掉，只剩 BUY"
    )
    assert engine.portfolio.get_position("X") is None


def test_L3b_one_bad_signal_does_not_drop_the_rest():
    """L3b 作用域：一条坏信号只能牺牲它自己，不能吞掉当天后续信号。

    依赖 backtest_engine.py:314-322：try 必须挪进 `for signal` 循环内。
    直接替换 _process_signal（而不是构造畸形字符串信号），
    避免与 :438-442 的字符串 .get() 分支 bug 混在一起。
    """
    engine = BacktestEngine(
        strategy=TechnicalStrategy("lamp"),
        initial_capital=1_000_000,
        commission_rate=0.001,
    )

    signals = [
        {"symbol": "A", "price": 10.0, "signal": "BUY"},
        {"symbol": "BAD", "price": 10.0, "signal": "BUY"},
        {"symbol": "B", "price": 10.0, "signal": "BUY"},
    ]
    engine._generate_signals = lambda strategy, date, prices: signals

    calls = []
    real = engine._process_signal

    def flaky(sig, date, prices):
        calls.append(sig["symbol"])
        if sig["symbol"] == "BAD":
            raise RuntimeError("boom")
        return real(sig, date, prices)

    engine._process_signal = flaky

    engine._execute_strategy(DATE, {"A": 10.0, "BAD": 10.0, "B": 10.0})

    assert calls == ["A", "BAD", "B"], "坏信号之后的信号被整段丢弃"
    assert engine.portfolio.get_position("A") is not None
    assert engine.portfolio.get_position("B") is not None
    assert engine.failed_signals == 1, "静默失败必须可聚合，不能只 print"


class _NeedsIndicators(TechnicalStrategy):
    """L4b fixture：声明所需指标，让“引擎没喂指标”变成可观测的计数。"""

    def __init__(self):
        super().__init__("l4b")
        self.required_indicators = [IndicatorSpec("sma_5", "SMA", {"period": 5})]
        self.calls = 0

    def generate_signals(self, indicators_data, **kwargs):
        self.calls += 1
        return super().generate_signals(indicators_data, **kwargs)

    def apply_rules(self, indicators_data, **kwargs):
        sma = indicators_data["sma_5"]
        if isinstance(sma, pd.DataFrame):
            assert "sma" in sma.columns, f"指标未真正计算: {sma.columns.tolist()}"
            value = sma["sma"].iloc[-1]
        else:
            assert isinstance(sma, (pd.Series, float, int)), f"指标未真正计算: {sma!r}"
            value = sma.iloc[-1] if hasattr(sma, "iloc") else float(sma)
        assert not pd.isna(value)
        return [{"type": "BUY"}]


def _deterministic_bars(rows: int = 20) -> pd.DataFrame:
    """写死价格序列，不用 np.random（避免 hash 随机化重演）。"""
    index = pd.bdate_range("2024-01-01", periods=rows)
    close = [10.0 + i * 0.1 for i in range(rows)]
    return pd.DataFrame(
        {
            "open": close,
            "high": [c + 0.1 for c in close],
            "low": [c - 0.1 for c in close],
            "close": close,
            "volume": [1000] * rows,
        },
        index=index,
    )


def test_L4b_strategy_receives_indicators():
    """L4b 输入契约：引擎必须把 required_indicators 喂给策略，而不是 OHLC 原表。

    当前 backtest_engine.py:366 传的是 current_date_data（OHLC DataFrame），
    策略内 raise 的“缺少所需指标”在 technical_strategy.py:122 被吞掉，
    只能通过 strategy.signal_errors 观测。信号输出形状（list 展平）是另一盏灯。
    """
    strategy = _NeedsIndicators()
    engine = BacktestEngine(
        strategy=strategy,
        initial_capital=1_000_000,
        commission_rate=0.001,
    )
    engine._data = {"X": _deterministic_bars()}
    date = engine._data["X"].index[-1]

    engine._execute_strategy(date, {"X": 11.9})

    assert strategy.calls == 1, "引擎没有把任何数据交给策略"
    assert strategy.signal_errors == 0, f"策略拿不到指标: {strategy.last_signal_error!r}"


def test_L4b2_signals_reach_the_book():
    """L4b2 输出契约：generate_signals 返回的 List[Dict] 必须逐条展开。

    当前 backtest_engine.py:383-391 把整个 list 塞进单个 signal 字段，
    _process_signal 拿到 list → kind 为空 → 静默无交易（连 failed_signals 都不加）。
    """
    strategy = _NeedsIndicators()
    engine = BacktestEngine(
        strategy=strategy,
        initial_capital=1_000_000,
        commission_rate=0.001,
    )
    engine._data = {"X": _deterministic_bars()}
    date = engine._data["X"].index[-1]

    engine._execute_strategy(date, {"X": 11.9})

    assert [t["action"] for t in engine.portfolio.trade_history] == ["BUY"]
    assert engine.failed_signals == 0


def test_L4c_engine_builds_declared_indicators():
    """L4c 装配契约：引擎必须按 IndicatorSpec 实例化并注册指标。

    id 相同但 period 不同是可观测的错数，所以断言 period，而不是只断言 key 存在。
    """
    strategy = _NeedsIndicators()
    engine = BacktestEngine(strategy=strategy, initial_capital=1_000_000)
    engine._data = {"X": _deterministic_bars()}

    assert engine.indicator_calculator.indicators == {}, "calculator 起点必须为空"

    engine._execute_strategy(engine._data["X"].index[-1], {"X": 11.9})

    assert strategy.calls == 1
    assert strategy.signal_errors == 0, f"装配失败: {strategy.last_signal_error!r}"
    assert "sma_5" in engine.indicator_calculator.indicators
    assert engine.indicator_calculator.indicators["sma_5"].period == 5


def test_L4c2_indicator_failure_is_loud():
    """L4c2 计算期失败：指标算错必须冒泡，不能按股票/策略静默跳过。"""
    engine = BacktestEngine(strategy=_NeedsIndicators(), initial_capital=1_000_000)
    bad = _deterministic_bars().drop(columns=["close"])
    engine._data = {"X": bad}

    with pytest.raises(IndicatorCalculationError, match="指标计算失败"):
        engine._execute_strategy(bad.index[-1], {"X": 11.9})

    assert engine.indicator_errors == 1


class _SignalEveryBar(TechnicalStrategy):
    """每根 bar 都给一条 BUY，用于端到端计数灯。"""

    def __init__(self):
        super().__init__("e1")

    def generate_signals(self, indicators_data, **kwargs):
        return [{"type": "BUY"}]


class _SpyFeed(HistoricalDataFeed):
    """L4a fixture：只记录引擎是否把取数委托给 datafeed。"""

    def __init__(self):
        super().__init__(data_manager=None)
        self.calls = 0

    async def get_data(self, symbols, start_date, end_date, frequency="daily"):
        self.calls += 1
        return {"X": _deterministic_bars()}


def test_E1_failures_are_reported_and_reset():
    """E1 失败计数必须挂到结果上，且每次 run 归零。"""
    engine = BacktestEngine(
        strategy=_SignalEveryBar(),
        datafeed=_SpyFeed(),
        initial_capital=1_000_000,
    )

    # 每轮第一次处理信号时故意抛一次
    state = {"raised": False}
    real = engine._process_signal

    def flaky(sig, date, prices):
        if not state["raised"]:
            state["raised"] = True
            raise RuntimeError("boom")
        return real(sig, date, prices)

    engine._process_signal = flaky

    first = engine.run("2024-01-01", "2024-03-01", symbols=["X"])
    assert first.execution_failures == {
        "signals": 1,
        "strategies": 0,
        "indicators": 0,
    }

    state["raised"] = False
    second = engine.run("2024-01-01", "2024-03-01", symbols=["X"])
    assert second.execution_failures["signals"] == 1, "计数器跨 run 累加了"


def test_E2_result_reports_real_data_source():
    """E2 真实 feed 的结果必须标出真实来源，而不是悄悄写成 mock。"""
    engine = BacktestEngine(
        strategy=_SignalEveryBar(),
        datafeed=_SpyFeed(),
        initial_capital=1_000_000,
    )
    result = engine.run("2024-01-01", "2024-03-01", symbols=["X"])

    assert result.data_source == "_SpyFeed"


def test_E3_default_feed_is_declared_as_mock():
    """E3 默认 feed 回落 mock 时，结果对象必须自报 mock。"""
    engine = BacktestEngine(strategy=_SignalEveryBar(), initial_capital=1_000_000)
    result = engine.run("2024-01-01", "2024-03-01", symbols=["X"])

    assert result.data_source == "mock"


def test_L4a_engine_delegates_loading_to_datafeed():
    """L4a 取数委托：_load_data 必须走 datafeed，而不是自己造 mock。

    当前 backtest_engine.py:254 直接调 datafeed._generate_mock_data，
    绕过 get_data，所以真实 data_manager 永远不会被用到。
    """
    feed = _SpyFeed()
    engine = BacktestEngine(
        strategy=TechnicalStrategy("l4a"),
        datafeed=feed,
        initial_capital=1_000_000,
    )

    engine.run("2024-01-01", "2024-02-01", symbols=["X"])

    assert feed.calls == 1, "引擎没有把取数委托给 datafeed"
    assert list(engine.get_data()) == ["X"]
