"""
Futu API数据源客户端
"""
import asyncio
import time
from typing import Dict, List, Optional, Any
from datetime import datetime
import pandas as pd
import futu as ft
from futu import Market, SecurityType, SimpleFilter, AccumulateFilter, StockField, SortDir, RET_OK
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
        
        # 设置数据源特性信息
        self.features = {
            '数据源名称': 'Futu API',
            '支持的市场': self.get_supported_markets(),
            '支持的K线周期': self.get_supported_periods(),
            '数据类型': ['历史K线数据', '市场快照数据', '批量数据', '复权因子数据'],
            '连接方式': 'OpenD API',
            '实时数据': False,
            '数据频率': '分钟级/日级',
            '实时数据订阅完成': False,
            '回调处理设置完成': False,
            '可实时推送数据种类': [],
            '免费使用': '免费但有限制',
            '数据延迟': '较小延迟'
        }
        
    def connect(self) -> bool:
        """连接Futu API
        
        建立与Futu OpenD服务的连接，创建行情和交易上下文。
        
        Returns:
            bool: 连接成功返回True，失败返回False
            
        Raises:
            Exception: 连接过程中出现错误时抛出异常
        """
        try:
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

    def disconnect(self) -> bool:
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
                autype=ft.AuType.QFQ if adjusted else ft.AuType.NONE,
                fields=[ft.KL_FIELD.ALL]
            )
            
            if ret == RET_OK:
                df: pd.DataFrame = data
                df['time_key'] = pd.to_datetime(df['time_key'])
                
                # 设置多级索引(time_key, code)
                df.set_index(['time_key', 'code'], inplace=True)
                df['adj_close'] = 0
                return df[['open', 'high', 'low', 'close', 'volume', 'adj_close']]
            else:
                raise Exception(f"Futu获取历史数据失败: {data}")
                
        except Exception as e:
            raise Exception(f"获取Futu历史数据错误: {e}")
    
    async def get_market_snapshot(
        self, 
        symbols: List[str]
    ) -> pd.DataFrame:
        """获取市场快照数据
        
        从Futu API获取指定股票的市场快照数据（非实时推送数据）。
        
        Args:
            symbols (List[str]): 股票代码列表，Futu格式（如：HK.00700, US.AAPL）
            
        Returns:
            pd.DataFrame: 包含市场快照数据的DataFrame
        Raises:
            ConnectionError: 客户端未连接时抛出
            Exception: 数据获取过程中出现错误时抛出
        """
        if not self.connected:
            raise ConnectionError("Futu客户端未连接")
        
        try:
            # 获取实时快照
            ret, data = self.quote_ctx.get_market_snapshot(symbols)
            
            if ret == RET_OK and len(data) > 0:
                # 获取价格相关字段和财务指标字段
                snapshot = data[[
                    'code', 'last_price', 'open_price', 'high_price', 'low_price', 
                    'prev_close_price', 'volume', 'turnover', 
                    # 财务指标字段
                    'pe_ratio', 'pb_ratio', 'ey_ratio', 'pe_ttm_ratio',
                    'dividend_ttm', 'dividend_ratio_ttm', 'dividend_lfy', 'dividend_lfy_ratio',
                    'total_market_val', 'circular_market_val',
                    'issued_shares', 'outstanding_shares',
                    'net_profit', 'earning_per_share', 'net_asset_per_share'
                ]]
                snapshot.set_index(['code'], inplace=True)
                       
                return snapshot
            else:
                raise Exception(f"Futu获取实时数据失败: {data}")
                
        except Exception as e:
            raise Exception(f"获取Futu实时数据错误: {e}")
    
    async def get_batch_data(
        self, 
        symbols: List[str], 
        start_date: str, 
        end_date: str,
        adjusted: bool = False,
        period: str = 'daily'
    ) -> pd.DataFrame:
        """批量获取Futu数据
        
        并发获取多个股票的历史数据，提高数据获取效率。
        
        Args:
            symbols (List[str]): 股票代码列表，支持Futu格式
            start_date (str): 开始日期，格式：YYYY-MM-DD
            end_date (str): 结束日期，格式：YYYY-MM-DD
            adjusted (bool): 是否复权，默认False（不复权）
            
        Returns:
            pd.DataFrame: 包含所有股票数据的DataFrame，使用多级索引(time_key, code)
            
        Raises:
            ConnectionError: 客户端未连接时抛出
            Exception: 数据获取过程中出现错误时抛出
        """
        results = []
        
        # 使用异步方式并发获取
        tasks = []
        for symbol in symbols:
            task = self.get_historical_data(symbol, start_date, end_date, adjusted, period)
            tasks.append(task)
        
        # 等待所有任务完成
        completed_tasks = await asyncio.gather(*tasks, return_exceptions=True)
        
        for i, result in enumerate(completed_tasks):
            symbol = symbols[i]
            if isinstance(result, Exception):
                print(f"获取{symbol}数据失败: {result}")
            elif not result.empty:

                result = result.reset_index()
                result = result.set_index(['time_key', 'code'])
                results.append(result)
        
        # 垂直合并所有数据
        if results:
            combined_df = pd.concat(results, axis=0)
            # 对索引进行排序：先按time_key排序，然后按code排序
            combined_df = combined_df.sort_index(level=['time_key', 'code'])
            return combined_df
        else:
            return pd.DataFrame()
    
    def get_supported_markets(self) -> List[str]:
        """获取Futu支持的市场列表
        
        返回Futu API支持的股票市场类型。
        
        Returns:
            List[str]: 支持的市场列表，包含：HK, US, SG, TW
        """
        return ['HK', 'US', 'SG', 'TW']
    
    def get_supported_periods(self) -> List[str]:
        """获取Futu支持的K线周期列表
        
        返回Futu API支持的K线数据周期类型。
        
        Returns:
            List[str]: 支持的K线周期列表，包含：1min, 5min, 15min, 30min, 60min, daily, weekly, monthly
        """
        return ['1min', '5min', '15min', '30min', '60min', 'daily', 'weekly', 'monthly']
    
    async def get_financial_statements(
        self, 
        symbol: str, 
        statement_type: str, 
        period: str = "annual"
    ) -> pd.DataFrame:
        """
        获取财务报表数据
        
        Args:
            symbol: 股票代码
            statement_type: 报表类型 (balance, income, cash_flow)
            period: 报告周期 (annual, quarterly)
            
        Returns:
            财务报表数据
        """
        # Futu API不直接支持获取财务报表数据
        # 返回空DataFrame
        return pd.DataFrame()
    
    async def get_financial_indicators(
        self, 
        symbol: str, 
        period: str = "annual"
    ) -> pd.DataFrame:
        """
        获取财务指标数据
        
        Args:
            symbol: 股票代码
            period: 报告周期 (annual, quarterly)
            
        Returns:
            财务指标数据
        """
        if not self.connected:
            raise ConnectionError("Futu客户端未连接")
        
        try:
            # 使用get_market_snapshot获取财务指标数据
            snapshot_data = await self.get_market_snapshot([symbol])
            
            if snapshot_data is not None and not snapshot_data.empty:
                # 获取指定股票的快照数据
                stock_data = snapshot_data.loc[symbol]
                
                # 提取财务指标，转换为与yfinance客户端一致的格式
                financial_indicators = {
                    # 市值
                    'market_cap': stock_data.get('total_market_val', None),
                    # 市盈率
                    'pe_ratio': stock_data.get('pe_ratio', None),
                    # 市净率
                    'pb_ratio': stock_data.get('pb_ratio', None),
                    # 股息率
                    'dividend_yield': stock_data.get('dividend_ratio_ttm', None),
                    # ROE - 从ey_ratio（收益率）获取
                    'roe': stock_data.get('ey_ratio', None),
                    # 每股盈利
                    'earning_per_share': stock_data.get('earning_per_share', None),
                    # 每股净资产
                    'net_asset_per_share': stock_data.get('net_asset_per_share', None),
                    # 净利润
                    'net_profit': stock_data.get('net_profit', None),
                    # 总股本
                    'issued_shares': stock_data.get('issued_shares', None),
                    # 流通股本
                    'outstanding_shares': stock_data.get('outstanding_shares', None),
                    # 流通市值
                    'circular_market_val': stock_data.get('circular_market_val', None),
                    # 市盈率TTM
                    'pe_ttm_ratio': stock_data.get('pe_ttm_ratio', None),
                    # TTM股息
                    'dividend_ttm': stock_data.get('dividend_ttm', None),
                    # LFY股息
                    'dividend_lfy': stock_data.get('dividend_lfy', None),
                    # LFY股息率
                    'dividend_lfy_ratio': stock_data.get('dividend_lfy_ratio', None)
                }
                
                # 将字典转换为DataFrame
                df = pd.DataFrame.from_dict(financial_indicators, orient='index', columns=['value'])
                return df
            else:
                return pd.DataFrame()
                
        except Exception as e:
            print(f"获取Futu财务指标数据错误: {e}")
            return pd.DataFrame()
    
    def _convert_period(self, period: str) -> int:
        """转换周期参数为Futu格式
        
        将字符串格式的周期参数转换为Futu API使用的枚举类型。
        
        Args:
            period (str): 周期参数，如：1min, 5min, daily等
            
        Returns:
            int: 对应的Futu API周期枚举值
        """
        period_mapping = {
            '1min': ft.KLType.K_1M,
            '5min': ft.KLType.K_5M,
            '15min': ft.KLType.K_15M,
            '30min': ft.KLType.K_30M,
            '60min': ft.KLType.K_60M,
            'daily': ft.KLType.K_DAY,
            'weekly': ft.KLType.K_WEEK,
            'monthly': ft.KLType.K_MON
        }
        return period_mapping.get(period, ft.KLType.K_DAY)  # 默认日线

    async def get_rehab_factors(self, symbol: str) -> pd.DataFrame:
        """获取复权因子数据
        
        从Futu API获取指定股票的复权因子数据，用于价格复权计算。
        
        Args:
            symbol (str): 股票代码，支持Futu格式（如：HK.00700, US.AAPL）
            
        Returns:
            Tuple[bool, pd.DataFrame]: 包含复权因子数据的DataFrame，包含以下字段：
                - ex_div_date: 除权除息日
                - split_ratio: 拆合股比例
                - per_cash_div: 每股派现
                - per_share_div_ratio: 送股比例
                - per_share_trans_ratio: 转增股比例
                - allotment_ratio: 配股比例
                - allotment_price: 配股价
                - stk_spo_ratio: 增发比例
                - stk_spo_price: 增发价格
                - spin_off_ratio: 分立比例
                - forward_adj_factorA: 前复权因子A
                - forward_adj_factorB: 前复权因子B
                - backward_adj_factorA: 后复权因子A
                - backward_adj_factorB: 后复权因子B
                
        Raises:
            ConnectionError: 客户端未连接时抛出
            Exception: 数据获取过程中出现错误时抛出
            
        Note:
            - 前复权价格 = 不复权价格 × 前复权因子A + 前复权因子B
            - 后复权价格 = 不复权价格 × 后复权因子A + 后复权因子B
            - 接口限制：每30秒内最多请求60次，在调用时需要注意频率控制
        """
        if not self.connected:
            raise ConnectionError("Futu客户端未连接")
        
        try:
            # 调用Futu API获取复权因子
            ret, data = self.quote_ctx.get_rehab(symbol)
            
            if ret == RET_OK:
                df: pd.DataFrame = data
                
                # 确保日期格式正确
                if 'ex_div_date' in df.columns:
                    df['ex_div_date'] = pd.to_datetime(df['ex_div_date'])
                
                # 设置索引为除权除息日
                if 'ex_div_date' in df.columns:
                    df.set_index('ex_div_date', inplace=True)
                
                return True, df
            else:
                return False, pd.DataFrame()
                
        except Exception as e:
            raise Exception(f"获取Futu复权因子错误: {e}")

    async def get_adjusted_price(self, symbol: str, raw_price: float, target_date: str = None, adjust_type: str = 'forward') -> float:
        """计算复权价格
        
        使用复权因子计算指定股票的复权价格，支持按时间点选择复权因子。
        
        Args:
            symbol (str): 股票代码
            raw_price (float): 原始价格（不复权价格）
            target_date (str, optional): 目标日期（YYYY-MM-DD格式），如果为None则使用最新复权因子
            adjust_type (str): 复权类型，可选：'forward'（前复权）或 'backward'（后复权）
            
        Returns:
            float: 复权后的价格
            
        Raises:
            Exception: 复权因子获取失败或计算错误时抛出
            
        Note:
            - 复权因子选择逻辑：选择目标日期之前（含）的最新复权因子
            - 如果target_date为None，则使用最新的复权因子
            - 如果目标日期早于所有复权因子日期，则返回原始价格
        """
        try:
            # 获取复权因子
            rehab_factors = await self.get_rehab_factors(symbol)
            
            if rehab_factors.empty:
                return raw_price  # 没有复权因子，返回原价
            
            # 选择复权因子
            if target_date is None:
                # 使用最新的复权因子
                factors = rehab_factors.iloc[-1]
            else:
                # 转换为datetime格式
                target_dt = pd.to_datetime(target_date)
                
                # 选择目标日期之前（含）的最新复权因子
                valid_factors = rehab_factors[rehab_factors.index <= target_dt]
                
                if valid_factors.empty:
                    # 目标日期早于所有复权因子，返回原始价格
                    return raw_price
                else:
                    factors = valid_factors.iloc[-1]
            
            # 计算复权价格
            if adjust_type == 'forward':
                # 前复权：价格 = 原价 × 因子A + 因子B
                factor_a = factors.get('forward_adj_factorA', 1.0)
                factor_b = factors.get('forward_adj_factorB', 0.0)
                adjusted_price = raw_price * factor_a + factor_b
            else:
                # 后复权：价格 = 原价 × 因子A + 因子B
                factor_a = factors.get('backward_adj_factorA', 1.0)
                factor_b = factors.get('backward_adj_factorB', 0.0)
                adjusted_price = raw_price * factor_a + factor_b
            
            return adjusted_price
            
        except Exception as e:
            raise Exception(f"计算复权价格错误: {e}")

    def get_stock_basicinfo(self, market: Market = Market.HK, stock_type: SecurityType = SecurityType.STOCK): 
        """
        指定市场指定证券类型的所有证券静态信息
        ，market：市场代码，使用的是富途api的市场代码，默认HK 港股
        ，stock_type：证券类型，使用的是富途api的证券类型代码，默认STOCK
        ，return：返回所有证券静态信息DataFrame
        """

        ret, data = self.quote_ctx.get_stock_basicinfo(market=market, stock_type=stock_type)
        if ret == RET_OK:
            data = data[data['delisting']==False]
            return True,data
        else:
            return False,pd.DataFrame()
    
    def get_basicfiltered_stocks(self,marketcode:Market = Market.HK) -> list: #快速过滤出10天交易量在HKD一亿 价格在HKD1以上的股票
        """
        过滤出市值大于10亿，换手率大于0.05%的股票
        ，marketcode：市场代码，使用的是富途api的市场代码，默认HK
        ，return：返回过滤后股票代码列表,股票名称字典
        """
        simple_filter = SimpleFilter()
        simple_filter.filter_min = 10*(10000*10000)
        # simple_filter.filter_max = 10000*(10000*10000)
        simple_filter.stock_field = StockField.MARKET_VAL
        simple_filter.is_no_filter = False

        accumulate_filter = AccumulateFilter()
        accumulate_filter.filter_min = 0.05
        accumulate_filter.stock_field = StockField.TURNOVER_RATE
        accumulate_filter.is_no_filter = False
        accumulate_filter.sort = SortDir.ASCEND
        accumulate_filter.days = 10

        nBegin = 0
        last_page = False
        ret_list = list()
        filtered_list = []
        filtered_dict = {}
        while not last_page:
            nBegin += len(ret_list)
            ret, ls = self.quote_ctx.get_stock_filter(market=marketcode, filter_list=[simple_filter,accumulate_filter], begin=nBegin)
            if ret == RET_OK:
                last_page, all_count, ret_list = ls
                for item in ret_list: #item是ft.StockFilterItem对象
                    filtered_list.append(item.stock_code)
                    filtered_dict[item.stock_code] = item.stock_name
            else:
                break
            time.sleep(3)
        filtered_list = sorted(filtered_list)

        if not filtered_list or  not isinstance(filtered_list, list):
            return False, [], {}
        return True, filtered_list, filtered_dict