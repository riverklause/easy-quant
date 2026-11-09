"""
本地数据存储管理 - 实现数据的持久化存储和读取
"""
from json import load
import os
import pandas as pd
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
import logging
from utils.settings import settings
from ..sources.adj_close import normalize_adj_close

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 数据布局（读写路径规则的唯一来源）：
#   data/meta/{name}.parquet                                根目录元数据（股票列表、配置、状态等）
#   data/historical/{source}/{symbol}_{period}.parquet       历史K线（扁平、无日期区间）
#   data/realtime/{kind}/{source}/{symbol}_{kind}_{start}_{end}.parquet
#   data/screener/{source}/{symbol}_{period}_{start}_{end}.parquet
#   data/backtest/{source}/{symbol}_{period}_{start}_{end}.parquet
META_DIR_NAME = 'meta'
HISTORICAL_DIR_NAME = 'historical'
REALTIME_DIR_NAME = 'realtime'
SCREENER_DIR_NAME = 'screener'
BACKTEST_DIR_NAME = 'backtest'
CATEGORY_DIRS = (
    HISTORICAL_DIR_NAME,
    REALTIME_DIR_NAME,
    SCREENER_DIR_NAME,
    BACKTEST_DIR_NAME,
)
DEFAULT_HISTORICAL_PERIOD = 'daily'


