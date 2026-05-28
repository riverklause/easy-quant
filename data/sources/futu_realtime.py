"""
Futu实时数据处理器
专注于数据接收，直接传递DataFrame给下游
"""
import time
from datetime import datetime
from typing import Dict, List, Callable, Any
import pandas as pd
from futu import *
from ..base_client import BaseDataSourceClient

#实时回调函数，注意futu api对于多个股票的实时回调是单个输出的，不合并
class FutuKlineHandler(CurKlineHandlerBase):
    """Futu K线数据处理器 - 只负责数据接收，直接传递DataFrame"""
    
    def __init__(self, data_callback: Callable):
        super().__init__()
        self.data_callback = data_callback
    
    def on_recv_rsp(self, rsp_pb):
        """接收K线数据响应"""
        ret_code, data = super().on_recv_rsp(rsp_pb)
        if ret_code != RET_OK:
            print(f"K线数据接收错误: {ret_code}")
            return ret_code, data
        
        if data is not None and len(data) > 0:
            df = data.copy()
            df['data_type'] = 'kline'
            self.data_callback(df)
        
        return RET_OK, data


class FutuOrderBookHandler(OrderBookHandlerBase):
    """Futu摆盘数据处理器 - 直接传递原始DataFrame"""
    
    def __init__(self, data_callback: Callable):
        super().__init__()
        self.data_callback = data_callback
    
    def on_recv_rsp(self, rsp_pb):
        """接收摆盘数据响应"""
        ret_code, data = super().on_recv_rsp(rsp_pb)
        if ret_code != RET_OK:
            print(f"摆盘数据接收错误: {ret_code}")
            return ret_code, data
        
        if data is not None and len(data) > 0:
            bid_prices, bid_volumes, bid_nums = [], [], []
            if 'Bid' in data and data['Bid']:
                for bid_tuple in data['Bid']:
                    if isinstance(bid_tuple, tuple) and len(bid_tuple) >= 3:
                        bid_prices.append(float(bid_tuple[0]))
                        bid_volumes.append(int(bid_tuple[1]))
                        bid_nums.append(int(bid_tuple[2]))
            
            ask_prices, ask_volumes, ask_nums = [], [], []
            if 'Ask' in data and data['Ask']:
                for ask_tuple in data['Ask']:
                    if isinstance(ask_tuple, tuple) and len(ask_tuple) >= 3:
                        ask_prices.append(float(ask_tuple[0]))
                        ask_volumes.append(int(ask_tuple[1]))
                        ask_nums.append(int(ask_tuple[2]))
            
            df = pd.DataFrame([{
                'code': data['code'],
                'name': data.get('name', ''),
                'time_key': datetime.now(),
                'bid_prices': bid_prices,
                'bid_volumes': bid_volumes,
                'bid_nums': bid_nums,
                'ask_prices': ask_prices,
                'ask_volumes': ask_volumes,
                'ask_nums': ask_nums,
                'data_type': 'order_book'
            }])
            self.data_callback(df)
        
        return RET_OK, data


class FutuQuoteHandler(StockQuoteHandlerBase):
    """Futu报价数据处理器 - 直接传递DataFrame"""
    
    def __init__(self, data_callback: Callable):
        super().__init__()
        self.data_callback = data_callback
    
    def on_recv_rsp(self, rsp_pb):
        """接收报价数据响应"""
        ret_code, data = super().on_recv_rsp(rsp_pb)
        if ret_code != RET_OK:
            print(f"报价数据接收错误: {ret_code}")
            return ret_code, data
        
        if data is not None and len(data) > 0:
            df = data.copy()
            df['time_key'] = datetime.now()
            df['data_type'] = 'quote'
            self.data_callback(df)
        
        return RET_OK, data

