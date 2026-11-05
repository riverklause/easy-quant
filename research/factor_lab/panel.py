"""把 per-symbol 的 DataFrame 拼成截面宽表（index=date, columns=symbol）。

面板形态选宽表而不是 MultiIndex：pandas 的 rank(axis=1) / quantile /
corrwith(method="spearman") 都是一行解决，不需要每次做截面都
groupby 绕一圈。等需要长表时再 .stack()。
"""

from typing import Dict

import pandas as pd


def to_panel(stock_data: Dict[str, pd.DataFrame], field: str = "close") -> pd.DataFrame:
    """对齐成宽表：索引取所有 symbol 的日期并集，缺失保留 NaN。

    pandas 字典式 DataFrame 构造遇到列 index 不同的情况自动外连接，
    这正是我们想要的语义：某 symbol 某日无数据 → NaN，不丢弃该日。
    """
    if not stock_data:
        return pd.DataFrame()
    return pd.DataFrame(
        {symbol: df[field] for symbol, df in stock_data.items()}
    ).sort_index()


def momentum(panel: pd.DataFrame, window: int = 20) -> pd.DataFrame:
    """N 日动量（因果：t 只用到 ≤t-window 的收盘价 + t 自己）。

    底层是 pandas.DataFrame.pct_change(window)——它自然满足因果性：
    pct_change[i] = (x[i] - x[i-window]) / x[i-window]，没有任何
    从未来向当前的回传，所以 FL1 因果灯直接绿。
    """
    return panel.pct_change(window)
