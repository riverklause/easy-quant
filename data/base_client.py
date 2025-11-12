"""
数据源客户端基类
定义统一的数据获取接口
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
from datetime import datetime
import pandas as pd


class BaseDataSourceClient(ABC):
    """数据源客户端基类"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化数据源客户端
        
        Args:
            config: 数据源配置字典
        """
        self.config = config
        self.connected = False
    
    @abstractmethod
    async def connect(self) -> bool:
        """连接数据源"""
        pass
    
    @abstractmethod
    async def disconnect(self) -> bool:
        """断开数据源连接"""
        pass
    
    @abstractmethod
    async def get_historical_data(
        self, 
        symbol: str, 
        start_date: str, 
        end_date: str, 
        adjusted: bool = False,
        period: str = "daily"
    ) -> pd.DataFrame:
        """
        获取历史数据
        
        Args:
            symbol: 股票代码
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
            adjusted: 是否复权
            period: 数据周期 (daily, weekly, monthly)
            
        Returns:
            DataFrame包含历史数据
        """
        pass
    
    @abstractmethod
    async def get_market_snapshot(
        self, 
        symbol: str, 
        adjusted: bool = True
    ) -> Dict[str, Any]:
        """
        获取市场快照数据
        
        Args:
            symbol: 股票代码
            adjusted: 是否复权
            
        Returns:
            市场快照数据字典
        """
        pass
    
    @abstractmethod
    async def get_batch_data(
        self, 
        symbols: List[str], 
        start_date: str, 
        end_date: str,
        adjusted: bool = False
    ) -> Dict[str, pd.DataFrame]:
        """
        批量获取多个股票的历史数据
        
        Args:
            symbols: 股票代码列表
            start_date: 开始日期
            end_date: 结束日期
            adjusted: 是否复权
            
        Returns:
            股票代码到DataFrame的映射
        """
        pass
    
    @abstractmethod
    def get_supported_markets(self) -> List[str]:
        """获取支持的市场列表"""
        pass
    
    @abstractmethod
    def get_supported_periods(self) -> List[str]:
        """获取支持的数据周期"""
        pass
    
    def validate_symbol(self, symbol: str) -> bool:
        """验证股票代码格式"""
        # 基础验证，子类可以重写
        return bool(symbol and isinstance(symbol, str) and len(symbol) > 0)
    
    def validate_date_range(self, start_date: str, end_date: str) -> bool:
        """验证日期范围"""
        try:
            start = datetime.strptime(start_date, "%Y-%m-%d")
            end = datetime.strptime(end_date, "%Y-%m-%d")
            return start <= end
        except ValueError:
            return False
    
    async def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        return {
            "connected": self.connected,
            "data_source": self.__class__.__name__,
            "timestamp": datetime.now().isoformat()
        }