class FutuTickerHandler(TickerHandlerBase):
    """Futu逐笔数据处理器 - 直接传递DataFrame"""
    
    def __init__(self, data_callback: Callable):
        super().__init__()
        self.data_callback = data_callback
    
    def on_recv_rsp(self, rsp_pb):
        """接收逐笔数据响应"""
        ret_code, data = super().on_recv_rsp(rsp_pb)
        if ret_code != RET_OK:
            print(f"逐笔数据接收错误: {ret_code}")
            return ret_code, data
        
        if data is not None and len(data) > 0:
            df = data.copy()
            df['data_type'] = 'ticker'
            self.data_callback(df)
        
        return RET_OK, data

class FutuTimeShareHandler(RTDataHandlerBase):
    """Futu分时数据处理器 - 直接传递DataFrame"""
    
    def __init__(self, data_callback: Callable):
        super().__init__()
        self.data_callback = data_callback
    
    def on_recv_rsp(self, rsp_pb):
        """接收分时数据响应"""
        ret_code, data = super().on_recv_rsp(rsp_pb)
        if ret_code != RET_OK:
            print(f"分时接收错误: {ret_code}")
            return ret_code, data
        
        if data is not None and len(data) > 0:
            df = data.copy()
            df['data_type'] = 'time_share'
            self.data_callback(df)
        
        return RET_OK, data


