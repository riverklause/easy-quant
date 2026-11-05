"""IC 衰减：同一因子在不同前瞻期上的表现。

签名刻意与"因子如何计算"解耦：调用方先算出 factor 宽表，
这里只负责换 horizon、重算 IC。这样测试不必为了造数据去拼 stock_data。
"""

import logging

import pandas as pd

from .ic import rank_ic
from .labels import forward_returns

logger = logging.getLogger(__name__)


def ic_decay(factor: pd.DataFrame,
             close: pd.DataFrame,
             horizons=(1, 5, 10, 20),
             min_stocks: int = 5) -> pd.DataFrame:
    """逐 horizon 的 IC 均值 / IR / 样本数。

    返回 DataFrame(index=horizon, columns=[mean_ic, ir, n])。
    horizon 越大，尾部 NaN 越多、n 越小，三个数必须一起报，否则会误读"衰减"。
    """
    rows = {}
    for horizon in horizons:
        ic = rank_ic(factor, forward_returns(close, horizon=horizon),
                     min_stocks=min_stocks)
        std = float(ic.std(ddof=1)) if len(ic) > 1 else float("nan")
        rows[horizon] = {
            "mean_ic": float(ic.mean()) if len(ic) else float("nan"),
            "ir": float(ic.mean()) / std if std else float("nan"),
            "n": len(ic),
        }

    return pd.DataFrame.from_dict(rows, orient="index").rename_axis("horizon")