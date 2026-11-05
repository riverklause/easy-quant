"""截面 RankIC（Spearman 秩相关）。

实现选择"先 rank 再 corrwith"，而不是 corrwith(method="spearman")：
后者的行级语义依赖 pandas 版本，前者把定义（秩上的 Pearson）写在代码里。
"""

import pandas as pd


def rank_ic(factor: pd.DataFrame, forward_returns: pd.DataFrame) -> pd.Series:
    """逐日截面秩相关。

    factor / forward_returns 均为 index=date、columns=symbol 的宽表，
    只在共同 symbol 上计算；任一侧为 NaN 的样本按对剔除，
    整行无法计算（如样本不足、常数截面）时结果为 NaN 并被丢弃。
    """
    common = factor.columns.intersection(forward_returns.columns)
    ranked_factor = factor[common].rank(axis=1)
    ranked_returns = forward_returns[common].rank(axis=1)
    return ranked_factor.corrwith(ranked_returns, axis=1).dropna()
