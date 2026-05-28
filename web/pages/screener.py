"""
条件选股页面
选股结果展示
"""

from dash import html, dcc, callback, Input, Output, State
import dash_bootstrap_components as dbc
import pandas as pd
from pathlib import Path

DATA_DIR = Path("data")
SCREENER_RESULT_DIR = DATA_DIR / "screener_results"


def get_screener_results():
    """获取选股结果列表"""
    results = []
    if SCREENER_RESULT_DIR.exists():
        for f in SCREENER_RESULT_DIR.glob("*.parquet"):
            results.append({
                'name': f.stem,
                'path': str(f),
                'modified': pd.Timestamp(f.stat().st_mtime, unit='s')
            })
    return sorted(results, key=lambda x: x['modified'], reverse=True)


def load_screener_result(path):
    """加载选股结果"""
    try:
        df = pd.read_parquet(path)
        return df
    except:
        return pd.DataFrame()


layout = html.Div([
    dbc.Row([
        dbc.Col([
            html.H4("条件选股", className="mb-3"),
        ])
    ]),

    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("选股条件选择"),
                dbc.CardBody([
                    dbc.Row([
                        dbc.Col([
                            html.Label("选择条件"),
                            dcc.Dropdown(
                                id="screener-condition-select",
                                options=[
                                    {'label': 'RSI超卖', 'value': 'rsi_oversold'},
                                    {'label': 'RSI超买', 'value': 'rsi_overbought'},
                                    {'label': 'MACD金叉', 'value': 'macd_cross_up'},
                                    {'label': 'MACD死叉', 'value': 'macd_cross_down'},
                                    {'label': '价格突破20日均线', 'value': 'price_above_ma20'},
                                    {'label': '价格跌破20日均线', 'value': 'price_below_ma20'},
                                    {'label': '成交量放大', 'value': 'volume_surge'},
                                ],
                                placeholder="选择选股条件",
                            ),
                        ], width=6),
                        dbc.Col([
                            html.Label("股票池"),
                            dcc.Dropdown(
                                id="screener-stockpool-select",
                                options=[
                                    {'label': '全部股票', 'value': 'all'},
                                    {'label': '关注列表', 'value': 'watchlist'},
                                    {'label': '过滤后股票', 'value': 'filtered'},
                                ],
                                value='all',
                            ),
                        ], width=4),
                        dbc.Col([
                            html.Label(" "),
                            dbc.Button("执行选股", id="run-screener-btn", color="primary", className="mt-2"),
                        ], width=2),
                    ]),
                ])
            ], className="mb-3")
        ])
    ]),

    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("选股结果"),
                dbc.CardBody([
                    html.Div(id="screener-result-table"),
                ])
            ], className="mb-3")
        ])
    ]),
])


@callback(
    Output("screener-result-table", "children"),
    Input("run-screener-btn", "n_clicks"),
    [State("screener-condition-select", "value"),
     State("screener-stockpool-select", "value")],
)
def run_screener(n_clicks, condition, stockpool):
    """执行选股"""
    if not n_clicks or not condition:
        return html.P("请选择选股条件后执行", className="text-muted")

    return dbc.Alert(f"选股条件: {condition}, 股票池: {stockpool} - 选股功能开发中", color="info")
