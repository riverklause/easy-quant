"""仓位计算抽象。

仓位计算器只回答"这一笔买入能用多少钱"，数量取整（整手）仍由引擎负责。
这样换仓位算法不会改动能不改的部分，回测撮合语义保持稳定。
"""

from typing import Protocol


class PositionSizer(Protocol):
    """仓位计算器协议"""

    def allocate(self, initial_capital: float) -> float:
        """返回单笔买入可用资金额度"""
        ...


class FixedFractionSizer:
    """固定比例仓位：每笔买入使用初始资金的固定比例"""

    def __init__(self, fraction: float = 0.1):
        if not 0 < fraction <= 1:
            raise ValueError(f"仓位比例必须在 (0, 1] 之间: {fraction}")
        self.fraction = fraction

    def allocate(self, initial_capital: float) -> float:
        return initial_capital * self.fraction
