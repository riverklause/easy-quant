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
