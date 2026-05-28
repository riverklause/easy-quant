"""
回测引擎使用示例
演示如何使用回测引擎进行策略回测
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + '/..')

import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from backtest import BacktestEngine, HistoricalDataFeed, PerformanceAnalyzer
from backtest.engine.portfolio import Portfolio
from strategy.technical_strategy import TechnicalStrategy
from strategy.multi_factor.multi_factor_strategy import MultiFactorStrategy


class SimpleMovingAverageStrategy(TechnicalStrategy):
    """
    简单移动平均策略
    当短期MA上穿长期MA时买入，下穿时卖出
    """
    
    def __init__(self, 
                 name: str = "SMA_Cross",
                 short_period: int = 10,
                 long_period: int = 30):
        super().__init__(name=name)
        self.short_period = short_period
        self.long_period = long_period
        self.position = None
        
        self.required_indicators = [f'sma_{self.short_period}', f'sma_{self.long_period}']
        
    def generate_signals(self, indicators_data, **kwargs):
        signals = []
        
        if not isinstance(indicators_data, dict):
            return signals
        
        for symbol, data in indicators_data.items():
            if data.empty or len(data) < self.long_period:
                continue
            
            sma_col = f'sma_{self.short_period}'
            long_sma_col = f'sma_{self.long_period}'
            
            if sma_col not in data.columns or long_sma_col not in data.columns:
                continue
            
            current_short = data[sma_col].iloc[-1]
            current_long = data[long_sma_col].iloc[-1]
            prev_short = data[sma_col].iloc[-2]
            prev_long = data[long_sma_col].iloc[-2]
            
            if prev_short <= prev_long and current_short > current_long:
                signals.append({
                    'type': 'BUY',
                    'symbol': symbol,
                    'price': data['close'].iloc[-1],
                    'reason': f'SMA{self.short_period} 上穿 SMA{self.long_period}'
                })
                self.position = symbol
            elif prev_short >= prev_long and current_short < current_long:
                signals.append({
                    'type': 'SELL',
                    'symbol': symbol,
                    'price': data['close'].iloc[-1],
                    'reason': f'SMA{self.short_period} 下穿 SMA{self.long_period}'
                })
                self.position = None
        
        return signals
    
    def get_required_indicators(self):
        return [f'sma_{self.short_period}', f'sma_{self.long_period}']


class RSIStrategy(TechnicalStrategy):
    """
    RSI策略
    RSI低于30买入，高于70卖出
    """
    
    def __init__(self, 
                 name: str = "RSI_Strategy",
                 rsi_period: int = 14,
                 oversold: int = 30,
                 overbought: int = 70):
        super().__init__(name=name)
        self.rsi_period = rsi_period
        self.oversold = oversold
        self.overbought = overbought
        self.position = None
        
        self.required_indicators = [f'rsi_{self.rsi_period}']
        
    def generate_signals(self, indicators_data, **kwargs):
        signals = []
        
        if not isinstance(indicators_data, dict):
            return signals
        
        for symbol, data in indicators_data.items():
            if data.empty or len(data) < self.rsi_period:
                continue
            
            rsi_col = f'rsi_{self.rsi_period}'
            
            if rsi_col not in data.columns:
                continue
            
            current_rsi = data[rsi_col].iloc[-1]
            
            if current_rsi < self.oversold and self.position is None:
                signals.append({
                    'type': 'BUY',
                    'symbol': symbol,
                    'price': data['close'].iloc[-1],
                    'reason': f'RSI={current_rsi:.2f} < {self.oversold}'
                })
                self.position = symbol
            elif current_rsi > self.overbought and self.position == symbol:
                signals.append({
                    'type': 'SELL',
                    'symbol': symbol,
                    'price': data['close'].iloc[-1],
                    'reason': f'RSI={current_rsi:.2f} > {self.overbought}'
                })
                self.position = None
        
        return signals
    
    def get_required_indicators(self):
        return [f'rsi_{self.rsi_period}']


def generate_sample_data(symbols: list, start_date: str, end_date: str) -> dict:
    """生成示例数据"""
    import pandas as pd
    import numpy as np
    
    result = {}
    
    start = pd.to_datetime(start_date)
    end = pd.to_datetime(end_date)
    dates = pd.date_range(start=start, end=end, freq='B')
    
    for symbol in symbols:
        np.random.seed(hash(symbol) % (2**31))
        
        initial_price = 100 + np.random.randn() * 20
        prices = [initial_price]
        
        for _ in range(len(dates) - 1):
            change = np.random.randn() * 2
            prices.append(prices[-1] + change)
        
        prices = np.maximum(prices, 1)
        
        df = pd.DataFrame({
            'date': dates,
            'open': prices * (1 + np.random.randn(len(dates)) * 0.01),
            'high': prices * (1 + np.abs(np.random.randn(len(dates)) * 0.02)),
            'low': prices * (1 - np.abs(np.random.randn(len(dates)) * 0.02)),
            'close': prices,
            'volume': np.random.randint(1000000, 10000000, len(dates))
        })
        df.set_index('date', inplace=True)
        
        result[symbol] = df
    
    return result


def demo_basic_backtest():
    """演示基础回测"""
    print("\n" + "="*60)
    print("基础回测演示")
    print("="*60)
    
    symbols = ['AAPL', 'GOOG', 'MSFT', 'AMZN', 'TSLA']
    
    data = generate_sample_data(symbols, '2024-01-01', '2024-12-31')
    
    datafeed = HistoricalDataFeed()
    datafeed._cache = data
    
    strategy = SimpleMovingAverageStrategy(
        name="SMA_Cross",
        short_period=10,
        long_period=30
    )
    
    engine = BacktestEngine(
        strategy=strategy,
        datafeed=datafeed,
        initial_capital=1000000,
        commission_rate=0.001,
        slippage=0.001
    )
    
    results = engine.run(
        start_date='2024-01-01',
        end_date='2024-12-31',
        symbols=symbols
    )
    
    results.print_summary()
    
    return results


def demo_multi_strategy_backtest():
    """演示多策略回测"""
    print("\n" + "="*60)
    print("多策略回测演示")
    print("="*60)
    
    symbols = ['AAPL', 'GOOG', 'MSFT']
    
    data = generate_sample_data(symbols, '2024-01-01', '2024-06-30')
    
    datafeed = HistoricalDataFeed()
    datafeed._cache = data
    
    strategies = [
        SimpleMovingAverageStrategy(name="SMA_10_30", short_period=10, long_period=30),
        RSIStrategy(name="RSI_Strategy", rsi_period=14)
    ]
    
    engine = BacktestEngine(
        strategy=strategies,
        datafeed=datafeed,
        initial_capital=1000000
    )
    
    results = engine.run(
        start_date='2024-01-01',
        end_date='2024-06-30',
        symbols=symbols
    )
    
    results.print_summary()
    
    return results


def demo_performance_analysis():
    """演示绩效分析"""
    print("\n" + "="*60)
    print("绩效分析演示")
    print("="*60)
    
    np.random.seed(42)
    dates = pd.date_range(start='2024-01-01', end='2024-12-31', freq='B')
    returns = pd.Series(np.random.randn(len(dates)) * 0.02, index=dates)
    
    benchmark_returns = pd.Series(np.random.randn(len(dates)) * 0.015, index=dates)
    
    analyzer = PerformanceAnalyzer(risk_free_rate=0.03)
    
    metrics = analyzer.analyze(returns, benchmark_returns)
    
    print("\n绩效指标:")
    print(f"  总收益率: {metrics.get('total_return', 0):.2%}")
    print(f"  年化收益率: {metrics.get('annual_return', 0):.2%}")
    print(f"  年化波动率: {metrics.get('annual_volatility', 0):.2%}")
    print(f"  夏普比率: {metrics.get('sharpe_ratio', 0):.2f}")
    print(f"  索提诺比率: {metrics.get('sortino_ratio', 0):.2f}")
    print(f"  卡玛比率: {metrics.get('calmar_ratio', 0):.2f}")
    print(f"  最大回撤: {metrics.get('max_drawdown', 0):.2%}")
    
    print("\n相对基准指标:")
    print(f"  Alpha: {metrics.get('alpha', 0):.2%}")
    print(f"  Beta: {metrics.get('beta', 0):.2f}")
    print(f"  信息比率: {metrics.get('information_ratio', 0):.2f}")
    print(f"  相关系数: {metrics.get('correlation', 0):.2f}")
    
    return metrics


def demo_portfolio_simulation():
    """演示组合模拟"""
    print("\n" + "="*60)
    print("组合模拟演示")
    print("="*60)
    
    portfolio = Portfolio(
        initial_capital=1000000,
        commission_rate=0.001,
        slippage=0.001
    )
    
    dates = pd.date_range(start='2024-01-01', end='2024-12-31', freq='B')
    
    prices = {'AAPL': 150, 'GOOG': 140, 'MSFT': 380}
    
    print(f"\n初始资金: {portfolio.initial_capital:,.2f}")
    
    for i, date in enumerate(dates[:10]):
        price_change = {k: v * (1 + np.random.randn() * 0.02) for k, v in prices.items()}
        
        if i == 0:
            portfolio.buy('AAPL', 1000, price_change['AAPL'], date)
            print(f"\n{date.date()}: 买入 AAPL 1000股 @ {price_change['AAPL']:.2f}")
        
        if i == 5:
            portfolio.sell('AAPL', 500, price_change['AAPL'], date)
            print(f"{date.date()}: 卖出 AAPL 500股 @ {price_change['AAPL']:.2f}")
        
        portfolio.record_snapshot(date, price_change)
    
    final_prices = {k: v * (1 + np.random.randn() * 0.1) for k, v in prices.items()}
    total_value = portfolio.get_total_value(final_prices)
    
    print(f"\n最终总资产: {total_value:,.2f}")
    print(f"总收益率: {(total_value - portfolio.initial_capital) / portfolio.initial_capital:.2%}")
    print(f"总交易次数: {len(portfolio.trade_history)}")
    print(f"总佣金: {portfolio._total_commission:,.2f}")
    
    equity_curve = portfolio.get_equity_curve()
    print(f"\n权益曲线数据点: {len(equity_curve)}")
    
    return portfolio


if __name__ == "__main__":
    print("="*60)
    print("回测引擎演示程序")
    print("="*60)
    
    results = demo_basic_backtest()
    
    demo_multi_strategy_backtest()
    
    demo_performance_analysis()
    
    demo_portfolio_simulation()
    
    print("\n" + "="*60)
    print(" 所有演示完成!")
    print("="*60)
