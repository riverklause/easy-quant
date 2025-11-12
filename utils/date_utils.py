"""
日期时间工具模块
支持港股、美股交易时间处理和日期计算
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, time
from typing import List, Tuple, Optional
import holidays

from .logger import logger

class DateUtils:
    """日期时间工具类"""
    
    def __init__(self):
        # 港股节假日
        self.hk_holidays = holidays.HK()
        # 美股节假日
        self.us_holidays = holidays.US()
        
        # 交易时间配置
        self.trading_hours = {
            'hk': {
                'market_open': time(9, 30),
                'market_close': time(16, 0),
                'lunch_start': time(12, 0),
                'lunch_end': time(13, 0)
            },
            'us': {
                'market_open': time(9, 30),
                'market_close': time(16, 0)
            }
        }
    
    def is_trading_day(self, date: datetime, market: str = 'hk') -> bool:
        """判断是否为交易日"""
        # 检查周末
        if date.weekday() >= 5:  # 周六或周日
            return False
        
        # 检查节假日
        if market == 'hk':
            return date.date() not in self.hk_holidays
        elif market == 'us':
            return date.date() not in self.us_holidays
        else:
            return True  # 其他市场默认所有工作日都是交易日
    
    def is_trading_time(self, dt: datetime, market: str = 'hk') -> bool:
        """判断是否为交易时间"""
        if not self.is_trading_day(dt, market):
            return False
        
        market_hours = self.trading_hours[market]
        current_time = dt.time()
        
        if market == 'hk':
            # 港股交易时间（含午休）
            return ((market_hours['market_open'] <= current_time < market_hours['lunch_start']) or
                    (market_hours['lunch_end'] <= current_time < market_hours['market_close']))
        else:
            # 美股交易时间（无午休）
            return market_hours['market_open'] <= current_time < market_hours['market_close']
    
    def get_next_trading_day(self, date: datetime, market: str = 'hk') -> datetime:
        """获取下一个交易日"""
        next_day = date + timedelta(days=1)
        while not self.is_trading_day(next_day, market):
            next_day += timedelta(days=1)
        return next_day
    
    def get_previous_trading_day(self, date: datetime, market: str = 'hk') -> datetime:
        """获取上一个交易日"""
        prev_day = date - timedelta(days=1)
        while not self.is_trading_day(prev_day, market):
            prev_day -= timedelta(days=1)
        return prev_day
    
    def get_trading_days_range(self, start_date: datetime, end_date: datetime, 
                              market: str = 'hk') -> List[datetime]:
        """获取指定日期范围内的所有交易日"""
        trading_days = []
        current_date = start_date
        
        while current_date <= end_date:
            if self.is_trading_day(current_date, market):
                trading_days.append(current_date)
            current_date += timedelta(days=1)
        
        return trading_days
    
    def get_trading_days_count(self, start_date: datetime, end_date: datetime, 
                              market: str = 'hk') -> int:
        """计算两个日期之间的交易日数量"""
        return len(self.get_trading_days_range(start_date, end_date, market))
    
    def format_date(self, dt: datetime, format_str: str = '%Y-%m-%d') -> str:
        """格式化日期"""
        return dt.strftime(format_str)
    
    def parse_date(self, date_str: str, format_str: str = '%Y-%m-%d') -> datetime:
        """解析日期字符串"""
        return datetime.strptime(date_str, format_str)
    
    def get_quarter_start_end(self, year: int, quarter: int) -> Tuple[datetime, datetime]:
        """获取季度的开始和结束日期"""
        quarter_starts = [
            datetime(year, 1, 1),   # Q1
            datetime(year, 4, 1),   # Q2
            datetime(year, 7, 1),   # Q3
            datetime(year, 10, 1)  # Q4
        ]
        
        start_date = quarter_starts[quarter - 1]
        if quarter == 4:
            end_date = datetime(year + 1, 1, 1) - timedelta(days=1)
        else:
            end_date = quarter_starts[quarter] - timedelta(days=1)
        
        return start_date, end_date
    
    def get_fiscal_year_start_end(self, year: int, fiscal_start_month: int = 4) -> Tuple[datetime, datetime]:
        """获取财年的开始和结束日期"""
        start_date = datetime(year, fiscal_start_month, 1)
        end_date = datetime(year + 1, fiscal_start_month, 1) - timedelta(days=1)
        return start_date, end_date
    
    def get_market_calendar(self, market: str = 'hk', 
                          start_date: Optional[datetime] = None, 
                          end_date: Optional[datetime] = None) -> pd.DatetimeIndex:
        """获取市场交易日历"""
        if start_date is None:
            start_date = datetime.now() - timedelta(days=365)
        if end_date is None:
            end_date = datetime.now()
        
        trading_days = self.get_trading_days_range(start_date, end_date, market)
        return pd.DatetimeIndex(trading_days)
    
    def calculate_time_delta(self, start_dt: datetime, end_dt: datetime, 
                           unit: str = 'days') -> float:
        """计算时间差"""
        delta = end_dt - start_dt
        
        if unit == 'days':
            return delta.total_seconds() / (24 * 3600)
        elif unit == 'hours':
            return delta.total_seconds() / 3600
        elif unit == 'minutes':
            return delta.total_seconds() / 60
        elif unit == 'seconds':
            return delta.total_seconds()
        else:
            return delta.total_seconds()

# 创建全局日期工具实例
date_utils = DateUtils()

# 便捷访问函数
def is_trading_day(date: datetime, market: str = 'hk') -> bool:
    """判断是否为交易日"""
    return date_utils.is_trading_day(date, market)

def is_trading_time(dt: datetime, market: str = 'hk') -> bool:
    """判断是否为交易时间"""
    return date_utils.is_trading_time(dt, market)

def get_next_trading_day(date: datetime, market: str = 'hk') -> datetime:
    """获取下一个交易日"""
    return date_utils.get_next_trading_day(date, market)

def get_trading_days_range(start_date: datetime, end_date: datetime, 
                         market: str = 'hk') -> List[datetime]:
    """获取交易日范围"""
    return date_utils.get_trading_days_range(start_date, end_date, market)

def format_date(dt: datetime, format_str: str = '%Y-%m-%d') -> str:
    """格式化日期"""
    return date_utils.format_date(dt, format_str)

if __name__ == "__main__":
    # 测试日期工具功能
    today = datetime.now()
    print(f"今天是交易日吗 (港股): {is_trading_day(today, 'hk')}")
    print(f"现在是交易时间吗 (港股): {is_trading_time(today, 'hk')}")
    
    next_trading_day = get_next_trading_day(today, 'hk')
    print(f"下一个交易日: {format_date(next_trading_day)}")
    
    # 测试交易日范围
    start = datetime(2024, 1, 1)
    end = datetime(2024, 1, 31)
    trading_days = get_trading_days_range(start, end, 'hk')
    print(f"2024年1月港股交易日数量: {len(trading_days)}")