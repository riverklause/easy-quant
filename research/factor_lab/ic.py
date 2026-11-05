"""截面 RankIC（Spearman 秩相关）。

实现选择"先 rank 再 corrwith"，而不是 corrwith(method="spearman")：
后者的行级语义依赖 pandas 版本，前者把定义（秩上的 Pearson）写在代码里。
"""

import logging
from dataclasses import dataclass
from math import isnan, sqrt

import pandas as pd

from .cross_section import paired_counts

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

    # 成对有效样本：与分档共用同一个定义
    counts = paired_counts(left, right)

    ic = left.rank(axis=1).corrwith(right.rank(axis=1), axis=1)
    ic = ic.where(counts >= min_stocks)

    too_small = int((counts < min_stocks).sum())
    if too_small:
        logger.warning("丢弃 %d 个截面（有效样本 < %d）", too_small, min_stocks)

    return ic.dropna()


@dataclass(frozen=True)
class ICSummary:
    """IC 序列的描述统计。

    t_stat 只是描述量（ir * sqrt(n)），**不作为通过/不通过的门槛**：
    阈值会随样本窗口翻转，门槛属于报告，不属于断言。
    """
    n: int
    mean: float
    std: float          # ddof=1
    ir: float           # mean / std
    positive_ratio: float
    t_stat: float
    autocorr1: float


def ic_summary(ic: pd.Series) -> ICSummary:
    """汇总一条 IC 序列。空序列返回 n=0、其余 NaN，不抛异常。"""
    ic = ic.dropna()
    n = len(ic)
    if n == 0:
        nan = float("nan")
        return ICSummary(0, nan, nan, nan, nan, nan, nan)

    mean = float(ic.mean())
    std = float(ic.std(ddof=1))
    ir = mean / std if std else float("nan")

    return ICSummary(
        n=n,
        mean=mean,
        std=std,
        ir=ir,
        positive_ratio=float((ic > 0).mean()),
        t_stat=ir * sqrt(n) if not isnan(ir) else float("nan"),
        autocorr1=float(ic.autocorr(lag=1)),
    )
