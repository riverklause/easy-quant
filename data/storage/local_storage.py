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

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

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
                            except:
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
            if merged.index.name == 'time_key' or merged.index.name == 'datetime':
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
        """
        # 移除特殊字符，确保路径安全
        safe_symbol = symbol.replace('.', '_')
        
        # 构建文件名
        if start_date and end_date:
            filename = f"{safe_symbol}_{data_type}_{start_date}_{end_date}_{source}.{format}"
        else:
            filename = f"{safe_symbol}_{data_type}_{source}.{format}"
        
        # 构建完整路径
        file_path = self.data_dir / data_type / source / filename
        
        return file_path
    
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
            # 构建搜索模式
            pattern = "*"
            
            if symbol:
                safe_symbol = symbol.replace('.', '_')
                pattern = f"{safe_symbol}_{pattern}"
            
            if data_type:
                pattern = f"{pattern}_{data_type}_{pattern}"
            
            if source:
                pattern = f"{pattern}_{source}"
            
            if format:
                pattern = f"{pattern}.{format}"
            else:
                pattern = f"{pattern}.*"
            
            # 搜索文件
            data_files = []
            for root, dirs, files in os.walk(self.data_dir):
                for file in files:
                    if file.startswith(symbol.replace('.', '_')) if symbol else True:
                        file_path = Path(root) / file
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
            # 提取文件名信息
            filename = file_path.stem
            parts = filename.split('_')
            
            info = {
                'file_path': str(file_path),
                'file_size': file_path.stat().st_size,
                'last_modified': datetime.fromtimestamp(file_path.stat().st_mtime),
                'format': file_path.suffix[1:],
                'symbol': parts[0].replace('_', '.'),
                'data_type': parts[1] if len(parts) > 1 else 'unknown',
                'source': parts[-1] if len(parts) > 2 else 'unknown'
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
            data_types = {}
            sources = {}
            
            for file_path in self.get_data_files():
                file_size = file_path.stat().st_size
                total_size += file_size
                file_count += 1
                
                # 提取数据类型和数据源信息
                info = self.get_data_info(file_path)
                data_type = info.get('data_type', 'unknown')
                source = info.get('source', 'unknown')
                
                # 更新统计信息
                data_types[data_type] = data_types.get(data_type, 0) + 1
                sources[source] = sources.get(source, 0) + 1
            
            stats = {
                'total_size': total_size,
                'file_count': file_count,
                'data_types': data_types,
                'sources': sources,
                'data_dir': str(self.data_dir)
            }
            
            return stats
        except Exception as e:
            logger.error(f"获取存储统计信息失败: {e}")
            return {}
