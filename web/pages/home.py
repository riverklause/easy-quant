"""
主页
"""

import logging
from datetime import datetime
from typing import Any, Optional, Sequence, Tuple

import dash_bootstrap_components as dbc
from dash import Input, Output, callback, html, no_update

from utils.trading_calendar import CalendarError, CalendarFutureUnavailable

logger = logging.getLogger(__name__)

# 日历状态卡片覆盖的市场（展示名）
CALENDAR_MARKETS: Tuple[Tuple[str, str], ...] = (
    ("HK", "港股"),
    ("US", "美股"),
    ("CN", "A股"),
)

_SESSION_LABELS = {
    "WHOLE": "全天",
    "MORNING": "上午市",
    "AFTERNOON": "下午市",
}


def _status_alert(label: str, message: str, color: str) -> dbc.Alert:
    return dbc.Alert(f"{label}：{message}", color=color, className="py-2 mb-1")


def build_calendar_status(
    calendar: Any,
    now: Optional[datetime] = None,
    markets: Sequence[Tuple[str, str]] = CALENDAR_MARKETS,
) -> html.Div:
    """构造交易日历状态卡片内容。

    calendar 可以是 ``DataManager.get_trading_calendar()`` 的返回值，也可以是
    同契约的测试替身。四类日历异常都转成可见提示：页面不崩溃，也不静默降级。
    """
    if calendar is None:
        return html.Div(
            [_status_alert("交易日历", "尚未初始化（数据管理器不可用）", "warning")]
        )

    moment = now or datetime.now().astimezone()
    items = []
    for market, label in markets:
        try:
            session_type = calendar.get_session_type(moment, market)
        except CalendarFutureUnavailable as exc:
            items.append(_status_alert(label, f"跨年日历未发布：{exc}", "warning"))
            continue
        except CalendarError as exc:
            items.append(_status_alert(label, f"交易日历不可用：{exc}", "danger"))
            continue
        except Exception:  # noqa: BLE001 - 状态卡片不允许把页面打崩
            logger.exception("[%s] 交易日历状态检查失败", market)
            items.append(_status_alert(label, "交易日历不可用：未知错误", "danger"))
            continue

        if session_type is None:
            items.append(_status_alert(label, "今日休市", "secondary"))
            continue

        try:
            intraday = calendar.is_trading_time(moment, market)
        except CalendarError as exc:
            items.append(_status_alert(label, f"交易日历不可用：{exc}", "danger"))
            continue
        except Exception:  # noqa: BLE001
            logger.exception("[%s] 交易时段检查失败", market)
            items.append(_status_alert(label, "交易日历不可用：未知错误", "danger"))
            continue

        session_label = _SESSION_LABELS.get(str(session_type), str(session_type))
        items.append(
            _status_alert(
                label,
                f"交易日（{session_label}）· {'盘中' if intraday else '非盘中'}",
                "success" if intraday else "info",
            )
        )
    return html.Div(items)


def update_calendar_status(pathname: Optional[str]):
    """首页日历状态回调：懒取 DataManager，不阻塞其他页面。"""
    if pathname not in (None, "/"):
        return no_update
    from web import app as web_app

    if web_app.data_manager is None:
        return build_calendar_status(None)
    try:
        calendar = web_app.data_manager.get_trading_calendar()
    except Exception:  # noqa: BLE001 - 日历创建失败按不可用展示
        logger.exception("获取交易日历失败")
        return build_calendar_status(None)
    return build_calendar_status(calendar)


@callback(
    Output("calendar-status-display", "children"),
    Input("url", "pathname"),
)
def _update_calendar_status(pathname):
    return update_calendar_status(pathname)


layout = html.Div([
    dbc.Container([
        dbc.Row([
            dbc.Col([
                html.H1("Easy-Quant 股票量化交易系统", className="text-center mb-4"),
                html.Hr(),
            ])
        ]),

        dbc.Row([
            dbc.Col([
                html.H4("欢迎使用 Easy-Quant"),
                html.P("第四阶段开发进行中...", className="text-muted"),
            ], width={"size": 8, "offset": 2}),
        ]),

        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardHeader("交易日历状态"),
                    dbc.CardBody(
                        html.Div("正在检查交易日历...", id="calendar-status-display")
                    ),
                ]),
            ], width={"size": 8, "offset": 2}),
        ], className="mb-3"),

        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H5("控制面板"),
                        html.P("关注股票、策略控制、数据下载、条件配置"),
                        dbc.Button("进入", href="/control", color="primary"),
                    ])
                ]),
            ], width=4),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H5("指标可视化"),
                        html.P("K线图表、技术指标展示"),
                        dbc.Button("进入", href="/indicators", color="primary"),
                    ])
                ]),
            ], width=4),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H5("绩效仪表盘"),
                        html.P("回测结果、绩效分析"),
                        dbc.Button("进入", href="/performance", color="primary"),
                    ])
                ]),
            ], width=4),
        ], className="mb-3"),

        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H5("条件选股"),
                        html.P("选股结果展示"),
                        dbc.Button("进入", href="/screener", color="primary"),
                    ])
                ]),
            ], width=6),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H5("实时监控"),
                        html.P("策略状态、信号、持仓、日志"),
                        dbc.Button("进入", href="/monitor", color="primary"),
                    ])
                ]),
            ], width=6),
        ], className="mb-3"),

        dbc.Row([
            dbc.Col([
                html.Hr(),
                html.P("技术栈: Dash + dash-extensions-WebSocket + Futu API + yfinance", className="text-center text-muted"),
            ]),
        ]),
    ], fluid=True),
])
