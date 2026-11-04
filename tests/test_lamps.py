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

from backtest.engine.backtest_engine import BacktestEngine
from backtest.engine.portfolio import Portfolio
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
        self.required_indicators = ["sma_5"]

    def apply_rules(self, indicators_data, **kwargs):
        assert "sma_5" in indicators_data, "指标契约未满足"
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

    assert strategy.signal_errors == 0, "策略拿不到指标：引擎传的是 OHLC，不是指标字典"
