"""截面操作的共用语义。

"有效样本"只能有一个定义，否则 rank_ic 和分档会在样本不足时
给出互相矛盾的结论。
"""

from dataclasses import dataclass
from typing import Mapping

import pandas as pd


def paired_counts(left: pd.DataFrame, right: pd.DataFrame) -> pd.Series:
    """每个截面上 factor 与标签**同时非 NaN** 的样本数。"""
    return (left.notna() & right.notna()).sum(axis=1)


@dataclass(frozen=True)
class CorrelationResult:
    """因子相关性矩阵及其支撑样本数。

    matrix: 对称，index/columns 为因子名，元素是逐日截面秩相关的时间均值
    n:      对称，每对因子真正参与平均的有效截面数（相关无法定义的日期不计，
            与 rank_ic 的 .dropna() 同一件事，区别是这里把它计数暴露出来）
    """
    matrix: pd.DataFrame
    n: pd.DataFrame


def _cross_section_rank_corr(left: pd.DataFrame,
                             right: pd.DataFrame,
                             min_stocks: int) -> tuple[float, int]:
    """一对因子的逐日截面 Spearman 均值，返回 (均值, 有效截面数)。

    秩在各面板自身支撑集上取、再由 corrwith 按 symbol 对齐——与 rank_ic 完全一致，
    这样"IC"和"相关性矩阵"不会对同一份数据给出两种口径。
    """
    common = left.columns.intersection(right.columns)
    a, b = left[common], right[common]

    per_date = (a.rank(axis=1)
                .corrwith(b.rank(axis=1), axis=1))
    per_date = per_date.where(paired_counts(a, b) >= min_stocks).dropna()

    if per_date.empty:
        return float("nan"), 0
    return float(per_date.mean()), len(per_date)


def factor_correlation(factors: Mapping[str, pd.DataFrame],
                       min_stocks: int = 5) -> CorrelationResult:
    """因子两两之间的截面相关性矩阵（逐日截面 Spearman 再取时间均值）。

    直接对面板求相关会把时间维度混进来（不同日期的水平差异会被当成截面差异），
    因此这里先逐日算、再平均。

    Args:
        factors: 因子名 → (index=date, columns=symbol) 宽表
        min_stocks: 单个截面要求的最小成对有效样本数，与 rank_ic 同义
    """
    names = list(factors)
    nan = float("nan")
    matrix = pd.DataFrame(nan, index=names, columns=names)
    counts = pd.DataFrame(0, index=names, columns=names)

    for i, name in enumerate(names):
        matrix.loc[name, name] = 1.0
        counts.loc[name, name] = int(
            (factors[name].notna().sum(axis=1) >= min_stocks).sum())
        for other in names[i + 1:]:
            corr, n = _cross_section_rank_corr(
                factors[name], factors[other], min_stocks)
            matrix.loc[name, other] = matrix.loc[other, name] = corr
            counts.loc[name, other] = counts.loc[other, name] = n

    return CorrelationResult(matrix=matrix, n=counts)
