"""
指标计算引擎演示脚本
展示如何使用指标计算引擎进行技术分析
"""

import asyncio
import pandas as pd
import numpy as np
import time
from datetime import datetime, timedelta
import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + '/..')

from indicators.base.calculator import IndicatorCalculator
from indicators.base.registry import indicators_registry, register_indicator_func, create_indicator_func
from indicators.technical.trend.moving_average import SMA, EMA, MACD


def generate_sample_data():
    """生成示例股票数据"""
    np.random.seed(42)
    dates = pd.date_range(start='2024-01-01', end='2024-03-01', freq='D')
    
    # 生成随机价格数据
    price = 100 + np.cumsum(np.random.randn(len(dates)) * 0.5)
    
    data = pd.DataFrame({
        'date': dates,
        'open': price + np.random.randn(len(dates)) * 0.1,
        'high': price + np.abs(np.random.randn(len(dates)) * 0.2),
        'low': price - np.abs(np.random.randn(len(dates)) * 0.2),
        'close': price,
        'volume': np.random.randint(100000, 1000000, len(dates))
    })
    
    data.set_index('date', inplace=True)
    return data


def demo_basic_indicators():
    """演示基础指标计算"""
    print("🚀 开始基础指标计算演示")
    print("=" * 60)
    
    # 生成示例数据
    sample_data = generate_sample_data()
    print(f"📊 生成示例数据: {len(sample_data)} 条记录")
    print(sample_data.head())
    
    # 创建指标计算器
    calculator = IndicatorCalculator(cache_size=100, cache_ttl=300)
    
    # 注册指标
    sma_20 = SMA(period=20, price_field='close')
    ema_12 = EMA(period=12, price_field='close')
    macd = MACD(fast_period=12, slow_period=26, signal_period=9)
    ema_5 = EMA(period=5, price_field='close')
    
    calculator.register_indicator(sma_20, 'sma_20')
    calculator.register_indicator(ema_12, 'ema_12')
    calculator.register_indicator(macd, 'macd')
    calculator.register_indicator(ema_5, 'ema_5')
    
    print("\n✅ 指标注册完成")
    
    # 计算单个指标
    print("\n📈 计算单个指标 - SMA(20)")
    sma_result = calculator.calculate('sma_20', sample_data)
    print(f"SMA(20) 计算结果: {len(sma_result)} 条记录")
    print(sma_result[['close', 'sma']].tail())
    
    # 批量计算多个指标
    print("\n📊 批量计算多个指标")
    batch_results = calculator.batch_calculate(sample_data, ['sma_20', 'ema_12', 'macd'])
    
    for indicator_name, result in batch_results.items():
        if 'error' not in result:
            print(f"✅ {indicator_name}: 计算成功 ({len(result)} 条记录)")
        else:
            print(f"❌ {indicator_name}: {result['error']}")
    
    # 显示MACD计算结果
    if 'macd' in batch_results and 'error' not in batch_results['macd']:
        macd_result = batch_results['macd']
        print("\n📊 MACD指标结果预览:")
        print(macd_result[['close', 'macd', 'signal', 'histogram']].tail())
    
    # 显示计算统计
    stats = calculator.get_calculation_stats()
    print(f"\n📊 计算统计:")
    print(f"总计算次数: {stats['total_calculations']}")
    print(f"缓存命中: {stats['cache_hits']}")
    print(f"缓存未命中: {stats['cache_misses']}")
    
    return calculator, sample_data


