"""TA1：交易分析器算不出来时必须留日志，而不是静默返回 0。"""

import logging

import pandas as pd


def test_TA1_trade_duration_failure_is_logged(caplog):
    """entry_date/exit_date 不是日期时，返回兜底值但必须记 warning。"""
    from backtest.analyzers.trade_analyzer import TradeAnalyzer

    trades = pd.DataFrame({
        "entry_date": ["2024-01-01"],
        "exit_date": ["not-a-date"],
    })

    with caplog.at_level(logging.WARNING, logger="backtest.analyzers.trade_analyzer"):
        stats = TradeAnalyzer()._calculate_trade_duration(trades)

    assert stats == {"average_holding_days": 0}
    assert "计算持仓时间失败" in caplog.text