class FutuRTProcessor(BaseDataSourceClient):
    """Futu实时数据处理器 - 专注于数据接收和标准化"""
    
    def __init__(self, config: Dict[str, Any]):
        """初始化Futu实时数据处理器"""
        
        super().__init__(config)
        self.quote_ctx = None
        self.data_callbacks = []  # 数据回调函数列表
        
        # 设置数据源特性信息
        self.features = {
            '数据源名称': 'Futu实时数据',
            '支持的市场': self.get_supported_markets(),
            '支持的K线周期': self.get_supported_periods(),
            '数据类型': ['实时K线数据', '实时摆盘数据', '实时报价数据'],
            '连接方式': 'OpenD实时推送',
            '实时数据': True,
            '数据频率': '秒级实时',
            '实时数据订阅完成': False,
            '回调处理设置完成': False,
            '可实时推送数据种类': ['K线-kline', '摆盘-order_book', '报价-quote'],
            '免费使用': '免费但有限制',
            '数据延迟': '实时'
        }
        
    def register_callback(self, callback: Callable):
        """添加回调推送数据后的处理工具列表，注意：这里添加的回调工具必须是一个可以接收字典参数的函数或对象"""
        self.data_callbacks.append(callback)
        self.features['回调处理设置完成'] = True
        print(f"✅ 数据回调函数已添加，当前回调数量: {len(self.data_callbacks)}")
    
    def unregister_callback(self, callback: Callable = None):
        """移除回调推送数据后的处理工具列表"""
        # Args:
        #     callback (Callable, optional): 要移除的回调函数或对象。如果为None，则移除所有回调函数。
        if callback in self.data_callbacks:
            self.data_callbacks.remove(callback)
            if len(self.data_callbacks) == 0:
                self.features['回调处理设置完成'] = False
            print(f"✅ 数据回调函数已移除，当前回调数量: {len(self.data_callbacks)}")
        elif callback is None:
            self.data_callbacks.clear()
            self.features['回调处理设置完成'] = False
            print(f"✅ 所有数据回调函数已移除，当前回调数量: {len(self.data_callbacks)}")
        else:
            print("❌ 回调函数未找到，无法移除")

    def _data_handler(self, data: pd.DataFrame):
        """统一数据处理器 - 分发DataFrame数据"""
        for callback in self.data_callbacks:
            try:
                callback(data)
            except Exception as e:
                print(f"数据回调执行错误: {e}")
    
    def connect(self):
        """连接Futu API"""
        try:
            self.quote_ctx = OpenQuoteContext(
                host=self.config.get('Futu_Host', '127.0.0.1'),
                port=self.config.get('Futu_Port', 11111)
            )
            print(f"✅ Futu API连接成功 (host={self.config.get('Futu_Host', '127.0.0.1')}, port={self.config.get('Futu_Port', 11111)})")
            self.connected = True
            return True
        except Exception as e:
            print(f"❌ Futu API连接失败: {e}")
            self.connected = False
            return False
    
    def subscribe_realtime_data(self, symbols: List[str], data_types: List[str] = ['kline', 'order_book', 'quote', 'ticker', 'time_share']):
        """订阅实时数据"""
        # Args:
        #     symbols (List[str]): 股票代码列表，支持Futu格式
        #     data_types (List[str]): 数据类型列表，可选['kline', 'order_book', 'quote', 'ticker']
        if not self.quote_ctx:
            print("❌ 请先连接Futu API")
            return False
        
        try:
            # 创建并注册处理器
            if 'kline' in data_types:
                # 创建K线数据处理器
                kline_handler = FutuKlineHandler(self._data_handler) # 定义处理器，_data_handler 是统一数据处理器被传递给K线数据处理器
                # 设置K线数据回调
                self.quote_ctx.set_handler(kline_handler)
                
            if 'order_book' in data_types:
                # 创建摆盘数据处理器
                order_book_handler = FutuOrderBookHandler(self._data_handler)
                # 设置摆盘数据回调
                self.quote_ctx.set_handler(order_book_handler)
                
            if 'quote' in data_types:
                # 创建报价数据处理器
                quote_handler = FutuQuoteHandler(self._data_handler)
                # 设置报价数据回调
                self.quote_ctx.set_handler(quote_handler)
                
            if 'ticker' in data_types:
                # 创建报价数据处理器
                ticker_handler = FutuTickerHandler(self._data_handler)
                # 设置报价数据回调
                self.quote_ctx.set_handler(ticker_handler)
                
            if 'time_share' in data_types:
                # 创建分时数据处理器
                time_share_handler = FutuTimeShareHandler(self._data_handler)
                # 设置分时数据回调
                self.quote_ctx.set_handler(time_share_handler)
            
            # 订阅数据
            for symbol in symbols:
                if 'kline' in data_types:
                    ret, msg = self.quote_ctx.subscribe(symbol, SubType.K_1M, subscribe_push=True)
                    if ret == RET_OK:
                        print(f"✅ 订阅 {symbol} K线数据成功")
                    else:
                        print(f"❌ 订阅 {symbol} K线数据失败: {msg}")
                
                if 'order_book' in data_types:
                    ret, msg = self.quote_ctx.subscribe(symbol, SubType.ORDER_BOOK, subscribe_push=True)
                    if ret == RET_OK:
                        print(f"✅ 订阅 {symbol} 摆盘数据成功")
                    else:
                        print(f"❌ 订阅 {symbol} 摆盘数据失败: {msg}")
                
                if 'quote' in data_types:
                    ret, msg = self.quote_ctx.subscribe(symbol, SubType.QUOTE, subscribe_push=True)
                    if ret == RET_OK:
                        print(f"✅ 订阅 {symbol} 报价数据成功")
                    else:
                        print(f"❌ 订阅 {symbol} 报价数据失败: {msg}")
                
                if 'ticker' in data_types:
                    ret, msg = self.quote_ctx.subscribe(symbol, SubType.TICKER, subscribe_push=True)
                    if ret == RET_OK:
                        print(f"✅ 订阅 {symbol} 逐笔数据成功")
                    else:
                        print(f"❌ 订阅 {symbol} 逐笔数据失败: {msg}")
                
                if 'time_share' in data_types:
                    ret, msg = self.quote_ctx.subscribe(symbol, SubType.RT_DATA, subscribe_push=True)
                    if ret == RET_OK:
                        print(f"✅ 订阅 {symbol} 分时数据成功")
                    else:
                        print(f"❌ 订阅 {symbol} 分时数据失败: {msg}")
            
            self.features['实时数据订阅完成'] = True
            return True
            
        except Exception as e:
            print(f"❌ 数据订阅失败: {e}")
            return False
    
    def disconnect(self):
        """断开连接"""
        # Args:
        #     None
        if self.quote_ctx:
            self.quote_ctx.close()
            print("✅ 实时数据订阅已取消")
        self.connected = False
        self.unregister_callback() #unregister_callback自带处理后提示，这里是注销全部回调函数/对象
        self.features['实时数据订阅完成'] = False
        self.features['回调处理设置完成'] = False
        print("✅ Futu API连接已关闭")

    def get_supported_markets(self) -> List[str]:
        """获取Futu支持的市场列表
        
        返回Futu API支持交易的市场代码列表。
        
        Returns:
            List[str]: 支持的市场代码列表，包含：HK（港股）、US（美股）、SH（沪市）、SZ（深市）
        """
        return ['HK', 'US', 'SH', 'SZ']
    
    def get_supported_periods(self) -> List[str]:
        """获取Futu支持的K线周期列表
        
        返回Futu API支持的K线数据周期类型。
        
        Returns:
            List[str]: 支持的K线周期列表，包含：1m（1分钟）、5m（5分钟）、15m（15分钟）、30m（30分钟）、1h（1小时））
        """
        return ['1m', '5m', '15m', '30m', '1h']

    async def get_historical_data(
        self, 
        symbol: str, 
        start_date: str, 
        end_date: str, 
        adjusted: bool = False,
        period: str = "daily"
    ) -> pd.DataFrame:
        """获取历史数据 - 实时数据处理器不支持此功能
        
        Args:
            symbol: 股票代码
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
            adjusted: 是否复权
            period: 数据周期
            
        Returns:
            DataFrame: 空DataFrame
            
        Raises:
            NotImplementedError: 实时数据处理器不支持历史数据获取
        """
        raise NotImplementedError("Futu实时数据处理器不支持历史数据获取，请使用FutuAPIClient")

    async def get_market_snapshot(self, symbol: str) -> Dict[str, Any]:
        """获取市场快照数据 - 实时数据处理器不支持此功能
        Args:
            symbol: 股票代码
            
        Returns:
            Dict: 空字典
        返回空字典表示不支持市场快照功能，请使用FutuAPIClient
        """
        return {}

    async def get_batch_data(
        self, 
        symbols: List[str], 
        start_date: str, 
        end_date: str,
        adjusted: bool = False
    ) -> Dict[str, pd.DataFrame]:
        """批量获取多个股票的历史数据 - 实时数据处理器不支持此功能，获取实时数据使用回调方法
        
        Args:
            symbols: 股票代码列表
            start_date: 开始日期
            end_date: 结束日期
            adjusted: 是否复权
            
        Returns:
            Dict: 空字典
            
        Raises:
            NotImplementedError: 实时数据处理器不支持批量数据获取
        """
        raise NotImplementedError("Futu实时数据处理器不支持批量数据获取，请使用FutuAPIClient")
    
    async def get_financial_statements(self, symbol, statement_type, period="annual"):
        """获取财务报表 - 实时数据处理器不支持此功能
        
        Args:
            symbol: 股票代码
            statement_type: 报表类型
            period: 报告期
            
        Raises:
            NotImplementedError: 实时数据处理器不支持财务报表获取
        """
        raise NotImplementedError("Futu实时数据处理器不支持财务报表获取，请使用FutuAPIClient")
    
    async def get_financial_indicators(self, symbol, period="annual"):
        """获取财务指标 - 实时数据处理器不支持此功能
        
        Args:
            symbol: 股票代码
            period: 报告期
            
        Raises:
            NotImplementedError: 实时数据处理器不支持财务指标获取
        """
        raise NotImplementedError("Futu实时数据处理器不支持财务指标获取，请使用FutuAPIClient")
