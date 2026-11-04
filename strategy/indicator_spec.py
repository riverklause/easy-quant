"""策略对指标的声明：id、指标类名与构造参数。"""

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Union


@dataclass(frozen=True)
class IndicatorSpec:
    """声明一个所需指标，供引擎实例化并注册。

    id: 策略内部使用的键，如 "sma_5"
    class_name: 指标注册表里的类名，如 "SMA"
    params: 构造参数，如 {"period": 5}
    """

    id: str
    class_name: str
    params: Dict[str, Any] = field(default_factory=dict)

    def __hash__(self) -> int:
        # params 是 dict，默认生成的 __hash__ 一调用就抛 TypeError；
        # 按 id 哈希与字段级 __eq__ 相容（相等必同 id）。
        return hash(self.id)


# 迁移期两种声明形式：IndicatorSpec（带参数）与裸字符串（无参数）
IndicatorDecl = Union[IndicatorSpec, str]


def indicator_ids(required: Iterable[IndicatorDecl]) -> List[str]:
    """把声明归一成指标 id，供 calculator 使用。

    字符串声明是迁移期的兼容形式（examples/ 里仍在用），
    这里不发 DeprecationWarning：本函数在每根 bar、每只股票上都会被调用。
    """
    ids: List[str] = []
    for decl in required:
        ids.append(decl.id if isinstance(decl, IndicatorSpec) else decl)
    return ids
