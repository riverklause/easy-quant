"""研究用标签：前瞻收益。

标签允许使用未来价格——这是评估的定义。**因子侧严禁 import 本模块**，
否则就是最经典的前瞻泄漏。
"""

import pandas as pd


def forward_returns(panel: pd.DataFrame, horizon: int = 1) -> pd.DataFrame:
    """t 日标签 = close[t+horizon] / close[t] - 1。

    最后一根 bar 没有前瞻收益，整行为 NaN。
    """
    return panel.shift(-horizon) / panel - 1
