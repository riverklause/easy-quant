"""
模块化策略组合演示脚本
展示如何使用 strategy.portfolios 模块中的预定义组合
"""

import sys
import os
from typing import Dict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + '/..')

import pandas as pd
import numpy as np
from strategy.strategy_manager import StrategyManager
from strategy.portfolios import (
    AggressiveGrowthPortfolio,
    ConservativeValuePortfolio,
    BalancedPortfolio,
    get_aggressive_growth_portfolio,
    get_conservative_value_portfolio,
    get_balanced_portfolio
)


def generate_sample_stock_data(num_stocks: int = 30, num_days: int = 252) -> Dict[str, pd.DataFrame]:
    """生成示例股票数据"""
    stock_data = {}
    
    for i in range(num_stocks):
        dates = pd.date_range(start='2024-01-01', periods=num_days)
        np.random.seed(i)
        
        base_price = 100 + np.random.randn() * 50
        price = base_price + np.cumsum(np.random.randn(num_days) * 2)
        price = np.maximum(price, 1)
        
        eps = 5 + np.random.randn(num_days) * 2
        bvps = 50 + np.random.randn(num_days) * 10
        market_cap = price * (1000000 + np.random.randint(0, 9000000))
        
        price_series = pd.Series(price)
        return_series = price_series.pct_change()
        return_series[0] = 0
        return_series = return_series.values
        
        market_return = return_series + np.random.randn(num_days) * 0.005
        
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
        
        stock_symbol = f'STOCK_{i+1:03d}'
        stock_data[stock_symbol] = df
    
    return stock_data


def demo_modular_portfolios():
    """演示模块化策略组合"""
    print("=== 开始演示模块化策略组合 ===")
    print("=" * 60)
    
    # 1. 创建策略管理器
    print("\n[1] 创建策略管理器...")
    strategy_manager = StrategyManager()
    
    # 2. 演示不同类型的预定义组合
    print("\n[2] 演示预定义策略组合...")
    
    # 方式1: 直接实例化
    print("\n--- 方式1: 直接实例化 ---")
    aggressive = AggressiveGrowthPortfolio()
    print(f"组合名称: {aggressive.name}")
    print(f"描述: {aggressive.description}")
    print(f"策略数量: {len(aggressive.strategy_configs)}")
    print(f"组合参数: {aggressive.params}")
    
    # 方式2: 使用快捷函数
    print("\n--- 方式2: 使用快捷函数 ---")
    conservative = get_conservative_value_portfolio()
    balanced = get_balanced_portfolio()
    
    print(f"\n保守价值组合: {conservative.name}")
    print(f"  策略数量: {len(conservative.strategy_configs)}")
    print(f"  风险等级: {conservative.params.get('risk_level')}")
    print(f"  再平衡频率: {conservative.params.get('rebalance_frequency')}")
    
    print(f"\n平衡型组合: {balanced.name}")
    print(f"  策略数量: {len(balanced.strategy_configs)}")
    print(f"  风险等级: {balanced.params.get('risk_level')}")
    
    # 3. 将组合添加到管理器
    print("\n\n[3] 将组合添加到策略管理器...")
    strategy_manager.add_portfolio(aggressive)
    strategy_manager.add_portfolio(conservative)
    strategy_manager.add_portfolio(balanced)
    
    # 4. 查看组合信息
    print("\n[4] 查看组合信息...")
    for portfolio_name in ['AggressiveGrowth', 'ConservativeValue', 'Balanced']:
        info = strategy_manager.get_portfolio_info(portfolio_name)
        if info:
            print(f"\n{portfolio_name}:")
            print(f"  策略数量: {info['strategy_count']}")
            print(f"  全局策略: {info['global_strategies_count']}")
            print(f"  覆盖股票: {info['covered_stocks']}")
    
    # 5. 获取特定股票的策略
    print("\n\n[5] 获取特定股票的策略...")
    stock_symbol = "STOCK_001"
    
    strategies_aggressive = strategy_manager.get_strategies_for_stock(stock_symbol, 'AggressiveGrowth')
    strategies_conservative = strategy_manager.get_strategies_for_stock(stock_symbol, 'ConservativeValue')
    strategies_balanced = strategy_manager.get_strategies_for_stock(stock_symbol, 'Balanced')
    
    print(f"\n{stock_symbol} 适用的策略:")
    print(f"  激进成长组合: {strategies_aggressive}")
    print(f"  保守价值组合: {strategies_conservative}")
    print(f"  平衡型组合: {strategies_balanced}")
    
    # 6. 导出/导入组合配置
    print("\n\n[6] 导出组合配置...")
    config = aggressive.export_config()
    print(f"激进成长组合配置已导出:")
    print(f"  名称: {config['name']}")
    print(f"  策略数: {len(config['strategy_configs'])}")
    print(f"  参数: {config['params']}")
    
    # 7. 演示自定义组合
    print("\n\n[7] 演示自定义组合...")
    from strategy.portfolios import BasePortfolio
    
    custom = BasePortfolio("MyCustomPortfolio", "我的自定义组合")
    custom.add_strategy(
        strategy_id="my_strategy_1",
        strategy_type="technical",
        indicators=["rsi", "macd"],
        params={"rsi_period": 14, "position_size": 0.5},
        applicable_stocks=None
    )
    custom.add_strategy(
        strategy_id="my_strategy_2",
        strategy_type="multi_factor",
        indicators=["pe_ratio", "roe"],
        params={"max_pe": 20, "position_size": 0.5},
        applicable_stocks=["STOCK_001", "STOCK_002"]
    )
    custom.params = {
        "rebalance_frequency": "weekly",
        "risk_level": "medium"
    }
    
    print(f"自定义组合: {custom.name}")
    print(f"  策略数量: {len(custom.strategy_configs)}")
    print(f"  全局策略: {custom.global_strategies}")
    print(f"  特定策略映射: {custom.stock_strategy_map}")
    
    # 添加到管理器
    strategy_manager.add_portfolio(custom)
    
    # 8. 获取所有组合
    print("\n\n[8] 所有组合列表...")
    all_portfolios = strategy_manager.get_all_portfolios()
    print(f"当前组合: {all_portfolios}")
    
    # 9. 清理
    print("\n\n[9] 清理资源...")
    for portfolio_name in all_portfolios:
        strategy_manager.remove_portfolio(portfolio_name)
    
    print("\n演示完成!")
    print("=" * 60)
    
    print("\n模块化策略组合的优势:")
    print("   1. 每个组合独立文件，便于管理")
    print("   2. 预定义组合可直接使用")
    print("   3. 易于扩展新的组合类型")
    print("   4. 支持配置导出/导入")
    print("   5. 与 StrategyManager 无缝集成")


if __name__ == "__main__":
    demo_modular_portfolios()
