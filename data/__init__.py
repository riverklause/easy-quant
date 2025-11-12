"""
数据获取模块
支持多数据源获取股票数据
"""

from .data_manager import DataManager
from .sources.futu_client import FutuAPIClient
from .sources.yfinance_client import YFinanceClient

__all__ = ['DataManager', 'FutuAPIClient', 'YFinanceClient']