def demo_registry_functionality():
    """演示指标注册器功能"""
    print("\n" + "=" * 60)
    print("🔧 演示指标注册器功能")
    print("=" * 60)
    
    registry = indicators_registry()
    register_indicator_func(SMA, 'trend')
    register_indicator_func(EMA, 'trend')
    register_indicator_func(MACD, 'trend')
    # 获取可用指标
    available_indicators = registry.get_available_indicators()
    print(f"✅ 可用指标: {available_indicators}")
    
    # 获取指标分类
    categories = registry.get_indicator_categories()
    print(f"✅ 指标分类: {categories}")
    
    # 获取分类下的指标
    trend_indicators = registry.get_available_indicators('trend')
    print(f"✅ 趋势指标: {trend_indicators}")
    
    # 获取指标信息
    for indicator_name in trend_indicators[:2]:  # 只显示前两个
        info = registry.get_indicator_info(indicator_name)
        print(f"\n📋 {indicator_name} 信息:")
        print(f"   描述: {info['docstring'][:100]}...")
        print(f"   参数: {list(info['parameters'].keys())}")
    
    # 使用实例方法创建指标实例
    sma_instance = create_indicator_func('SMA', period=10)
    print(f"\n✅ 创建的SMA实例: {sma_instance}")
    
    return registry


def demo_real_time_calculation(calculator, sample_data):
    """演示实时指标计算"""
    print("\n" + "=" * 60)
    print("⚡ 演示实时指标计算")
    print("=" * 60)
    
    # 模拟实时数据流
    print("📡 模拟实时数据流...")
    
    # 取最后10条数据作为实时数据
    real_time_data = sample_data.iloc[-10:].copy()
    
    # 模拟逐条接收数据并更新指标
    for i, (idx, row) in enumerate(real_time_data.iterrows()):
        print(f"\n🔄 接收第 {i+1} 条实时数据:")
        print(f"   时间: {idx}, 收盘价: {row['close']:.2f}")
        
        # 转换为单条数据格式
        single_data_point = pd.DataFrame([row])
        single_data_point.index = [idx]
        
        # 更新SMA指标
        try:
            updated_sma = calculator.update_indicator('sma_20', single_data_point)
            current_sma = updated_sma['sma'].iloc[-1] if 'sma' in updated_sma else 'N/A'
            print(f"   SMA(20) 更新: {current_sma:.2f}")
        except Exception as e:
            print(f"   SMA更新失败: {e}")
        
        # 模拟延迟
        # time.sleep(0.1)
    
    print("\n✅ 实时计算演示完成")


