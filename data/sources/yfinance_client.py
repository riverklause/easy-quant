"""
yfinance数据源客户端
"""
import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime
import pandas as pd
import yfinance as yf

from ..base_client import BaseDataSourceClient


class YFinanceClient(BaseDataSourceClient):
    """yfinance数据源客户端"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化yfinance客户端
        
        Args:
            config: yfinance配置，包含proxy等
        """
        super().__init__(config)
        self.proxy = config.get('yf_proxy')
        
        # 在初始化时统一设置代理
        if self.proxy:
            yf.set_config(proxy=self.proxy)
        
    async def connect(self) -> bool:
        """连接yfinance（yfinance无需显式连接）"""
        self.connected = True
        return True
    
    async def disconnect(self) -> bool:
        """断开yfinance连接（yfinance无需显式断开）"""
        self.connected = False
        return True
    
    async def get_historical_data(
        self, 
        symbol: str, 
        start_date: str, 
        end_date: str, 
        adjusted: bool = False,
        period: str = "daily"
    ) -> pd.DataFrame:
        """获取yfinance历史数据（复用get_batch_data逻辑）"""
        try:
            # 使用get_batch_data获取单个股票数据
            batch_result = await self.get_batch_data(
                symbols=[symbol],
                start_date=start_date,
                end_date=end_date,
                adjusted=adjusted,
                period=period,
                batch_size=1  # 单个股票，batch_size设为1
            )
            
            if batch_result.empty:
                raise Exception(f"未找到{symbol}的历史数据")
            
            # 从多级索引DataFrame中提取单个股票的数据
            # 重置索引，将多级索引转换为普通列
            df = batch_result.reset_index()
            
            # 过滤出当前股票的数据
            df = df[df['code'] == symbol]
            
            # 设置时间索引
            df = df.set_index('time_key')
            
            # 移除code列，因为已经是单个股票
            df = df.drop(columns=['code'])
            
            return df
            
        except Exception as e:
            raise Exception(f"获取yfinance历史数据错误: {e}")
    
    async def get_market_snapshot(
        self, 
        symbol: str, 
        adjusted: bool = True
    ) -> Dict[str, Any]:
        """yfinance不适合获取市场快照数据，返回空数据表"""
        # yfinance主要提供历史数据，不适合市场快照数据获取
        # 返回空字典表示不支持市场快照功能
        return {}
    
    async def get_batch_data(
        self, 
        symbols: List[str], 
        start_date: str, 
        end_date: str,
        adjusted: bool = False,
        period: str = "daily",
        batch_size: int = 200
    ) -> pd.DataFrame:
        """批量获取yfinance数据
        
        Args:
            symbols: 股票代码列表
            start_date: 开始日期
            end_date: 结束日期
            adjusted: 是否复权
            batch_size: 批量大小，控制并发数量避免频率限制
            
        Returns:
            包含各股票数据的字典
        """
        try:
            # 转换股票代码为yfinance格式
            yf_symbol = [self._convert_symbol(symbol) for symbol in symbols]
            
            # 使用yfinance的download方法进行批量下载（性能更优）
            interval = self._convert_period(period)
            #按照batch_size分组防止yfinance频率限制
            yf_symbols = [yf_symbol[i:i + batch_size] for i in 
                            range(0, len(yf_symbol), batch_size)]
            # 批量下载数据（多线程模式）
            batch_data = pd.DataFrame()
            for symbols_batch in yf_symbols:
                temp_data = yf.download(
                    symbols_batch,
                    start=start_date,
                    end=end_date,
                    interval=interval,
                    auto_adjust=adjusted,
                    threads=True,  # 启用多线程
                    group_by='ticker'  # 按股票代码分组
                )
                if temp_data.empty:
                    continue
                batch_data = temp_data if batch_data.empty else pd.concat([batch_data, temp_data])
            

            batch_data = batch_data.stack(level=0, future_stack=True)
            batch_data.index.names = ['time_key', 'code']
            
            return self._process_dataframe(batch_data)
            
        except Exception as e:
            # 如果批量下载失败，回退到原来的逐个下载方法
            print(f"批量下载失败，回退到逐个下载: {e}")
            return await self._fallback_batch_download(symbols, start_date, end_date, adjusted, period, batch_size)
    
    def _process_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """处理数据框格式，保持一致性"""
        
        # 重命名列
        column_mapping = {
            'Open': 'open',
            'High': 'high', 
            'Low': 'low',
            'Close': 'close',
            'Adj Close': 'adj_close',
            'Volume': 'volume'
        }
        df = df.rename(columns=column_mapping)
        
        # 将code索引列从yfinance格式转换为Futu格式
        if 'code' in df.index.names:
            # 重置索引以访问code列
            df_reset = df.reset_index()
            
            # 导入symbol_utils模块
            from utils.symbol_utils import convert_symbol_format
            
            # 转换code列中的股票代码格式
            df_reset['code'] = df_reset['code'].apply(
                lambda symbol: convert_symbol_format(symbol, 'futu', 'yfinance')
            )
            
            # 重新设置索引
            df = df_reset.set_index(['time_key', 'code'])
        
        return df
    
 
    def get_supported_markets(self) -> List[str]:
        """yfinance支持的市场，注意是futu的市场前缀"""
        return ['US', 'HK', 'SH', 'SZ']
    
    def get_supported_periods(self) -> List[str]:
        """yfinance支持的周期"""
        return ['1m', '2m', '5m', '15m', '30m', '60m', '90m', '1h', '1d', '5d', '1wk', '1mo', '3mo']
    
    def _convert_symbol(self, symbol: str) -> str:
        """转换股票代码为yfinance格式
        
        Args:
            symbol: yfinance格式的股票代码 (如: 0700.HK, AAPL, 000001.SZ, 600000.SS)
            
        Returns:
            yfinance格式的股票代码 (无需转换，直接返回)
        """
        # yfinance客户端接收的已经是yfinance格式，无需转换
        return symbol
    
    def _convert_period(self, period: str) -> str:
        """转换周期参数为yfinance格式"""
        period_mapping = {
            '1min': '1m',
            '5min': '5m',
            '15min': '15m',
            '30min': '30m',
            '60min': '60m',
            'daily': '1d',
            'weekly': '1wk',
            'monthly': '1mo'
        }
        return period_mapping.get(period, '1d')  # 默认日线
