"""
数据处理工具模块
支持数据清洗、转换和特征工程
"""
import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional, Union
from sklearn.preprocessing import StandardScaler, MinMaxScaler
from sklearn.impute import SimpleImputer

from .logger import logger

class DataUtils:
    """数据处理工具类"""
    
    def __init__(self):
        self.scalers = {}
        self.imputers = {}
    
    def clean_data(self, df: pd.DataFrame, 
                  fill_method: str = 'ffill',
                  remove_duplicates: bool = True,
                  handle_outliers: bool = True) -> pd.DataFrame:
        """数据清洗"""
        df_clean = df.copy()
        
        # 处理缺失值
        if fill_method:
            if fill_method == 'ffill':
                df_clean = df_clean.ffill()
            elif fill_method == 'bfill':
                df_clean = df_clean.bfill()
            elif fill_method == 'mean':
                df_clean = df_clean.fillna(df_clean.mean())
            elif fill_method == 'median':
                df_clean = df_clean.fillna(df_clean.median())
        
        # 去除重复值
        if remove_duplicates:
            df_clean = df_clean.drop_duplicates()
        
        # 处理异常值（使用IQR方法）
        if handle_outliers:
            numeric_cols = df_clean.select_dtypes(include=[np.number]).columns
            for col in numeric_cols:
                Q1 = df_clean[col].quantile(0.25)
                Q3 = df_clean[col].quantile(0.75)
                IQR = Q3 - Q1
                lower_bound = Q1 - 1.5 * IQR
                upper_bound = Q3 + 1.5 * IQR
                
                # 将异常值替换为边界值
                df_clean[col] = np.where(df_clean[col] < lower_bound, lower_bound, df_clean[col])
                df_clean[col] = np.where(df_clean[col] > upper_bound, upper_bound, df_clean[col])
        
        logger.info(f"数据清洗完成，原始形状: {df.shape}, 清洗后形状: {df_clean.shape}")
        return df_clean
    
    def normalize_data(self, df: pd.DataFrame, 
                      method: str = 'standard',
                      columns: List[str] = None,
                      fit: bool = True) -> pd.DataFrame:
        """数据标准化/归一化"""
        df_norm = df.copy()
        
        if columns is None:
            columns = df_norm.select_dtypes(include=[np.number]).columns.tolist()
        
        for col in columns:
            if col not in df_norm.columns:
                continue
                
            key = f"{method}_{col}"
            
            if method == 'standard':
                if fit or key not in self.scalers:
                    self.scalers[key] = StandardScaler()
                    self.scalers[key].fit(df_norm[[col]])
                df_norm[col] = self.scalers[key].transform(df_norm[[col]]).flatten()
            
            elif method == 'minmax':
                if fit or key not in self.scalers:
                    self.scalers[key] = MinMaxScaler()
                    self.scalers[key].fit(df_norm[[col]])
                df_norm[col] = self.scalers[key].transform(df_norm[[col]]).flatten()
            
            elif method == 'zscore':
                mean_val = df_norm[col].mean()
                std_val = df_norm[col].std()
                df_norm[col] = (df_norm[col] - mean_val) / std_val
            
            elif method == 'log':
                df_norm[col] = np.log1p(df_norm[col])
        
        logger.debug(f"数据标准化完成，方法: {method}")
        return df_norm
    
    def create_technical_features(self, df: pd.DataFrame, 
                                 price_col: str = 'close',
                                 volume_col: str = 'volume') -> pd.DataFrame:
        """创建技术指标特征"""
        df_features = df.copy()
        
        # 价格变化特征
        df_features['price_change'] = df_features[price_col].pct_change()
        df_features['price_change_abs'] = df_features[price_col].diff().abs()
        
        # 移动平均特征
        for window in [5, 10, 20, 50]:
            df_features[f'ma_{window}'] = df_features[price_col].rolling(window).mean()
            df_features[f'ma_ratio_{window}'] = df_features[price_col] / df_features[f'ma_{window}']
        
        # 波动率特征
        df_features['volatility_5'] = df_features[price_col].pct_change().rolling(5).std()
        df_features['volatility_20'] = df_features[price_col].pct_change().rolling(20).std()
        
        # 成交量特征
        if volume_col in df_features.columns:
            df_features['volume_ma_5'] = df_features[volume_col].rolling(5).mean()
            df_features['volume_ma_20'] = df_features[volume_col].rolling(20).mean()
            df_features['volume_ratio'] = df_features[volume_col] / df_features['volume_ma_20']
        
        # 高低价特征
        if all(col in df_features.columns for col in ['high', 'low']):
            df_features['high_low_ratio'] = df_features['high'] / df_features['low']
            df_features['body_ratio'] = (df_features['close'] - df_features['open']) / (df_features['high'] - df_features['low'])
        
        logger.debug("技术指标特征创建完成")
        return df_features
    
    def create_time_features(self, df: pd.DataFrame, 
                           datetime_col: str = 'datetime') -> pd.DataFrame:
        """创建时间特征"""
        df_time = df.copy()
        
        if datetime_col in df_time.columns:
            dt_series = pd.to_datetime(df_time[datetime_col])
            
            # 时间周期特征
            df_time['hour'] = dt_series.dt.hour
            df_time['day_of_week'] = dt_series.dt.dayofweek
            df_time['day_of_month'] = dt_series.dt.day
            df_time['month'] = dt_series.dt.month
            df_time['quarter'] = dt_series.dt.quarter
            df_time['year'] = dt_series.dt.year
            
            # 是否为交易时间特征
            df_time['is_weekend'] = df_time['day_of_week'].isin([5, 6]).astype(int)
            df_time['is_month_end'] = dt_series.dt.is_month_end.astype(int)
            df_time['is_quarter_end'] = dt_series.dt.is_quarter_end.astype(int)
            df_time['is_year_end'] = dt_series.dt.is_year_end.astype(int)
        
        logger.debug("时间特征创建完成")
        return df_time
    
    def create_lag_features(self, df: pd.DataFrame, 
                          columns: List[str],
                          lags: List[int] = [1, 2, 3, 5, 10]) -> pd.DataFrame:
        """创建滞后特征"""
        df_lag = df.copy()
        
        for col in columns:
            if col not in df_lag.columns:
                continue
            
            for lag in lags:
                df_lag[f'{col}_lag_{lag}'] = df_lag[col].shift(lag)
        
        logger.debug(f"滞后特征创建完成，列: {columns}, 滞后: {lags}")
        return df_lag
    
    def create_rolling_features(self, df: pd.DataFrame,
                              columns: List[str],
                              windows: List[int] = [5, 10, 20]) -> pd.DataFrame:
        """创建滚动窗口特征"""
        df_roll = df.copy()
        
        for col in columns:
            if col not in df_roll.columns:
                continue
            
            for window in windows:
                # 滚动统计量
                df_roll[f'{col}_roll_mean_{window}'] = df_roll[col].rolling(window).mean()
                df_roll[f'{col}_roll_std_{window}'] = df_roll[col].rolling(window).std()
                df_roll[f'{col}_roll_min_{window}'] = df_roll[col].rolling(window).min()
                df_roll[f'{col}_roll_max_{window}'] = df_roll[col].rolling(window).max()
                df_roll[f'{col}_roll_median_{window}'] = df_roll[col].rolling(window).median()
        
        logger.debug(f"滚动特征创建完成，列: {columns}, 窗口: {windows}")
        return df_roll
    
    def split_train_test(self, df: pd.DataFrame, 
                        test_size: float = 0.2,
                        time_col: str = None) -> tuple:
        """分割训练集和测试集"""
        if time_col and time_col in df.columns:
            # 按时间分割
            df_sorted = df.sort_values(time_col)
            split_idx = int(len(df_sorted) * (1 - test_size))
            train_df = df_sorted.iloc[:split_idx]
            test_df = df_sorted.iloc[split_idx:]
        else:
            # 随机分割
            split_idx = int(len(df) * (1 - test_size))
            indices = np.random.permutation(len(df))
            train_idx, test_idx = indices[:split_idx], indices[split_idx:]
            train_df = df.iloc[train_idx]
            test_df = df.iloc[test_idx]
        
        logger.info(f"数据集分割完成，训练集: {len(train_df)}, 测试集: {len(test_df)}")
        return train_df, test_df
    
    def calculate_correlation(self, df: pd.DataFrame, 
                             target_col: str = None) -> pd.DataFrame:
        """计算特征相关性"""
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        corr_matrix = df[numeric_cols].corr()
        
        if target_col and target_col in numeric_cols:
            # 返回与目标变量的相关性
            target_corr = corr_matrix[target_col].sort_values(ascending=False)
            return target_corr
        
        return corr_matrix

