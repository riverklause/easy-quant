"""
策略与选股管理
包含：策略控制、选股条件配置
"""

from dash import html, dcc, callback, Input, Output, State
import dash_bootstrap_components as dbc
import pandas as pd
from pathlib import Path

DATA_DIR = Path("data")

SCREENER_CONFIG_FILE = DATA_DIR / "ScreenerConfig.parquet"


def get_screener_configs():
    """获取选股条件配置"""
    if SCREENER_CONFIG_FILE.exists():
        try:
            df = pd.read_parquet(SCREENER_CONFIG_FILE)
            return df.to_dict('records') if not df.empty else []
        except:
            return []
    return []


def save_screener_config(config):
    """保存选股条件配置"""
    configs = get_screener_configs()
    configs.append(config)
    if configs:
        df = pd.DataFrame(configs)
        df.to_parquet(SCREENER_CONFIG_FILE, index=False)


layout = html.Div([
    dbc.Row([
        dbc.Col([
            html.H4("策略与选股管理", className="mb-3"),
        ])
    ]),

    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("策略控制"),
                dbc.CardBody([
                    dbc.Row([
                        dbc.Col([
                            html.Label("策略状态"),
                            dbc.RadioItems(
                                id="strategy-status-radio",
                                options=[
                                    {"label": "运行中", "value": "running"},
                                    {"label": "已停止", "value": "stopped"},
                                ],
                                value="stopped",
                                inline=True,
                            )
                        ])
                    ]),
                    html.Hr(),
                    dbc.Row([
                        dbc.Col([
                            html.Label("运行模式"),
                            dbc.Select(
                                id="strategy-mode-select",
                                options=[
                                    {"label": "实时模式", "value": "realtime"},
                                    {"label": "过滤模式", "value": "filter"},
                                    {"label": "回测模式", "value": "backtest"},
                                ],
                                value="realtime",
                            )
                        ])
                    ]),
                    html.Hr(),
                    dbc.Button("保存策略设置", id="save-strategy-btn", color="primary"),
                    html.Div(id="strategy-status-display"),
                ])
            ], className="mb-3")
        ])
    ]),

    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("选股条件配置"),
                dbc.CardBody([
                    dbc.Button("添加条件", id="add-condition-btn", color="success", className="me-2"),
                    html.Div(id="add-condition-modal-container"),
                    dbc.Button("删除条件", id="remove-condition-btn", color="danger", className="me-2"),
                    html.Hr(),
                    html.Div(id="screener-config-display"),
                ])
            ], className="mb-3")
        ])
    ]),
])


@callback(
    Output("screener-config-display", "children"),
    Input("add-condition-btn", "n_clicks"),
    Input("remove-condition-btn", "n_clicks"),
)
def update_screener_config(n_add, n_remove):
    """更新选股条件配置显示"""
    configs = get_screener_configs()
    if not configs:
        return html.P("暂无选股条件配置", className="text-muted")

    return dbc.Table([
        html.Thead(html.Tr([html.Th("条件名称"), html.Th("条件类型"), html.Th("参数")])),
        html.Tbody([
            html.Tr([html.Td(c.get('name', '')), html.Td(c.get('type', '')), html.Td(str(c.get('params', {})))])
            for c in configs
        ])
    ], striped=True, bordered=True, hover=True)


@callback(
    Output("strategy-status-display", "children"),
    Input("save-strategy-btn", "n_clicks"),
    [State("strategy-status-radio", "value"),
     State("strategy-mode-select", "value")],
)
def update_strategy(n_clicks, status, mode):
    """更新策略设置"""
    if n_clicks:
        return dbc.Alert(f"策略已设置为: {status}, 模式: {mode}", color="success")
    return ""
