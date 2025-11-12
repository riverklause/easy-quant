"""
Futu API数据源客户端
"""
import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime
import pandas as pd
import futu as ft

from ..base_client import BaseDataSourceClient


class FutuAPIClient(BaseDataSourceClient):
    """Futu API数据源客户端"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化Futu客户端
        
        Args:
            config: Futu配置，包含host, port, websocket_port, websocket_key等
        """
        super().__init__(config)
        self.quote_ctx = None
        self.trade_ctx = None
        
    async def connect(self) -> bool:
        """连接Futu API
        
        建立与Futu OpenD服务的连接，创建行情和交易上下文。
        
        Returns:
            bool: 连接成功返回True，失败返回False
            
        Raises:
            Exception: 连接过程中出现错误时抛出异常
        """
        try:
            # 这里使用异步方式连接Futu API
            # 实际实现需要根据Futu API的异步支持进行调整
            
            # 创建行情上下文
            self.quote_ctx = ft.OpenQuoteContext(
                host=self.config.get('Futu_Host', '127.0.0.1'),
                port=self.config.get('Futu_Port', 11111)
            )
            
            # 创建交易上下文（如果需要交易功能）
            if self.config.get('Futu_TrdEnv') == 'REAL':
                self.trade_ctx = ft.OpenSecTradeContext(
                    host=self.config.get('Futu_Host', '127.0.0.1'),
                    port=self.config.get('Futu_Port', 11111),
                    security_firm=ft.SecurityFirm.FUTUSECURITIES
                )
            
            self.connected = True
            return True
            
        except Exception as e:
            print(f"Futu连接失败: {e}")
            self.connected = False
            return False

    async def disconnect(self) -> bool:
        """断开Futu连接
        
        关闭与Futu OpenD服务的连接，释放行情和交易上下文资源。
        
        Returns:
            bool: 断开成功返回True，失败返回False
            
        Raises:
            Exception: 断开连接过程中出现错误时抛出异常
        """
        try:
            if self.quote_ctx:
                self.quote_ctx.close()
            if self.trade_ctx:
                self.trade_ctx.close()
            self.connected = False
            return True
        except Exception as e:
            print(f"Futu断开连接失败: {e}")
            return False
    
    async def get_historical_data(
        self, 
        symbol: str, 
        start_date: str, 
        end_date: str, 
        adjusted: bool = False,
        period: str = "daily"
    ) -> pd.DataFrame:
        """获取Futu历史数据
        
        从Futu API获取指定股票的历史K线数据。
        
        Args:
            symbol (str): 股票代码，支持Futu格式（如：HK.00700, US.AAPL）
            start_date (str): 开始日期，格式：YYYY-MM-DD
            end_date (str): 结束日期，格式：YYYY-MM-DD
            adjusted (bool): 是否复权，默认False（不复权）
            period (str): K线周期，支持：1min, 5min, 15min, 30min, 60min, daily, weekly, monthly
            
        Returns:
            pd.DataFrame: 包含历史数据的DataFrame，包含open, high, low, close, volume等列
            
        Raises:
            ConnectionError: 客户端未连接时抛出
            Exception: 数据获取过程中出现错误时抛出
        """
        if not self.connected:
            raise ConnectionError("Futu客户端未连接")
        
        try:
            # 转换周期参数
            futu_period = self._convert_period(period)
            
            # 获取K线数据
            ret, data, page_req_key = self.quote_ctx.request_history_kline(
                code=symbol,
                start=start_date,
                end=end_date,
                ktype=futu_period,
                autype=ft.KL_FIELD.REAL if not adjusted else ft.KL_FIELD.FORWARD,
                fields=[ft.KL_FIELD.ALL]
            )
            
            if ret == ft.RET_OK:
                df: pd.DataFrame = data
                df['time_key'] = pd.to_datetime(df['time_key'])
                df.set_index('time_key', inplace=True)
                
                # 注释掉无用的列重命名映射（原列名和目标列名相同）
                # column_mapping = {
                #     'open': 'open',
                #     'close': 'close', 
                #     'high': 'high',
                #     'low': 'low',
                #     'volume': 'volume',
                #     'turnover': 'turnover'
                # }
                # df = df.rename(columns=column_mapping)
                
                return df
            else:
                raise Exception(f"Futu获取历史数据失败: {data}")
                
        except Exception as e:
            raise Exception(f"获取Futu历史数据错误: {e}")
    
    async def get_market_snapshot(
        self, 
        symbol: str, 
        adjusted: bool = True
    ) -> Dict[str, Any]:
        """获取市场快照数据
        
        从Futu API获取指定股票的市场快照数据（非实时推送数据）。
        
        Args:
            symbol (str): 股票代码，支持Futu格式（如：HK.00700, US.AAPL）
            adjusted (bool): 是否复权，默认True（复权）
            
        Returns:
            Dict[str, Any]: 包含市场快照数据的字典，包含last_price, open_price, high_price等字段
            
        Raises:
            ConnectionError: 客户端未连接时抛出
            Exception: 数据获取过程中出现错误时抛出
        """
        if not self.connected:
            raise ConnectionError("Futu客户端未连接")
        
        try:
            # 获取实时报价
            ret, data = self.quote_ctx.get_market_snapshot([symbol])
            
            if ret == ft.RET_OK and len(data) > 0:
                snapshot = data.iloc[0]
                
                real_time_data = {
                    'symbol': symbol,
                    'last_price': snapshot['last_price'],
                    'open_price': snapshot['open_price'],
                    'high_price': snapshot['high_price'], 
                    'low_price': snapshot['low_price'],
                    'prev_close': snapshot['prev_close_price'],
                    'volume': snapshot['volume'],
                    'turnover': snapshot['turnover'],
                    'timestamp': datetime.now().isoformat(),
                    'data_source': 'futu'
                }
                
                return real_time_data
            else:
                raise Exception(f"Futu获取实时数据失败: {data}")
                
        except Exception as e:
            raise Exception(f"获取Futu实时数据错误: {e}")
    
    async def get_batch_data(
        self, 
        symbols: List[str], 
        start_date: str, 
        end_date: str,
        adjusted: bool = False
    ) -> Dict[str, pd.DataFrame]:
        """批量获取Futu数据
        
        并发获取多个股票的历史数据，提高数据获取效率。
        
        Args:
            symbols (List[str]): 股票代码列表，支持Futu格式
            start_date (str): 开始日期，格式：YYYY-MM-DD
            end_date (str): 结束日期，格式：YYYY-MM-DD
            adjusted (bool): 是否复权，默认False（不复权）
            
        Returns:
            Dict[str, pd.DataFrame]: 字典，键为股票代码，值为对应的历史数据DataFrame
            
        Raises:
            ConnectionError: 客户端未连接时抛出
            Exception: 数据获取过程中出现错误时抛出
        """
        results = {}
        
        # 使用异步方式并发获取
        tasks = []
        for symbol in symbols:
            task = self.get_historical_data(symbol, start_date, end_date, adjusted)
            tasks.append(task)
        
        # 等待所有任务完成
        completed_tasks = await asyncio.gather(*tasks, return_exceptions=True)
        
        for i, result in enumerate(completed_tasks):
            symbol = symbols[i]
            if isinstance(result, Exception):
                print(f"获取{symbol}数据失败: {result}")
            else:
                results[symbol] = result
        
        return results
    
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
            List[str]: 支持的K线周期列表，包含：1min, 5min, 15min, 30min, 60min, daily, weekly, monthly
        """
        return ['1min', '5min', '15min', '30min', '60min', 'daily', 'weekly', 'monthly']
    
    def _convert_period(self, period: str) -> int:
        """转换周期参数为Futu格式
        
        将字符串格式的周期参数转换为Futu API使用的枚举类型。
        
        Args:
            period (str): 周期参数，如：1min, 5min, daily等
            
        Returns:
            int: 对应的Futu API周期枚举值
        """
        period_mapping = {
            '1min': ft.KLType.k_1Mk_1M,
            '5min': ft.KLType.k_5Mk_5M,
            '15min': ft.KLType.k_15Mk_15M,
            '30min': ft.KLType.k_30Mk_30M,
            '60min': ft.KLType.k_60Mk_60M,
            'daily': ft.KLType.k_Day,
            'weekly': ft.KLType.k_Week,
            'monthly': ft.KLType.k_Month
        }
        return period_mapping.get(period, 1440)  # 默认日线