# 股票代码格式转换函数
def convert_symbol_format(symbol: str, target_source: str) -> str:
    """
    将Futu格式的股票代码转换为目标数据源格式
    
    Args:
        symbol: Futu格式的股票代码 (如: 00700.HK, 000001.SZ, AAPL.US)
        target_source: 目标数据源 ('futu' 或 'yfinance')
        
    Returns:
        str: 转换后的股票代码
    """
    if target_source == 'futu':
        # Futu格式保持不变
        return symbol
    elif target_source == 'yfinance':
        # 将Futu格式转换为yfinance格式
        if symbol.endswith('.HK'):
            # 港股: Futu格式 00700.HK -> yfinance格式 0700.HK
            # 移除前导零，但保留.HK后缀
            code_part = symbol[:-3]  # 获取代码部分
            # 移除前导零
            code_part = code_part.lstrip('0')
            # 如果全部是零，保留一个零
            if not code_part:
                code_part = '0'
            return f"{code_part}.HK"
        elif symbol.endswith('.SZ'):
            # 深市A股: Futu格式 000001.SZ -> yfinance格式 000001.SZ
            # A股代码保持不变
            return symbol
        elif symbol.endswith('.SS'):
            # 沪市A股: Futu格式 600000.SS -> yfinance格式 600000.SS
            # A股代码保持不变
            return symbol
        elif symbol.endswith('.US'):
            # 美股: Futu格式 AAPL.US -> yfinance格式 AAPL
            return symbol[:-3]
        else:
            # 默认认为是美股，直接返回
            return symbol
    else:
        raise ValueError(f"不支持的数据源: {target_source}")


