"""薄适配器：把 per-symbol 的指标 calculate 结果拼成截面宽表。

indicators 模块的 calculate 签名是 `(pd.DataFrame) → pd.DataFrame`，
按单只 symbol 的 OHLCV 输入、返回含 output_fields 列的 DataFrame。
本模块把它循环调用、再按 symbol 拼成宽表（index=date, columns=symbol）。

重要：这个适配器只做"循环 + 拼表"，没有任何面板级 future leakage
操作（不 shift、不 groupby rolling）——所以 T3 已经钉住的因果性在
这里自动保留。adapter 不重新计算指标，只是搬运结果。
"""

from typing import Dict

import pandas as pd


def indicator_factor(stock_data: Dict[str, pd.DataFrame],
                     indicator,
                     field: str) -> pd.DataFrame:
    """对每只 symbol 调一次 indicator.calculate(df)，取 field 列，拼成宽表。

    Args:
        stock_data: {symbol: OHLCV DataFrame}
        indicator: 已经 __init__ 好的指标实例（需有 output_fields + calculate）
        field: 从 calculate 结果中抽哪一列作为因子值

    Raises:
        ValueError: field 不在 indicator.output_fields 里（不是 KeyError）。
    """
    if field not in indicator.output_fields:
        raise ValueError(
            f"{indicator.name} 没有输出字段 '{field}'；"
            f"可用字段: {indicator.output_fields}"
        )
    frames = {
        symbol: indicator.calculate(df)[field]
        for symbol, df in stock_data.items()
    }
    # 字典式构造自动外连接（日期并集 + 缺失 NaN 保留）
    return pd.DataFrame(frames).sort_index()
