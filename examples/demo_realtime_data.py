"""
实时数据管理功能演示脚本
演示如何使用DataManager管理实时数据，包括更新、获取和保存到本地
"""

import asyncio
from datetime import datetime
from data.data_manager import DataManager
from utils.settings import settings

async def main():
    """主函数"""
    print("=" * 60)
    print("实时数据管理功能演示")
    print("=" * 60)
    
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
    
    # 测试实时数据管理功能
    print("\n2. 测试实时数据管理功能")
    
    # 模拟实时数据
    test_data = {
        'quote': [
            {'time_key': datetime.now().isoformat(), 'code': 'US.AAPL', 'last_price': 150.0, 'volume': 1000000},
            {'time_key': datetime.now().isoformat(), 'code': 'US.AAPL', 'last_price': 150.1, 'volume': 1500000},
            {'time_key': datetime.now().isoformat(), 'code': 'US.AAPL', 'last_price': 150.2, 'volume': 2000000}
        ],
        'order_book': [
            {'time_key': datetime.now().isoformat(), 'code': 'US.AAPL', 'bid': 149.9, 'ask': 150.1},
            {'time_key': datetime.now().isoformat(), 'code': 'US.AAPL', 'bid': 150.0, 'ask': 150.2}
        ],
        'kline': [
            {'time_key': datetime.now().isoformat(), 'code': 'US.AAPL', 'open': 149.5, 'high': 150.5, 'low': 149.0, 'close': 150.0, 'volume': 10000000},
            {'time_key': datetime.now().isoformat(), 'code': 'US.AAPL', 'open': 150.0, 'high': 151.0, 'low': 149.5, 'close': 150.5, 'volume': 12000000}
        ],
        'tick': [
            {'time_key': datetime.now().isoformat(), 'code': 'US.AAPL', 'price': 150.0, 'volume': 10000},
            {'time_key': datetime.now().isoformat(), 'code': 'US.AAPL', 'price': 150.1, 'volume': 15000},
            {'time_key': datetime.now().isoformat(), 'code': 'US.AAPL', 'price': 150.2, 'volume': 20000}
        ]
    }
    
    # 测试1: 更新实时数据到内存缓存
    print("\n3. 测试更新实时数据到内存缓存")
    
    for data_type, data_list in test_data.items():
        for data in data_list:
            if data_type in ['kline', 'tick']:
                data_manager.update_realtime_data(data_type, data, symbol='US.AAPL')
            else:
                data_manager.update_realtime_data(data_type, data)
        print(f"   ✅ 更新 {len(data_list)} 条{data_type}数据到内存缓存")
    
    # 测试2: 从内存缓存获取实时数据
    print("\n4. 测试从内存缓存获取实时数据")
    
    for data_type in test_data.keys():
        if data_type in ['kline', 'tick']:
            data = data_manager.get_realtime_data(data_type, symbol='US.AAPL')
        else:
            data = data_manager.get_realtime_data(data_type)
        print(f"   ✅ 获取 {len(data)} 条{data_type}数据")
    
    # 测试3: 保存实时数据到本地
    print("\n5. 测试保存实时数据到本地")
    
    for data_type in test_data.keys():
        if data_type in ['kline', 'tick']:
            saved = data_manager.save_realtime_data_to_local(data_type, symbol='US.AAPL')
        else:
            saved = data_manager.save_realtime_data_to_local(data_type)
        status = "成功" if saved else "失败"
        print(f"   ✅ 保存{data_type}数据到本地: {status}")
    
    # 测试4: 查看保存的实时数据文件
    print("\n6. 查看保存的实时数据文件")
    
    for data_type in test_data.keys():
        files = data_manager.storage_manager.get_data_files(
            data_type=f'realtime_{data_type}',
            source='futu'
        )
        if files:
            print(f"   ✅ {data_type}数据文件: {[str(f.name) for f in files]}")
        else:
            print(f"   ⚠️  未找到{data_type}数据文件")
    
    # 测试5: 清理过期数据
    print("\n7. 测试清理过期实时数据")
    
    # 模拟创建一个过期文件（使用100天前的日期）
    import os
    from datetime import timedelta
    import pandas as pd
    
    # 创建一个测试用的过期数据
    expired_date = (datetime.now() - timedelta(days=100)).strftime('%Y-%m-%d')
    expired_data = pd.DataFrame([{'time_key': expired_date, 'code': 'US.AAPL', 'last_price': 100.0}])
    
    # 保存过期数据
    expired_saved = data_manager.storage_manager.save_data(
        data=expired_data,
        symbol='US.AAPL',
        data_type='realtime_quote',
        start_date=expired_date,
        end_date=expired_date,
        source='futu'
    )
    
    if expired_saved:
        print(f"   ✅ 创建了一个过期测试文件（{expired_date}）")
    
    # 清理过期数据
    deleted_count = data_manager.cleanup_old_realtime_data(days=15)
    print(f"   ✅ 清理过期实时数据: 删除了 {deleted_count} 个文件")
    
    # 测试6: 再次查看保存的实时数据文件
    print("\n8. 再次查看保存的实时数据文件")
    
    for data_type in test_data.keys():
        files = data_manager.storage_manager.get_data_files(
            data_type=f'realtime_{data_type}',
            source='futu'
        )
        if files:
            print(f"   ✅ {data_type}数据文件: {[str(f.name) for f in files]}")
        else:
            print(f"   ⚠️  未找到{data_type}数据文件")
    
    # 断开数据源连接
    print("\n9. 断开数据源连接...")
    data_manager.disconnect_all()
    
    print("\n" + "=" * 60)
    print("实时数据管理功能演示完成")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())
