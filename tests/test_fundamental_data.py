"""
基本面数据获取测试
验证获取财务报表和财务指标的功能
"""

import sys
import os

# 将项目根目录添加到Python路径
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import asyncio
import pandas as pd
from data.data_manager import DataManager


async def test_fundamental_data():
    """测试基本面数据获取功能"""
    print("=" * 60)
    print("基本面数据获取测试")
    print("=" * 60)
    
    # 初始化数据管理器
    print("\n1. 初始化数据管理器...")
    data_manager = DataManager()
    
    # 连接数据源
    print("\n2. 连接数据源...")
    data_manager.connect_all()
    
    # 测试用股票代码（使用Futu格式）
    test_symbol = "US.AAPL"  # yfinance测试用
    test_symbol_hk = "HK.00700"  # Futu测试用（腾讯控股）
    
    # 测试获取财务报表数据
    print("\n3. 测试获取财务报表数据...")
    
    # 使用yfinance数据源测试
    print("\n   3.1 使用yfinance数据源：")
    try:
        # 测试获取资产负债表
        balance_sheet = await data_manager.get_financial_statements(
            test_symbol, "balance", "yfinance", "annual"
        )
        print(f"      - 资产负债表数据形状: {balance_sheet.shape}")
        
        # 测试获取利润表
        income_statement = await data_manager.get_financial_statements(
            test_symbol, "income", "yfinance", "annual"
        )
        print(f"      - 利润表数据形状: {income_statement.shape}")
        
        # 测试获取现金流量表
        cash_flow = await data_manager.get_financial_statements(
            test_symbol, "cash_flow", "yfinance", "annual"
        )
        print(f"      - 现金流量表数据形状: {cash_flow.shape}")
        
    except Exception as e:
        print(f"      - 获取财务报表失败: {e}")
    
    # 使用futu数据源测试（应该返回空DataFrame，因为Futu API不直接支持财务报表）
    print("\n   3.2 使用futu数据源：")
    try:
        balance_sheet = await data_manager.get_financial_statements(
            test_symbol_hk, "balance", "futu", "annual"
        )
        print(f"      - 资产负债表数据形状: {balance_sheet.shape}")
    except Exception as e:
        print(f"      - 获取财务报表失败: {e}")
    
    # 测试获取财务指标数据
    print("\n4. 测试获取财务指标数据...")
    
    # 使用yfinance数据源测试
    print("\n   4.1 使用yfinance数据源：")
    try:
        financial_indicators = await data_manager.get_financial_indicators(
            test_symbol, "yfinance", "annual"
        )
        print(f"      - 财务指标数据形状: {financial_indicators.shape}")
        print(f"      - 财务指标列表: {list(financial_indicators.index)}")
    except Exception as e:
        print(f"      - 获取财务指标失败: {e}")
    
    # 使用futu数据源测试（使用香港股票）
    print("\n   4.2 使用futu数据源：")
    try:
        financial_indicators = await data_manager.get_financial_indicators(
            test_symbol_hk, "futu", "annual"
        )
        print(f"      - 财务指标数据形状: {financial_indicators.shape}")
        if not financial_indicators.empty:
            print(f"      - 财务指标列表: {list(financial_indicators.index)}")
            print(f"      - 部分财务指标值:")
            print(financial_indicators.head())
    except Exception as e:
        print(f"      - 获取财务指标失败: {e}")
    
    # 断开数据源连接
    print("\n5. 断开数据源连接...")
    data_manager.disconnect_all()
    
    print("\n" + "=" * 60)
    print("基本面数据获取测试完成")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_fundamental_data())
