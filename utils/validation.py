"""
数据验证模块
支持数据质量检查和验证规则
"""
import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional, Callable
from datetime import datetime

from .logger import logger

class ValidationUtils:
    """数据验证工具类"""
    
    def __init__(self):
        self.validation_rules = {}
        self.custom_validators = {}
    
    def validate_dataframe(self, df: pd.DataFrame, 
                         rules: Dict[str, List[Callable]] = None) -> Dict[str, Any]:
        """验证DataFrame数据质量"""
        validation_results = {
            'is_valid': True,
            'errors': [],
            'warnings': [],
            'summary': {}
        }
        
        # 基本数据质量检查
        basic_checks = self._perform_basic_checks(df)
        validation_results['errors'].extend(basic_checks['errors'])
        validation_results['warnings'].extend(basic_checks['warnings'])
        
        # 自定义规则检查
        if rules:
            custom_checks = self._perform_custom_checks(df, rules)
            validation_results['errors'].extend(custom_checks['errors'])
            validation_results['warnings'].extend(custom_checks['warnings'])
        
        # 更新验证状态
        validation_results['is_valid'] = len(validation_results['errors']) == 0
        
        # 生成摘要
        validation_results['summary'] = {
            'total_rows': len(df),
            'total_columns': len(df.columns),
            'error_count': len(validation_results['errors']),
            'warning_count': len(validation_results['warnings']),
            'missing_values': df.isnull().sum().sum(),
            'duplicate_rows': df.duplicated().sum()
        }
        
        logger.info(f"数据验证完成，有效性: {validation_results['is_valid']}")
        return validation_results
    
    def _perform_basic_checks(self, df: pd.DataFrame) -> Dict[str, List[str]]:
        """执行基本数据质量检查"""
        errors = []
        warnings = []
        
        # 检查DataFrame是否为空
        if df.empty:
            errors.append("DataFrame为空")
            return {'errors': errors, 'warnings': warnings}
        
        # 检查列名是否有效
        invalid_cols = [col for col in df.columns if not isinstance(col, str) or col.strip() == '']
        if invalid_cols:
            errors.append(f"存在无效列名: {invalid_cols}")
        
        # 检查数据类型
        for col in df.columns:
            # 检查数值列的异常值
            if pd.api.types.is_numeric_dtype(df[col]):
                if df[col].isnull().all():
                    warnings.append(f"数值列 '{col}' 全部为缺失值")
                elif df[col].nunique() == 1:
                    warnings.append(f"数值列 '{col}' 只有一个唯一值")
        
        # 检查缺失值比例
        missing_ratio = df.isnull().sum() / len(df)
        high_missing_cols = missing_ratio[missing_ratio > 0.5].index.tolist()
        if high_missing_cols:
            warnings.append(f"以下列缺失值比例超过50%: {high_missing_cols}")
        
        # 检查重复行
        duplicate_count = df.duplicated().sum()
        if duplicate_count > 0:
            warnings.append(f"存在 {duplicate_count} 个重复行")
        
        return {'errors': errors, 'warnings': warnings}
    
    def _perform_custom_checks(self, df: pd.DataFrame, 
                              rules: Dict[str, List[Callable]]) -> Dict[str, List[str]]:
        """执行自定义验证规则"""
        errors = []
        warnings = []
        
        for col, validators in rules.items():
            if col not in df.columns:
                errors.append(f"验证规则指定的列 '{col}' 不存在")
                continue
            
            for validator in validators:
                try:
                    result = validator(df[col])
                    if not result:
                        errors.append(f"列 '{col}' 验证失败")
                except Exception as e:
                    errors.append(f"列 '{col}' 验证器执行错误: {e}")
        
        return {'errors': errors, 'warnings': warnings}
    
    def validate_stock_data(self, df: pd.DataFrame) -> Dict[str, Any]:
        """验证股票数据质量"""
        stock_rules = {
            'required_columns': ['open', 'high', 'low', 'close', 'volume'],
            'price_checks': [
                lambda col: col.min() > 0,  # 价格必须为正数
                lambda col: col.isnull().sum() == 0  # 价格不能有缺失值
            ],
            'volume_checks': [
                lambda col: col.min() >= 0  # 成交量不能为负数
            ]
        }
        
        validation_results = {
            'is_valid': True,
            'errors': [],
            'warnings': [],
            'missing_columns': []
        }
        
        # 检查必需列
        missing_cols = [col for col in stock_rules['required_columns'] 
                       if col not in df.columns]
        if missing_cols:
            validation_results['errors'].append(f"缺少必需列: {missing_cols}")
            validation_results['missing_columns'] = missing_cols
        
        # 价格数据验证
        for price_col in ['open', 'high', 'low', 'close']:
            if price_col in df.columns:
                if df[price_col].min() <= 0:
                    validation_results['errors'].append(f"{price_col} 价格必须为正数")
                if df[price_col].isnull().any():
                    validation_results['errors'].append(f"{price_col} 价格存在缺失值")
        
        # 成交量验证
        if 'volume' in df.columns:
            if df['volume'].min() < 0:
                validation_results['errors'].append("成交量不能为负数")
        
        # 高低价逻辑验证
        if all(col in df.columns for col in ['high', 'low', 'open', 'close']):
            invalid_high_low = df[df['high'] < df['low']]
            if len(invalid_high_low) > 0:
                validation_results['errors'].append("存在高价低于低价的数据")
            
            invalid_price_range = df[(df['high'] < df['open']) | (df['high'] < df['close']) |
                                   (df['low'] > df['open']) | (df['low'] > df['close'])]
            if len(invalid_price_range) > 0:
                validation_results['errors'].append("价格范围逻辑错误")
        
        validation_results['is_valid'] = len(validation_results['errors']) == 0
        
        logger.info(f"股票数据验证完成，有效性: {validation_results['is_valid']}")
        return validation_results
    
    def validate_time_series(self, df: pd.DataFrame, 
                           time_col: str = 'datetime') -> Dict[str, Any]:
        """验证时间序列数据"""
        validation_results = {
            'is_valid': True,
            'errors': [],
            'warnings': [],
            'time_gaps': []
        }
        
        if time_col not in df.columns:
            validation_results['errors'].append(f"时间列 '{time_col}' 不存在")
            validation_results['is_valid'] = False
            return validation_results
        
        # 转换为时间类型
        try:
            time_series = pd.to_datetime(df[time_col])
        except Exception as e:
            validation_results['errors'].append(f"时间列转换失败: {e}")
            validation_results['is_valid'] = False
            return validation_results
        
        # 检查时间顺序
        if not time_series.is_monotonic_increasing:
            validation_results['warnings'].append("时间序列不是单调递增")
        
        # 检查时间间隔
        time_diffs = time_series.diff().dropna()
        if len(time_diffs) > 0:
            unique_intervals = time_diffs.unique()
            if len(unique_intervals) > 1:
                validation_results['warnings'].append("时间间隔不一致")
            
            # 检测时间间隔异常
            median_interval = time_diffs.median()
            outlier_threshold = median_interval * 3
            time_gaps = time_diffs[time_diffs > outlier_threshold]
            if len(time_gaps) > 0:
                validation_results['time_gaps'] = time_gaps.tolist()
                validation_results['warnings'].append(f"检测到 {len(time_gaps)} 个时间间隔异常")
        
        validation_results['is_valid'] = len(validation_results['errors']) == 0
        
        logger.info(f"时间序列验证完成，有效性: {validation_results['is_valid']}")
        return validation_results
    
    def add_custom_validator(self, name: str, validator: Callable):
        """添加自定义验证器"""
        self.custom_validators[name] = validator
        logger.debug(f"自定义验证器 '{name}' 添加成功")
    
    def create_numeric_validator(self, min_val: float = None, 
                               max_val: float = None,
                               allow_nan: bool = False) -> Callable:
        """创建数值验证器"""
        def validator(series):
            if not allow_nan and series.isnull().any():
                return False
            
            if min_val is not None and series.min() < min_val:
                return False
            
            if max_val is not None and series.max() > max_val:
                return False
            
            return True
        
        return validator
    
    def create_categorical_validator(self, allowed_values: List) -> Callable:
        """创建分类验证器"""
        def validator(series):
            unique_values = set(series.dropna().unique())
            return unique_values.issubset(set(allowed_values))
        
        return validator

