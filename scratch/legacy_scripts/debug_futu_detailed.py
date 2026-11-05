#!/usr/bin/env python3
"""
Futu API详细调试脚本 - 检查所有可能的问题
"""
import sys
import os
import time

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def debug_futu_detailed():
    """详细调试Futu API"""
    print("=== Futu API详细调试 ===")
    
    try:
        # 检查futu模块
        print("\n1. 检查futu模块...")
        import futu as ft
        print(f"   ✅ futu模块版本: {ft.__version__}")
        
        # 检查Futu API的可用类
        print("\n2. 检查Futu API可用类...")
        futu_classes = [cls for cls in dir(ft) if 'Handler' in cls or 'Base' in cls]
        print(f"   可用处理器类: {futu_classes}")
        
        # 检查CurKlineHandlerBase是否存在
        if hasattr(ft, 'CurKlineHandlerBase'):
            print("   ✅ CurKlineHandlerBase类存在")
        else:
            print("   ❌ CurKlineHandlerBase类不存在")
            print("   请检查futu-api版本，可能需要更新")
            return
        
        # 检查OpenD服务连接
        print("\n3. 检查OpenD服务连接...")
        try:
            quote_ctx = ft.OpenQuoteContext(host='127.0.0.1', port=11111)
            print("   ✅ OpenD服务连接成功")
            
            # 测试获取市场状态
            print("\n4. 测试获取市场状态...")
            ret, data = quote_ctx.get_market_state()
            
            if ret == ft.RET_OK:
                print("   ✅ 市场状态获取成功")
                if data is not None:
                    print(f"   市场状态数据条数: {len(data)}")
                    print(f"   数据类型: {type(data)}")
            else:
                print(f"   ❌ 市场状态获取失败: {data}")
            
            # 测试K线处理器
            print("\n5. 测试K线处理器...")
            
            class TestKlineHandler(ft.CurKlineHandlerBase):
                def __init__(self):
                    super().__init__()
                    self.received_count = 0
                
                def on_recv_rsp(self, rsp_pb):
                    ret_code, data = super().on_recv_rsp(rsp_pb)
                    self.received_count += 1
                    print(f"   📨 K线处理器第{self.received_count}次收到数据: ret_code={ret_code}")
                    
                    if ret_code != ft.RET_OK:
                        print(f"   ❌ 数据接收错误: {data}")
                        return ret_code, data
                    
                    if data is not None:
                        print(f"   数据类型: {type(data)}")
                        if hasattr(data, 'shape'):
                            print(f"   数据形状: {data.shape}")
                        if hasattr(data, 'columns'):
                            print(f"   数据列名: {list(data.columns)}")
                        if hasattr(data, 'iloc') and len(data) > 0:
                            print(f"   第一条数据: {data.iloc[0].to_dict()}")
                    
                    return ft.RET_OK, data
            
            # 设置处理器
            kline_handler = TestKlineHandler()
            quote_ctx.set_handler(kline_handler)
            print("   ✅ K线处理器设置成功")
            
            # 订阅K线数据
            print("\n6. 订阅K线数据...")
            ret, data = quote_ctx.subscribe(['HK.00700'], [ft.SubType.K_1M], is_first_push=True)
            
            if ret == ft.RET_OK:
                print("   ✅ K线数据订阅成功")
                print(f"   订阅结果: {data}")
                
                # 等待实时数据
                print("\n7. 等待10秒接收实时数据...")
                for i in range(10):
                    print(f"   等待中... {i+1}/10秒 (收到{kline_handler.received_count}条数据)")
                    time.sleep(1)
                
                print(f"\n   总计收到数据: {kline_handler.received_count}条")
                
            else:
                print(f"   ❌ K线数据订阅失败: {data}")
            
            # 关闭连接
            print("\n8. 关闭连接...")
            quote_ctx.close()
            print("   ✅ 连接已关闭")
            
        except Exception as e:
            print(f"   ❌ OpenD服务连接失败: {e}")
            print("   请检查:")
            print("   - Futu OpenD服务是否正在运行")
            print("   - 端口11111是否被占用")
            print("   - 防火墙设置")
            import traceback
            traceback.print_exc()
        
    except ImportError as e:
        print(f"❌ 无法导入futu模块: {e}")
        print("请确保futu-api已正确安装:")
        print("pip install futu-api")
    except Exception as e:
        print(f"❌ 调试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n=== 调试完成 ===")

if __name__ == "__main__":
    debug_futu_detailed()