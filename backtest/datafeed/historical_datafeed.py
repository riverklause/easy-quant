"""
历史数据源
为回测提供历史数据支持
"""

from typing import Dict, List, Optional, Union
from datetime import datetime
import pandas as pd
import numpy as np
from abc import ABC, abstractmethod


class BaseDataFeed(ABC):
    """
    数据源抽象基类
    """
    
    @abstractmethod
    def get_data(self, symbols: List[str], start_date: str, 
                 end_date: str, frequency: str = 'daily') -> Dict[str, pd.DataFrame]:
        """
        获取历史数据
        
        Args:
            symbols: 股票代码列表
            start_date: 开始日期
            end_date: 结束日期
            frequency: 数据频率 (daily, weekly, monthly)
            
        Returns:
            股票数据字典，key为股票代码，value为DataFrame
        """
        pass
    
    @abstractmethod
    def get_symbols(self) -> List[str]:
        """获取所有可用股票代码"""
        pass


class HistoricalDataFeed(BaseDataFeed):
    """
    历史数据源
    整合DataManager获取历史数据进行回测
    """
    
    def __init__(self, data_manager=None):
        """
        初始化历史数据源
        
        Args:
            data_manager: DataManager实例，如果为None则创建mock数据
        """
        self.data_manager = data_manager
        self._cache: Dict[str, pd.DataFrame] = {}
        self._frequency_map = {
            'daily': '1d',
            'weekly': '1w', 
            'monthly': '1M'
        }
    
    async def get_data(self, 
                       symbols: List[str], 
                       start_date: str, 
                       end_date: str,
                       frequency: str = 'daily') -> Dict[str, pd.DataFrame]:
        """
        获取历史数据
        
        Args:
            symbols: 股票代码列表
            start_date: 开始日期
            end_date: 结束日期
            frequency: 数据频率
            
        Returns:
            股票数据字典
        """
        if self.data_manager is None:
            return self._generate_mock_data(symbols, start_date, end_date, frequency)
        
        result = {}
        
        for symbol in symbols:
            cache_key = f"{symbol}_{start_date}_{end_date}_{frequency}"
            
            if cache_key in self._cache:
                result[symbol] = self._cache[cache_key]
                continue
            
            try:
                freq = self._frequency_map.get(frequency, '1d')
                data = await self.data_manager.get_historical_data(
                    symbol=symbol,
                    start_date=start_date,
                    end_date=end_date,
                    data_source='yfinance'
                )
                
                if data is not None and not data.empty:
                    result[symbol] = data
                    self._cache[cache_key] = data
                    
            except Exception as e:
                print(f"获取 {symbol} 数据失败: {e}")
                continue
        
        return result
    
    def get_data_sync(self, 
                      symbols: List[str], 
                      start_date: str, 
                      end_date: str,
                      frequency: str = 'daily') -> Dict[str, pd.DataFrame]:
        """
        同步获取历史数据
        
        Args:
            symbols: 股票代码列表
            start_date: 开始日期
            end_date: 结束日期
            frequency: 数据频率
            
        Returns:
            股票数据字典
        """
        if self.data_manager is None:
            return self._generate_mock_data(symbols, start_date, end_date, frequency)
        
        result = {}
        
        for symbol in symbols:
            cache_key = f"{symbol}_{start_date}_{end_date}_{frequency}"
            
            if cache_key in self._cache:
                result[symbol] = self._cache[cache_key]
                continue
        
        return result
    
    def _generate_mock_data(self, 
                           symbols: List[str], 
                           start_date: str, 
                           end_date: str,
                           frequency: str = 'daily') -> Dict[str, pd.DataFrame]:
        """
        生成模拟数据用于测试
        
        Args:
            symbols: 股票代码列表
            start_date: 开始日期
            end_date: 结束日期
            frequency: 数据频率
            
        Returns:
            模拟数据字典
        """
        result = {}
        
        start = pd.to_datetime(start_date)
        end = pd.to_datetime(end_date)
        
        if frequency == 'daily':
            dates = pd.date_range(start=start, end=end, freq='B')
        elif frequency == 'weekly':
            dates = pd.date_range(start=start, end=end, freq='W')
        elif frequency == 'monthly':
            dates = pd.date_range(start=start, end=end, freq='M')
        else:
            dates = pd.date_range(start=start, end=end, freq='B')
        
        for symbol in symbols:
            np.random.seed(hash(symbol) % (2**31))
            
            initial_price = 100 + np.random.randn() * 20
            prices = [initial_price]
            
            for _ in range(len(dates) - 1):
                change = np.random.randn() * 2
                prices.append(prices[-1] + change)
            
            prices = np.maximum(prices, 1)
            
            df = pd.DataFrame({
                'date': dates,
                'open': prices * (1 + np.random.randn(len(dates)) * 0.01),
                'high': prices * (1 + np.abs(np.random.randn(len(dates)) * 0.02)),
                'low': prices * (1 - np.abs(np.random.randn(len(dates)) * 0.02)),
                'close': prices,
                'volume': np.random.randint(1000000, 10000000, len(dates))
            })
            df.set_index('date', inplace=True)
            
            result[symbol] = df
        
        return result
    
    def get_symbols(self) -> List[str]:
        """获取所有可用股票代码"""
        if self._cache:
            return list(self._cache.keys())
        return []
    
    def clear_cache(self):
        """清除缓存"""
        self._cache.clear()
    
    def preload_data(self, 
                     symbols: List[str], 
                     start_date: str, 
                     end_date: str,
                     frequency: str = 'daily'):
        """
        预加载数据到缓存
        
        Args:
            symbols: 股票代码列表
            start_date: 开始日期
            end_date: 结束日期
            frequency: 数据频率
        """
        self._generate_mock_data(symbols, start_date, end_date, frequency)
    
    def get_combined_data(self, 
                          symbols: List[str], 
                          start_date: str, 
                          end_date: str,
                          frequency: str = 'daily') -> pd.DataFrame:
        """
        获取合并后的数据（用于多股票分析）
        
        Args:
            symbols: 股票代码列表
            start_date: 开始日期
            end_date: 结束日期
            frequency: 数据频率
            
        Returns:
            合并后的DataFrame
        """
        data_dict = self._generate_mock_data(symbols, start_date, end_date, frequency)
        
        close_prices = pd.DataFrame()
        
        for symbol, df in data_dict.items():
            if 'close' in df.columns:
                close_prices[symbol] = df['close']
        
        close_prices.sort_index(inplace=True)
        
        return close_prices
    
    def get_returns_data(self,
                         symbols: List[str],
                         start_date: str,
                         end_date: str,
                         frequency: str = 'daily') -> pd.DataFrame:
        """
        获取收益率数据
        
        Args:
            symbols: 股票代码列表
            start_date: 开始日期
            end_date: 结束日期
            frequency: 数据频率
            
        Returns:
            收益率DataFrame
        """
        close_data = self.get_combined_data(symbols, start_date, end_date, frequency)
        
        returns = close_data.pct_change()
        
        return returns.dropna()
    
    def get_trading_dates(self, start_date: str, end_date: str) -> pd.DatetimeIndex:
        """
        获取交易日列表
        
        Args:
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            交易日索引
        """
        dates = pd.date_range(start=start_date, end=end_date, freq='B')
        return dates