# 创建全局验证工具实例
validation_utils = ValidationUtils()

# 便捷访问函数
def validate_dataframe(df: pd.DataFrame, **kwargs) -> Dict[str, Any]:
    """验证DataFrame数据质量"""
    return validation_utils.validate_dataframe(df, **kwargs)

def validate_stock_data(df: pd.DataFrame) -> Dict[str, Any]:
    """验证股票数据质量"""
    return validation_utils.validate_stock_data(df)

def validate_time_series(df: pd.DataFrame, **kwargs) -> Dict[str, Any]:
    """验证时间序列数据"""
    return validation_utils.validate_time_series(df, **kwargs)

def add_custom_validator(name: str, validator: Callable):
    """添加自定义验证器"""
    validation_utils.add_custom_validator(name, validator)

def create_numeric_validator(**kwargs) -> Callable:
    """创建数值验证器"""
    return validation_utils.create_numeric_validator(**kwargs)

if __name__ == "__main__":
    # 测试验证功能
    test_data = {
        'datetime': pd.date_range('2024-01-01', periods=100, freq='D'),
        'open': np.random.normal(100, 5, 100),
        'high': np.random.normal(105, 5, 100),
        'low': np.random.normal(95, 5, 100),
        'close': np.random.normal(102, 5, 100),
        'volume': np.random.randint(1000, 10000, 100)
    }
    
    df = pd.DataFrame(test_data)
    
    # 测试股票数据验证
    stock_validation = validate_stock_data(df)
    print("股票数据验证结果:", stock_validation['is_valid'])
    
    # 测试时间序列验证
    ts_validation = validate_time_series(df)
    print("时间序列验证结果:", ts_validation['is_valid'])
    
    # 测试通用验证
    general_validation = validate_dataframe(df)
    print("通用验证结果:", general_validation['is_valid'])
    print("验证摘要:", general_validation['summary'])