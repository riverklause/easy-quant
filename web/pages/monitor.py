"""
实时监控页面
策略运行状态、信号、持仓、日志等
"""

from dash import html, dcc, callback, Input, Output, State
import dash_bootstrap_components as dbc
from datetime import datetime


layout = html.Div([
    dbc.Row([
        dbc.Col([
            html.H4("实时监控", className="mb-3"),
        ])
    ]),

    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("策略状态"),
                dbc.CardBody([
                    dbc.Row([
                        dbc.Col([
                            html.H5(id="strategy-status-indicator", children="已停止"),
                        ], width="auto"),
                        dbc.Col([
                            dbc.Badge("数据未连接", color="danger", id="data-status-badge"),
                        ], width="auto"),
                    ]),
                    html.Hr(),
                    dbc.Row([
                        dbc.Col([
                            html.Label("运行模式"),
                            html.P(id="strategy-mode-display", children="实时模式"),
                        ], width=4),
                        dbc.Col([
                            html.Label("监控股票数"),
                            html.P(id="monitored-count-display", children="0"),
                        ], width=4),
                        dbc.Col([
                            html.Label("数据连接"),
                            html.P(id="connection-status-display", children="未连接"),
                        ], width=4),
                    ]),
                ])
            ], className="mb-3")
        ], width=6),

        dbc.Col([
            dbc.Card([
                dbc.CardHeader("资产状况"),
                dbc.CardBody([
                    dbc.Row([
                        dbc.Col([
                            html.Label("现金"),
                            html.H3(id="cash-display", children="¥0.00"),
                        ], width=6),
                        dbc.Col([
                            html.Label("总资产"),
                            html.H3(id="total-asset-display", children="¥0.00"),
                        ], width=6),
                    ]),
                    html.Hr(),
                    dbc.Row([
                        dbc.Col([
                            html.Label("持仓数量"),
                            html.P(id="position-count-display", children="0"),
                        ], width=4),
                        dbc.Col([
                            html.Label("持仓市值"),
                            html.P(id="position-value-display", children="¥0.00"),
                        ], width=8),
                    ]),
                ])
            ], className="mb-3")
        ], width=6),
    ]),

    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("最新信号"),
                dbc.CardBody([
                    html.Div(id="latest-signals-display"),
                ])
            ], className="mb-3")
        ], width=6),

        dbc.Col([
            dbc.Card([
                dbc.CardHeader("实时行情"),
                dbc.CardBody([
                    html.Div(id="realtime-quotes-display"),
                ])
            ], className="mb-3")
        ], width=6),
    ]),

    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("执行日志"),
                dbc.CardBody([
                    html.Div(
                        id="execution-logs-display",
                        style={'maxHeight': '300px', 'overflowY': 'scroll'}
                    ),
                ])
            ], className="mb-3")
        ])
    ]),

    dcc.Interval(
        id="monitor-interval",
        interval=2000,
        n_intervals=0
    ),
])


@callback(
    [Output("strategy-status-indicator", "children"),
     Output("strategy-status-indicator", "color"),
     Output("data-status-badge", "children"),
     Output("data-status-badge", "color"),
     Output("strategy-mode-display", "children"),
     Output("monitored-count-display", "children"),
     Output("connection-status-display", "children"),
     Output("cash-display", "children"),
     Output("total-asset-display", "children"),
     Output("position-count-display", "children"),
     Output("position-value-display", "children"),
     Output("latest-signals-display", "children"),
     Output("realtime-quotes-display", "children"),
     Output("execution-logs-display", "children")],
    Input("monitor-interval", "n_intervals"),
)
def update_monitor(n):
    """更新监控数据"""
    return [
        "已停止",
        "secondary",
        "数据未连接",
        "danger",
        "实时模式",
        "0",
        "未连接",
        "¥0.00",
        "¥0.00",
        "0",
        "¥0.00",
        html.P("暂无信号", className="text-muted"),
        html.P("暂无行情", className="text-muted"),
        html.P("暂无日志", className="text-muted"),
    ]
