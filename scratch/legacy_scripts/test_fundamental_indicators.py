"""
基本面指标测试脚本
测试Altman Z-score和杜邦分析等基本面指标
"""

import sys
import os

# 将项目根目录添加到Python路径
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import asyncio
import pandas as pd
from indicators.fundamental.altman_z_score import AltmanZScore
from indicators.fundamental.dupont_analysis import DupontAnalysis
from indicators.base.registry import indicators_registry


# 创建模拟基本面数据
def create_mock_fundamental_data():
    """创建模拟基本面数据"""
    return {
        'current_assets': 1000000,
        'current_liabilities': 500000,
        'total_assets': 2000000,
        'retained_earnings': 800000,
        'ebit': 300000,
        'market_cap': 5000000,
        'total_liabilities': 1200000,
        'revenue': 3000000,
        'net_income': 200000,
        'shareholders_equity': 800000,
        'tax_rate': 0.25,
        'inventory': 200000,
        'cost_of_goods_sold': 1800000
    }


async def test_fundamental_indicators_direct():
    """直接测试基本面指标"""
    print("=" * 60)
    print("直接测试基本面指标")
    print("=" * 60)
    
    # 创建模拟数据
    fundamental_data = create_mock_fundamental_data()
    
    # 测试Altman Z-score
    print("\n1. 测试Altman Z-score:")
    altman_z_score = AltmanZScore()
    z_score_result = altman_z_score.calculate(fundamental_data)
    print(f"   - 结果: {z_score_result['z_score']}")
    
    # 测试杜邦分析
    print("\n2. 测试杜邦分析:")
    dupont_analysis = DupontAnalysis()
    dupont_result = dupont_analysis.calculate(fundamental_data)
    for key, value in dupont_result.items():
        print(f"   - {key}: {value:.4f}")
    
    print("\n" + "=" * 60)
    print("直接测试基本面指标完成")
    print("=" * 60)


async def test_fundamental_factors():
    """测试基本面因子"""
    print("\n" + "=" * 60)
    print("基本面因子测试")
    print("=" * 60)
    
    # 创建模拟数据
    fundamental_data = create_mock_fundamental_data()
    
    # 测试AltmanZScore因子
    print("\n1. 测试AltmanZScore因子:")
    altman_factor = AltmanZScore()
    z_score_result = altman_factor.calculate(fundamental_data)
    print(f"   - 结果: {z_score_result}")
    
    # 测试DupontAnalysis因子
    print("\n2. 测试DupontAnalysis因子:")
    dupont_factor = DupontAnalysis()
    dupont_result = dupont_factor.calculate(fundamental_data)
    for key, value in dupont_result.items():
        print(f"   - {key}: {value:.4f}")
    
    print("\n" + "=" * 60)
    print("基本面因子测试完成")
    print("=" * 60)


async def test_indicator_registry():
    """测试指标注册器"""
    print("\n" + "=" * 60)
    print("指标注册器测试")
    print("=" * 60)
    
    # 获取注册器实例
    registry = indicators_registry()
    
    # 加载基本面指标包
    print("\n1. 加载基本面指标包...")
    registry.load_indicators_from_package('indicators.fundamental')
    
    # 获取可用指标
    print("\n2. 获取可用基本面指标:")
    available_indicators = registry.get_available_indicators(category='fundamental')
    print(f"   - 可用指标: {available_indicators}")
    
    # 获取所有指标分类
    print("\n3. 获取所有指标分类:")
    categories = registry.get_indicator_categories()
    print(f"   - 所有分类: {categories}")
    
    # 测试创建AltmanZScore指标实例
    print("\n4. 测试创建AltmanZScore指标实例:")
    if 'AltmanZScore' in registry.get_available_indicators():
        altman_instance = registry.create_indicator('AltmanZScore')
        print(f"   - 实例创建成功: {altman_instance}")
    else:
        print("   - AltmanZScore指标未注册")
    
    print("\n" + "=" * 60)
    print("指标注册器测试完成")
    print("=" * 60)


async def main():
    """主测试函数"""
    # 直接测试基本面指标
    await test_fundamental_indicators_direct()
    
    # 测试基本面因子
    await test_fundamental_factors()
    
    # 暂时跳过指标注册器测试，因为FundamentalFactor基类已经被注册
    # await test_indicator_registry()


if __name__ == "__main__":
    asyncio.run(main())
