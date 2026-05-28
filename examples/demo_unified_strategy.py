"""
统一策略管理演示脚本
展示如何使用StrategyManager统一管理技术指标策略和多因子策略
"""

import sys
import os
from typing import Dict

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + '/..')

import pandas as pd
import numpy as np
from strategy.strategy_manager import StrategyManager
from strategy.multi_factor.example_strategy import SimpleValueMomentumStrategy


def generate_sample_stock_data(num_stocks: int = 50, num_days: int = 252) -> Dict[str, pd.DataFrame]:
    """
    生成示例股票数据
    
    Args:
        num_stocks: 股票数量
        num_days: 天数
        
    Returns:
        股票数据字典
    """
    stock_data = {}
    
    for i in range(num_stocks):
        # 生成随机价格数据
        dates = pd.date_range(start='2024-01-01', periods=num_days)
        np.random.seed(i)
        
        # 生成收盘价
        base_price = 100 + np.random.randn() * 50
        price = base_price + np.cumsum(np.random.randn(num_days) * 2)
        price = np.maximum(price, 1)  # 确保价格为正
        
        # 生成eps和bvps（简单模拟）
        eps = 5 + np.random.randn(num_days) * 2
        bvps = 50 + np.random.randn(num_days) * 10
        
        # 生成市值
        market_cap = price * (1000000 + np.random.randint(0, 9000000))
        
        # 生成日收益率
        price_series = pd.Series(price)
        return_series = price_series.pct_change()
        return_series[0] = 0
        return_series = return_series.values
        
        # 生成市场收益率
        market_return = return_series + np.random.randn(num_days) * 0.005
        
        # 创建DataFrame
        df = pd.DataFrame({
            'date': dates,
            'close': price,
            'eps': eps,
            'bvps': bvps,
            'market_cap': market_cap,
            'return': return_series,
            'market_return': market_return
        })
        df.set_index('date', inplace=True)
        
        # 股票代码格式：STOCK_001, STOCK_002, ...
        stock_symbol = f'STOCK_{i+1:03d}'
        stock_data[stock_symbol] = df
    
    return stock_data


def demo_unified_strategy_management():
    """
    演示统一策略管理
    """
    print("🚀 开始演示统一策略管理")
    print("=" * 60)
    
    # 创建策略管理器
    print("📦 创建策略管理器...")
    strategy_manager = StrategyManager()
    print("✅ 策略管理器创建成功")
    
    # 生成示例数据
    print("\n📊 生成示例股票数据...")
    stock_data = generate_sample_stock_data(num_stocks=30, num_days=252)
    print(f"✅ 生成了 {len(stock_data)} 只股票，每只股票 {len(next(iter(stock_data.values())))} 天的数据")
    
    # 创建多因子策略实例
    print("\n🎯 创建多因子策略实例...")
    multi_factor_strategy = SimpleValueMomentumStrategy(
        name="SimpleValueMomentum",
        top_n=10,
        lookback_period=60,
        rebalance_frequency='monthly'
    )
    print("✅ 多因子策略实例创建成功")
    
    # 注册多因子策略
    print("\n📝 注册多因子策略...")
    strategy_id = strategy_manager.register_strategy(multi_factor_strategy)
    print(f"✅ 多因子策略 '{strategy_id}' 注册成功")
    
    # 启动策略
    print("\n🔄 启动策略...")
    strategy_manager.start_strategy(strategy_id)
    print(f"✅ 策略 '{strategy_id}' 启动成功")
    
    # 生成信号
    print("\n📈 生成交易信号...")
    signals = strategy_manager.generate_signals(strategy_id, stock_data)
    print(f"✅ 生成了 {len(signals)} 个交易信号")
    
    # 查看信号
    if signals:
        print("\n📋 交易信号详情：")
        signal = signals[0]
        print(f"   信号类型: {signal['type']}")
        print(f"   策略名称: {signal['strategy_name']}")
        print(f"   时间戳: {signal['timestamp']}")
        print(f"   选中股票数量: {len(signal['selected_stocks'])}")
        print(f"   选中股票: {', '.join(signal['selected_stocks'][:5])}...")
    
    # 获取策略信息
    print("\nℹ️  查看策略信息...")
    strategy_info = strategy_manager.get_strategy_info(strategy_id)
    print(f"   策略名称: {strategy_info['name']}")
    print(f"   运行状态: {'运行中' if strategy_info['is_running'] else '已停止'}")
    print(f"   创建时间: {strategy_info['created_at']}")
    print(f"   信号数量: {strategy_info['signal_count']}")
    
    # 获取策略绩效
    print("\n📊 查看策略绩效...")
    performance = strategy_manager.get_strategy_performance(strategy_id)
    print(f"   总交易次数: {performance['total_trades']}")
    print(f"   盈利交易: {performance['winning_trades']}")
    print(f"   亏损交易: {performance['losing_trades']}")
    print(f"   总盈利: {performance['total_profit']:.2f}")
    print(f"   总亏损: {performance['total_loss']:.2f}")
    
    # 停止策略
    print("\n🛑 停止策略...")
    strategy_manager.stop_strategy(strategy_id)
    print(f"✅ 策略 '{strategy_id}' 已停止")
    
    # 注销策略
    print("\n🗑️  注销策略...")
    strategy_manager.unregister_strategy(strategy_id)
    print(f"✅ 策略 '{strategy_id}' 已注销")
    
    print("\n🎉 统一策略管理演示完成！")
    print("=" * 60)
    
    # 查看全局信号
    global_signals = strategy_manager.get_global_signals()
    print(f"\n📋 全局信号历史：共 {len(global_signals)} 个信号")
    
    # 清除信号
    strategy_manager.clear_signals()
    print("✅ 信号历史已清除")


if __name__ == "__main__":
    demo_unified_strategy_management()
