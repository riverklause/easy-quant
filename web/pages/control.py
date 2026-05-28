"""
控制面板主页
用于选择进入具体的控制面板
"""

from dash import html
import dash_bootstrap_components as dbc

layout = html.Div([
    dbc.Container([
        dbc.Row([
            dbc.Col([
                html.H4("控制面板", className="mb-4"),
                html.Hr(),
            ])
        ]),

        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H5("股票与数据管理"),
                        html.P("关注股票列表、历史数据下载"),
                        dbc.Button("进入", href="/control/stock", color="primary"),
                    ])
                ]),
            ], width=6),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H5("策略与选股管理"),
                        html.P("策略控制、选股条件配置"),
                        dbc.Button("进入", href="/control/strategy", color="primary"),
                    ])
                ]),
            ], width=6),
        ]),
    ]),
])
