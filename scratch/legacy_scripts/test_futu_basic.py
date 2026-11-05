#!/usr/bin/env python3
"""
基本Futu API连接测试脚本
"""
import asyncio
import futu as ft
from data.sources.futu_realtime import FutuRawDataProcessor

async def test_futu_connection():
    """测试Futu API基本连接功能"""
    print("=== 开始Futu API连接测试 ===")
    
    try:
        # 首先创建Futu OpenQuoteContext
        print("1. 创建Futu OpenQuoteContext...")
        quote_ctx = ft.OpenQuoteContext(host='127.0.0.1', port=11111)
        print("✅ Futu OpenQuoteContext创建成功")
        
        # 创建Futu原始数据处理器
        print("2. 创建FutuRawDataProcessor实例...")
        futu_processor = FutuRawDataProcessor(quote_ctx)
        
        # 连接Futu API
        print("3. 连接Futu API...")
        if futu_processor.connect():
            print("✅ Futu API连接成功")
        else:
            print("❌ Futu API连接失败")
            quote_ctx.close()
            return
        
        # 订阅K线数据
        print("4. 订阅K线数据...")
        await futu_processor.subscribe_realtime_data(['HK.00700'], ['kline'])
        print("✅ K线数据订阅成功")
        
        # 等待数据回调
        print("5. 等待5秒数据回调...")
        await asyncio.sleep(5)
        
        # 检查连接状态
        print("6. 检查连接状态...")
        if futu_processor.is_connected:
            print("✅ 连接状态正常")
        else:
            print("❌ 连接状态异常")
        
        # 关闭连接
        print("7. 关闭连接...")
        quote_ctx.close()
        print("✅ 连接已关闭")
        
        print("✅ Futu API连接测试完成")
        
    except Exception as e:
        print(f"❌ 测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_futu_connection())