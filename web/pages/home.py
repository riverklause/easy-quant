"""
主页
"""

from dash import html
import dash_bootstrap_components as dbc

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
