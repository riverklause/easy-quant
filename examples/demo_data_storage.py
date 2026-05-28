"""
数据获取功能演示脚本
演示如何使用DataManager从数据源获取历史数据和批量数据
"""

import asyncio
import pandas as pd
from data.data_manager import DataManager
from utils.settings import settings

async def main():
    """主函数"""
    print("=" * 50)
    print("数据获取功能演示")
    print("=" * 50)
    
    # 初始化数据管理器
    data_manager = DataManager()
    
    # 连接数据源
    print("\n1. 连接数据源...")
    connected = data_manager.connect_all()
    if not connected:
        print("⚠️  警告: 部分数据源连接失败")
    
    # 检查可用数据源
    available_sources = data_manager.get_available_sources()
    print(f"可用数据源: {available_sources}")
    
    # 使用yfinance数据源（无需API密钥）
    data_source = 'yfinance'
    if data_source not in available_sources:
        print(f"❌ 数据源{data_source}不可用，切换到其他数据源")
        data_source = available_sources[0] if available_sources else None
        if not data_source:
            print("❌ 没有可用数据源，退出演示")
            return
    
    print(f"使用数据源: {data_source}")
    
    # 测试股票列表
    symbols = ['US.AAPL', 'US.GOOG', 'US.MSFT']
    start_date = '2024-01-01'
    end_date = '2024-12-31'
    period = 'daily'
    
    print("\n2. 获取历史数据（第一次请求，将从数据源获取）")
    print(f"股票列表: {symbols}")
    print(f"时间范围: {start_date} 到 {end_date}")
    print(f"周期: {period}")
    
    # 第一次请求：从数据源获取数据
    first_data = await data_manager.get_historical_data(
        symbol=symbols[0],
        start_date=start_date,
        end_date=end_date,
        data_source=data_source,
        period=period
    )
    
    print(f"\n✅ 第一次获取数据成功，数据形状: {first_data.shape}")
    print(f"数据前5行:")
    print(first_data.head())
    
    print("\n3. 再次获取相同数据（第二次请求，将从数据源获取）")
    
    # 第二次请求：从数据源获取数据
    second_data = await data_manager.get_historical_data(
        symbol=symbols[0],
        start_date=start_date,
        end_date=end_date,
        data_source=data_source,
        period=period
    )
    
    print(f"✅ 第二次获取数据成功，数据形状: {second_data.shape}")
    print(f"数据前5行:")
    print(second_data.head())
    
    # 验证两次获取的数据是否相同
    if first_data.shape == second_data.shape and first_data.equals(second_data):
        print("\n✅ 验证通过: 两次获取的数据完全相同")
    else:
        print("\n❌ 验证失败: 两次获取的数据不同")
    
    print("\n4. 批量获取数据")
    
    # 批量获取数据
    batch_data = await data_manager.get_batch_data(
        symbols=symbols,
        data_source=data_source,
        start_date=start_date,
        end_date=end_date,
        period=period
    )
    
    print(f"✅ 批量获取数据成功，获取了 {len(batch_data)} 只股票的数据")
    for symbol, data in batch_data.items():
        print(f"  - {symbol}: 数据形状 {data.shape}")
    
    print("\n5. 获取市场快照数据")
    
    # 获取市场快照数据
    snapshot_data = await data_manager.get_market_snapshot(
        symbols=symbols,
        data_source=data_source
    )
    
    if snapshot_data is not None:
        if isinstance(snapshot_data, pd.DataFrame) and not snapshot_data.empty:
            print(f"✅ 获取市场快照数据成功，数据形状: {snapshot_data.shape}")
            print(f"快照数据:")
            print(snapshot_data)
        elif isinstance(snapshot_data, dict) and snapshot_data:
            print(f"✅ 获取市场快照数据成功，返回字典格式")
            print(f"快照数据:")
            print(snapshot_data)
        else:
            print("⚠️  市场快照数据获取失败或为空（可能是数据源限制）")
    else:
        print("⚠️  市场快照数据获取失败或为空（可能是数据源限制）")
    
    print("\n" + "=" * 50)
    print("数据获取功能演示完成")
    print("=" * 50)
    
    # 断开数据源连接
    data_manager.disconnect_all()

if __name__ == "__main__":
    asyncio.run(main())