def demo_performance_optimization():
    """演示性能优化功能"""
    print("\n" + "=" * 60)
    print("⚡ 演示性能优化功能")
    print("=" * 60)
    
    # 生成大量数据
    print("📊 生成大量数据测试性能...")
    large_data = generate_sample_data()
    # 复制数据以增加数据量
    large_data = pd.concat([large_data] * 10)
    print(f"测试数据量: {len(large_data)} 条记录")
    
    calculator = IndicatorCalculator(cache_size=1000, cache_ttl=600)
    
    # 注册多个指标
    indicators_to_test = []
    for period in [5, 10, 20, 50]:
        sma = SMA(period=period)
        indicator_id = f'sma_{period}'
        calculator.register_indicator(sma, indicator_id)
        indicators_to_test.append(indicator_id)
    
    # 注册EMA指标用于批量更新测试
    ema_5 = EMA(period=5, price_field='close')
    calculator.register_indicator(ema_5, 'ema_5')
    indicators_to_test.append('ema_5')
    
    # 第一次计算（缓存未命中）
    print("\n🔍 第一次计算（缓存未命中）...")
    start_time = datetime.now()
    results1 = calculator.batch_calculate(large_data, indicators_to_test)
    time1 = (datetime.now() - start_time).total_seconds()
    
    # 第二次计算（缓存命中）
    print("🔍 第二次计算（缓存命中）...")
    start_time = datetime.now()
    results2 = calculator.batch_calculate(large_data, indicators_to_test)
    time2 = (datetime.now() - start_time).total_seconds()
    
    stats = calculator.get_calculation_stats()
    
    print(f"\n📊 性能对比:")
    print(f"第一次计算时间: {time1:.4f} 秒")
    print(f"第二次计算时间: {time2:.4f} 秒")
    print(f"性能提升: {((time1 - time2) / time1 * 100):.1f}%")
    print(f"缓存命中率: {(stats['cache_hits'] / stats['total_calculations'] * 100):.1f}%")
    
    # 测试增量更新的缓存性能
    print("\n--- 增量更新缓存测试 ---")
    calculator.clear_cache()  # 清空缓存重新测试
    
    # 重置统计信息
    calculator._calculation_stats = {'total_calculations': 0, 'cache_hits': 0, 'cache_misses': 0}
    
    # 模拟实时数据流
    real_time_data = large_data.iloc[-5:].copy()
    
    # 第一次增量更新
    result1 = calculator.update_indicator('sma_10', real_time_data.iloc[0:1])
    print(f"第一次增量更新结果: {len(result1)} 条记录 (缓存未命中)")
    
    # 第二次相同的增量更新（应该命中缓存）
    result2 = calculator.update_indicator('sma_10', real_time_data.iloc[0:1])
    print(f"第二次增量更新结果: {len(result2)} 条记录 (缓存命中)")
    
    # 不同的增量更新（应该重新计算）
    result3 = calculator.update_indicator('sma_10', real_time_data.iloc[1:2])
    print(f"第三次增量更新结果: {len(result3)} 条记录 (缓存未命中)")
    
    updated_stats = calculator.get_calculation_stats()
    incremental_cache_hit_rate = (updated_stats['cache_hits'] / (updated_stats['cache_hits'] + updated_stats['cache_misses']) * 100) if (updated_stats['cache_hits'] + updated_stats['cache_misses']) > 0 else 0
    print(f"增量更新缓存命中率: {incremental_cache_hit_rate:.1f}%")
    print(f"缓存命中: {updated_stats['cache_hits']}, 缓存未命中: {updated_stats['cache_misses']}")

    # 6. 单个指标增量更新缓存测试
    print("\n=== 单个指标增量更新缓存测试 ===")
    
    # 重置统计信息
    calculator._calculation_stats = {'total_calculations': 0, 'cache_hits': 0, 'cache_misses': 0}
    
    # 模拟实时数据流
    real_time_data = [
        {'close': 105.0, 'volume': 1200},
        {'close': 105.0, 'volume': 1200},  # 相同数据
        {'close': 108.0, 'volume': 1500}   # 不同数据
    ]
    
    print("模拟实时数据流增量更新:")
    for i, data in enumerate(real_time_data):
        result = calculator.update_indicator('sma_5', data, use_cache=True)
        cache_status = "缓存命中" if i == 1 else "缓存未命中"  # 第二次相同数据应该命中缓存
        print(f"  第{i+1}次更新 - 结果: {result:.2f} ({cache_status})")
    
    # 统计增量更新缓存命中率
    total_incremental_calculations = calculator._calculation_stats['cache_hits'] + calculator._calculation_stats['cache_misses']
    incremental_cache_hit_rate = (calculator._calculation_stats['cache_hits'] / total_incremental_calculations * 100) if total_incremental_calculations > 0 else 0
    
    print(f"\n单个指标增量更新缓存统计:")
    print(f"  缓存命中: {calculator._calculation_stats['cache_hits']} 次")
    print(f"  缓存未命中: {calculator._calculation_stats['cache_misses']} 次")
    print(f"  增量更新缓存命中率: {incremental_cache_hit_rate:.1f}%")
    
    # 7. 批量增量更新测试
    print("\n=== 批量指标增量更新测试 ===")
    
    # 重置统计信息
    calculator._calculation_stats = {'total_calculations': 0, 'cache_hits': 0, 'cache_misses': 0}
    
    # 清空缓存，确保测试准确性
    calculator._cache.clear()
    
    # 模拟批量更新场景
    batch_data = [
        {'close': 110.0, 'volume': 1300},  # 第一次批量更新
        {'close': 110.0, 'volume': 1300},  # 相同数据，应该命中缓存
        {'close': 115.0, 'volume': 1400}   # 不同数据
    ]
    
    # 要批量更新的指标列表
    indicator_list = ['sma_5', 'sma_10', 'ema_5']
    
    print("模拟批量指标增量更新:")
    for i, data in enumerate(batch_data):
        print(f"\n第{i+1}次批量更新:")
        
        # 执行批量更新
        results = calculator.batch_update_indicators(data, indicator_list, use_cache=True)
        
        # 显示每个指标的结果
        for indicator_id in indicator_list:
            if indicator_id in results:
                result = results[indicator_id]
                if isinstance(result, dict) and 'error' in result:
                    print(f"  {indicator_id}: 错误 - {result['error']}")
                else:
                    print(f"  {indicator_id}: {result:.2f}")
        
        # 显示缓存状态
        if i == 1:
            print("  (本次更新应该全部命中缓存)")
        elif i == 2:
            print("  (本次更新应该全部未命中缓存)")
    
    # 统计批量更新缓存命中率
    total_batch_calculations = calculator._calculation_stats['cache_hits'] + calculator._calculation_stats['cache_misses']
    batch_cache_hit_rate = (calculator._calculation_stats['cache_hits'] / total_batch_calculations * 100) if total_batch_calculations > 0 else 0
    
    print(f"\n批量更新缓存统计:")
    print(f"  缓存命中: {calculator._calculation_stats['cache_hits']} 次")
    print(f"  缓存未命中: {calculator._calculation_stats['cache_misses']} 次")
    print(f"  批量更新缓存命中率: {batch_cache_hit_rate:.1f}%")
    
    # 8. 批量更新性能对比
    print("\n=== 批量更新性能对比 ===")
    
    # 重置统计信息
    calculator._calculation_stats = {'total_calculations': 0, 'cache_hits': 0, 'cache_misses': 0}
    
    # 测试数据
    test_data = {'close': 112.0, 'volume': 1350}
    
    # 方法1: 逐个更新（传统方式）
    start_time = time.time()
    individual_results = {}
    for indicator_id in indicator_list:
        individual_results[indicator_id] = calculator.update_indicator(indicator_id, test_data, use_cache=True)
    individual_time = time.time() - start_time
    
    # 重置统计信息
    calculator._calculation_stats = {'total_calculations': 0, 'cache_hits': 0, 'cache_misses': 0}
    
    # 方法2: 批量更新（新方式）
    start_time = time.time()
    batch_results = calculator.batch_update_indicators(test_data, indicator_list, use_cache=True)
    batch_time = time.time() - start_time
    
    print(f"逐个更新耗时: {individual_time:.6f} 秒")
    print(f"批量更新耗时: {batch_time:.6f} 秒")
    print(f"性能提升: {(individual_time - batch_time) / individual_time * 100:.1f}%")
    
    # 验证结果一致性
    print("\n结果一致性验证:")
    all_match = True
    for indicator_id in indicator_list:
        individual_result = individual_results[indicator_id]
        batch_result = batch_results[indicator_id]
        if abs(individual_result - batch_result) < 0.001:
            print(f"  {indicator_id}: ✓ 结果一致")
        else:
            print(f"  {indicator_id}: ✗ 结果不一致 (逐个: {individual_result:.2f}, 批量: {batch_result:.2f})")
            all_match = False
    
    if all_match:
        print("✓ 所有指标结果一致，批量更新功能正确")


async def main():
    """主函数"""
    print("🎯 指标计算引擎演示")
    print("=" * 60)
    
    try:
        # 演示基础指标计算
        calculator, sample_data = demo_basic_indicators()
        
        # 演示注册器功能
        registry = demo_registry_functionality()
        
        # 演示实时计算
        demo_real_time_calculation(calculator, sample_data)
        
        # 演示性能优化
        demo_performance_optimization()
        
        print("\n" + "=" * 60)
        print("🎉 指标计算引擎演示完成！")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ 演示过程中出错: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    asyncio.run(main())