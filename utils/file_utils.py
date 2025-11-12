"""
文件操作工具模块
支持Parquet文件读写和文件管理
"""
import os
import shutil
import json
import pickle
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from pathlib import Path
from typing import Any, Dict, List, Optional

from .settings import settings
from .logger import logger

class FileUtils:
    """文件操作工具类"""
    
    def __init__(self):
        self.data_base_path = settings.DATA_BASE_PATH
    
    def ensure_dir(self, dir_path: Path) -> Path:
        """确保目录存在"""
        dir_path.mkdir(parents=True, exist_ok=True)
        return dir_path
    
    def save_parquet(self, df: pd.DataFrame, file_path: Path, 
                    partition_cols: List[str] = None, **kwargs) -> bool:
        """保存DataFrame为Parquet文件"""
        try:
            # 确保目录存在
            self.ensure_dir(file_path.parent)
            
            # 保存Parquet文件
            if partition_cols:
                # 分区保存
                table = pa.Table.from_pandas(df)
                pq.write_to_dataset(
                    table,
                    root_path=file_path.parent,
                    partition_cols=partition_cols,
                    **kwargs
                )
            else:
                # 单文件保存
                df.to_parquet(file_path, **kwargs)
            
            logger.info(f"Parquet文件保存成功: {file_path}")
            return True
        except Exception as e:
            logger.error(f"Parquet文件保存失败 {file_path}: {e}")
            return False
    
    def read_parquet(self, file_path: Path, **kwargs) -> Optional[pd.DataFrame]:
        """读取Parquet文件"""
        try:
            if file_path.is_dir():
                # 读取分区数据集
                dataset = pq.ParquetDataset(file_path, **kwargs)
                df = dataset.read().to_pandas()
            else:
                # 读取单文件
                df = pd.read_parquet(file_path, **kwargs)
            
            logger.debug(f"Parquet文件读取成功: {file_path}")
            return df
        except Exception as e:
            logger.error(f"Parquet文件读取失败 {file_path}: {e}")
            return None
    
    def save_json(self, data: Any, file_path: Path, indent: int = 2) -> bool:
        """保存JSON文件"""
        try:
            self.ensure_dir(file_path.parent)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=indent)
            
            logger.debug(f"JSON文件保存成功: {file_path}")
            return True
        except Exception as e:
            logger.error(f"JSON文件保存失败 {file_path}: {e}")
            return False
    
    def read_json(self, file_path: Path) -> Optional[Any]:
        """读取JSON文件"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            logger.debug(f"JSON文件读取成功: {file_path}")
            return data
        except Exception as e:
            logger.error(f"JSON文件读取失败 {file_path}: {e}")
            return None
    
    def save_pickle(self, data: Any, file_path: Path) -> bool:
        """保存Pickle文件"""
        try:
            self.ensure_dir(file_path.parent)
            
            with open(file_path, 'wb') as f:
                pickle.dump(data, f)
            
            logger.debug(f"Pickle文件保存成功: {file_path}")
            return True
        except Exception as e:
            logger.error(f"Pickle文件保存失败 {file_path}: {e}")
            return False
    
    def read_pickle(self, file_path: Path) -> Optional[Any]:
        """读取Pickle文件"""
        try:
            with open(file_path, 'rb') as f:
                data = pickle.load(f)
            
            logger.debug(f"Pickle文件读取成功: {file_path}")
            return data
        except Exception as e:
            logger.error(f"Pickle文件读取失败 {file_path}: {e}")
            return None
    
    def list_files(self, dir_path: Path, pattern: str = "*") -> List[Path]:
        """列出目录中的文件"""
        try:
            if not dir_path.exists():
                return []
            
            files = list(dir_path.glob(pattern))
            return sorted(files)
        except Exception as e:
            logger.error(f"文件列表获取失败 {dir_path}: {e}")
            return []
    
    def get_file_size(self, file_path: Path) -> int:
        """获取文件大小（字节）"""
        try:
            return file_path.stat().st_size
        except Exception as e:
            logger.error(f"文件大小获取失败 {file_path}: {e}")
            return 0
    
    def get_directory_size(self, dir_path: Path) -> int:
        """获取目录总大小（字节）"""
        try:
            total_size = 0
            for file_path in dir_path.rglob('*'):
                if file_path.is_file():
                    total_size += file_path.stat().st_size
            return total_size
        except Exception as e:
            logger.error(f"目录大小获取失败 {dir_path}: {e}")
            return 0
    
    def delete_file(self, file_path: Path) -> bool:
        """删除文件"""
        try:
            if file_path.exists():
                file_path.unlink()
                logger.info(f"文件删除成功: {file_path}")
                return True
            return False
        except Exception as e:
            logger.error(f"文件删除失败 {file_path}: {e}")
            return False
    
    def delete_directory(self, dir_path: Path) -> bool:
        """删除目录"""
        try:
            if dir_path.exists():
                shutil.rmtree(dir_path)
                logger.info(f"目录删除成功: {dir_path}")
                return True
            return False
        except Exception as e:
            logger.error(f"目录删除失败 {dir_path}: {e}")
            return False
    
    def copy_file(self, src_path: Path, dst_path: Path) -> bool:
        """复制文件"""
        try:
            self.ensure_dir(dst_path.parent)
            shutil.copy2(src_path, dst_path)
            logger.info(f"文件复制成功: {src_path} -> {dst_path}")
            return True
        except Exception as e:
            logger.error(f"文件复制失败 {src_path} -> {dst_path}: {e}")
            return False
    
    def move_file(self, src_path: Path, dst_path: Path) -> bool:
        """移动文件"""
        try:
            self.ensure_dir(dst_path.parent)
            shutil.move(src_path, dst_path)
            logger.info(f"文件移动成功: {src_path} -> {dst_path}")
            return True
        except Exception as e:
            logger.error(f"文件移动失败 {src_path} -> {dst_path}: {e}")
            return False

# 创建全局文件工具实例
file_utils = FileUtils()

# 便捷访问函数
def save_parquet(df: pd.DataFrame, file_path: Path, **kwargs) -> bool:
    """保存Parquet文件"""
    return file_utils.save_parquet(df, file_path, **kwargs)

def read_parquet(file_path: Path, **kwargs) -> Optional[pd.DataFrame]:
    """读取Parquet文件"""
    return file_utils.read_parquet(file_path, **kwargs)

def save_json(data: Any, file_path: Path, **kwargs) -> bool:
    """保存JSON文件"""
    return file_utils.save_json(data, file_path, **kwargs)

def list_files(dir_path: Path, pattern: str = "*") -> List[Path]:
    """列出文件"""
    return file_utils.list_files(dir_path, pattern)

def get_data_file_path(data_type: str, filename: str) -> Path:
    """获取数据文件路径"""
    return settings.DATA_BASE_PATH / data_type / filename

if __name__ == "__main__":
    # 测试文件工具功能
    test_df = pd.DataFrame({
        'symbol': ['AAPL', 'GOOGL', 'MSFT'],
        'price': [150.0, 2800.0, 300.0],
        'volume': [1000000, 500000, 800000]
    })
    
    test_file = settings.DATA_BASE_PATH / 'test' / 'test_data.parquet'
    
    # 测试保存和读取
    save_parquet(test_df, test_file)
    loaded_df = read_parquet(test_file)
    print("读取的DataFrame:")
    print(loaded_df)
    
    # 测试文件列表
    files = list_files(settings.DATA_BASE_PATH)
    print(f"数据目录文件数量: {len(files)}")