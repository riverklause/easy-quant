"""逐日分档平均前瞻收益（分位数回测的原料）。"""

import logging

import numpy as np
import pandas as pd

from .cross_section import paired_counts

logger = logging.getLogger(__name__)


def quantile_returns(factor: pd.DataFrame,
                     forward_returns: pd.DataFrame,
                     n_groups: int = 5,
                     min_stocks: int = 5) -> pd.DataFrame:
    """按因子逐日分档，返回各档平均前瞻收益。

    分档：`rank(pct=True, method="first")` → `ceil(pct * n_groups)`。
    用 method="first" 打破并列，保证同一截面的分档确定性；
    qcut 遇并列会丢边界或报错，因此不用。

    有效样本（成对非 NaN）< min_stocks 的截面整行丢弃并记 warning，
    与 `rank_ic` 共用 `paired_counts`，语义一致。
    """
    common = factor.columns.intersection(forward_returns.columns)
    left = factor[common]
    right = forward_returns[common]

    counts = paired_counts(left, right)
    pct = left.rank(axis=1, method="first", pct=True)
    groups = np.ceil(pct * n_groups).clip(1, n_groups)

    columns = {
        f"Q{g}": right.where(groups.eq(g)).mean(axis=1)
        for g in range(1, n_groups + 1)
    }
    result = pd.DataFrame(columns, index=left.index)

    too_small = counts < min_stocks
    if int(too_small.sum()):
        logger.warning("丢弃 %d 个截面（有效样本 < %d）",
                       int(too_small.sum()), min_stocks)
    result = result.where(~too_small)

    return result.dropna(how="all")
