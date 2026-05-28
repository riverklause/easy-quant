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
        self.proxy = config.get('yfinance_proxy')
        
        # 在初始化时统一设置代理
        if self.proxy:
            yf.set_config(proxy=self.proxy)
        
        # 设置数据源特性信息
        self.features = {
            '数据源名称': 'Yahoo Finance',
            '支持的市场': self.get_supported_markets(),
            '支持的K线周期': self.get_supported_periods(),
            '数据类型': ['历史K线数据', '批量数据'],
            '连接方式': 'HTTP API',
            '实时数据': False,
            '数据频率': '分钟级/日级',
            '实时数据订阅完成': False,
            '回调处理设置完成': False,
            '可实时推送数据种类': [],
            '免费使用': True,
            '数据延迟': '15分钟'
        }
        
    def connect(self) -> bool:
        """连接yfinance（yfinance无需显式连接）"""
        self.connected = True
        return True
    
    def disconnect(self) -> bool:
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
            
            return batch_result
            
        except Exception as e:
            raise Exception(f"获取yfinance历史数据错误: {e}")
    
    async def get_market_snapshot(
        self, 
        symbols: List[str],
    ) -> pd.DataFrame:
        """
        获取市场快照数据
        
        使用yfinance的ticker.info获取市场快照数据，包括价格数据和财务指标
        
        Args:
            symbols: 股票代码列表
            
        Returns:
            pd.DataFrame: 包含市场快照数据的DataFrame
        """
        # 导入yfinance模块
        import yfinance as yf
        
        # 准备结果列表
        results = []
        
        for symbol in symbols:
            try:
                # 获取Ticker对象
                ticker = yf.Ticker(symbol)
                
                # 获取股票信息
                info = ticker.info
                
                # 尝试多种方式获取当前价格
                current_price = None
                # 优先使用当前价格
                for field in ['currentPrice', 'regularMarketPrice', 'price', 'close', 'regularMarketClose', 'previousClose', 'regularMarketPreviousClose']:
                    if field in info and info[field] is not None:
                        current_price = info[field]
                        break
                
                snapshot_data = {
                    # 价格相关字段
                    'code': symbol,
                    'last_price': current_price,
                    'open_price': info.get('open') or info.get('regularMarketOpen'),
                    'high_price': info.get('dayHigh') or info.get('regularMarketDayHigh'),
                    'low_price': info.get('dayLow') or info.get('regularMarketDayLow'),
                    'prev_close_price': info.get('previousClose') or info.get('regularMarketPreviousClose'),
                    'volume': info.get('volume') or info.get('regularMarketVolume'),
                    'turnover': info.get('regularMarketVolume') * current_price if info.get('regularMarketVolume') and current_price else None,
                    # 财务指标字段
                    'pe_ratio': info.get('forwardPE', None),
                    'pb_ratio': info.get('priceToBook', None),
                    'ey_ratio': info.get('returnOnEquity', None),
                    'pe_ttm_ratio': info.get('trailingPE', None),
                    'dividend_ttm': info.get('dividendYield', None),
                    'dividend_ratio_ttm': info.get('dividendYield', None),
                    'dividend_lfy': info.get('dividendYield', None),
                    'dividend_lfy_ratio': info.get('dividendYield', None),
                    'total_market_val': info.get('marketCap', None),
                    'circular_market_val': info.get('floatMarketCap', None) or info.get('marketCap', None),
                    'issued_shares': info.get('sharesOutstanding', None),
                    'outstanding_shares': info.get('floatShares', None) or info.get('sharesOutstanding', None),
                    'net_profit': info.get('netIncomeToCommon', None),
                    'earning_per_share': info.get('trailingEps', None),
                    'net_asset_per_share': info.get('bookValue', None)
                }
                
                results.append(snapshot_data)
            except Exception as e:
                print(f"获取{symbol}市场快照失败: {e}")
                continue
        
        # 转换为DataFrame
        if results:
            snapshot_df = pd.DataFrame(results)
            snapshot_df.set_index(['code'], inplace=True)
            return snapshot_df
        else:
            return pd.DataFrame()
    
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
            包含各股票数据的dataframe
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

            batch_data = batch_data.stack(level=0, future_stack=True) # 转换为多级索引
            batch_data.index.names = ['time_key', 'code']
            result = self._process_dataframe(batch_data)
            result['adj_close'] = 0
            return result[['open', 'high', 'low', 'close', 'volume', 'adj_close']]
            
        except Exception as e:
            # 如果批量下载失败，直接抛出异常
            print(f"批量下载失败: {e}")
            raise e
    
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
        
        # 检查是否是Series对象（多级索引时可能是Series）
        if isinstance(df, pd.Series):
            # 如果是Series，先转换为DataFrame
            df = df.to_frame()
            # 重命名列
            df = df.rename(columns={0: 'value'})
        else:
            # 如果是DataFrame，正常重命名列
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
        # 导入yfinance模块
        import yfinance as yf
        
        # 获取Ticker对象
        ticker = yf.Ticker(symbol)
        
        # 根据报表类型获取对应的数据
        if statement_type == "balance":
            # 获取资产负债表
            data = ticker.balance_sheet
        elif statement_type == "income":
            # 获取利润表
            data = ticker.income_stmt
        elif statement_type == "cash_flow":
            # 获取现金流量表
            data = ticker.cash_flow
        else:
            # 其他情况返回空DataFrame
            data = pd.DataFrame()
        
        # 转换为统一格式
        data_reset = data.T.reset_index()
        data_reset = data_reset.rename(columns={'index': 'Date'})
        data_reset['code'] = symbol
        
        # 转换代码格式
        from utils.symbol_utils import convert_symbol_format
        data_reset['code'] = data_reset['code'].apply(convert_symbol_format, args=('yfinance', 'futu'))
        
        # 重新设置索引
        data = data_reset.set_index(['Date', 'code'])
        
        return data
    
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
            财务指标数据DataFrame
        """
        # 导入yfinance模块
        import yfinance as yf
        
        # 获取Ticker对象
        ticker = yf.Ticker(symbol)
        
        # 获取关键财务指标 - 只获取一次info，避免多次API调用
        ticker_info = ticker.info
        
        # 获取关键财务指标，包括市值、市盈率、市净率、股息率、ROE、利润率、营收增长率
        financials = {}
        
        # 获取市值
        financials['market_cap'] = ticker_info.get('marketCap', None)
        
        # 获取市盈率
        financials['pe_ratio'] = ticker_info.get('forwardPE', None)
        
        # 获取市净率
        financials['pb_ratio'] = ticker_info.get('priceToBook', None)
        
        # 获取股息率
        financials['dividend_yield'] = ticker_info.get('dividendYield', None)
        
        # 获取ROE
        financials['roe'] = ticker_info.get('returnOnEquity', None)
        
        # 获取利润率
        financials['profit_margin'] = ticker_info.get('profitMargins', None)
        
        # 获取营收增长率
        financials['revenue_growth'] = ticker_info.get('revenueGrowth', None)
        
        # 将字典转换为DataFrame
        df = pd.DataFrame.from_dict(financials, orient='index', columns=['value'])
        
        return df
    
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
