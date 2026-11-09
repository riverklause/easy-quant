"""adj_close 列的统一写法。

列语义 = 数据源提供的复权收盘价：
- yfinance：auto_adjust=False 时返回真实的 Adj Close；
- futu：autype=NONE 不返回复权列 → NaN，需要时由复权因子派生。

永不写 0：0 会把"未知"伪装成"复权价为零"，而且能通过任何"非空"检查。
"""

import pandas as pd


def with_adj_close(df: pd.DataFrame) -> pd.DataFrame:
    """缺列时补 NaN；已有列（源的真值）原样保留。

    Args:
        df: 含 OHLCV 的数据框

    Returns:
        保证含 adj_close 列的数据框（不修改入参）
    """
    if 'adj_close' in df.columns:
        return df
    df = df.copy()
    df['adj_close'] = float('nan')
    return df


def normalize_adj_close(df: pd.DataFrame) -> pd.DataFrame:
    """把 adj_close 里的 0 归一为 NaN（读时兜底）。

    早期落盘的文件用 0 占位，0 不是合法的复权价。只改返回值，不改磁盘文件：
    历史文件靠这一层兜底，重抓与否都不影响正确性。

    Args:
        df: 可能含 adj_close 的数据框

    Returns:
        归一后的数据框（不修改入参；无 adj_close 列时原样返回）
    """
    if 'adj_close' not in df.columns:
        return df
    df = df.copy()
    zeros = df['adj_close'] == 0
    # 旧文件里全 0 时该列是 int64，先转 float 才能放 NaN
    df['adj_close'] = df['adj_close'].astype('float64')
    df.loc[zeros, 'adj_close'] = float('nan')
    return df
