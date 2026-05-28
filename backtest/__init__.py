"""
回测引擎模块
提供历史数据回测功能，支持策略绩效评估和风险分析
"""

from backtest.engine.backtest_engine import BacktestEngine
from backtest.engine.portfolio import Portfolio
from backtest.engine.order_executor import OrderExecutor, Order, OrderType, OrderStatus
from backtest.datafeed.historical_datafeed import HistoricalDataFeed
from backtest.analyzers.performance import PerformanceAnalyzer
from backtest.analyzers.risk import RiskAnalyzer
from backtest.analyzers.trade_analyzer import TradeAnalyzer
from backtest.results.result_store import BacktestResult

__all__ = [
    'BacktestEngine',
    'Portfolio',
    'OrderExecutor',
    'Order',
    'OrderType',
    'OrderStatus',
    'HistoricalDataFeed',
    'PerformanceAnalyzer',
    'RiskAnalyzer',
    'TradeAnalyzer',
    'BacktestResult',
]
