"""截面操作的共用语义。

"有效样本"只能有一个定义，否则 rank_ic 和分档会在样本不足时
给出互相矛盾的结论。
"""

import pandas as pd


def paired_counts(left: pd.DataFrame, right: pd.DataFrame) -> pd.Series:
    """每个截面上 factor 与标签**同时非 NaN** 的样本数。"""
    return (left.notna() & right.notna()).sum(axis=1)
