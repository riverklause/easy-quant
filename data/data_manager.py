"""
数据管理器 - 统一管理多数据源的数据获取
"""
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
import pandas as pd
import asyncio

from .sources.futu_client import FutuAPIClient
from .sources.yfinance_client import YFinanceClient
from .base_client import BaseDataSourceClient
from utils.symbol_utils import convert_symbol_format, validate_symbol_format


class DataManager:
    """数据管理器 - 统一管理多数据源"""
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        初始化数据管理器
        1、读取配置 2、定义self变量 3、初始化数据源客户端
        Args:
            config: 配置信息，包含各数据源的配置（可选，默认从settings.py获取）
        """
        if config is None:
            config = self._get_default_config()
        
        self.config = config
        self.clients: Dict[str, BaseDataSourceClient] = {}
        self.connected = False
        
        # 初始化数据源客户端
        self._init_clients()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """从settings.py获取配置，如果读取失败则报错"""
        try:
            from utils.settings import settings
            
            # 严格验证DataConfig类的核心配置项是否存在
            config_data = settings.data
            
            # 验证DataConfig类的核心配置项
            required_data_fields = ['data_dir', 'cache_dir', 'update_interval']
            for field in required_data_fields:
                if not hasattr(config_data, field):
                    raise ImportError(f"settings.py中缺少DataConfig核心配置项: {field}")
            
            # 验证Futu配置项
            required_futu_fields = ['Futu_Host', 'Futu_Port', 'Futu_TrdEnv']
            for field in required_futu_fields:
                if not hasattr(config_data, field):
                    raise ImportError(f"settings.py中缺少Futu配置项: {field}")
            
            # 验证yfinance配置项
            if not hasattr(config_data, 'yfinance_proxy'):
                raise ImportError("settings.py中缺少yfinance代理配置")
            
            # 验证可用的数据源配置项
            if not hasattr(config_data, 'available_data_sources'):
                raise ImportError("settings.py中缺少available_data_sources配置项")
            
            # 返回配置字典，目前有要传递给futu和yfinance客户端的配置参数和本类需要的参数
            return {
                'futu': {
                    'host': config_data.Futu_Host,
                    'port': config_data.Futu_Port,
                    'trd_env': config_data.Futu_TrdEnv,
                    'rsa_key_path': settings.futu_rsa_key_path,
                },
                'yfinance': {
                    'yf_proxy': config_data.yfinance_proxy,
                },
                'available_data_sources': config_data.available_data_sources,
            }
        except ImportError as e:
            # 如果settings.py不存在或配置不完整，直接报错
            raise ImportError(f"无法从settings.py读取配置: {e}")
    
    def _init_clients(self):
        """初始化数据源客户端"""
        # 初始化futu客户端
        if 'futu' in self.config['available_data_sources']:
            self.clients['futu'] = FutuAPIClient(self.config['futu'])
        
        # 初始化yfinance客户端
        if 'yfinance' in self.config['available_data_sources']: 
            self.clients['yfinance'] = YFinanceClient(self.config['yfinance'])
    
    async def connect_all(self) -> bool:
        """连接所有数据源"""
        try:
            tasks = []
            for client_name, client in self.clients.items():
                tasks.append(client.connect())
            
            # 等待所有连接完成
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 检查连接结果
            for i, result in enumerate(results):
                client_name = list(self.clients.keys())[i]
                if isinstance(result, Exception):
                    print(f"连接{client_name}失败: {result}")
                elif not result:
                    print(f"连接{client_name}失败")
            
            self.connected = all(not isinstance(r, Exception) and r for r in results)
            return self.connected
            
        except Exception as e:
            print(f"连接数据源失败: {e}")
            self.connected = False
            return False
    
    async def disconnect_all(self) -> bool:
        """断开所有数据源连接"""
        try:
            tasks = []
            for client_name, client in self.clients.items():
                tasks.append(client.disconnect())
            
            # 等待所有断开连接完成
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            self.connected = False
            return True
            
        except Exception as e:
            print(f"断开数据源连接失败: {e}")
            return False
    
    async def get_historical_data(
        self, 
        symbol: str, 
        start_date: str, 
        end_date: str, 
        data_source: str,
        adjusted: bool = False,
        period: str = "daily"
    ) -> pd.DataFrame:
        """
        获取历史数据
        
        Args:
            symbol: 股票代码（使用Futu格式，如：HK.00700, SZ.000001, US.AAPL）
            start_date: 开始日期
            end_date: 结束日期
            data_source: 数据源 目前仅支持('futu', 'yfinance')
            adjusted: 是否复权
            period: 数据周期
            
        Returns:
            pandas DataFrame 包含历史数据
        """
        if data_source not in self.clients:
            raise Exception(f"数据源{data_source}未配置或不可用")
        
        client = self.clients[data_source]
        
        # 根据数据源转换股票代码格式
        converted_symbol = convert_symbol_format(symbol, data_source, from_format='futu')
        
        # 验证股票代码格式（验证转换后的符号）
        if not validate_symbol_format(converted_symbol, data_source):
            raise Exception(f"股票代码{symbol}转换后的格式{converted_symbol}不符合{data_source}数据源要求")
        
        # 验证股票代码
        if not client.validate_symbol(converted_symbol):
            raise Exception(f"股票代码{converted_symbol}在数据源{data_source}中无效")
        
        # 验证日期范围
        if not client.validate_date_range(start_date, end_date):
            raise Exception(f"日期范围无效: {start_date} 到 {end_date}")
        
        return await client.get_historical_data(converted_symbol, start_date, end_date, adjusted, period)
    
    async def get_market_snapshot(
        self, 
        symbol: str, 
        data_source: str,
        adjusted: bool = True
    ) -> Dict[str, Any]:
        """
        获取市场快照数据
        
        Args:
            symbol: 股票代码（使用Futu格式，如：HK.00700, SZ.000001, US.AAPL）
            data_source: 数据源 ('futu', 'yfinance')
            adjusted: 是否复权
            
        Returns:
            字典包含市场快照数据
        """
        if data_source not in self.clients:
            raise ValueError(f"不支持的数据源: {data_source}")
        
        client = self.clients[data_source]
        
        # 根据数据源转换股票代码格式
        converted_symbol = convert_symbol_format(symbol, data_source)
        
        # 验证股票代码格式（验证转换后的符号）
        if not validate_symbol_format(converted_symbol, data_source):
            raise Exception(f"股票代码{symbol}转换后的格式{converted_symbol}不符合{data_source}数据源要求")
        
        # 验证股票代码
        if not client.validate_symbol(converted_symbol):
            raise Exception(f"股票代码{converted_symbol}在数据源{data_source}中无效")
        
        return await client.get_market_snapshot(converted_symbol, adjusted)
    
    async def get_batch_data(
        self, 
        symbols: List[str], 
        data_source: str,
        start_date: str, 
        end_date: str,
        adjusted: bool = False,
        period: str = "daily"
    ) -> Dict[str, pd.DataFrame]:
        """
        批量获取历史数据
        
        Args:
            symbols: 股票代码列表（使用Futu格式，如：HK.00700, SZ.000001, US.AAPL）
            data_source: 数据源 ('futu', 'yfinance')
            start_date: 开始日期
            end_date: 结束日期
            adjusted: 是否复权
            period: 数据周期
            
        Returns:
            字典，键为股票代码，值为对应的DataFrame
        """
        if data_source not in self.clients:
            raise ValueError(f"不支持的数据源: {data_source}")
        
        client = self.clients[data_source]
        
        # 转换股票代码格式
        converted_symbols = []
        for symbol in symbols:
            # 根据数据源转换股票代码格式
            converted_symbol = convert_symbol_format(symbol, data_source)
            
            # 验证股票代码格式（验证转换后的符号）
            if not validate_symbol_format(converted_symbol, data_source):
                raise Exception(f"股票代码{symbol}转换后的格式{converted_symbol}不符合{data_source}数据源要求")
            
            converted_symbols.append(converted_symbol)
        
        # 验证股票代码
        for symbol in converted_symbols:
            if not client.validate_symbol(symbol):
                raise Exception(f"股票代码{symbol}在数据源{data_source}中无效")
        
        # 验证日期范围
        if not client.validate_date_range(start_date, end_date):
            raise Exception(f"日期范围无效: {start_date} 到 {end_date}")
        
        return await client.get_batch_data(converted_symbols, start_date, end_date, adjusted, period)
    
    # 数据源必须明确指定
    
    async def health_check(self) -> Dict[str, bool]:
        """检查各数据源的健康状态"""
        health_status = {}
        
        for client_name, client in self.clients.items():
            try:
                is_healthy = await client.health_check()
                health_status[client_name] = is_healthy
            except Exception as e:
                print(f"检查{client_name}健康状态失败: {e}")
                health_status[client_name] = False
        
        return health_status
    
    def get_available_sources(self) -> List[str]:
        """获取可用的数据源列表"""
        return list(self.clients.keys())
    
    def get_source_info(self, source: str) -> Dict[str, Any]:
        """获取数据源信息"""
        if source not in self.clients:
            raise Exception(f"数据源{source}未配置")
        
        client = self.clients[source]
        return {
            'supported_markets': client.get_supported_markets(),
            'supported_periods': client.get_supported_periods(),
            'connected': client.connected
        }
    
    async def test_connection(self, source: str = 'all') -> Dict[str, bool]:
        """测试数据源连接"""
        test_results = {}
        
        if source == 'all':
            sources_to_test = list(self.clients.keys())
        else:
            if source not in self.clients:
                raise Exception(f"数据源{source}未配置")
            sources_to_test = [source]
        
        for source_name in sources_to_test:
            client = self.clients[source_name]
            try:
                # 测试连接
                connected = await client.connect()
                test_results[source_name] = connected
                
                # 如果连接成功，立即断开（避免保持连接）
                if connected:
                    await client.disconnect()
                    
            except Exception as e:
                print(f"测试{source_name}连接失败: {e}")
                test_results[source_name] = False
        
        return test_results