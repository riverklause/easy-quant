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
    
    # 使用专门的on_realtime_data方法作为回调函数，该方法只接受一个参数
    data_manager.register_callback('futu_RT', data_manager.on_realtime_data)
    data_manager.subscribe_realtime_data('futu_RT', ['HK.01951', 'HK.00700'],['kline','quote'])
    
    await asyncio.sleep(10)
    data = data_manager.get_realtime_data('quote', 'HK.00700')
    print(data)

    data_manager.disconnect_all()

if __name__ == "__main__":
    asyncio.run(main())
