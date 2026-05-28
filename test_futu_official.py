#!/usr/bin/env python3
"""
基于官方文档的Futu API正确测试脚本
"""
import sys
import os
import time
import pandas as pd

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_futu_official():
    """基于官方文档的正确测试"""
    print("=== 基于官方文档的Futu API测试 ===")
    
    try:
        import futu as ft
        print(f"✅ futu模块版本: {ft.__version__}")
        
        # 1. 创建Futu OpenQuoteContext
        print("\n1. 创建Futu OpenQuoteContext...")
        quote_ctx = ft.OpenQuoteContext(host='127.0.0.1', port=11111)
        print("✅ Futu OpenQuoteContext创建成功")
        
        # 2. 测试K线处理器 - 基于官方文档
        print("\n2. 测试K线处理器...")
        
        class CurKlineTest(ft.CurKlineHandlerBase):
            def on_recv_rsp(self, rsp_pb):
                ret_code, data = super().on_recv_rsp(rsp_pb)
                if ret_code != ft.RET_OK:
                    print(f"❌ K线数据接收错误: {data}")
                    return ret_code, data
                
                print(f"✅ K线处理器接收到数据: ret_code={ret_code}")
                if data is not None:
                    if isinstance(data, pd.DataFrame):
                        print(f"   数据条数: {len(data)}")
                        if len(data) > 0:
                            print(f"   第一条数据: {data.iloc[0].to_dict()}")
                    else:
                        print(f"   数据类型: {type(data)}")
                
                return ft.RET_OK, data
        
        # 3. 设置K线处理器
        print("\n3. 设置K线处理器...")
        kline_handler = CurKlineTest()
        quote_ctx.set_handler(kline_handler)
        print("✅ K线处理器设置成功")
        
        # 4. 订阅K线数据
        print("\n4. 订阅K线数据...")
        ret, data = quote_ctx.subscribe(['HK.00700'], [ft.SubType.K_1M], is_first_push=True)
        
        if ret == ft.RET_OK:
            print("✅ K线数据订阅成功")
            print(f"   订阅结果: {data}")
        else:
            print(f"❌ K线数据订阅失败: {data}")
            quote_ctx.close()
            return
        
        # 5. 等待实时数据推送
        print("\n5. 等待15秒接收实时数据推送...")
        for i in range(15):
            print(f"   等待中... {i+1}/15秒")
            time.sleep(1)
        
        # 6. 关闭连接
        print("\n6. 关闭连接...")
        quote_ctx.close()
        print("✅ 连接已关闭")
        
        print("\n✅ 基于官方文档的Futu API测试完成")
        
    except ImportError as e:
        print(f"❌ 无法导入futu模块: {e}")
    except Exception as e:
        print(f"❌ 测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_futu_official()