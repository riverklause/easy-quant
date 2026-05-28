"""
数据管理器 - 统一管理多数据源的数据获取
"""
from typing import Dict, List, Optional, Any, Union, Callable
from datetime import datetime, timedelta
import pandas as pd
import asyncio

from .sources.futu_client import FutuAPIClient
from .sources.yfinance_client import YFinanceClient
from .sources.futu_realtime import FutuRTProcessor
from .storage.local_storage import LocalStorageManager

from .base_client import BaseDataSourceClient
from utils.symbol_utils import convert_symbol_format,convert_symbols_format, validate_symbol_format, validate_symbols_format
from utils.settings import settings

class DataManager:
    """
    数据管理器 - 统一管理多数据源。
    使用方法：
    1、初始化数据管理器 datamanager = DataManager()，这个过程自动读取settings.py中的配置，并按照读取的配置初始化数据源客户端参数
    2、建立数据连接 connect= datamanager.connect_all()，建立连接并不耗费什么资源，全连接方便使用
    3、如果是实时数据源，需要注册回调数据获取函数  data_manager.register_callback('futu_RT', data_manager.on_realtime_data)
    4、获取历史数据 df = await data_manager.get_historical_data(symbol, start_date, end_date, data_source)
    5、获取历史批量数据 batch_data = await data_manager.get_batch_data(symbols, start_date, end_date, data_source)
    6、如果是实时数据源，需要订阅实时数据 data_manager.subscribe_realtime_data(data_source,symbols, data_types)
    7、从内存中读取实时数据 df = await data_manager.get_realtime_data(symbol, data_source)
    8、断开数据连接 data_manager.disconnect_all()
    """

    def __init__(self, config: Dict[str, Any] = None):
        """
        初始化数据管理器
        1、读取配置 2、定义self变量 3、初始化数据源客户端 4、初始化本地存储管理器
        Args:
            config: 配置信息，包含各数据源的配置（可选，默认从settings.py获取）
        """
        if config is None:
            config = self._get_default_config()
        self.config = config
        self.clients: Dict[str, BaseDataSourceClient] = {}
        self.connected = False
        
        # 初始化本地存储管理器
        self.storage_manager = LocalStorageManager(
            data_dir=str(settings.data.data_dir),
            cache_dir=str(settings.data.cache_dir)
        )
        
        # 初始化实时数据内存缓存（每个symbol一个大DataFrame，手动限制行数）
        self.realtime_cache: Dict[str, Dict[str, pd.DataFrame]] = {}
        self.maxlen_config = {
            'quote': 1000,
            'order_book': 1000,
            'time_share': 1000,
            'broker': 100,
            'kline': 1000,
            'ticker': 10000
        }
        for data_type in self.maxlen_config:
            self.realtime_cache[data_type] = {}
        self.lastest_data: Dict[str, Dict[str, pd.DataFrame]] = {}
        
        # 从配置中初始化可用数据源客户端
        self._init_clients()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """从settings.py获取配置并验证，如果读取失败则报错"""
        try:     
            #从settings.py获取DataConfig类的配置
            config_data = settings.data 
            # 验证DataConfig类的基础配置项
            required_fields = ['data_dir', 'cache_dir', 'update_interval']
            for field in required_fields:
                if not hasattr(config_data, field):
                    raise ImportError(f"settings.py中缺少DataConfig核心配置项: {field}")
            
            # 验证Futu与Futu_RT配置项(Futu_RT与Futu配置相同)
            required_fields = ['Futu_Host', 'Futu_Port', 'Futu_TrdEnv']
            if all(field not in config_data.futu for field in required_fields):
                raise ImportError(f"settings.py中缺少Futu配置项: {field}")
            
            # 验证yfinance配置项
            required_fields = ['yfinance_proxy']
            if all(field not in config_data.yfinance for field in required_fields):
                raise ImportError("settings.py中缺少yfinance代理配置")
            
            # 验证可用的数据源配置项
            required_fields = ['available_data_sources']
            if all(field not in config_data.available_data_sources for field in required_fields):
                raise ImportError("settings.py中缺少available_data_sources配置项")
            
            # 返回配置字典，目前有要传递给futu和yfinance客户端的配置参数和本类需要的参数
            return {
                'futu':config_data.futu,
                'yfinance':config_data.yfinance,
                'available_data_sources': config_data.available_data_sources
            }
        except ImportError as e:
            # 如果settings.py不存在或配置不完整，直接报错
            raise ImportError(f"无法从settings.py读取配置: {e}")
    
    def _init_clients(self):
        """
        从config(来自settings.py)中的available_data_sources配置项，初始化可用的数据源客户端
        初始化完成后，将客户端实例存储在self.clients字典中，键为数据源端名称，值为客户端实例
        """
        
        # 获取可用的数据源列表
        available_data_sources = self.config['available_data_sources']['available_data_sources']
        print(available_data_sources)
        # 初始化futu客户端参数
        if 'futu' in available_data_sources:
            temp_config = {**self.config['futu'], **self.config['available_data_sources']}
            self.clients['futu'] = FutuAPIClient(temp_config)
        
        # 初始化Futu实时数据客户端参数
        if 'futu_RT' in available_data_sources:
            temp_config = {**self.config['futu'], **self.config['available_data_sources']}
            self.clients['futu_RT'] = FutuRTProcessor(temp_config)
        
        # 初始化yfinance客户端参数
        if 'yfinance' in available_data_sources:
            temp_config = {**self.config['yfinance'], **self.config['available_data_sources']}

            self.clients['yfinance'] = YFinanceClient(temp_config)
        
    def connect_all(self) -> bool:
        """
        连接所有可用数据源客户端，
        返回是否所有客户端连接成功，
        如果有客户端连接失败，返回False，否则返回True，
        连接成功后，更新self.connected属性为True，
        self.clients字典中存储所有客户端完成连接
        """
        try:
            for client_name, client in self.clients.items():
                try:
                    # 根据客户端类型调用相应的方法
                    if hasattr(client, 'connect') and callable(getattr(client, 'connect')):
                        result = client.connect()  # 同步调用
                        if not result:
                            print(f"连接{client_name}失败")
                        else:
                            print(f"✅ 连接{client_name}成功")
                    else:
                        print(f"客户端{client_name}没有connect方法")
                except Exception as e:
                    print(f"连接{client_name}失败: {e}")
            
            # 检查连接状态
            print("\n🔍 检查各客户端连接状态:")
            for client_name, client in self.clients.items():
                connected_status = getattr(client, 'connected', '无connected属性')
                print(f"   {client_name}: {connected_status}")
            
            self.connected = all(getattr(client, 'connected', False) for client in self.clients.values())
            print(f"\n📊 总体连接状态: {self.connected}")
            return self.connected
            
        except Exception as e:
            print(f"连接数据源失败: {e}")
            self.connected = False
            return False
    
    def disconnect_all(self) -> bool:
        """
        断开self.clients中所有可用数据源客户端连接
        返回是否所有客户端断开成功，
        如果有客户端断开失败，返回False，否则返回True，
        断开成功后，更新self.connected属性为False
        """
        try:
            for client_name, client in self.clients.items():
                try:
                    # 根据客户端类型调用相应的方法
                    if hasattr(client, 'disconnect') and callable(getattr(client, 'disconnect')):
                        client.disconnect()  # 同步调用
                    else:
                        print(f"客户端{client_name}没有disconnect方法")
                except Exception as e:
                    print(f"断开{client_name}连接失败: {e}")
            
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
            data_source: 数据源 目前仅支持('futu', 'futu_RT', 'yfinance')
            adjusted: 是否复权，默认不复权
            period:数据周期，默认daily
            
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
        
        # 直接从数据源获取数据
        data = await client.get_historical_data(converted_symbol, start_date, end_date, adjusted, period)
        
        return data
    
    async def get_market_snapshot(
        self, 
        symbols: List[str], 
        data_source: str = 'futu'
    ) -> pd.DataFrame:
        """
        获取市场快照数据
        
        Args:
            symbols: 股票代码列表（使用Futu格式，如：HK.00700, SZ.000001, US.AAPL）
            data_source: 数据源，默认为'futu'
            
        Returns:
            pandas DataFrame 包含市场快照数据
        """
        if data_source not in self.clients:
            raise ValueError(f"不支持的数据源: {data_source}")
        
        client = self.clients[data_source]
        
        # 根据数据源转换股票代码格式
        converted_symbols = convert_symbols_format(symbols, data_source, from_format='futu')
        
        # 验证股票代码
        for converted_symbol in converted_symbols:
            if not client.validate_symbol(converted_symbol):
                raise Exception(f"股票代码{converted_symbol}在数据源{data_source}中无效")
        
        # 直接从数据源获取快照数据，不使用本地缓存
        data = await client.get_market_snapshot(converted_symbols)
        
        # 将索引从转换后的代码改回原始代码
        if not data.empty:
            # 创建转换映射
            symbol_map = {converted: original for converted, original in zip(converted_symbols, symbols)}
            # 重新索引，保持原始代码顺序
            data = data.reset_index()
            # 将转换后的代码替换为原始代码
            data['code'] = data['code'].map(symbol_map)
            # 重新设置索引
            data = data.set_index('code')
        
        return data
    
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
            start_date: 开始日期，使用字符串，格式为"YYYY-MM-DD"
            end_date: 结束日期，使用字符串，格式为"YYYY-MM-DD"
            adjusted: 是否复权
            period: 数据周期
            
        Returns:
            字典，键为股票代码，值为对应的DataFrame
        """
        if data_source not in self.clients:
            raise ValueError(f"不支持的数据源: {data_source}")
        
        client = self.clients[data_source]
        
        # 转换股票代码格式
        converted_symbols = convert_symbols_format(symbols, data_source, from_format='futu')

        # 验证股票代码
        if not validate_symbols_format(converted_symbols, data_source):
            raise Exception(f"股票代码列表{converted_symbols}转换后的格式不符合{data_source}数据源要求")
        
        # 验证日期范围
        if not client.validate_date_range(start_date, end_date):
            raise Exception(f"日期范围无效: {start_date} 到 {end_date}")
        
        # 从数据源获取批量数据
        result = {}
        
        # 创建转换映射
        symbol_map = {converted: original for converted, original in zip(converted_symbols, symbols)}
        
        # 调用客户端的批量获取方法
        fetched_data = await client.get_batch_data(converted_symbols, start_date, end_date, adjusted, period)
        
        # 处理返回的数据，根据客户端返回的格式不同进行不同处理
        if isinstance(fetched_data, dict):
            # 如果返回的是字典格式，需要将转换后的代码映射回原始代码
            for converted_symbol, data in fetched_data.items():
                if converted_symbol in symbol_map:
                    original_symbol = symbol_map[converted_symbol]
                    result[original_symbol] = data
        elif isinstance(fetched_data, pd.DataFrame) and not fetched_data.empty:
            # 如果返回的是DataFrame格式，需要按股票代码分组处理
            # 检查是否有code列或多级索引
            if 'code' in fetched_data.columns:
                # 如果code是列，按code分组
                for converted_symbol, group in fetched_data.groupby('code'):
                    if converted_symbol in symbol_map:
                        original_symbol = symbol_map[converted_symbol]
                        # 移除code列并设置时间索引
                        data = group.drop(columns=['code']).set_index('time_key')
                        result[original_symbol] = data
            elif 'code' in fetched_data.index.names:
                # 如果code是索引的一部分，按code索引级别分组
                # 获取所有唯一的转换后股票代码
                unique_converted_symbols = fetched_data.index.get_level_values('code').unique()
                for converted_symbol in unique_converted_symbols:
                    if converted_symbol in symbol_map:
                        original_symbol = symbol_map[converted_symbol]
                        try:
                            # 尝试获取该股票的数据
                            data = fetched_data.xs(converted_symbol, level='code', drop_level=False)
                            if not data.empty:
                                result[original_symbol] = data
                        except KeyError:
                            # 该股票数据不存在，跳过
                            continue
        
        return result
    
    # 数据源必须明确指定
    
    def health_check(self) -> Dict[str, bool]:
        """检查各数据源的健康状态"""
        health_status = {}
        
        for client_name, client in self.clients.items():
            try:
                is_healthy = client.health_check()
                health_status[client_name] = is_healthy
            except Exception as e:
                print(f"检查{client_name}健康状态失败: {e}")
                health_status[client_name] = False
        
        return health_status
    
    def get_available_sources(self) -> List[str]:
        """获取可用的数据源列表"""
        return list(self.clients.keys())
    
    def get_source_info(self, data_source: str) -> Dict[str, Any]:
        """获取指定数据源的详细信息"""
        if data_source not in self.clients:
            raise ValueError(f"数据源 {data_source} 不存在")
        
        client = self.clients[data_source]
        
        # 直接返回client的features属性
        if hasattr(client, 'features'):
            features = client.features
            # 将中文键名映射为英文键名以兼容测试代码
            key_mapping = {
                '数据源名称': 'data_source_name',
                '支持的市场': 'supported_markets',
                '支持的K线周期': 'supported_periods',
                '数据类型': 'data_types',
                '连接方式': 'connection_type',
                '实时数据': 'real_time_data',
                '数据频率': 'data_frequency',
                '实时数据订阅完成': 'subscription_complete',
                '回调处理设置完成': 'callback_complete',
                '可实时推送数据种类': 'realtime_data_types',
                '免费使用': 'free_to_use',
                '数据延迟': 'data_delay'
            }
            
            # 创建新的字典，将中文键名转换为英文键名
            english_features = {}
            for chinese_key, value in features.items():
                english_key = key_mapping.get(chinese_key, chinese_key)
                english_features[english_key] = value
            
            return english_features
        else:
            # 如果client没有features属性，返回默认信息
            return {
                'data_source_name': data_source,
                'supported_markets': [],
                'supported_periods': [],
                'data_types': [],
                'connection_type': 'unknown',
                'real_time_data': False,
                'data_frequency': 'unknown'
            }
    
    def on_realtime_data(self, data: pd.DataFrame):
        """
        实时数据回调处理方法 - 专门用于处理FutuRTProcessor的回调
        
        Args:
            data: 实时数据DataFrame，包含data_type和code字段
        """
        if data is None or data.empty:
            print(f"警告: 收到空的实时数据")
            return
        
        data_type = data['data_type'].iloc[0] if 'data_type' in data.columns else None
        symbol = data['code'].iloc[0] if 'code' in data.columns else None
        
        if data_type and symbol:
            self.update_realtime_data(data_type, data, symbol)
        else:
            print(f"警告: 收到无效的实时数据，缺少data_type或code字段")
    
    def update_realtime_data(self, data_type: str, data: pd.DataFrame, symbol: Optional[str] = None):
        """
        更新实时数据到内存缓存
        
        Args:
            data_type: 数据类型 ('quote', 'order_book', 'time_share', 'broker', 'kline', 'ticker')
            data: 实时数据DataFrame
            symbol: 股票代码
        """
        if data_type not in self.realtime_cache:
            raise ValueError(f"不支持的数据类型: {data_type}")
        
        if not symbol:
            raise ValueError(f"更新{data_type}数据时必须指定股票代码")
        
        maxlen = self.maxlen_config.get(data_type, 1000)
        
        if symbol not in self.realtime_cache[data_type]:
            self.realtime_cache[data_type][symbol] = pd.DataFrame()
        
        cached_df = self.realtime_cache[data_type][symbol]
        
        time_key = data['time_key'].iloc[0] if 'time_key' in data.columns else None
        
        if not cached_df.empty:
            last_time = cached_df['time_key'].iloc[-1] if 'time_key' in cached_df.columns else None # 获取缓存中最后一条的时间
            if last_time == time_key: # 时间相同：替换最后一条（更新）
                self.realtime_cache[data_type][symbol] = pd.concat(
                    [cached_df.iloc[:-1], data], ignore_index=True
                )
            else: # 时间不同：追加新数据
                self.realtime_cache[data_type][symbol] = pd.concat(
                    [cached_df, data], ignore_index=True
                )
        else: # 缓存为空：直接赋值
            self.realtime_cache[data_type][symbol] = data.copy()
        
        if len(self.realtime_cache[data_type][symbol]) > maxlen:
            self.realtime_cache[data_type][symbol] = self.realtime_cache[data_type][symbol].tail(maxlen)
        
        self.lastest_data[symbol] = self.lastest_data.get(symbol, {}) # 初始化或更新股票的最新数据字典
        self.lastest_data[symbol][data_type] = data
    
    def get_realtime_data(self, data_type: str, symbol: Optional[str] = None) -> pd.DataFrame:
        """
        从内存缓存获取实时数据
        
        Args:
            data_type: 数据类型 ('quote', 'order_book', 'time_share', 'broker', 'kline', 'ticker')
            symbol: 股票代码，用于过滤某只股票的实时数据，默认None表示返回所有
            
        Returns:
            实时数据DataFrame
        """
        if data_type not in self.realtime_cache:
            raise ValueError(f"不支持的数据类型: {data_type}")
        
        if symbol:
            return self.realtime_cache[data_type].get(symbol, pd.DataFrame())
        else:
            df_list = list(self.realtime_cache[data_type].values())
            
            if not df_list:
                return pd.DataFrame()
            
            return pd.concat(df_list, ignore_index=True)
    
    def get_lastest_data(self, data_types: List[str], symbols: Optional[list[str]] = None) -> Dict:
        """
        获取最新的实时数据
        
        Args:
            data_types: 数据类型列表 ('quote', 'order_book', 'broker', 'kline', 'ticker', 'time_share')
            symbols: 股票代码列表，默认None表示返回所有
            
        Returns:
            最新的实时数据字典
        """
        if not data_types or len(data_types) == 0 or not all(
            i in ['quote', 'order_book', 'broker', 'kline', 'ticker', 'time_share'] for i in data_types):
            raise ValueError(f"不支持的数据类型: {data_types}")

        # 根据数据类型返回最新数据
        if symbols:
            data_from_symbols = {symbol: self.lastest_data.get(symbol,{}) for symbol in symbols}
            return {k:{sk:sv for sk,sv in v.items() if sk in data_types} for k,v in data_from_symbols.items()}
        else:
            return {k:{sk:sv for sk,sv in v.items() if sk in data_types} for k,v in self.lastest_data.items()}
    
    def save_realtime_data_to_local(self, data_type: str, symbol: Optional[str] = None, trading_day: Optional[str] = None):
        """
        将实时数据保存到本地文件
        
        Args:
            data_type: 数据类型 ('quote', 'order_book', 'time_share', 'broker', 'kline', 'ticker')
            symbol: 股票代码，用于kline和ticker类型 
            trading_day: 交易日，格式：YYYY-MM-DD
            
        Returns:
            是否保存成功
        """
        import pandas as pd
        from datetime import datetime
        
        # 获取实时数据
        realtime_data = self.get_realtime_data(data_type, symbol)
        if not realtime_data:
            return False
        
        # 转换为DataFrame
        df = pd.DataFrame(realtime_data)
        if df.empty:
            return False
        
        # 确定交易日
        if not trading_day:
            trading_day = datetime.now().strftime('%Y-%m-%d')
        
        # 保存数据
        return self.storage_manager.save_data(
            data=df,
            symbol=symbol or 'ALL',
            data_type=f'realtime_{data_type}',
            start_date=trading_day,
            end_date=trading_day,
            source='futu'
        )
    
    def cleanup_old_realtime_data(self, days: int = 15):
        """
        清理过期的实时数据
        
        Args:
            days: 保留天数，默认为15个交易日
            
        Returns:
            清理的文件数量
        """
        from datetime import datetime, timedelta
        import os
        
        deleted_count = 0
        cutoff_date = datetime.now() - timedelta(days=days)
        cutoff_str = cutoff_date.strftime('%Y-%m-%d')
        
        # 遍历所有实时数据类型
        for data_type in self.realtime_cache.keys():
            # 获取相关文件
            files = self.storage_manager.get_data_files(
                data_type=f'realtime_{data_type}',
                source='futu'
            )
            
            # 删除过期文件
            for file_path in files:
                if cutoff_str in str(file_path):
                    self.storage_manager.delete_data(
                        symbol='ALL',
                        data_type=f'realtime_{data_type}',
                        source='futu',
                        start_date=cutoff_str,
                        end_date=cutoff_str
                    )
                    deleted_count += 1
        
        return deleted_count
    
    async def get_financial_statements(
        self, 
        symbol: str, 
        statement_type: str, 
        data_source: str, 
        period: str = "annual"
    ) -> pd.DataFrame:
        """
        获取财务报表数据
        
        Args:
            symbol: 股票代码（使用Futu格式，如：HK.00700, SZ.000001, US.AAPL）
            statement_type: 报表类型 (balance, income, cash_flow)
            data_source: 数据源 ('yfinance', 'futu')
            period: 报告周期 (annual, quarterly)
            
        Returns:
            财务报表数据DataFrame
        """
        if data_source not in self.clients:
            raise Exception(f"数据源{data_source}未配置或不可用")
        
        client = self.clients[data_source]
        
        # 根据数据源转换股票代码格式
        converted_symbol = convert_symbol_format(symbol, data_source, from_format='futu')
        
        # 验证股票代码格式
        if not validate_symbol_format(converted_symbol, data_source):
            raise Exception(f"股票代码{symbol}转换后的格式{converted_symbol}不符合{data_source}数据源要求")
        
        # 验证股票代码
        if not client.validate_symbol(converted_symbol):
            raise Exception(f"股票代码{converted_symbol}在数据源{data_source}中无效")
        
        # 获取财务报表数据
        data = await client.get_financial_statements(converted_symbol, statement_type, period)
        
        # 确保返回的数据使用原始股票代码
        if not data.empty:
            # 如果数据中包含code列，将其替换为原始代码
            if 'code' in data.columns:
                data['code'] = symbol
            # 如果数据中包含code作为索引，将其替换为原始代码
            elif 'code' in data.index.names:
                # 重置索引
                data = data.reset_index()
                # 将转换后的代码替换为原始代码
                data['code'] = symbol
                # 重新设置索引
                data = data.set_index(['Date', 'code'])
        
        return data
    
    async def get_financial_indicators(
        self, 
        symbol: str, 
        data_source: str, 
        period: str = "annual"
    ) -> pd.DataFrame:
        """
        获取财务指标数据
        
        Args:
            symbol: 股票代码（使用Futu格式，如：HK.00700, SZ.000001, US.AAPL）
            data_source: 数据源 ('yfinance', 'futu')
            period: 报告周期 (annual, quarterly)
            
        Returns:
            财务指标数据DataFrame
        """
        if data_source not in self.clients:
            raise Exception(f"数据源{data_source}未配置或不可用")
        
        client = self.clients[data_source]
        
        # 根据数据源转换股票代码格式
        converted_symbol = convert_symbol_format(symbol, data_source, from_format='futu')
        
        # 验证股票代码格式
        if not validate_symbol_format(converted_symbol, data_source):
            raise Exception(f"股票代码{symbol}转换后的格式{converted_symbol}不符合{data_source}数据源要求")
        
        # 验证股票代码
        if not client.validate_symbol(converted_symbol):
            raise Exception(f"股票代码{converted_symbol}在数据源{data_source}中无效")
        
        # 获取财务指标数据
        data = await client.get_financial_indicators(converted_symbol, period)
        
        # 确保返回的数据使用原始股票代码
        if not data.empty:
            # 如果数据中包含code列，将其替换为原始代码
            if 'code' in data.columns:
                data['code'] = symbol
            # 如果数据中包含code作为索引，将其替换为原始代码
            elif 'code' in data.index.names:
                # 重置索引
                data = data.reset_index()
                # 将转换后的代码替换为原始代码
                data['code'] = symbol
                # 重新设置索引
                data = data.set_index(['Date', 'code']) if 'Date' in data.columns else data.set_index('code')
        
        return data
    
    def register_callback(self, data_source: str = 'futu_RT', callback: Callable = None):
        """注册回调函数
        
        Args:
            data_source: 数据源名称
            callback: 回调函数，必须是一个可以接收字典参数的函数或对象
        """
        if data_source not in self.clients:
            raise ValueError(f"不支持的数据源: {data_source}")
        
        # 检查客户端是否支持回调注册
        if data_source != 'futu_RT':
            raise ValueError(f"数据源{data_source}不支持回调注册")

        client = self.clients[data_source]

        # 调用客户端的回调注册方法
        if callback is None:
            raise ValueError("回调函数不能为空")
        
        # 确保callback是一个绑定方法，能够直接调用
        # 如果callback是实例方法，我们需要将其绑定到self上
        import inspect
        if inspect.ismethod(callback):
            # 已经是绑定方法，可以直接使用
            bound_callback = callback
        else:
            # 是普通函数或未绑定方法，需要绑定到self上
            bound_callback = lambda data: callback(data)
        
        # 如果回调函数是DataManager的实例方法，我们需要确保它被正确绑定
        if hasattr(callback, '__self__') and callback.__self__ is None:
            # 未绑定方法，使用__get__方法绑定到self上
            bound_callback = callback.__get__(self, self.__class__)
        
        def callback_adapter(data: Dict):
            """适配层，将futu_RT客户端传递的单参数数据转换为回调函数所需的格式"""
            # 调用绑定后的回调函数
            bound_callback(data)
        
        client.register_callback(callback_adapter)
        print(f"✅ 回调函数已注册到{data_source}")

    def subscribe_realtime_data(
        self, 
        data_source: str  = 'futu_RT',
        symbols: List[str] = None,
        data_types: List[str] = ['kline', 'order_book', 'quote', 'ticker', 'time_share']
    ) -> bool:
        """订阅实时数据
        
        Args:
            data_source: 数据源名称，目前仅支持'futu_RT'
            symbols: 股票代码列表（使用Futu格式，如：HK.00700, SZ.000001, US.AAPL）
            data_types: 数据类型列表，可选['kline', 'order_book', 'quote', 'ticker', 'time_share']
            
        Returns:
            bool: 订阅成功返回True，失败返回False
        """
        if data_source not in self.clients:
            raise ValueError(f"不支持的数据源: {data_source}")
        
        if data_source != 'futu_RT':
            raise ValueError(f"实时数据订阅仅支持futu_RT数据源，当前数据源: {data_source}")
        
        client = self.clients[data_source]
        
        # 检查客户端是否支持实时数据订阅
        if not hasattr(client, 'subscribe_realtime_data') or not callable(getattr(client, 'subscribe_realtime_data')):
            raise ValueError(f"数据源{data_source}不支持实时数据订阅")
        
        try:
            # 检查symbols参数是否为None或空列表
            if symbols is None or len(symbols) == 0:
                print("⚠️  警告: 未提供股票代码列表，无法订阅实时数据")
                return False
            
            # 转换股票代码格式
            converted_symbols = convert_symbols_format(symbols, data_source, from_format='futu')
            
            # 调用客户端的实时数据订阅方法
            result = client.subscribe_realtime_data(converted_symbols, data_types)
            return result
            
        except Exception as e:
            print(f"订阅实时数据失败: {e}")
            return False
    
    def add_realtime_callback(
        self, 
        data_source: str,
        callback: Callable
    ) -> bool:
        """添加实时数据回调函数
        
        Args:
            data_source: 数据源名称，目前仅支持'futu_RT'
            callback: 回调函数，接收标准化后的实时数据字典
            
        Returns:
            bool: 添加成功返回True，失败返回False
        """
        if data_source not in self.clients:
            raise ValueError(f"不支持的数据源: {data_source}")
        
        if data_source != 'futu_RT':
            raise ValueError(f"实时数据回调仅支持futu_RT数据源，当前数据源: {data_source}")
        
        client = self.clients[data_source]
        
        # 检查客户端是否支持回调添加
        if not hasattr(client, 'add_data_callback') or not callable(getattr(client, 'add_data_callback')):
            raise ValueError(f"数据源{data_source}不支持实时数据回调")
        
        try:
            # 添加回调函数
            client.add_data_callback(callback)
            return True
            
        except Exception as e:
            print(f"添加实时数据回调失败: {e}")
            return False