def validate_symbol_format(symbol: str, source: str) -> bool:
    """
    验证股票代码格式是否符合数据源要求
    
    Args:
        symbol: 股票代码
        source: 数据源 ('futu' 或 'yfinance')
        
    Returns:
        bool: 格式是否有效
    """
    if not symbol or not isinstance(symbol, str):
        return False
    
    if source == 'futu':
        # Futu格式验证: 支持 .HK, .SZ, .SS, .US 后缀
        valid_suffixes = ['.HK', '.SZ', '.SS', '.US']
        return any(symbol.endswith(suffix) for suffix in valid_suffixes)
    elif source == 'yfinance':
        # yfinance格式验证: 支持各种格式
        # yfinance相对灵活，基本验证即可
        return len(symbol) > 0
    else:
        return False


# 创建全局数据处理工具实例
data_utils = DataUtils()

# 便捷访问函数
def clean_data(df: pd.DataFrame, **kwargs) -> pd.DataFrame:
    """数据清洗"""
    return data_utils.clean_data(df, **kwargs)

def normalize_data(df: pd.DataFrame, **kwargs) -> pd.DataFrame:
    """数据标准化"""
    return data_utils.normalize_data(df, **kwargs)

def create_technical_features(df: pd.DataFrame, **kwargs) -> pd.DataFrame:
    """创建技术指标特征"""
    return data_utils.create_technical_features(df, **kwargs)

def create_time_features(df: pd.DataFrame, **kwargs) -> pd.DataFrame:
    """创建时间特征"""
    return data_utils.create_time_features(df, **kwargs)

def split_train_test(df: pd.DataFrame, **kwargs) -> tuple:
    """分割训练测试集"""
    return data_utils.split_train_test(df, **kwargs)

if __name__ == "__main__":
    # 测试数据处理功能
    test_data = {
        'datetime': pd.date_range('2024-01-01', periods=100, freq='D'),
        'close': np.random.normal(100, 10, 100).cumsum(),
        'volume': np.random.randint(1000, 10000, 100),
        'high': np.random.normal(105, 5, 100),
        'low': np.random.normal(95, 5, 100)
    }
    
    df = pd.DataFrame(test_data)
    print("原始数据形状:", df.shape)
    
    # 测试数据清洗
    df_clean = clean_data(df)
    print("清洗后数据形状:", df_clean.shape)
    
    # 测试特征工程
    df_features = create_technical_features(df_clean)
    df_features = create_time_features(df_features)
    print("特征工程后数据形状:", df_features.shape)
    print("特征列:", df_features.columns.tolist())