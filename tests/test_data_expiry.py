"""
数据过期判断测试脚本
测试不同过期检查方法和参数的效果
"""

import asyncio
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
from data.storage.local_storage import LocalStorageManager
from utils.settings import settings

# 创建测试数据
def create_test_data(symbol, days=365):
    """创建测试用的历史数据"""
    # 创建时间索引
    end_date = datetime(2024, 12, 31)
    start_date = end_date - timedelta(days=days)
    dates = pd.date_range(start=start_date, end=end_date, freq='D')
    
    # 创建多级索引
    codes = [symbol] * len(dates)
    multi_index = pd.MultiIndex.from_tuples(list(zip(dates, codes)), names=['time_key', 'code'])
    
    # 创建随机数据
    import numpy as np
    np.random.seed(42)
    data = {
        'open': np.random.uniform(100, 200, len(dates)),
        'high': np.random.uniform(100, 200, len(dates)),
        'low': np.random.uniform(100, 200, len(dates)),
        'close': np.random.uniform(100, 200, len(dates)),
        'volume': np.random.randint(1000000, 10000000, len(dates))
    }
    
    return pd.DataFrame(data, index=multi_index)

async def test_expiry_check_methods():
    """测试不同的过期检查方法"""
    print("=" * 60)
    print("数据过期判断测试")
    print("=" * 60)
    
    # 初始化存储管理器
    storage_manager = LocalStorageManager()
    
    # 创建测试数据
    symbol = 'TEST.AAPL'
    test_data = create_test_data(symbol, days=365)
    
    # 保存测试数据
    save_result = storage_manager.save_data(
        data=test_data,
        symbol=symbol,
        data_type='historical',
        start_date='2024-01-01',
        end_date='2024-12-31',
        source='test'
    )
    
    print(f"\n1. 保存测试数据: {'成功' if save_result else '失败'}")
    
    # 测试1: 基于文件时间的过期判断
    print("\n2. 测试基于文件时间的过期判断:")
    print("   - 过期阈值: 1 小时")
    
    # 加载数据，使用文件时间判断
    data1 = storage_manager.load_data(
        symbol=symbol,
        data_type='historical',
        start_date='2024-01-01',
        end_date='2024-12-31',
        source='test',
        load_if_expired=False,
        max_age_hours=1,
        expiry_check_method='file_time'
    )
    
    print(f"   - 结果: {'数据未过期，加载成功' if data1 is not None else '数据已过期，需要更新'}")
    
    # 测试2: 基于数据内容的过期判断
    print("\n3. 测试基于数据内容的过期判断:")
    print("   - 过期阈值: 24 小时")
    
    data2 = storage_manager.load_data(
        symbol=symbol,
        data_type='historical',
        start_date='2024-01-01',
        end_date='2024-12-31',
        source='test',
        load_if_expired=False,
        max_age_hours=24,
        expiry_check_method='data_content'
    )
    
    print(f"   - 结果: {'数据未过期，加载成功' if data2 is not None else '数据已过期，需要更新'}")
    
    # 测试3: 混合判断（文件时间+数据内容）
    print("\n4. 测试混合判断（文件时间+数据内容）:")
    print("   - 过期阈值: 24 小时")
    
    data3 = storage_manager.load_data(
        symbol=symbol,
        data_type='historical',
        start_date='2024-01-01',
        end_date='2024-12-31',
        source='test',
        load_if_expired=False,
        max_age_hours=24,
        expiry_check_method='hybrid'
    )
    
    print(f"   - 结果: {'数据未过期，加载成功' if data3 is not None else '数据已过期，需要更新'}")
    
    # 测试4: 不同过期阈值
    print("\n5. 测试不同过期阈值:")
    thresholds = [1, 24, 168]  # 1小时, 1天, 7天
    
    for threshold in thresholds:
        data = storage_manager.load_data(
            symbol=symbol,
            data_type='historical',
            start_date='2024-01-01',
            end_date='2024-12-31',
            source='test',
            load_if_expired=False,
            max_age_hours=threshold,
            expiry_check_method='hybrid'
        )
        status = "数据未过期" if data is not None else "数据已过期"
        print(f"   - 阈值 {threshold} 小时: {status}")
    
    # 测试5: 关闭过期检查（load_if_expired=True表示无论是否过期都加载）
    print("\n6. 测试关闭过期检查:")
    
    data5 = storage_manager.load_data(
        symbol=symbol,
        data_type='historical',
        start_date='2024-01-01',
        end_date='2024-12-31',
        source='test',
        load_if_expired=True,
        max_age_hours=1,
        expiry_check_method='hybrid'
    )
    
    print(f"   - 结果: {'数据加载成功（过期检查关闭）' if data5 is not None else '数据加载失败'}")
    
    # 测试6: 测试不同数据类型
    print("\n7. 测试不同数据类型:")
    
    # 创建快照数据（单级索引）
    snapshot_data = pd.DataFrame({
        'last_price': [150.0],
        'volume': [1000000],
        'timestamp': [datetime.now() - timedelta(hours=2)]
    }, index=pd.Index([symbol], name='code'))
    
    # 保存快照数据
    storage_manager.save_data(
        data=snapshot_data,
        symbol=symbol,
        data_type='snapshot',
        source='test'
    )
    
    # 加载快照数据，使用混合判断
    snapshot_result = storage_manager.load_data(
        symbol=symbol,
        data_type='snapshot',
        source='test',
        load_if_expired=False,
        max_age_hours=1,
        expiry_check_method='hybrid'
    )
    
    print(f"   - 快照数据结果: {'数据未过期' if snapshot_result is not None else '数据已过期'}")
    
    # 清理测试数据
    print("\n8. 清理测试数据...")
    storage_manager.delete_data(
        symbol=symbol,
        data_type='historical',
        source='test'
    )
    storage_manager.delete_data(
        symbol=symbol,
        data_type='snapshot',
        source='test'
    )
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(test_expiry_check_methods())
