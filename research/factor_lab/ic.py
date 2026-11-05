"""截面 RankIC（Spearman 秩相关）。

实现选择"先 rank 再 corrwith"，而不是 corrwith(method="spearman")：
后者的行级语义依赖 pandas 版本，前者把定义（秩上的 Pearson）写在代码里。
"""

import logging

import pandas as pd

logger = logging.getLogger(__name__)


def rank_ic(factor: pd.DataFrame,
            forward_returns: pd.DataFrame,
            min_stocks: int = 5) -> pd.Series:
    """逐日截面秩相关。

    有效样本 = 同一 symbol 上 factor 与 forward_returns **同时非 NaN** 的个数。
    有效样本 < min_stocks 的截面被丢弃并记 warning；相关无法定义
    （如常数截面）的截面由 pandas 返回 NaN，同样被丢弃，但不计入该 warning。

    Args:
        factor: index=date、columns=symbol 的宽表
        forward_returns: 同 shape 的标签宽表
        min_stocks: 单个截面要求的最小有效样本数
    """
    common = factor.columns.intersection(forward_returns.columns)
    left = factor[common]
    right = forward_returns[common]

    # 成对有效样本：任一侧缺失都不算（FL3 契约钉住的单位）
    counts = (left.notna() & right.notna()).sum(axis=1)

    ic = left.rank(axis=1).corrwith(right.rank(axis=1), axis=1)
    ic = ic.where(counts >= min_stocks)

    too_small = int((counts < min_stocks).sum())
    if too_small:
        logger.warning("丢弃 %d 个截面（有效样本 < %d）", too_small, min_stocks)

    return ic.dropna()
