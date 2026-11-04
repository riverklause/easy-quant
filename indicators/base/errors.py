"""
指标模块异常
"""


class IndicatorCalculationError(RuntimeError):
    """指标计算/装配失败：必须冒泡，不允许按股票或策略静默跳过。"""