class LocalStorageManager:
    """
    本地数据存储管理器 - 实现数据的持久化存储和读取
    支持Parquet和CSV格式的数据存储
    """
    
    def __init__(self, 
                 data_dir: str = None,
                 cache_dir: str = None,
                 storage_format: str = 'parquet'):
        """
        初始化本地存储管理器
        
        Args:
            data_dir: 数据存储根目录，比如'./data'
            cache_dir: 缓存目录
            storage_format: 默认存储格式 ('parquet' 或 'csv')
        """
        if not data_dir:
            self.data_dir = settings.data.data_dir
        else:
            self.data_dir = Path(data_dir)
        if not cache_dir:
            self.cache_dir = settings.data.cache_dir
        else:
            self.cache_dir = Path(cache_dir)

        self.storage_format = storage_format.lower()
        if self.storage_format not in ['parquet', 'csv']:
            raise ValueError(f"不支持的存储格式: {self.storage_format}")
        
        # 确保目录存在
        self._ensure_dirs()
    
    def _ensure_dirs(self):
        """确保存储目录存在"""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        (self.data_dir / META_DIR_NAME).mkdir(parents=True, exist_ok=True)

    def build_meta_path(self, name: str, format: Optional[str] = None) -> Path:
        """
        构建根目录元数据文件路径（单一事实来源）：data/meta/{name}.{format}

        Args:
            name: 元数据名称，如 'StockList'、'ScreenerConfig'
            format: 存储格式，默认使用管理器格式

        Returns:
            元数据文件路径
        """
        fmt = format or self.storage_format
        return self.data_dir / META_DIR_NAME / f"{name}.{fmt}"

    def _parse_data_type(self, data_type: str):
        """
        将 data_type 拆分为 (category, period)

        例: 'historical_daily' -> ('historical', 'daily')
            'realtime_quote'   -> ('realtime', 'quote')
            'historical'       -> ('historical', None)
        """
        parts = str(data_type).split('_', 1)
        category = parts[0]
        period = parts[1] if len(parts) > 1 and parts[1] else None
        return category, period

    def build_path(self,
                   category: str,
                   symbol: Optional[str] = None,
                   source: str = 'unknown',
                   period: Optional[str] = None,
                   start_date: Optional[str] = None,
                   end_date: Optional[str] = None,
                   format: Optional[str] = None) -> Path:
        """
        按数据布局构建数据文件路径（所有读写路径规则的唯一来源）

        Args:
            category: 数据类别 ('historical' / 'realtime' / 'screener' / 'backtest')
            symbol: 股票代码
            source: 数据源
            period: 周期/类型（历史K线为周期，实时为数据类型）
            start_date: 开始日期（历史K线忽略，文件名不含日期区间）
            end_date: 结束日期
            format: 存储格式

        Returns:
            文件路径
        """
        fmt = format or self.storage_format
        safe_symbol = str(symbol if symbol else 'ALL').replace('.', '_')
        source = source or 'unknown'

        if category == HISTORICAL_DIR_NAME:
            period = period or DEFAULT_HISTORICAL_PERIOD
            return self.data_dir / HISTORICAL_DIR_NAME / source / f"{safe_symbol}_{period}.{fmt}"

        if category == REALTIME_DIR_NAME:
            kind = period or 'realtime'
            if start_date and end_date:
                filename = f"{safe_symbol}_realtime_{kind}_{start_date}_{end_date}.{fmt}"
            else:
                filename = f"{safe_symbol}_realtime_{kind}.{fmt}"
            return self.data_dir / REALTIME_DIR_NAME / kind / source / filename

        # screener / backtest 以及其他类别：data/{category}/{source}/{name}.{fmt}
        name_parts = [safe_symbol, period, start_date, end_date]
        filename = '_'.join(str(p) for p in name_parts if p) + f".{fmt}"
        return self.data_dir / category / source / filename
    
    def save_data(self, 
                 data: pd.DataFrame,
                 symbol: str,
                 data_type: str = 'historical',
                 start_date: Optional[str] = None,
                 end_date: Optional[str] = None,
                 source: str = 'unknown',
                 format: Optional[str] = None) -> bool:
        """
        保存数据到本地文件
        
        Args:
            data: 要保存的数据
            symbol: 股票代码
            data_type: 数据类型 ('historical', 'realtime', 'snapshot', 'factors'等)
            start_date: 开始日期
            end_date: 结束日期
            source: 数据源
            format: 存储格式 ('parquet' 或 'csv')
            
        Returns:
            是否保存成功
        """
        try:
            if data.empty:
                logger.warning(f"尝试保存空数据: {symbol} {data_type}")
                return False
            
            # 确定存储格式
            storage_format = format or self.storage_format
            
            # 构建文件路径
            file_path = self._build_file_path(symbol, data_type, start_date, end_date, source, storage_format)
            
            # 确保父目录存在
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 保存数据
            if storage_format == 'parquet':
                data.to_parquet(file_path)
            elif storage_format == 'csv':
                data.to_csv(file_path, index=True)
            else:
                raise ValueError(f"不支持的存储格式: {storage_format}")
            
            logger.info(f"数据保存成功: {file_path}")
            return True
        except Exception as e:
            logger.error(f"保存数据失败: {e}")
            return False
    
    def _get_data_end_date(self, data: pd.DataFrame) -> Optional[datetime]:
        """
        提取数据的最后一个时间索引
        
        Args:
            data: 要检查的数据
            
        Returns:
            最后一个数据点的时间，或None如果无法提取
        """
        try:
            # 检查数据是否为空
            if data.empty:
                return None
            
            # 处理多级索引
            if isinstance(data.index, pd.MultiIndex):
                # 查找时间相关的索引级别
                time_levels = [level for level in data.index.names if 'time' in level.lower() or 'date' in level.lower()]
                if time_levels:
                    # 使用第一个找到的时间索引级别
                    last_value = data.index.get_level_values(time_levels[0])[-1]
                    # 检查是否为日期时间类型
                    if isinstance(last_value, (datetime, pd.Timestamp)):
                        return last_value
                    else:
                        return None
                else:
                    # 如果没有时间索引，返回None
                    return None
            else:
                # 单级索引
                last_value = data.index[-1]
                # 检查是否为日期时间类型
                if isinstance(last_value, (datetime, pd.Timestamp)):
                    return last_value
                else:
                    # 检查数据列中是否有时间相关列
                    time_columns = [col for col in data.columns if 'time' in col.lower() or 'date' in col.lower()]
                    if time_columns:
                        # 使用第一个找到的时间列
                        last_time_value = data[time_columns[0]].iloc[-1]
                        if isinstance(last_time_value, (datetime, pd.Timestamp, str)):
                            # 如果是字符串，尝试转换为datetime
                            try:
                                return pd.to_datetime(last_time_value)
                            except (ValueError, TypeError):
                                return None
                        return last_time_value
                    return None
        except Exception as e:
            logger.warning(f"提取数据结束时间失败: {e}")
            return None
    
    def _check_data_expiry(self, 
                          data: pd.DataFrame,
                          file_path: Path,
                          not_check_expired: bool,
                          max_age_hours: int,
                          data_type: str,
                          expiry_check_method: str = 'hybrid') -> bool:
        """
        检查数据是否过期，支持多种判断方式
        
        Args:
            data: 要检查的数据
            file_path: 文件路径
            not_check_expired: 是否关闭过期检查，True时无论数据是否过期都返回未过期（False）
            max_age_hours: 最大有效时间（小时）
            data_type: 数据类型
            expiry_check_method: 过期检查方式 ('file_time', 'data_content', 'hybrid')
            
        Returns:
            bool: 数据是否过期，过期返回True，否则返回False
        """
        # 检查是否开启过期检查，True时无论数据是否过期都返回未过期（False）
        if not_check_expired:
            return False
        
        # 历史数据默认不做数据内容过期检查（除非明确设置了expiry_check_method）
        if data_type.startswith('historical') and expiry_check_method != 'data_content':
            # 历史数据仅做文件时间检查，且默认关闭
            return False
        
        # 基于文件时间的检查
        if expiry_check_method in ['file_time', 'hybrid']:
            file_age = datetime.now() - datetime.fromtimestamp(file_path.stat().st_mtime)
            if file_age > timedelta(hours=max_age_hours):
                logger.info(f"文件已过期 ({file_age}), 需要更新: {file_path}")
                return True
        
        # 基于数据内容的检查
        if expiry_check_method in ['data_content', 'hybrid'] and not data.empty:
            # 获取数据的最后一个时间点
            last_data_date = self._get_data_end_date(data)
            if last_data_date:
                # 计算数据年龄
                data_age = datetime.now() - last_data_date
                
                # 仅对非历史数据进行数据内容过期检查
                if data_type not in ['historical']:
                    if data_age > timedelta(hours=max_age_hours):
                        logger.info(f"{data_type}数据已过期 ({data_age}), 最后更新: {last_data_date}, 需要更新: {file_path}")
                        return True
        
        return False
    
    def load_data(self, 
                 symbol: str,
                 data_type: str = 'historical',
                 start_date: Optional[str] = None,
                 end_date: Optional[str] = None,
                 source: str = 'unknown',
                 format: Optional[str] = None,
                 load_if_expired: bool = False,
                 max_age_hours: int = 24,
                 expiry_check_method: str = 'hybrid') -> Optional[pd.DataFrame]:
        """
        从本地文件加载数据
        
        Args:
            symbol: 股票代码
            data_type: 数据类型
            start_date: 开始日期
            end_date: 结束日期
            source: 数据源
            format: 存储格式
            load_if_expired: 是否在数据过期时加载,默认False,True时无论数据是否过期都会加载数据
            max_age_hours: 数据最大有效时间（小时）
            expiry_check_method: 过期检查方式 ('file_time', 'data_content', 'hybrid')
            
        Returns:
            加载的数据，或None如果加载失败
        """
        try:
            # 确定存储格式
            storage_format = format or self.storage_format
            
            # 构建文件路径
            file_path = self._build_file_path(symbol, data_type, start_date, end_date, source, storage_format)
            
            # 检查文件是否存在
            if not file_path.exists():
                logger.info(f"数据文件不存在: {file_path}")
                return None
            
            # 加载数据（先加载，再检查过期）
            if storage_format == 'parquet':
                data = pd.read_parquet(file_path)
            elif storage_format == 'csv':
                data = pd.read_csv(file_path, index_col=0, parse_dates=True)
            else:
                raise ValueError(f"不支持的存储格式: {storage_format}")
            
            # 旧文件用 0 占位 adj_close：读时归一为 NaN，避免"未知"被当成"复权价为零"
            data = normalize_adj_close(data)
            
            # 检查数据是否过期，过期的话返回None，但load_if_expired为True时无论数据是否过期都会加载数据
            if self._check_data_expiry(data, file_path, load_if_expired, max_age_hours, data_type, expiry_check_method):
                return None
            
            logger.info(f"数据加载成功: {file_path}")
            return data
        except Exception as e:
            logger.error(f"加载数据失败: {e}")
            return None
    
    def merge_data(self, 
                  existing_data: pd.DataFrame,
                  new_data: pd.DataFrame,
                  on_columns: Optional[List[str]] = None) -> pd.DataFrame:
        """
        合并现有数据和新数据
        
        Args:
            existing_data: 现有数据
            new_data: 新数据
            on_columns: 用于合并的列名
            
        Returns:
            合并后的数据
        """
        try:
            if existing_data.empty:
                return new_data
            
            if new_data.empty:
                return existing_data
            
            # 使用索引合并
            if on_columns is None:
                # 合并并去重
                merged = pd.concat([existing_data, new_data])
                merged = merged[~merged.index.duplicated(keep='last')]
            else:
                # 使用指定列合并
                merged = pd.merge(existing_data, new_data, on=on_columns, how='outer')
            
            # 按索引排序
            index_names = merged.index.names if isinstance(merged.index, pd.MultiIndex) else [merged.index.name]
            if any(name in ('time_key', 'datetime') for name in index_names if name):
                merged = merged.sort_index()
            
            return merged
        except Exception as e:
            logger.error(f"合并数据失败: {e}")
            return existing_data
    
    def update_data(self, 
                   new_data: pd.DataFrame,
                   symbol: str,
                   data_type: str = 'historical',
                   start_date: Optional[str] = None,
                   end_date: Optional[str] = None,
                   source: str = 'unknown',
                   format: Optional[str] = None) -> bool:
        """
        更新本地数据文件，合并现有数据和新数据
        
        Args:
            new_data: 新数据
            symbol: 股票代码
            data_type: 数据类型
            start_date: 开始日期
            end_date: 结束日期
            source: 数据源
            format: 存储格式
            
        Returns:
            是否更新成功
        """
        try:
            if new_data.empty:
                logger.warning(f"尝试更新空数据: {symbol} {data_type}")
                return False
            
            # 加载现有数据
            existing_data = self.load_data(
                symbol=symbol,
                data_type=data_type,
                start_date=start_date,
                end_date=end_date,
                source=source,
                format=format
            )
            
            if existing_data is None:
                # 没有现有数据，直接保存
                return self.save_data(
                    data=new_data,
                    symbol=symbol,
                    data_type=data_type,
                    start_date=start_date,
                    end_date=end_date,
                    source=source,
                    format=format
                )
            else:
                # 合并数据
                merged_data = self.merge_data(existing_data, new_data)
                
                # 保存合并后的数据
                return self.save_data(
                    data=merged_data,
                    symbol=symbol,
                    data_type=data_type,
                    start_date=start_date,
                    end_date=end_date,
                    source=source,
                    format=format
                )
        except Exception as e:
            logger.error(f"更新数据失败: {e}")
            return False
    
    def delete_data(self, 
                   symbol: str,
                   data_type: str = 'historical',
                   start_date: Optional[str] = None,
                   end_date: Optional[str] = None,
                   source: str = 'unknown',
                   format: Optional[str] = None) -> bool:
        """
        删除本地数据文件
        
        Args:
            symbol: 股票代码
            data_type: 数据类型
            start_date: 开始日期
            end_date: 结束日期
            source: 数据源
            format: 存储格式
            
        Returns:
            是否删除成功
        """
        try:
            storage_format = format or self.storage_format
            file_path = self._build_file_path(symbol, data_type, start_date, end_date, source, storage_format)
            
            if file_path.exists():
                file_path.unlink()
                logger.info(f"数据文件删除成功: {file_path}")
                return True
            else:
                logger.warning(f"尝试删除不存在的数据文件: {file_path}")
                return False
        except Exception as e:
            logger.error(f"删除数据文件失败: {e}")
            return False
    
    def _build_file_path(self, 
                        symbol: str,
                        data_type: str,
                        start_date: Optional[str] = None,
                        end_date: Optional[str] = None,
                        source: str = 'unknown',
                        format: str = 'parquet') -> Path:
        """
        构建数据文件路径
        
        Args:
            symbol: 股票代码
            data_type: 数据类型
            start_date: 开始日期
            end_date: 结束日期
            source: 数据源
            format: 存储格式
            
        Returns:
            文件路径

        说明：保留 data_type 入参以兼容既有调用，实际路径规则统一由 build_path 决定。
        """
        category, period = self._parse_data_type(data_type)
        return self.build_path(
            category=category,
            symbol=symbol,
            source=source,
            period=period,
            start_date=start_date,
            end_date=end_date,
            format=format,
        )
    
    def get_data_files(self, 
                      symbol: Optional[str] = None,
                      data_type: Optional[str] = None,
                      source: Optional[str] = None,
                      format: Optional[str] = None) -> List[Path]:
        """
        获取符合条件的数据文件列表
        
        Args:
            symbol: 股票代码
            data_type: 数据类型
            source: 数据源
            format: 存储格式
            
        Returns:
            符合条件的文件路径列表
        """
        try:
            fmt = format or self.storage_format
            safe_symbol = symbol.replace('.', '_') if symbol else None

            # 依据 data_type 确定搜索根目录（类别/实时类型）
            if data_type:
                category, period = self._parse_data_type(data_type)
                if category == REALTIME_DIR_NAME and period:
                    root = self.data_dir / REALTIME_DIR_NAME / period
                else:
                    root = self.data_dir / category
            else:
                root = self.data_dir

            if not root.exists():
                return []

            data_files = []
            for file_path in root.rglob(f"*.{fmt}"):
                # 排除元数据目录
                if META_DIR_NAME in file_path.relative_to(self.data_dir).parts:
                    continue
                if safe_symbol and not file_path.name.startswith(safe_symbol):
                    continue
                if source and source not in file_path.relative_to(self.data_dir).parts:
                    continue
                data_files.append(file_path)

            return data_files
        except Exception as e:
            logger.error(f"获取数据文件列表失败: {e}")
            return []
    
    def get_data_info(self, 
                     file_path: Path) -> Dict[str, Any]:
        """
        获取数据文件信息
        
        Args:
            file_path: 文件路径
            
        Returns:
            数据文件信息
        """
        try:
            # 依据相对路径解析类别/数据源（路径规则见模块顶部说明）
            rel_parts = file_path.relative_to(self.data_dir).parts
            category = rel_parts[0] if len(rel_parts) > 1 else 'root'
            source = rel_parts[-2] if len(rel_parts) >= 3 else 'unknown'

            info = {
                'file_path': str(file_path),
                'file_size': file_path.stat().st_size,
                'last_modified': datetime.fromtimestamp(file_path.stat().st_mtime),
                'format': file_path.suffix[1:],
                'category': category,
                'source': source,
            }
            
            return info
        except Exception as e:
            logger.error(f"获取数据文件信息失败: {e}")
            return {}
    
    def clear_old_data(self, 
                      days: int = 30,
                      data_type: Optional[str] = None,
                      source: Optional[str] = None) -> int:
        """
        清理旧数据文件
        
        Args:
            days: 保留最近多少天的数据
            data_type: 数据类型
            source: 数据源
            
        Returns:
            清理的文件数量
        """
        try:
            deleted_count = 0
            cutoff_date = datetime.now() - timedelta(days=days)
            
            for file_path in self.get_data_files(data_type=data_type, source=source):
                last_modified = datetime.fromtimestamp(file_path.stat().st_mtime)
                if last_modified < cutoff_date:
                    file_path.unlink()
                    deleted_count += 1
                    logger.info(f"清理旧数据文件: {file_path}")
            
            return deleted_count
        except Exception as e:
            logger.error(f"清理旧数据失败: {e}")
            return 0
    
    def get_storage_stats(self) -> Dict[str, Any]:
        """
        获取存储统计信息
        
        Returns:
            存储统计信息
        """
        try:
            total_size = 0
            file_count = 0
            categories = {}
            sources = {}
            
            for file_path in self.get_data_files():
                file_size = file_path.stat().st_size
                total_size += file_size
                file_count += 1
                
                # 提取类别和数据源信息
                info = self.get_data_info(file_path)
                category = info.get('category', 'unknown')
                source = info.get('source', 'unknown')
                
                # 更新统计信息
                categories[category] = categories.get(category, 0) + 1
                sources[source] = sources.get(source, 0) + 1
            
            stats = {
                'total_size': total_size,
                'file_count': file_count,
                'categories': categories,
                'sources': sources,
                'data_dir': str(self.data_dir)
            }
            
            return stats
        except Exception as e:
            logger.error(f"获取存储统计信息失败: {e}")
            return {}
