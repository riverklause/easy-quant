"""
Futu API官方文档模式演示 - 基于官方文档的正确实现
"""
import time
import futu as ft


class OfficialKlineHandler(ft.CurKlineHandlerBase):
    """官方K线处理器"""
    
    def __init__(self, name="KlineHandler"):
        super().__init__()
        self.name = name
        self.data_count = 0
    
    def on_recv_rsp(self, rsp_pb):
        ret_code, data = super(OfficialKlineHandler, self).on_recv_rsp(rsp_pb)
        if ret_code != ft.RET_OK:
            print(f"{self.name}: error, msg: {data}")
            return ret_code, data
        
        self.data_count += 1
        print(f"{self.name} 第{self.data_count}次接收: {data}")
        
        # 官方文档模式：返回RET_OK, data
        return ft.RET_OK, data


class OfficialOrderBookHandler(ft.OrderBookHandlerBase):
    """官方摆盘处理器"""
    
    def __init__(self, name="OrderBookHandler"):
        super().__init__()
        self.name = name
        self.data_count = 0
    
    def on_recv_rsp(self, rsp_pb):
        ret_code, data = super(OfficialOrderBookHandler, self).on_recv_rsp(rsp_pb)
        if ret_code != ft.RET_OK:
            print(f"{self.name}: error, msg: {data}")
            return ret_code, data
        
        self.data_count += 1
        print(f"{self.name} 第{self.data_count}次接收: {data}")
        
        return ft.RET_OK, data


class OfficialQuoteHandler(ft.StockQuoteHandlerBase):
    """官方报价处理器"""
    
    def __init__(self, name="QuoteHandler"):
        super().__init__()
        self.name = name
        self.data_count = 0
    
    def on_recv_rsp(self, rsp_pb):
        ret_code, data = super(OfficialQuoteHandler, self).on_recv_rsp(rsp_pb)
        if ret_code != ft.RET_OK:
            print(f"{self.name}: error, msg: {data}")
            return ret_code, data
        
        self.data_count += 1
        print(f"{self.name} 第{self.data_count}次接收: {data}")
        
        return ft.RET_OK, data


def demo_official_kline():
    """演示官方K线模式"""
    print("=== Futu官方K线模式演示 ===")
    
    quote_ctx = ft.OpenQuoteContext(host='127.0.0.1', port=11111)
    
    try:
        # 创建处理器
        handler = OfficialKlineHandler("官方K线测试")
        
        # 设置回调处理器
        quote_ctx.set_handler(handler)
        
        # 订阅K线数据类型
        ret, data = quote_ctx.subscribe(['HK.00700'], [ft.SubType.K_1M], is_first_push=True)
        
        if ret == ft.RET_OK:
            print(f"订阅成功: {data}")
        else:
            print(f'订阅失败: {data}')
            return
        
        # 等待数据推送
        print("等待Futu API推送实时K线数据...")
        time.sleep(15)
        
    except Exception as e:
        print(f"演示出错: {e}")
    finally:
        quote_ctx.close()
        print("K线演示结束")


def demo_official_order_book():
    """演示官方摆盘模式"""
    print("\n=== Futu官方摆盘模式演示 ===")
    
    quote_ctx = ft.OpenQuoteContext(host='127.0.0.1', port=11111)
    
    try:
        # 创建处理器
        handler = OfficialOrderBookHandler("官方摆盘测试")
        
        # 设置回调处理器
        quote_ctx.set_handler(handler)
        
        # 订阅摆盘数据类型
        ret, data = quote_ctx.subscribe(['HK.00700'], [ft.SubType.ORDER_BOOK], is_first_push=True)
        
        if ret == ft.RET_OK:
            print(f"订阅成功: {data}")
        else:
            print(f'订阅失败: {data}')
            return
        
        # 等待数据推送
        print("等待Futu API推送实时摆盘数据...")
        time.sleep(10)
        
    except Exception as e:
        print(f"演示出错: {e}")
    finally:
        quote_ctx.close()
        print("摆盘演示结束")


def demo_official_quote():
    """演示官方报价模式"""
    print("\n=== Futu官方报价模式演示 ===")
    
    quote_ctx = ft.OpenQuoteContext(host='127.0.0.1', port=11111)
    
    try:
        # 创建处理器
        handler = OfficialQuoteHandler("官方报价测试")
        
        # 设置回调处理器
        quote_ctx.set_handler(handler)
        
        # 订阅报价数据类型
        ret, data = quote_ctx.subscribe(['HK.00700'], [ft.SubType.QUOTE], is_first_push=True)
        
        if ret == ft.RET_OK:
            print(f"订阅成功: {data}")
        else:
            print(f'订阅失败: {data}')
            return
        
        # 等待数据推送
        print("等待Futu API推送实时报价数据...")
        time.sleep(10)
        
    except Exception as e:
        print(f"演示出错: {e}")
    finally:
        quote_ctx.close()
        print("报价演示结束")


if __name__ == "__main__":
    # 运行官方模式演示
    demo_official_kline()
    demo_official_order_book()
    demo_official_quote()