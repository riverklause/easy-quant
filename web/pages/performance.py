"""
绩效仪表盘页面
回测结果展示
"""

from dash import html, dcc, callback, Input, Output, State
import dash_bootstrap_components as dbc
import pandas as pd
from pathlib import Path
import plotly.graph_objects as go

BACKTEST_DIR = Path("data/backtest")


def get_backtest_results():
    """获取回测结果列表"""
    results = []
    if BACKTEST_DIR.exists():
        for f in BACKTEST_DIR.glob("*.parquet"):
            results.append({
                'name': f.stem,
                'path': str(f),
                'modified': pd.Timestamp(f.stat().st_mtime, unit='s')
            })
    return sorted(results, key=lambda x: x['modified'], reverse=True)


def load_backtest_result(path):
    """加载回测结果"""
    try:
        df = pd.read_parquet(path)
        return df
    except:
        return pd.DataFrame()


layout = html.Div([
    dbc.Row([
        dbc.Col([
            html.H4("绩效仪表盘", className="mb-3"),
        ])
    ]),

    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("回测结果选择"),
                dbc.CardBody([
                    dbc.Select(
                        id="backtest-select",
                        options=[
                            {'label': r['name'], 'value': r['path']}
                            for r in get_backtest_results()
                        ],
                        placeholder="选择回测结果",
                    ),
                    html.Hr(),
                    dbc.Button("加载回测结果", id="load-backtest-btn", color="primary"),
                ])
            ], className="mb-3")
        ], width=6),

        dbc.Col([
            dbc.Card([
                dbc.CardHeader("绩效指标"),
                dbc.CardBody([
                    html.Div(id="performance-metrics"),
                ])
            ], className="mb-3")
        ], width=6),
    ]),

    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("收益曲线"),
                dbc.CardBody([
                    dcc.Graph(id="equity-curve-chart"),
                ])
            ], className="mb-3")
        ])
    ]),

    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("交易记录"),
                dbc.CardBody([
                    html.Div(id="trade-history-table"),
                ])
            ], className="mb-3")
        ])
    ]),
])


@callback(
    [Output("performance-metrics", "children"),
     Output("equity-curve-chart", "figure"),
     Output("trade-history-table", "children")],
    Input("load-backtest-btn", "n_clicks"),
    State("backtest-select", "value"),
)
def load_performance(n_clicks, selected_path):
    """加载绩效数据"""
    if not selected_path:
        return "请选择回测结果", go.Figure(), "暂无数据"

    df = load_backtest_result(selected_path)

    if df.empty:
        return "数据加载失败", go.Figure(), "暂无数据"

    metrics_html = []
    if 'total_return' in df.columns:
        total_return = df['total_return'].iloc[-1] if len(df) > 0 else 0
        metrics_html.append(html.P(f"总收益率: {total_return:.2f}%"))

    if 'max_drawdown' in df.columns:
        max_dd = df['max_drawdown'].min() if len(df) > 0 else 0
        metrics_html.append(html.P(f"最大回撤: {max_dd:.2f}%"))

    if 'sharpe_ratio' in df.columns:
        sharpe = df['sharpe_ratio'].iloc[-1] if len(df) > 0 else 0
        metrics_html.append(html.P(f"夏普比率: {sharpe:.2f}"))

    if not metrics_html:
        metrics_html = [html.P("暂无绩效数据")]

    fig = go.Figure()
    if 'portfolio_value' in df.columns:
        fig.add_trace(go.Scatter(
            x=df.index,
            y=df['portfolio_value'],
            mode='lines',
            name='组合价值',
            line=dict(color='blue')
        ))
    elif 'total_return' in df.columns:
        fig.add_trace(go.Scatter(
            x=df.index,
            y=df['total_return'],
            mode='lines',
            name='总收益率',
            line=dict(color='blue')
        ))

    fig.update_layout(
        template='plotly_white',
        height=400,
        xaxis_title='时间',
        yaxis_title='价值',
    )

    table = dbc.Table([
        html.Thead(html.Tr([
            html.Th("时间"),
            html.Th("类型"),
            html.Th("股票"),
            html.Th("价格"),
            html.Th("数量"),
        ])),
        html.Tbody([
            html.Tr([
                html.Td(str(row.get('timestamp', ''))),
                html.Td(row.get('action', '')),
                html.Td(row.get('symbol', '')),
                html.Td(f"{row.get('price', 0):.2f}"),
                html.Td(row.get('quantity', 0)),
            ])
            for _, row in df.head(20).iterrows() if 'action' in row
        ]) if 'action' in df.columns else html.Tbody([html.Tr(html.Td("暂无交易记录"))])
    ], striped=True, bordered=True, hover=True)

    return metrics_html, fig, table
