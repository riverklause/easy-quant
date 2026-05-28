"""
指标可视化页面
K线图 + 指标选择器
"""

from dash import html, dcc, callback, Input, Output, State
import dash_bootstrap_components as dbc
import pandas as pd
from pathlib import Path
import plotly.graph_objects as go
from plotly.subplots import make_subplots

DATA_DIR = Path("data")
HISTORICAL_DIR = DATA_DIR / "historical_daily"

AVAILABLE_INDICATORS = [
    {'label': 'SMA', 'value': 'sma'},
    {'label': 'EMA', 'value': 'ema'},
    {'label': 'MACD', 'value': 'macd'},
    {'label': 'RSI', 'value': 'rsi'},
    {'label': 'KDJ', 'value': 'kdj'},
    {'label': 'CCI', 'value': 'cci'},
    {'label': 'ADX', 'value': 'adx'},
    {'label': 'ATR', 'value': 'atr'},
    {'label': 'Bollinger Bands', 'value': 'bollinger'},
    {'label': 'OBV', 'value': 'obv'},
]


def get_available_symbols():
    """获取可用的股票代码"""
    symbols = []
    if HISTORICAL_DIR.exists():
        for source_dir in HISTORICAL_DIR.iterdir():
            if source_dir.is_dir():
                for f in source_dir.glob("*.parquet"):
                    name = f.stem
                    parts = name.split('_')
                    if parts:
                        code = parts[0].replace('_', '.')
                        if code not in symbols:
                            symbols.append(code)
    return [{'label': s, 'value': s} for s in symbols]


def load_kline_data(symbol, source='yfinance'):
    """加载K线数据"""
    symbol_safe = symbol.replace('.', '_')
    file_path = HISTORICAL_DIR / source / f"{symbol_safe}_historical_daily_*.parquet"

    for f in HISTORICAL_DIR.glob(f"{source}/*.parquet"):
        if symbol_safe in f.stem:
            try:
                df = pd.read_parquet(f)
                return df
            except:
                pass
    return pd.DataFrame()


layout = html.Div([
    dbc.Row([
        dbc.Col([
            html.H4("指标可视化", className="mb-3"),
        ])
    ]),

    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("股票选择"),
                dbc.CardBody([
                    dbc.Row([
                        dbc.Col([
                            html.Label("股票代码"),
                            dcc.Dropdown(
                                id="indicator-symbol-select",
                                options=get_available_symbols(),
                                placeholder="选择股票",
                                value=None,
                            ),
                        ], width=4),
                        dbc.Col([
                            html.Label("数据源"),
                            dbc.Select(
                                id="indicator-source-select",
                                options=[
                                    {'label': 'yfinance', 'value': 'yfinance'},
                                    {'label': 'Futu', 'value': 'futu'},
                                ],
                                value='yfinance',
                            ),
                        ], width=3),
                        dbc.Col([
                            html.Label("时间范围"),
                            dcc.Dropdown(
                                id="indicator-period-select",
                                options=[
                                    {'label': '最近1个月', 'value': '1m'},
                                    {'label': '最近3个月', 'value': '3m'},
                                    {'label': '最近6个月', 'value': '6m'},
                                    {'label': '最近1年', 'value': '1y'},
                                    {'label': '全部', 'value': 'all'},
                                ],
                                value='6m',
                            ),
                        ], width=3),
                        dbc.Col([
                            html.Label(" "),
                            dbc.Button("加载数据", id="load-indicator-btn", color="primary", className="mt-2"),
                        ], width=2),
                    ]),
                ])
            ], className="mb-3")
        ])
    ]),

    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("指标选择"),
                dbc.CardBody([
                    dbc.Checklist(
                        id="indicator-select-checklist",
                        options=AVAILABLE_INDICATORS,
                        value=[],
                        inline=True,
                    ),
                ])
            ], className="mb-3")
        ])
    ]),

    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    dcc.Graph(id="kline-chart"),
                ])
            ], className="mb-3")
        ])
    ]),
])


@callback(
    Output("kline-chart", "figure"),
    [Input("load-indicator-btn", "n_clicks"),
     Input("indicator-select-checklist", "value")],
    [State("indicator-symbol-select", "value"),
     State("indicator-source-select", "value"),
     State("indicator-period-select", "value")],
)
def update_chart(n_clicks, selected_indicators, symbol, source, period):
    """更新K线图表"""
    if not symbol:
        return go.Figure()

    df = load_kline_data(symbol, source)

    if df.empty:
        return go.Figure()

    df = df.sort_values('time_key' if 'time_key' in df.columns else df.index.name or df.columns[0])

    if period != 'all':
        days_map = {'1m': 30, '3m': 90, '6m': 180, '1y': 365}
        days = days_map.get(period, 180)
        df = df.tail(days)

    row_count = 1
    if selected_indicators:
        row_count += len(selected_indicators)

    fig = make_subplots(
        rows=row_count, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.05,
        subplot_titles=(['K线'] + selected_indicators) if selected_indicators else ['K线']
    )

    if 'open' in df.columns and 'high' in df.columns and 'low' in df.columns and 'close' in df.columns:
        fig.add_trace(
            go.Candlestick(
                x=df.index,
                open=df['open'],
                high=df['high'],
                low=df['low'],
                close=df['close'],
                name='K线'
            ),
            row=1, col=1
        )
    else:
        fig.add_trace(
            go.Scatter(x=df.index, y=df['close'], name='收盘价', line=dict(color='blue')),
            row=1, col=1
        )

    if 'volume' in df.columns and selected_indicators:
        fig.add_trace(
            go.Bar(x=df.index, y=df['volume'], name='成交量', marker_color='gray'),
            row=2, col=1
        )

    fig.update_layout(
        height=300 * row_count,
        showlegend=True,
        template='plotly_white',
    )

    return fig
