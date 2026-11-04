"""按策略声明装配指标实例；引擎与 StrategyExecutor 共用。"""

from typing import Iterable

from indicators.base.calculator import IndicatorCalculator
from indicators.base.registry import IndicatorRegistry
from strategy.indicator_spec import IndicatorDecl, IndicatorSpec


def ensure_indicators(
    registry: IndicatorRegistry,
    calculator: IndicatorCalculator,
    specs: Iterable[IndicatorDecl],
) -> None:
    """幂等装配：已注册则校验，未注册则按声明实例化。

    字符串声明（迁移期）无法推断参数，跳过。
    """
    for spec in specs:
        if not isinstance(spec, IndicatorSpec):
            continue

        existing = calculator.indicators.get(spec.id)
        if existing is not None:
            declared = {
                key: getattr(existing, "parameters", {}).get(key)
                for key in spec.params
            }
            if type(existing).__name__ != spec.class_name or declared != spec.params:
                raise ValueError(f"指标 id 冲突: {spec.id}")
            continue

        indicator = registry.create_indicator(spec.class_name, **spec.params)
        calculator.register_indicator(indicator, spec.id)
