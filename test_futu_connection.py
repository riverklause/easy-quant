"""
测试Futu连接和数据订阅的简单脚本
"""
import futu as ft
import asyncio

async def test_futu_connection():
    """测试Futu连接和基本数据订阅"""
    print("=== 测试Futu连接 ===")
    
    try:
        # 创建Futu连接
        quote_ctx = ft.OpenQuoteContext(host='127.0.0.1', port=11111)
        print("✅ Futu连接创建成功")
        
        # 测试连接状态
        ret, data = quote_ctx.get_global_state()
        if ret == ft.RET_OK:
            print(f"✅ Futu OpenD状态: {data}")
        else:
            print(f"❌ 获取Futu OpenD状态失败")
            return
        
        # 测试订阅K线数据
        symbols = ['HK.00700']
        print(f"尝试订阅K线数据: {symbols}")
        
        ret, err = quote_ctx.subscribe(symbols, ft.SubType.K_1M, is_first_push=True)
        if ret == ft.RET_OK:
            print("✅ K线数据订阅成功")
        else:
            print(f"❌ K线数据订阅失败: {err}")
            return
        
        # 设置K线回调
        def kline_callback(data):
            print(f"[回调] 接收到K线数据: {data['code']}, 时间: {data['time_key']}, 收盘价: {data['close']}")
        
        quote_ctx.set_handler(kline_callback)
        print("✅ K线回调设置成功")
        
        # 等待一段时间看是否有数据
        print("等待10秒接收数据...")
        await asyncio.sleep(10)
        
        # 尝试获取历史K线数据
        print("尝试获取历史K线数据...")
        ret, data, page_req_key = quote_ctx.request_history_kline(
            'HK.00700', start='2024-01-01', end='2024-01-10', 
            ktype=ft.KLType.K_1M, max_count=10
        )
        
        if ret == ft.RET_OK:
            print(f"✅ 历史K线数据获取成功，共{len(data)}条数据")
            for i, row in data.iterrows():
                print(f"  时间: {row['time_key']}, 收盘价: {row['close']}")
        else:
            print(f"❌ 历史K线数据获取失败")
        
        quote_ctx.close()
        print("✅ 测试完成")
        
    except Exception as e:
        print(f"❌ 测试过程中出错: {e}")

if __name__ == "__main__":
    asyncio.run(test_futu_connection())