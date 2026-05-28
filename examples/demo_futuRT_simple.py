#!/usr/bin/env python3
"""
futu数据获取测试程序 - 简化版本

直接使用DataManager类，按照实际使用方式调用
使用DataManager内置的默认配置（从utils/settings.py自动读取）
"""
import asyncio
import time
import pandas as pd
from datetime import datetime, timedelta
from data.data_manager import DataManager


async def test_futuRT_simple():
    """简化版futu测试"""
    print("🚀 开始futu数据获取测试（简化版）")
    print("=" * 50)
    
    # 直接使用DataManager的默认构造函数
    # DataManager会自动从utils/settings.py读取配置
    data_manager = DataManager()
    
    # 连接数据源
    print("🔄 连接数据源...")
    connected = data_manager.connect_all()
    if not connected:
        print("❌ 连接失败，无法继续测试")
        return
    print("✅ 连接成功")
    # 注册回调函数
    data_manager.register_callback('futu_RT', printdata)
    
    try:
        # 1. 测试单个股票历史数据
        print("\n📊 测试单个股票历史数据")
        end_date = datetime.now().strftime('%Y-%m-%d')
        print(f"当前日期: {end_date}")

        # 1. 测试实时数据订阅
        print("\n📊 测试实时数据订阅")
        subscribe_result = data_manager.subscribe_realtime_data(
            data_source='futu_RT',
            symbols=['HK.00700'],
            data_types=['kline']
        )
        print(f"✅ 实时数据订阅结果: {subscribe_result}")
        time.sleep(5)
        
        # 2. 测试批量数据获取
        print("\n📦 测试批量数据获取")
        symbols = ['HK.01951', 'HK.02400', 'HK.00700']

        subscribe_result = data_manager.subscribe_realtime_data(
            data_source='futu_RT',
            symbols=symbols,
            data_types=['kline', 'quote','order_book']
        )
        
        print(f"✅ 实时数据订阅结果: {subscribe_result}")
        time.sleep(5)
        
        # 3. 测试数据源信息
        print("\nℹ️  测试数据源信息")
        info = data_manager.get_source_info('futu_RT')
        print(f"✅ 支持的市场: {info['supported_markets']}")
        print(f"✅ 支持的周期: {info['supported_periods']}")

        # 4. 测试获取快照
        print("\n🔍 测试获取快照数据")
        snapshot = await data_manager.get_market_snapshot(
            symbols=['HK.00700'],
            data_source='futu_RT'
        )
        print(f"✅ 成功获取快照数据: {snapshot}")
        
    except Exception as e:
        print(f"❌ 测试过程中出错: {e}")
    
    finally:
        # 断开连接
        print("\n🔄 断开数据源连接...")
        data_manager.disconnect_all()
        print("✅ 断开成功")
    
    print("\n" + "=" * 50)
    print("🎉 测试完成！")

def printdata(data):
    print(f"收到实时数据: {data}")

async def main():
    """主函数"""
    # 运行基础测试
    await test_futuRT_simple()
    
    # 运行多市场测试
    # await test_multiple_markets()


if __name__ == '__main__':
    asyncio.run(main())