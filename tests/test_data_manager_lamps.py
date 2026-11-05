"""DM1-DM3：DataManager 的健康检查、配置校验与数据源路由。

全部离线：clients 为空或替换为桩，不触发任何网络/OpenD。
"""

import asyncio

import pytest

from data.data_manager import DataManager


def _minimal_config():
    return {
        "futu": {},
        "yfinance": {},
        "available_data_sources": {"available_data_sources": []},
    }


def test_DM1_health_check_reflects_client_state():
    """体检结果必须是真实状态，不能永远是 truthy 的 coroutine。"""
    dm = DataManager(config=_minimal_config())

    class _Down:
        async def health_check(self):
            return {"connected": False, "data_source": "fake"}

    dm.clients = {"fake": _Down()}

    got = asyncio.run(dm.health_check())

    assert got["fake"]["connected"] is False


def test_DM2_single_missing_field_still_raises(monkeypatch):
    """缺一个 Futu 字段就要报错，而不是等 _init_clients 深处炸。"""
    class _Data:
        data_dir, cache_dir, update_interval = "d", "c", 1
        futu = {"Futu_Host": "h", "Futu_Port": 11111}  # 缺 Futu_TrdEnv
        yfinance = {"yfinance_proxy": None}
        available_data_sources = {"available_data_sources": ["futu"]}

    monkeypatch.setattr(
        "data.data_manager.settings", type("S", (), {"data": _Data()})()
    )

    # 只测校验函数本身，避免构造 DataManager 时创建真实目录
    dm = DataManager.__new__(DataManager)
    with pytest.raises(ImportError, match="Futu_TrdEnv"):
        dm._get_default_config()


def test_DM3_unknown_data_source_rejected():
    """未配置的数据源必须在入口处拒绝，而不是拼出一个格式错误的请求。"""
    dm = DataManager(config=_minimal_config())

    with pytest.raises(Exception, match="未配置或不可用"):
        asyncio.run(
            dm.get_historical_data(
                "HK.00700", "2024-01-01", "2024-01-31", "nope"
            )
        )
