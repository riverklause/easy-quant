"""
股票筛选执行引擎
每个条件/条件组独立过滤，得到各自的股票列表
"""

import logging
from collections import defaultdict
from typing import Dict, List, Any, Union
import pandas as pd
from screener.filter_condition import FilterCondition

logger = logging.getLogger(__name__)


def _safe_evaluate(cond: FilterCondition, data) -> bool:
    """条件组里定位哪个条件坏了时用：抛错即 False。"""
    try:
        return cond.evaluate(data)
    except Exception:
        return False


class StockScreener:
    """
    股票筛选执行引擎
    每个条件/条件组独立并行过滤
    """

    def __init__(self, name: str = "StockScreener", fail_fast: bool = False):
        self.name = name
        self.fail_fast = fail_fast
        self.filter_list: List[Union[FilterCondition, List[FilterCondition]]] = []
        self.condition_errors: Dict[str, int] = defaultdict(int)

    def add_condition(self, condition: FilterCondition):
        """添加单个条件"""
        self.filter_list.append(condition)

    def add_condition_group(self, conditions: List[FilterCondition]):
        """添加条件组（组内AND关系）"""
        self.filter_list.append(conditions)

    def screen(self, stock_data: Dict[str, pd.DataFrame]) -> Dict[str, List[str]]:
        """并行过滤，返回每个条件对应的股票列表"""
        results = {}
        self.condition_errors.clear()

        for i, filter_item in enumerate(self.filter_list):
            if isinstance(filter_item, FilterCondition):
                results[filter_item.name] = self._filter_single(
                    filter_item, stock_data
                )
            else:
                group_name = '+'.join([c.name for c in filter_item])
                results[group_name] = self._filter_group(
                    filter_item, stock_data
                )

        return results

    def _filter_single(self, condition: FilterCondition,
                      stock_data: Dict[str, pd.DataFrame]) -> List[str]:
        """过滤单个条件"""
        passed = []
        for symbol, data in stock_data.items():
            try:
                if condition.evaluate(data):
                    passed.append(symbol)
            except Exception as exc:
                logger.exception(
                    "条件 %s 在 symbol=%s 上评估失败: %s",
                    condition.name, symbol, exc,
                )
                self.condition_errors[condition.name] += 1
                if self.fail_fast:
                    raise
        return passed

    def _filter_group(self, conditions: List[FilterCondition],
                     stock_data: Dict[str, pd.DataFrame]) -> List[str]:
        """过滤条件组（组内AND关系）"""
        passed = []
        
        for symbol, data in stock_data.items():
            try:
                if all(condition.evaluate(data) for condition in conditions):
                    passed.append(symbol)
            except Exception as exc:
                bad = next((c.name for c in conditions
                            if not _safe_evaluate(c, data)), "group")
                logger.exception(
                    "条件组（%s）在 symbol=%s 上评估失败: %s",
                    bad, symbol, exc,
                )
                self.condition_errors[bad] += 1
                if self.fail_fast:
                    raise
        
        return passed

    def get_filter_info(self) -> List[Dict]:
        """获取过滤条件信息"""
        info = []
        for item in self.filter_list:
            if isinstance(item, FilterCondition):
                info.append({
                    'type': 'single',
                    'name': item.name
                })
            else:
                info.append({
                    'type': 'group',
                    'names': [c.name for c in item]
                })
        return info
