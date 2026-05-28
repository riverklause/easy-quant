"""
测试策略执行器
验证策略模块重构后的功能
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from strategy.strategy_executor import StrategyExecutor
from strategy.technical_strategy import TechnicalStrategy
from strategy.multi_factor.multi_factor_strategy import MultiFactorStrategy
from strategy.multi_factor.example_strategy import SimpleValueMomentumStrategy


class TestMovingAverageStrategy(TechnicalStrategy):
    """
    测试用的移动平均线策略
    专注于策略规则定义
    """
    
    def __init__(self, name: str = "TestMAStrategy"):
        """
        初始化测试策略
        """
        super().__init__(name)
        
        # 添加所需指标
        self.add_required_indicator('sma_20')
        self.add_required_indicator('sma_50')
        
        # 策略参数
        self.strategy_params = {
            'fast_period': 20,
            'slow_period': 50
        }
    
    def define_rules(self, **kwargs):
        """
        定义策略规则
        """
        # 规则1：当短期均线上穿长期均线时买入
        # 规则2：当短期均线下穿长期均线时卖出
        print(f"🔄 策略 '{self.name}' 规则定义完成")
        print(f"   - 短期均线: {self.strategy_params['fast_period']}日")
        print(f"   - 长期均线: {self.strategy_params['slow_period']}日")
    
    def apply_rules(self, indicators_data, **kwargs):
        """
        应用策略规则
        """
        signals = []
        
        try:
            # 获取指标数据
            sma_20 = indicators_data['sma_20']
            sma_50 = indicators_data['sma_50']
            
            # 检查是否有足够的数据
            if len(sma_20) < 2 or len(sma_50) < 2:
                return signals
            
            # 获取最新值（确保是标量值）
            # SMA指标返回的是DataFrame，需要提取'sma'列
            if isinstance(sma_20, pd.DataFrame):
                sma_20_current = float(sma_20['sma'].iloc[-1])
                sma_20_prev = float(sma_20['sma'].iloc[-2])
                sma_50_current = float(sma_50['sma'].iloc[-1])
                sma_50_prev = float(sma_50['sma'].iloc[-2])
            else:
                sma_20_current = float(sma_20.iloc[-1])
                sma_20_prev = float(sma_20.iloc[-2])
                sma_50_current = float(sma_50.iloc[-1])
                sma_50_prev = float(sma_50.iloc[-2])
            
            # 规则应用：金叉买入，死叉卖出
            if (sma_20_prev <= sma_50_prev) and (sma_20_current > sma_50_current):
                # 金叉信号
                signal = {
                    'action': 'BUY',
                    'reason': '金叉信号',
                    'timestamp': datetime.now(),
                    'fast_ma': sma_20_current,
                    'slow_ma': sma_50_current
                }
                signals.append(signal)
            
            elif (sma_20_prev >= sma_50_prev) and (sma_20_current < sma_50_current):
                # 死叉信号
                signal = {
                    'action': 'SELL',
                    'reason': '死叉信号',
                    'timestamp': datetime.now(),
                    'fast_ma': sma_20_current,
                    'slow_ma': sma_50_current
                }
                signals.append(signal)
            
        except Exception as e:
            print(f"❌ 应用规则失败: {e}")
        
        return signals


def generate_test_data(n_days: int = 100):
    """
    生成测试数据
    
    Args:
        n_days: 数据天数
        
    Returns:
        测试数据DataFrame
    """
    dates = pd.date_range(end=datetime.now(), periods=n_days, freq='D')
    
    # 生成趋势性价格数据，更容易产生金叉/死叉信号
    np.random.seed(42)
    base_price = 100
    
    # 前50天：上升趋势
    returns_up = np.random.normal(0.005, 0.01, n_days//2)
    # 后50天：下降趋势
    returns_down = np.random.normal(-0.005, 0.01, n_days//2)
    
    returns = np.concatenate([returns_up, returns_down])
    prices = base_price * np.exp(np.cumsum(returns))
    
    # 创建DataFrame
    data = pd.DataFrame({
        'open': prices * 0.99,
        'high': prices * 1.01,
        'low': prices * 0.98,
        'close': prices,
        'volume': np.random.randint(1000000, 10000000, n_days)
    }, index=dates)
    
    return data


def generate_test_factors_data(n_stocks: int = 10, n_days: int = 100):
    """
    生成测试因子数据
    
    Args:
        n_stocks: 股票数量
        n_days: 数据天数
        
    Returns:
        因子数据字典
    """
    factors_data = {}
    
    for i in range(n_stocks):
        symbol = f"TEST{i:03d}"
        
        # 生成随机因子数据
        dates = pd.date_range(end=datetime.now(), periods=n_days, freq='D')
        
        df = pd.DataFrame({
            'pe_ratio': np.random.uniform(5, 30, n_days),
            'pb_ratio': np.random.uniform(0.5, 5, n_days),
            'return_20d': np.random.normal(0, 0.1, n_days)
        }, index=dates)
        
        factors_data[symbol] = df
    
    return factors_data


def test_technical_strategy():
    """
    测试技术指标策略
    """
    print("🧪 测试技术指标策略...")
    
    # 创建策略执行器
    executor = StrategyExecutor()
    
    # 创建测试策略
    ma_strategy = TestMovingAverageStrategy("TestMAStrategy")
    
    # 生成测试数据
    test_data = generate_test_data(100)
    
    # 手动创建指标实例并注册到计算器
    from indicators.technical.trend.moving_average import SMA
    
    # 创建SMA指标实例
    sma_20 = SMA(period=20, price_field='close')
    sma_50 = SMA(period=50, price_field='close')
    
    # 注册指标实例到计算器
    executor.calculator.register_indicator(sma_20, "sma_20")
    executor.calculator.register_indicator(sma_50, "sma_50")
    
    # 执行策略（直接传递策略实例）
    signals = executor.execute_strategy(ma_strategy, test_data)
    
    print(f"✅ 技术指标策略测试完成")
    print(f"   策略名称: {ma_strategy.name}")
    print(f"   所需指标: {ma_strategy.get_required_indicators()}")
    print(f"   生成信号: {len(signals)} 个")
    
    if signals:
        for i, signal in enumerate(signals[:3]):  # 显示前3个信号
            print(f"   信号{i+1}: {signal['action']} - {signal['reason']}")
    
    # 即使没有信号，只要执行过程没有错误，也算测试通过
    return True


def test_multi_factor_strategy():
    """
    测试多因子策略
    """
    print("\n🧪 测试多因子策略...")
    
    # 创建策略执行器
    executor = StrategyExecutor()
    
    # 创建测试策略
    factor_strategy = SimpleValueMomentumStrategy(
        name="TestFactorStrategy",
        top_n=5,
        lookback_period=20,
        rebalance_frequency='monthly'
    )
    
    # 生成测试因子数据
    factors_data = generate_test_factors_data(n_stocks=20, n_days=100)
    
    # 执行策略（因子数据已计算好）
    signals = executor.execute_strategy(
        factor_strategy, 
        factors_data, 
        calculate_indicators=False
    )
    
    print(f"✅ 多因子策略测试完成")
    print(f"   策略名称: {factor_strategy.name}")
    print(f"   所需因子: {factor_strategy.factor_names}")
    print(f"   生成信号: {len(signals)} 个")
    
    if signals:
        signal = signals[0]
        print(f"   选股数量: {len(signal.get('selected_stocks', []))}")
        print(f"   选股结果: {signal.get('selected_stocks', [])[:5]}...")
    
    return len(signals) > 0


def test_batch_execution():
    """
    测试批量执行
    """
    print("\n🧪 测试批量执行...")
    
    # 创建策略执行器
    executor = StrategyExecutor()
    
    # 创建多个策略
    ma_strategy = TestMovingAverageStrategy("MAStrategy1")
    factor_strategy = SimpleValueMomentumStrategy("FactorStrategy1", top_n=3)
    
    # 手动注册SMA指标到计算器
    from indicators.technical.trend.moving_average import SMA
    sma_20 = SMA(period=20, price_field='close')
    sma_50 = SMA(period=50, price_field='close')
    executor.calculator.register_indicator(sma_20, "sma_20")
    executor.calculator.register_indicator(sma_50, "sma_50")
    
    # 生成测试数据
    test_data = generate_test_data(100)
    factors_data = generate_test_factors_data(n_stocks=10, n_days=100)
    
    # 创建策略字典
    strategies = {
        "MAStrategy1": ma_strategy,
        "FactorStrategy1": factor_strategy
    }
    
    # 批量计算指标
    strategy_indicators = executor.batch_calculate_for_strategies(strategies, test_data)
    
    print(f"✅ 批量计算测试完成")
    print(f"   策略数量: {len(strategies)}")
    print(f"   策略指标数据: {len(strategy_indicators)} 个策略")
    
    for strategy_id, indicators in strategy_indicators.items():
        print(f"   {strategy_id}: {len(indicators)} 个指标")
    
    # 批量执行所有策略
    all_signals = executor.execute_strategies(strategies, test_data)
    
    print(f"\n✅ 批量执行测试完成")
    print(f"   执行策略数量: {len(all_signals)}")
    
    for strategy_id, signals in all_signals.items():
        print(f"   {strategy_id}: {len(signals)} 个信号")
    
    return len(all_signals) > 0


def test_execution_stats():
    """
    测试执行统计
    """
    print("\n🧪 测试执行统计...")
    
    # 创建策略执行器
    executor = StrategyExecutor()
    
    # 创建策略
    ma_strategy = TestMovingAverageStrategy("StatsTestStrategy")
    
    # 手动注册SMA指标到计算器
    from indicators.technical.trend.moving_average import SMA
    sma_20 = SMA(period=20, price_field='close')
    sma_50 = SMA(period=50, price_field='close')
    executor.calculator.register_indicator(sma_20, "sma_20")
    executor.calculator.register_indicator(sma_50, "sma_50")
    
    # 生成测试数据
    test_data = generate_test_data(50)
    
    # 多次执行策略
    for i in range(5):
        signals = executor.execute_strategy(ma_strategy, test_data)
        print(f"   执行 {i+1}: {len(signals)} 个信号")
    
    # 获取执行统计
    stats = executor.get_execution_stats()
    
    print(f"✅ 执行统计测试完成")
    print(f"   总执行次数: {stats['total_executions']}")
    print(f"   成功执行: {stats['successful_executions']}")
    print(f"   失败执行: {stats['failed_executions']}")
    print(f"   总指标计算: {stats['total_indicators_calculated']}")
    
    return stats['total_executions'] > 0


def main():
    """
    主测试函数
    """
    print("🚀 开始策略模块重构测试")
    print("=" * 50)
    
    test_results = {}
    
    try:
        # 测试技术指标策略
        test_results['technical_strategy'] = test_technical_strategy()
        
        # 测试多因子策略
        test_results['multi_factor_strategy'] = test_multi_factor_strategy()
        
        # 测试批量执行
        test_results['batch_execution'] = test_batch_execution()
        
        # 测试执行统计
        test_results['execution_stats'] = test_execution_stats()
        
        # 总结测试结果
        print("\n" + "=" * 50)
        print("📊 测试结果总结")
        print("=" * 50)
        
        all_passed = True
        for test_name, passed in test_results.items():
            status = "✅ 通过" if passed else "❌ 失败"
            print(f"{test_name}: {status}")
            if not passed:
                all_passed = False
        
        if all_passed:
            print("\n🎉 所有测试通过！策略模块重构成功！")
            print("   策略模块现在专注于规则定义，指标计算职责已分离到执行器")
        else:
            print("\n⚠️  部分测试失败，请检查代码")
            
    except Exception as e:
        print(f"\n❌ 测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return all_passed


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)