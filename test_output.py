import pandas as pd
import numpy as np
from datetime import datetime
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 生成测试数据
dates = pd.date_range(end=datetime.now(), periods=100, freq='D')
np.random.seed(42)
base_price = 100

# 前50天上升，后50天下降
returns_up = np.random.normal(0.005, 0.01, 50)
returns_down = np.random.normal(-0.005, 0.01, 50)
returns = np.concatenate([returns_up, returns_down])
prices = base_price * np.exp(np.cumsum(returns))

test_data = pd.DataFrame({
    'open': prices * 0.99,
    'high': prices * 1.01,
    'low': prices * 0.98,
    'close': prices,
    'volume': np.random.randint(1000000, 10000000, 100)
}, index=dates)

# 创建一个简单的测试来看batch_calculate返回什么
from indicators.base.calculator import IndicatorCalculator
from indicators.technical.trend.moving_average import SMA

# 创建计算器
calculator = IndicatorCalculator()

# 注册SMA指标
sma_20 = SMA(period=20, price_field='close')
sma_50 = SMA(period=50, price_field='close')
calculator.register_indicator(sma_20, 'sma_20')
calculator.register_indicator(sma_50, 'sma_50')

# 批量计算
result = calculator.batch_calculate(test_data, ['sma_20', 'sma_50'], use_cache=False)

print('='*60)
print('batch_calculate 返回的数据结构:')
print('='*60)
print(f'返回类型: {type(result)}')
print(f'返回的键: {result.keys()}')
print()

for symbol, indicators in result.items():
    print(f'股票/符号: {symbol}')
    print(f'  指标数量: {len(indicators)}')
    print(f'  指标键: {indicators.keys()}')
    for ind_name, ind_value in indicators.items():
        print(f'    {ind_name}: 类型={type(ind_value).__name__}')
        if isinstance(ind_value, pd.DataFrame):
            print(f'      形状: {ind_value.shape}')
            print(f'      列: {ind_value.columns.tolist()}')
            print(f'      前3行:')
            print(ind_value.head(3).to_string())
        elif isinstance(ind_value, dict) and 'error' in ind_value:
            print(f'      错误: {ind_value["error"]}')
    print()

# 现在用StrategyExecutor来执行，看看它返回什么
from strategy.strategy_executor import StrategyExecutor
from strategy.technical_strategy import TechnicalStrategy

class TestMAStrategy(TechnicalStrategy):
    def __init__(self):
        super().__init__('TestMAStrategy')
        self.add_required_indicator('sma_20')
        self.add_required_indicator('sma_50')

    def define_rules(self, **kwargs):
        pass

    def apply_rules(self, indicators_data, **kwargs):
        print()
        print('='*60)
        print('策略apply_rules接收到的indicators_data:')
        print('='*60)
        print(f'类型: {type(indicators_data)}')
        print(f'键: {indicators_data.keys() if isinstance(indicators_data, dict) else "N/A"}')

        signals = []
        sma_20 = indicators_data.get('sma_20')
        sma_50 = indicators_data.get('sma_50')

        if sma_20 is None or sma_50 is None:
            print(f'ERROR: sma_20={sma_20}, sma_50={sma_50}')
            return signals

        # 如果是嵌套结构（按股票分组的），尝试获取第一个股票的数据
        if isinstance(sma_20, dict) and 'unknown' in sma_20:
            sma_20 = sma_20['unknown']
            sma_50 = sma_50['unknown']

        print(f'sma_20类型: {type(sma_20)}')
        print(f'sma_50类型: {type(sma_50)}')

        if isinstance(sma_20, pd.DataFrame):
            sma_20_current = float(sma_20['sma'].iloc[-1])
            sma_20_prev = float(sma_20['sma'].iloc[-2])
            sma_50_current = float(sma_50['sma'].iloc[-1])
            sma_50_prev = float(sma_50['sma'].iloc[-2])

            if (sma_20_prev <= sma_50_prev) and (sma_20_current > sma_50_current):
                signal = {
                    'action': 'BUY',
                    'reason': '金叉信号',
                    'fast_ma': sma_20_current,
                    'slow_ma': sma_50_current
                }
                signals.append(signal)
            elif (sma_20_prev >= sma_50_prev) and (sma_20_current < sma_50_current):
                signal = {
                    'action': 'SELL',
                    'reason': '死叉信号',
                    'fast_ma': sma_20_current,
                    'slow_ma': sma_50_current
                }
                signals.append(signal)

        return signals

executor = StrategyExecutor()
strategy = TestMAStrategy()

# 注册指标
executor.calculator.register_indicator(sma_20, 'sma_20')
executor.calculator.register_indicator(sma_50, 'sma_50')

signals = executor.execute_strategy(strategy, test_data)

print()
print('='*60)
print('execute_strategy 最终返回:')
print('='*60)
print(f'返回类型: {type(signals)}')
print(f'信号数量: {len(signals)}')
if signals:
    print('信号内容:')
    for i, sig in enumerate(signals):
        print(f'  信号 {i+1}: {sig}')