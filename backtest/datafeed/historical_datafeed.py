"""
历史数据源
为回测提供历史数据支持
"""

from typing import Dict, List, Optional, Union
from datetime import datetime
import logging

import pandas as pd
import numpy as np
from abc import ABC, abstractmethod

from utils.trading_calendar import CalendarError, infer_market

logger = logging.getLogger(__name__)


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
    
    def __init__(self, data_manager=None, allow_mock: bool = True, calendar=None):
        """
        初始化历史数据源
        
        Args:
            data_manager: DataManager实例，如果为None则创建mock数据
            allow_mock: 未配置 data_manager 时是否允许回落模拟数据
            calendar: TradingCalendar 实例；未显式传入时从 data_manager 懒获取
        """
        self.data_manager = data_manager
        self.allow_mock = allow_mock
        self.used_mock = False
        self.failed_symbols = 0
        self._cache: Dict[str, pd.DataFrame] = {}
        self._calendar = calendar
        self._calendar_resolved = calendar is not None
        self._calendar_error: Optional[Exception] = None

    def _get_calendar(self):
        """懒解析日历：构造 DataFeed 时不触发任何日历创建或 futu 请求。

        data_manager 没有日历入口（旧路径）→ None；
        入口存在但抛异常 → 记录 _calendar_error，真实路径必须显式失败。
        """
        if not self._calendar_resolved:
            self._calendar_resolved = True
            getter = getattr(self.data_manager, "get_trading_calendar", None)
            if callable(getter):
                try:
                    self._calendar = getter()
                except Exception as exc:  # noqa: BLE001 - 真实路径由调用方按 error 抛出
                    logger.warning("获取交易日历失败: %s", exc)
                    self._calendar = None
                    self._calendar_error = exc
        return self._calendar
    
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
        self.failed_symbols = 0

        if self.data_manager is None:
            if not self.allow_mock:
                raise ValueError("未配置 data_manager，且 allow_mock=False")
            self.used_mock = True
            logger.warning("未配置 data_manager，使用模拟数据")
            return self._generate_mock_data(symbols, start_date, end_date, frequency)
        
        result = {}
        
        for symbol in symbols:
            cache_key = f"{symbol}_{start_date}_{end_date}_{frequency}"
            
            if cache_key in self._cache:
                result[symbol] = self._cache[cache_key]
                continue
            
            try:
                data = await self.data_manager.get_historical_data(
                    symbol=symbol,
                    start_date=start_date,
                    end_date=end_date,
                    data_source='yfinance',
                    period=frequency
                )
                
                if data is not None and not data.empty:
                    result[symbol] = data
                    self._cache[cache_key] = data
                    
            except Exception:
                self.failed_symbols += 1
                logger.exception("获取 %s 数据失败", symbol)
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
            dates = self._mock_daily_dates(symbols, start, end)
        elif frequency == 'weekly':
            dates = pd.date_range(start=start, end=end, freq='W')
        elif frequency == 'monthly':
            dates = pd.date_range(start=start, end=end, freq='ME')
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

    def _mock_daily_dates(self, symbols: List[str], start, end) -> pd.DatetimeIndex:
        """mock 日线日轴：单市场且日历可用时走日历，其余回工作日并 WARNING。"""
        calendar = self._get_calendar()
        if calendar is None:
            if self._calendar_error is not None:
                logger.warning(
                    "mock 日线日历不可用，回退工作日 freq='B': %s", self._calendar_error
                )
            else:
                logger.warning("未配置日历，mock 日线回退工作日 freq='B'")
            return pd.date_range(start=start, end=end, freq='B')

        market = infer_market(symbols)
        if market is None:
            logger.warning("mock 日线无法推断唯一市场，回退工作日 freq='B'")
        else:
            try:
                return calendar.get_trading_days(market, start, end)
            except CalendarError as exc:
                logger.warning("mock 日线读取交易日历失败，回退工作日: %s", exc)
        return pd.date_range(start=start, end=end, freq='B')
    
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
    
    def get_trading_dates(self, start_date: str, end_date: str, market: str = "hk") -> pd.DatetimeIndex:
        """
        获取交易日列表
        
        Args:
            start_date: 开始日期
            end_date: 结束日期
            market: 市场（HK/US/CN），默认 hk；必须由调用方按标的市场显式传入，
                默认值仅用于兼容旧的两参数调用
            
        Returns:
            交易日索引
        """
        calendar = self._get_calendar()
        if calendar is not None:
            # 日历异常原样抛出，不回工作日
            return calendar.get_trading_days(market, start_date, end_date)
        if self._calendar_error is not None:
            raise self._calendar_error

        logger.warning("未配置交易日历，回退工作日 freq='B'")
        return pd.date_range(start=start_date, end=end_date, freq='B')
