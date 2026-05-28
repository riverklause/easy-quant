"""
策略组合管理演示脚本
展示如何使用策略组合管理系统，包括技术指标策略和多因子策略的组合使用
"""

import sys
import os
from typing import Dict

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + '/..')

import pandas as pd
import numpy as np
from strategy.strategy_manager import StrategyManager
from strategy.strategy_portfolio import StrategyPortfolio
from strategy.multi_factor.example_strategy import SimpleValueMomentumStrategy


def generate_sample_stock_data(num_stocks: int = 30, num_days: int = 252) -> Dict[str, pd.DataFrame]:
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


def demo_strategy_portfolio():
    """
    演示策略组合管理
    """
    print("🚀 开始演示策略组合管理")
    print("=" * 60)
    
    # 1. 创建策略管理器
    print("📦 创建策略管理器...")
    strategy_manager = StrategyManager()
    print("✅ 策略管理器创建成功")
    
    # 2. 生成示例数据
    print("\n📊 生成示例股票数据...")
    stock_data = generate_sample_stock_data(num_stocks=30, num_days=252)
    print(f"✅ 生成了 {len(stock_data)} 只股票，每只股票 {len(next(iter(stock_data.values())))} 天的数据")
    
    # 3. 创建策略实例
    print("\n🎯 创建多因子策略实例...")
    
    # 创建简单价值动量策略
    value_momentum_strategy = SimpleValueMomentumStrategy(
        name="SimpleValueMomentum",
        top_n=10,
        lookback_period=60,
        rebalance_frequency='monthly'
    )
    
    # 创建Fama-French三因子策略
    from strategy.multi_factor.example_strategy import FamaFrenchThreeFactorStrategy
    fama_french_strategy = FamaFrenchThreeFactorStrategy(
        name="FamaFrenchThreeFactor",
        top_n=10,
        lookback_period=60,
        rebalance_frequency='monthly'
    )
    
    print("✅ 多因子策略实例创建成功")
    
    # 4. 注册策略
    print("\n📝 注册策略...")
    strategy_manager.register_strategy(value_momentum_strategy)
    strategy_manager.register_strategy(fama_french_strategy)
    print(f"✅ 已注册 {len(strategy_manager.strategies)} 个策略")
    
    # 5. 创建策略组合
    print("\n🔧 创建策略组合...")
    portfolio = StrategyPortfolio("MyInvestmentPortfolio")
    
    # 6. 向组合添加策略
    print("\n📋 向组合添加策略...")
    
    # 添加全局策略（适用于所有股票）
    portfolio.add_strategy(
        strategy_id="SimpleValueMomentum",
        strategy_type="multi_factor",
        indicators=["pe_ratio", "pb_ratio", "return_20d"],
        params={"top_n": 10, "lookback_period": 60},
        applicable_stocks=None  # 适用于所有股票
    )
    
    # 添加特定股票策略（仅适用于部分股票）
    portfolio.add_strategy(
        strategy_id="FamaFrenchThreeFactor",
        strategy_type="multi_factor",
        indicators=["market_beta", "size_factor", "value_factor"],
        params={"top_n": 5, "lookback_period": 60},
        applicable_stocks=["STOCK_001", "STOCK_002", "STOCK_003", "STOCK_004", "STOCK_005"]  # 仅适用于这些股票
    )
    
    # 7. 将组合添加到策略管理器
    strategy_manager.add_portfolio(portfolio)
    
    # 8. 查看组合信息
    print("\nℹ️  查看组合信息...")
    portfolio_info = strategy_manager.get_portfolio_info("MyInvestmentPortfolio")
    print(f"   组合名称: {portfolio_info['name']}")
    print(f"   策略数量: {portfolio_info['strategy_count']}")
    print(f"   全局策略: {portfolio_info['global_strategies_count']} 个")
    print(f"   特定策略: {portfolio_info['stock_specific_strategies_count']} 个")
    print(f"   覆盖股票: {portfolio_info['covered_stocks']} 只")
    
    # 9. 获取适用于特定股票的策略
    print("\n🎯 获取适用于特定股票的策略...")
    
    # 获取适用于所有股票的策略
    strategies_all = strategy_manager.get_strategies_for_stock("STOCK_010")
    print(f"   适用于 STOCK_010 的策略: {strategies_all}")
    
    # 获取适用于特定股票的策略（应该包含全局策略+特定策略）
    strategies_specific = strategy_manager.get_strategies_for_stock("STOCK_001")
    print(f"   适用于 STOCK_001 的策略: {strategies_specific}")
    
    # 10. 启动策略
    print("\n🔄 启动策略...")
    strategy_manager.start_strategy("SimpleValueMomentum")
    strategy_manager.start_strategy("FamaFrenchThreeFactor")
    print("✅ 策略启动成功")
    
    # 11. 为特定股票生成信号
    print("\n📈 为特定股票生成交易信号...")
    
    # 为STOCK_001生成信号（应该同时使用两个策略）
    signals_stock001 = strategy_manager.generate_signals_for_stock("STOCK_001", stock_data)
    print(f"   为 STOCK_001 生成了 {len(signals_stock001)} 个信号")
    
    # 为STOCK_010生成信号（应该只使用全局策略）
    signals_stock010 = strategy_manager.generate_signals_for_stock("STOCK_010", stock_data)
    print(f"   为 STOCK_010 生成了 {len(signals_stock010)} 个信号")
    
    # 12. 查看信号详情
    if signals_stock001:
        print("\n📋 信号详情：")
        for i, signal in enumerate(signals_stock001[:2]):
            print(f"\n   信号 {i+1}:")
            print(f"      类型: {signal['type']}")
            print(f"      策略: {signal['strategy_name']}")
            print(f"      时间: {signal['timestamp']}")
            print(f"      选股数量: {len(signal['selected_stocks'])}")
            print(f"      选中股票: {', '.join(signal['selected_stocks'][:3])}...")
    
    # 13. 演示策略组合管理功能
    print("\n⚙️  演示策略组合管理功能...")
    
    # 更新策略参数
    portfolio.update_strategy_params("SimpleValueMomentum", top_n=15)
    print("✅ 策略参数已更新")
    
    # 复制组合
    copied_portfolio = portfolio.copy_portfolio("MyCopiedPortfolio")
    strategy_manager.add_portfolio(copied_portfolio)
    print(f"✅ 已复制组合，当前共有 {len(strategy_manager.portfolios)} 个组合")
    
    # 获取所有组合
    all_portfolios = strategy_manager.get_all_portfolios()
    print(f"   当前组合列表: {all_portfolios}")
    
    # 14. 停止策略
    print("\n🛑 停止策略...")
    strategy_manager.stop_strategy("SimpleValueMomentum")
    strategy_manager.stop_strategy("FamaFrenchThreeFactor")
    print("✅ 策略已停止")
    
    # 15. 清理
    print("\n🗑️  清理资源...")
    strategy_manager.remove_portfolio("MyInvestmentPortfolio")
    strategy_manager.remove_portfolio("MyCopiedPortfolio")
    print("✅ 资源清理完成")
    
    print("\n🎉 策略组合管理演示完成！")
    print("=" * 60)
    
    print("\n📌 演示要点总结：")
    print("   1. ✅ 策略组合管理系统已成功实现")
    print("   2. ✅ 支持全局策略和特定股票策略")
    print("   3. ✅ 策略注册和组合管理功能正常")
    print("   4. ✅ 能够为特定股票生成交易信号")
    print("   5. ✅ 支持策略参数动态更新")
    print("   6. ✅ 支持组合复制和管理")
    print("\n📚 架构优势：")
    print("   - 统一的策略管理接口")
    print("   - 灵活的策略组合配置")
    print("   - 支持多种策略类型")
    print("   - 事件驱动的架构设计")
    print("   - 完整的生命周期管理")


if __name__ == "__main__":
    demo_strategy_portfolio()
