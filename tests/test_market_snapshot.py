"""
市场快照数据获取测试
验证get_market_snapshot方法的功能
"""

import sys
import os

# 将项目根目录添加到Python路径
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import asyncio
from data.data_manager import DataManager


async def test_market_snapshot():
    """测试市场快照数据获取功能"""
    print("=" * 60)
    print("市场快照数据获取测试")
    print("=" * 60)
    
    # 初始化数据管理器
    print("\n1. 初始化数据管理器...")
    data_manager = DataManager()
    
    # 连接数据源
    print("\n2. 连接数据源...")
    data_manager.connect_all()
    
    # 测试用股票代码
    test_symbols = ["US.AAPL", "HK.00700"]
    
    # 3. 测试获取市场快照数据
    print("\n3. 测试获取市场快照数据...")
    
    # 3.1 测试yfinance数据源
    print("\n   3.1 使用yfinance数据源：")
    for symbol in test_symbols:
        try:
            snapshot = await data_manager.get_market_snapshot([symbol], "yfinance")
            print(f"      - 股票代码 {symbol}: 数据形状 {snapshot.shape}")
            if not snapshot.empty:
                print(f"        主要字段: {list(snapshot.columns[:10])}...")
                print(f"        最后价格: {snapshot.loc[symbol]['last_price'] if symbol in snapshot.index else 'N/A'}")
        except Exception as e:
            print(f"      - 获取{symbol}市场快照失败: {e}")
    
    # 3.2 测试futu数据源
    print("\n   3.2 使用futu数据源：")
    for symbol in test_symbols:
        try:
            snapshot = await data_manager.get_market_snapshot([symbol], "futu")
            print(f"      - 股票代码 {symbol}: 数据形状 {snapshot.shape}")
            if not snapshot.empty:
                print(f"        主要字段: {list(snapshot.columns[:10])}...")
                print(f"        最后价格: {snapshot.loc[symbol]['last_price'] if symbol in snapshot.index else 'N/A'}")
        except Exception as e:
            print(f"      - 获取{symbol}市场快照失败: {e}")
    
    # 4. 断开数据源连接
    print("\n4. 断开数据源连接...")
    data_manager.disconnect_all()
    
    print("\n" + "=" * 60)
    print("市场快照数据获取测试完成")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_market_snapshot())
