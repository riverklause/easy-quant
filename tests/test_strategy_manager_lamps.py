"""SM1-SM7：策略管理器 / 策略组合的 smoke 灯。

覆盖策略注册、启停、组合路由与信号记账。用技术指标策略桩，
不引入数据源和指标依赖。
"""

import pytest

from strategy.strategy_manager import StrategyManager
from strategy.strategy_portfolio import StrategyPortfolio
from strategy.technical_strategy import TechnicalStrategy


class _StubStrategy(TechnicalStrategy):
    """最小策略：不需要指标，恒定产出一条 BUY。"""

    def __init__(self, name: str):
        super().__init__(name)
        self.initialize_calls = []
        self.stop_calls = 0

    def define_rules(self, **kwargs):
        self.initialize_calls.append(kwargs)

    def apply_rules(self, indicators_data, **kwargs):
        return [{"type": "BUY"}]

    def stop(self):
        self.stop_calls += 1
        super().stop()


class _RecordingExecutor:
    """只记录路由结果，隔离指标计算链路。"""

    def __init__(self):
        self.calls = []

    def execute_strategy(self, strategy, data, **kwargs):
        self.calls.append(strategy.name)
        return [{"strategy_name": strategy.name, "type": "BUY"}]

    def update_strategy(self, strategy, data, **kwargs):
        strategy.update(data, **kwargs)


# ---------- StrategyPortfolio ----------


def test_SM1_portfolio_routes_global_and_stock_specific():
    """组合路由：股票拿到「全局策略 + 自身专属策略」。"""
    pf = StrategyPortfolio("p")
    pf.add_strategy("G", "technical", [], {})
    pf.add_strategy("S", "technical", [], {}, applicable_stocks=["X"])

    assert pf.get_strategies_for_stock("X") == ["G", "S"]
    assert pf.get_strategies_for_stock("Y") == ["G"]


def test_SM2_portfolio_remove_cleans_all_three_stores():
    """移除策略必须同时清掉配置、全局列表与股票映射。"""
    pf = StrategyPortfolio("p")
    pf.add_strategy("G", "technical", [], {})
    pf.add_strategy("S", "technical", [], {}, applicable_stocks=["X"])

    pf.remove_strategy("S")
    pf.remove_strategy("G")

    assert pf.strategy_configs == []
    assert pf.global_strategies == []
    assert pf.get_strategies_for_stock("X") == []


def test_SM3_portfolio_copy_round_trips_config():
    """导出/导入往返：配置、路由、参数都不丢。"""
    pf = StrategyPortfolio("p")
    pf.add_strategy("G", "technical", ["sma_5"], {"period": 5})
    pf.add_strategy("S", "technical", [], {}, applicable_stocks=["X"])
    pf.update_strategy_params("G", fast=3)

    copy = pf.copy_portfolio("p2")

    assert copy.name == "p2"
    assert copy.get_all_strategies() == ["G", "S"]
    assert copy.get_strategy_config("G")["params"] == {"period": 5, "fast": 3}
    assert copy.get_strategies_for_stock("X") == ["G", "S"]


# ---------- StrategyManager ----------


def test_SM4_register_and_unregister_contract():
    """注册契约：重复 ID / 非 BaseStrategy 拒绝；注销会停止运行中的策略。"""
    manager = StrategyManager()
    strategy = _StubStrategy("s1")
    manager.register_strategy(strategy)

    with pytest.raises(ValueError):
        manager.register_strategy(_StubStrategy("s1"))
    with pytest.raises(ValueError):
        manager.register_strategy(object())

    manager.start_strategy("s1")
    assert strategy.is_running

    manager.unregister_strategy("s1")
    assert "s1" not in manager.strategies
    assert strategy.stop_calls == 1
    assert not strategy.is_running


def test_SM5_start_initializes_once_with_args():
    """启停契约：start 只能初始化一次，且启动参数必须送达 initialize。

    当前 manager 先 initialize(**kwargs) 再调用 start()，而 start() 内部
    又 initialize()（无参数）——参数被静默覆盖。
    """
    manager = StrategyManager()
    strategy = _StubStrategy("s1")
    manager.register_strategy(strategy)

    manager.start_strategy("s1", period=10)

    assert strategy.initialize_calls == [{"period": 10}]
    assert strategy.is_running


def test_SM6_stop_all_stops_individually_started_strategy():
    """stop_all 必须停掉所有运行中的策略，无论它们是怎么启动的。"""
    manager = StrategyManager()
    strategy = _StubStrategy("s1")
    manager.register_strategy(strategy)

    manager.start_strategy("s1")
    manager.stop_all_strategies()

    assert not strategy.is_running
    assert strategy.stop_calls == 1
    assert manager.is_running is False


def test_SM7_portfolio_routing_and_signal_bookkeeping():
    """管理器路由：只调用该股票的适用策略，信号进入全局历史且可按策略过滤。"""
    manager = StrategyManager(strategy_executor=_RecordingExecutor())
    manager.register_strategy(_StubStrategy("G"))
    manager.register_strategy(_StubStrategy("S"))

    portfolio = StrategyPortfolio("p")
    portfolio.add_strategy("G", "technical", [], {})
    portfolio.add_strategy("S", "technical", [], {}, applicable_stocks=["X"])
    manager.add_portfolio(portfolio)

    signals = manager.generate_signals_for_stock("X", None)

    assert [s["strategy_name"] for s in signals] == ["G", "S"]
    assert manager.get_global_signals("S") == [signals[1]]

    manager.clear_signals("S")
    assert manager.get_global_signals("S") == []
    assert manager.get_global_signals("G") == [signals[0]]


class _BrokenInitStrategy(_StubStrategy):
    def define_rules(self, **kwargs):
        super().define_rules(**kwargs)
        raise RuntimeError("init boom")


def test_SM8_failed_initialize_must_not_leave_running():
    """初始化失败时，is_running 必须保持 False（不能“状态说在跑、其实没初始化”）。"""
    manager = StrategyManager()
    strategy = _BrokenInitStrategy("bad")
    manager.register_strategy(strategy)

    with pytest.raises(RuntimeError):
        manager.start_strategy("bad")

    assert strategy.is_running is False
    assert manager.is_running is False


def test_SM9_manager_running_state_is_derived():
    """manager.is_running 必须是派生状态：单停最后一个策略后归 False，可再次 start_all。"""
    manager = StrategyManager()
    strategy = _StubStrategy("s1")
    manager.register_strategy(strategy)

    manager.start_strategy("s1")
    assert manager.is_running is True

    manager.stop_strategy("s1")
    assert manager.is_running is False

    manager.start_all_strategies()
    assert strategy.is_running is True
