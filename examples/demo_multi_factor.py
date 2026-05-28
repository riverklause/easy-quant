"""
多因子策略演示脚本
展示如何使用多因子策略框架实现和运行多因子策略
"""

import sys
import os
from typing import Dict
# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + '/..')

import pandas as pd
import numpy as np
from strategy.multi_factor.example_strategy import SimpleValueMomentumStrategy


def generate_sample_stock_data(num_stocks: int = 100, num_days: int = 252) -> Dict[str, pd.DataFrame]:
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


def demo_simple_value_momentum_strategy():
    """
    演示简单价值动量多因子策略
    """
    print("🚀 开始演示简单价值动量多因子策略")
    print("=" * 60)
    
    # 生成示例数据
    print("📊 生成示例股票数据...")
    stock_data = generate_sample_stock_data(num_stocks=50, num_days=252)
    print(f"✅ 生成了 {len(stock_data)} 只股票，每只股票 {len(next(iter(stock_data.values())))} 天的数据")
    
    # 显示示例数据
    sample_symbol = list(stock_data.keys())[0]
    print(f"\n📋 示例股票 {sample_symbol} 数据：")
    print(stock_data[sample_symbol].head())
    
    # 创建策略实例
    print("\n🎯 创建简单价值动量策略实例...")
    strategy = SimpleValueMomentumStrategy(
        top_n=10,          # 选股数量：10只
        lookback_period=60,  # 回测期数：60天
        rebalance_frequency='monthly'  # 调仓频率：每月
    )
    
    # 运行策略
    print("\n🔄 运行策略...")
    selected_stocks = strategy.run_strategy(stock_data)
    
    # 显示选股结果
    print(f"\n📈 选股结果：")
    print(f"✅ 选中了 {len(selected_stocks)} 只股票")
    print(f"📋 选中的股票：{', '.join(selected_stocks)}")
    
    # 计算因子贡献
    print("\n📊 因子贡献分析：")
    # 准备因子数据
    enhanced_data = strategy.calculate_factors(stock_data)
    sample_df = pd.concat(enhanced_data.values())
    
    # 模拟收益率
    sample_returns = sample_df['return'].dropna()
    factor_data = sample_df[strategy.factor_names].dropna()
    
    if len(factor_data) > 0 and len(sample_returns) > 0:
        contributions = strategy.calculate_factor_contributions(factor_data, sample_returns)
        print("因子贡献度：")
        for factor, contribution in contributions.items():
            print(f"  {factor}: {contribution:.4f}")
    
    print("\n🎉 简单价值动量多因子策略演示完成！")
    print("=" * 60)


if __name__ == "__main__":
    demo_simple_value_momentum_strategy()
