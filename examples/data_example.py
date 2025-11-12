"""
数据获取模块使用示例
"""
import asyncio
import pandas as pd
from datetime import datetime, timedelta

from data.data_manager import DataManager


async def example_basic_usage():
    """基本使用示例"""
    print("=== 数据获取模块基本使用示例 ===")
    
    # 1. 创建数据管理器（自动从settings.py获取配置）
    data_manager = DataManager()
    
    print(f"可用数据源: {data_manager.get_available_sources()}")
    
    # 2. 连接数据源
    print("连接数据源...")
    connected = await data_manager.connect_all()
    print(f"连接状态: {connected}")
    
    # 3. 检查数据源健康状态
    print("检查数据源健康状态...")
    health_status = await data_manager.health_check()
    print(f"健康状态: {health_status}")
    
    # 4. 获取单个股票历史数据
    print("获取腾讯历史数据...")
    try:
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        
        df = await data_manager.get_historical_data(
            symbol='00700.HK',
            start_date=start_date,
            end_date=end_date,
            data_source='futu',
            period='daily'
        )
        print(f"获取到{len(df)}条数据")
        print(df.head())
    except Exception as e:
        print(f"获取历史数据失败: {e}")
    
    # 5. 获取实时数据
    print("获取苹果实时数据...")
    try:
        real_time_data = await data_manager.get_real_time_data('AAPL')
        print(f"实时数据: {real_time_data}")
    except Exception as e:
        print(f"获取实时数据失败: {e}")
    
    # 6. 批量获取数据
    print("批量获取数据...")
    try:
        symbols = ['00700.HK', 'AAPL', '000001.SZ']
        batch_data = await data_manager.get_batch_data(
            symbols=symbols,
            start_date=start_date,
            end_date=end_date
        )
        print(f"批量获取结果: {len(batch_data)}个股票")
        for symbol, data in batch_data.items():
            print(f"{symbol}: {len(data)}条数据")
    except Exception as e:
        print(f"批量获取数据失败: {e}")
    
    # 7. 断开连接
    print("断开数据源连接...")
    await data_manager.disconnect_all()
    print("示例完成")


async def example_advanced_usage():
    """高级使用示例"""
    print("\n=== 数据获取模块高级使用示例 ===")
    
    # 使用默认配置（从settings.py获取）
    data_manager = DataManager()
    
    # 1. 获取数据源信息
    print("数据源信息:")
    for source in data_manager.get_available_sources():
        info = data_manager.get_source_info(source)
        print(f"{source}: {info}")
    
    # 2. 测试连接
    print("测试连接...")
    test_results = await data_manager.test_connection('all')
    print(f"连接测试结果: {test_results}")
    
    # 3. 指定数据源获取数据
    print("指定futu数据源获取港股数据...")
    try:
        df = await data_manager.get_historical_data(
            symbol='00700.HK',
            start_date='2023-01-01',
            end_date='2023-01-31',
            data_source='futu',  # 指定使用futu
            period='daily'
        )
        print(f"获取到{len(df)}条数据")
    except Exception as e:
        print(f"指定数据源获取失败: {e}")
    
    print("高级示例完成")


if __name__ == "__main__":
    # 运行示例
    asyncio.run(example_basic_usage())
    asyncio.run(example_advanced_usage())