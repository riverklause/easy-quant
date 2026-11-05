"""P1：预定义组合是配置草稿——必须可导入、且确实声明了策略槽位。"""

import pytest

from strategy.portfolios import (
    get_aggressive_growth_portfolio,
    get_balanced_portfolio,
    get_conservative_value_portfolio,
)


@pytest.mark.parametrize("factory", [
    get_aggressive_growth_portfolio,
    get_balanced_portfolio,
    get_conservative_value_portfolio,
])
def test_P1_presets_declare_strategy_slots(factory):
    portfolio = factory()
    assert len(portfolio.strategy_configs) > 0, \
        f"{portfolio.name} 没有任何策略槽位"
