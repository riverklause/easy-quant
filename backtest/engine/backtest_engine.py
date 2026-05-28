"""
回测引擎核心
负责回测的完整执行流程
"""

from typing import Dict, List, Optional, Any, Union, Callable
from datetime import datetime
import pandas as pd
import numpy as np
import asyncio

from backtest.engine.portfolio import Portfolio
from backtest.engine.order_executor import SimpleOrderExecutor, OrderSide
from backtest.datafeed.historical_datafeed import HistoricalDataFeed
from backtest.analyzers.performance import PerformanceAnalyzer
from backtest.analyzers.risk import RiskAnalyzer
from backtest.analyzers.trade_analyzer import TradeAnalyzer
from backtest.results.result_store import BacktestResult

from strategy.base_strategy import BaseStrategy
from strategy.technical_strategy import TechnicalStrategy
from strategy.multi_factor.multi_factor_strategy import MultiFactorStrategy


class BacktestEngine:
    """
    回测引擎
    职责：
    1. 管理回测生命周期
    2. 协调数据加载和策略执行
    3. 管理组合模拟
    4. 生成回测报告
    """
    
    def __init__(self,
                 strategy: Union[BaseStrategy, List[BaseStrategy]],
                 datafeed: HistoricalDataFeed = None,
                 initial_capital: float = 1000000,
                 commission_rate: float = 0.001,
                 slippage: float = 0.0,
                 risk_free_rate: float = 0.03):
        """
        初始化回测引擎
        
        Args:
            strategy: 策略实例或策略列表
            datafeed: 历史数据源
            initial_capital: 初始资金
            commission_rate: 佣金费率
            slippage: 滑点
            risk_free_rate: 无风险利率
        """
        self.strategies = strategy if isinstance(strategy, list) else [strategy]
        self.datafeed = datafeed or HistoricalDataFeed()
        
        self.portfolio = Portfolio(
            initial_capital=initial_capital,
            commission_rate=commission_rate,
            slippage=slippage
        )
        
        self.order_executor = SimpleOrderExecutor(
            slippage=slippage,
            commission_rate=commission_rate
        )
        
        self.performance_analyzer = PerformanceAnalyzer(risk_free_rate=risk_free_rate)
        self.risk_analyzer = RiskAnalyzer()
        self.trade_analyzer = TradeAnalyzer()
        
        self.initial_capital = initial_capital
        self.risk_free_rate = risk_free_rate
        
        self._data: Dict[str, pd.DataFrame] = {}
        self._is_running = False
        self._results: Optional[BacktestResult] = None
        
        self._progress_callback: Optional[Callable] = None
    
    def set_progress_callback(self, callback: Callable[[int, int], None]):
        """
        设置进度回调
        
        Args:
            callback: 回调函数，参数为 (current, total)
        """
        self._progress_callback = callback
    
    def run(self,
            start_date: str,
            end_date: str,
            symbols: List[str] = None,
            frequency: str = 'daily',
            rebalance_dates: List[str] = None,
            benchmark_symbol: str = None) -> BacktestResult:
        """
        执行回测
        
        Args:
            start_date: 开始日期
            end_date: 结束日期
            symbols: 股票代码列表
            frequency: 数据频率 (daily, weekly, monthly)
            rebalance_dates: 调仓日期列表（可选）
            benchmark_symbol: 基准股票代码（可选）
            
        Returns:
            BacktestResult回测结果
        """
        self._is_running = True
        self.portfolio.reset()
        
        print(f"开始回测: {start_date} ~ {end_date}")
        print(f"初始资金: {self.initial_capital:,.2f}")
        
        self._data = self._load_data(symbols, start_date, end_date, frequency)
        
        if not self._data:
            print("没有加载到数据，回测终止")
            return self._create_empty_result(start_date, end_date)
        
        trading_dates = self._get_trading_dates()
        
        if rebalance_dates:
            rebalance_dates = [pd.to_datetime(d) for d in rebalance_dates]
        
        prev_value = self.initial_capital
        
        total_dates = len(trading_dates)
        
        for i, date in enumerate(trading_dates):
            if not self._is_running:
                break
            
            current_prices = self._get_current_prices(date)
            
            if current_prices:
                self._execute_strategy(date, current_prices)
                
                self.portfolio.record_snapshot(date, current_prices, prev_value)
                prev_value = self.portfolio.get_total_value(current_prices)
            
            if rebalance_dates and date in rebalance_dates:
                self._rebalance(date, current_prices)
            
            if self._progress_callback:
                self._progress_callback(i + 1, total_dates)
        
        self._generate_results(start_date, end_date, benchmark_symbol)
        
        self._is_running = False
        
        print(f"回测完成")
        
        return self._results
    
    def run_async(self,
                  start_date: str,
                  end_date: str,
                  symbols: List[str] = None,
                  frequency: str = 'daily',
                  rebalance_dates: List[str] = None,
                  benchmark_symbol: str = None) -> BacktestResult:
        """
        异步执行回测
        
        Args:
            start_date: 开始日期
            end_date: 结束日期
            symbols: 股票代码列表
            frequency: 数据频率
            rebalance_dates: 调仓日期列表
            benchmark_symbol: 基准股票代码
            
        Returns:
            BacktestResult回测结果
        """
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        return loop.run_until_complete(
            self._run_async_impl(start_date, end_date, symbols, frequency, 
                               rebalance_dates, benchmark_symbol)
        )
    
    async def _run_async_impl(self,
                              start_date: str,
                              end_date: str,
                              symbols: List[str],
                              frequency: str,
                              rebalance_dates: List[str],
                              benchmark_symbol: str) -> BacktestResult:
        """异步回测实现"""
        self._is_running = True
        self.portfolio.reset()
        
        self._data = await self.datafeed.get_data(symbols, start_date, end_date, frequency)
        
        if not self._data:
            return self._create_empty_result(start_date, end_date)
        
        trading_dates = self._get_trading_dates()
        prev_value = self.initial_capital
        
        for date in trading_dates:
            if not self._is_running:
                break
            
            current_prices = self._get_current_prices(date)
            
            if current_prices:
                self._execute_strategy(date, current_prices)
                self.portfolio.record_snapshot(date, current_prices, prev_value)
                prev_value = self.portfolio.get_total_value(current_prices)
        
        self._generate_results(start_date, end_date, benchmark_symbol)
        
        self._is_running = False
        
        return self._results
    
    def stop(self):
        """停止回测"""
        self._is_running = False
        print("回测已停止")
    
    def _load_data(self, 
                   symbols: Optional[List[str]], 
                   start_date: str, 
                   end_date: str,
                   frequency: str) -> Dict[str, pd.DataFrame]:
        """
        加载数据
        
        Args:
            symbols: 股票代码列表
            start_date: 开始日期
            end_date: 结束日期
            frequency: 数据频率
            
        Returns:
            股票数据字典
        """
        if symbols is None:
            symbols = self._get_strategy_symbols()
        
        return self.datafeed._generate_mock_data(symbols, start_date, end_date, frequency)
    
    def _get_strategy_symbols(self) -> List[str]:
        """获取策略所需的股票代码"""
        symbols = set()
        
        for strategy in self.strategies:
            if hasattr(strategy, 'get_required_symbols'):
                symbols.update(strategy.get_required_symbols())
            elif hasattr(strategy, 'applicable_stocks') and strategy.applicable_stocks:
                symbols.update(strategy.applicable_stocks)
        
        return list(symbols) if symbols else ['AAPL', 'GOOG', 'MSFT']
    
    def _get_trading_dates(self) -> List[pd.Timestamp]:
        """获取交易日期列表"""
        if not self._data:
            return []
        
        all_dates = set()
        for df in self._data.values():
            if not df.empty and hasattr(df.index, 'tolist'):
                all_dates.update(df.index.tolist())
        
        dates = sorted([d for d in all_dates if isinstance(d, pd.Timestamp)])
        
        return dates
    
    def _get_current_prices(self, date: pd.Timestamp) -> Dict[str, float]:
        """
        获取指定日期的价格
        
        Args:
            date: 日期
            
        Returns:
            价格字典
        """
        prices = {}
        
        for symbol, df in self._data.items():
            if df.empty:
                continue
            
            if date in df.index:
                close_price = df.loc[date, 'close']
                prices[symbol] = float(close_price)
            else:
                available_dates = df.index[df.index <= date]
                if len(available_dates) > 0:
                    last_date = available_dates[-1]
                    close_price = df.loc[last_date, 'close']
                    prices[symbol] = float(close_price)
        
        return prices
    
    def _execute_strategy(self, date: pd.Timestamp, current_prices: Dict[str, float]):
        """
        执行策略生成信号
        
        Args:
            date: 当前日期
            current_prices: 当前价格
        """
        for strategy in self.strategies:
            try:
                signals = self._generate_signals(strategy, date, current_prices)
                
                for signal in signals:
                    self._process_signal(signal, date, current_prices)
                    
            except Exception as e:
                print(f"执行策略 {strategy.name} 出错: {e}")
    
    def _generate_signals(self, 
                         strategy: BaseStrategy, 
                         date: pd.Timestamp,
                         current_prices: Dict[str, float]) -> List[Dict]:
        """
        生成交易信号
        
        Args:
            strategy: 策略
            date: 日期
            current_prices: 当前价格
            
        Returns:
            信号列表
        """
        signals = []
        
        if isinstance(strategy, TechnicalStrategy):
            signals = self._generate_technical_signals(strategy, date, current_prices)
        elif isinstance(strategy, MultiFactorStrategy):
            signals = self._generate_factor_signals(strategy, date, current_prices)
        
        return signals
    
    def _generate_technical_signals(self,
                                    strategy: TechnicalStrategy,
                                    date: pd.Timestamp,
                                    current_prices: Dict[str, float]) -> List[Dict]:
        """生成技术指标策略信号"""
        signals = []
        
        for symbol, price in current_prices.items():
            if symbol not in self._data:
                continue
            
            df = self._data[symbol]
            current_date_data = df[df.index <= date]
            
            if len(current_date_data) < 10:
                continue
            
            try:
                signal = strategy.generate_signals(current_date_data)
                
                if signal:
                    signals.append({
                        'symbol': symbol,
                        'price': price,
                        'signal': signal,
                        'strategy': strategy.name
                    })
                    
            except Exception:
                continue
        
        return signals
    
    def _generate_factor_signals(self,
                                 strategy: MultiFactorStrategy,
                                 date: pd.Timestamp,
                                 current_prices: Dict[str, float]) -> List[Dict]:
        """生成多因子策略信号"""
        signals = []
        
        stock_data = {}
        
        for symbol in current_prices.keys():
            if symbol in self._data:
                df = self._data[symbol]
                current_date_data = df[df.index <= date]
                
                if len(current_date_data) > 0:
                    stock_data[symbol] = current_date_data
        
        if stock_data:
            try:
                result = strategy.generate_signals(stock_data)
                
                if result:
                    selected_stocks = result[0].get('selected_stocks', [])
                    
                    for symbol in selected_stocks:
                        signals.append({
                            'symbol': symbol,
                            'price': current_prices.get(symbol),
                            'signal': 'BUY',
                            'strategy': strategy.name
                        })
                        
            except Exception as e:
                print(f"多因子策略信号生成失败: {e}")
        
        return signals
    
    def _process_signal(self, 
                       signal: Dict, 
                       date: pd.Timestamp,
                       current_prices: Dict[str, float]):
        """
        处理交易信号
        
        Args:
            signal: 信号
            date: 日期
            current_prices: 当前价格
        """
        symbol = signal.get('symbol')
        price = signal.get('price')
        
        if not symbol or not price:
            return
        
        signal_type = signal.get('signal')
        
        if isinstance(signal_type, str):
            if signal_type.upper() == 'BUY' or signal_type.get('type') == 'BUY':
                self._execute_buy(symbol, price, date)
            elif signal_type.upper() == 'SELL' or signal_type.get('type') == 'SELL':
                self._execute_sell(symbol, price, date)
    
    def _execute_buy(self, symbol: str, price: float, date: pd.Timestamp):
        """执行买入"""
        position = self.portfolio.get_position(symbol)
        
        if position:
            return
        
        allocation = self.initial_capital * 0.1
        quantity = int(allocation / price / 100) * 100
        
        if quantity > 0:
            self.portfolio.buy(symbol, quantity, price, date)
    
    def _execute_sell(self, symbol: str, price: float, date: pd.Timestamp):
        """执行卖出"""
        position = self.portfolio.get_position(symbol)
        
        if position:
            self.portfolio.sell(symbol, position.quantity, price, date)
    
    def _rebalance(self, date: pd.Timestamp, current_prices: Dict[str, float]):
        """
        调仓
        
        Args:
            date: 日期
            current_prices: 当前价格
        """
        pass
    
    def _generate_results(self, 
                         start_date: str, 
                         end_date: str,
                         benchmark_symbol: Optional[str]):
        """生成回测结果"""
        equity_curve = self.portfolio.get_equity_curve()
        trade_history = self.portfolio.get_trade_history()
        
        returns = self.portfolio.get_returns_series()
        
        benchmark_returns = None
        if benchmark_symbol and benchmark_symbol in self._data:
            benchmark_data = self._data[benchmark_symbol]
            benchmark_returns = benchmark_data['close'].pct_change().dropna()
        
        performance_metrics = {}
        if not returns.empty:
            performance_metrics = self.performance_analyzer.analyze(
                returns, benchmark_returns
            )
        
        risk_metrics = {}
        if not returns.empty:
            risk_metrics = self.risk_analyzer.analyze(returns)
        
        trade_metrics = {}
        if not trade_history.empty:
            trade_metrics = self.trade_analyzer.analyze(trade_history)
        
        self._results = BacktestResult(
            strategy_name=self.strategies[0].name if self.strategies else 'Unknown',
            start_date=start_date,
            end_date=end_date,
            initial_capital=self.initial_capital,
            equity_curve=equity_curve,
            trades=trade_history,
            performance_metrics=performance_metrics,
            risk_metrics=risk_metrics,
            trade_metrics=trade_metrics,
            benchmark_returns=benchmark_returns,
            config={
                'commission_rate': self.portfolio.commission_rate,
                'slippage': self.portfolio.slippage,
                'risk_free_rate': self.risk_free_rate,
            }
        )
    
    def _create_empty_result(self, start_date: str, end_date: str) -> BacktestResult:
        """创建空结果"""
        return BacktestResult(
            strategy_name=self.strategies[0].name if self.strategies else 'Unknown',
            start_date=start_date,
            end_date=end_date,
            initial_capital=self.initial_capital,
        )
    
    def get_results(self) -> Optional[BacktestResult]:
        """
        获取回测结果
        
        Returns:
            BacktestResult实例
        """
        return self._results
    
    def get_portfolio(self) -> Portfolio:
        """
        获取组合管理器
        
        Returns:
            Portfolio实例
        """
        return self.portfolio
    
    def get_data(self) -> Dict[str, pd.DataFrame]:
        """
        获取回测数据
        
        Returns:
            股票数据字典
        """
        return self._data
