"""FP0-FP4：复权价格计算（离线，不依赖 OpenD）。

复权算错不会报错，只会让回测收益/因子 IC 全部被污染，所以这里钉住
公式、日期选择、边界回退和非法枚举。
"""

import asyncio

import pandas as pd
import pytest
from futu import RET_OK

from data.sources.futu_client import FutuAPIClient


def _factors(rows) -> pd.DataFrame:
    """rows: [(date, forward_a, forward_b, backward_a, backward_b), ...]"""
    df = pd.DataFrame(
        [
            {
                "forward_adj_factorA": fa,
                "forward_adj_factorB": fb,
                "backward_adj_factorA": ba,
                "backward_adj_factorB": bb,
            }
            for _, fa, fb, ba, bb in rows
        ],
        index=pd.to_datetime([date for date, *_ in rows]),
    )
    df.index.name = "ex_div_date"
    return df


def _client(factors: pd.DataFrame) -> FutuAPIClient:
    client = FutuAPIClient(config={})

    async def fake_get_rehab_factors(symbol):
        return factors

    client.get_rehab_factors = fake_get_rehab_factors
    return client


def _adjust(client, target_date=None, adjust_type="forward", raw=10.0):
    return asyncio.run(
        client.get_adjusted_price(
            "HK.00700", raw, target_date=target_date, adjust_type=adjust_type
        )
    )


def test_FP1_forward_and_backward_formulas():
    """前复权 10×2+1=21；后复权 10×0.5−2=3。"""
    factors = _factors([("2024-01-02", 2.0, 1.0, 0.5, -2.0)])
    client = _client(factors)

    assert _adjust(client, adjust_type="forward") == pytest.approx(21.0)
    assert _adjust(client, adjust_type="backward") == pytest.approx(3.0)


def test_FP2_date_selection_has_no_look_ahead():
    """target=d4 只能取 d3 的因子，不能顺手用 d5。"""
    factors = _factors([
        ("2024-01-01", 1.1, 0.0, 1.0, 0.0),
        ("2024-01-03", 1.2, 0.0, 1.0, 0.0),
        ("2024-01-05", 1.3, 0.0, 1.0, 0.0),
    ])
    client = _client(factors)

    assert _adjust(client, target_date="2024-01-04") == pytest.approx(12.0)


def test_FP3_boundaries_fall_back_to_raw_price():
    """目标日早于全部因子 / 因子表为空：返回原价。"""
    client = _client(_factors([("2024-01-03", 2.0, 1.0, 1.0, 0.0)]))
    assert _adjust(client, target_date="2024-01-02") == pytest.approx(10.0)

    assert _adjust(_client(pd.DataFrame()), target_date="2024-01-02") == pytest.approx(10.0)


@pytest.mark.parametrize("bad", ["fwd", "Forward", "backwards", ""])
def test_FP4_unknown_adjust_type_is_rejected(bad):
    """非法枚举必须报错，不能静默按后复权计算。"""
    client = _client(_factors([("2024-01-02", 2.0, 1.0, 2.0, 1.0)]))

    with pytest.raises(ValueError, match="复权类型"):
        _adjust(client, adjust_type=bad)


def test_FP0_rehab_factors_returns_dataframe():
    """get_rehab_factors 的契约是 DataFrame——get_adjusted_price 就是这么消费的。"""
    factors = _factors([("2024-01-02", 2.0, 1.0, 1.0, 0.0)])

    class _QuoteCtx:
        def get_rehab(self, symbol):
            return RET_OK, factors.copy()

    client = FutuAPIClient(config={})
    client.connected = True
    client.quote_ctx = _QuoteCtx()

    got = asyncio.run(client.get_rehab_factors("HK.00700"))

    assert isinstance(got, pd.DataFrame)
    assert got.index.name == "ex_div_date"
