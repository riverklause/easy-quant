"""
Dash Web应用 - 使用 dash-extensions 实现实时推送
"""

from dash import Dash, html, dcc, Input, Output, callback, callback_context, State, no_update
from dash import DiskcacheManager
import dash_bootstrap_components as dbc
from dash_extensions import WebSocket
from datetime import datetime
import diskcache
import pandas as pd
from pathlib import Path

data_state_manager = None
data_manager = None

diskcache_cache = diskcache.Cache("./.cache")
background_callback_manager = DiskcacheManager(diskcache_cache)

app = Dash(__name__, 
           external_stylesheets=[dbc.themes.BOOTSTRAP],
           background_callback_manager=background_callback_manager,
           suppress_callback_exceptions=True) # 抑制回调异常，方便使用动态创建组件作为回调

app.layout = html.Div([
    dcc.Location(id='url', refresh=False),
    dbc.NavbarSimple(
        brand="Easy-Quant",
        brand_href="/",
        color="dark",
        dark=True,
        children=[
            dbc.NavItem(dcc.Link("首页", href="/", className="nav-link")),
            dbc.NavItem(dcc.Link("控制面板", href="/control", className="nav-link")),
            dbc.NavItem(dcc.Link("指标可视化", href="/indicators", className="nav-link")),
            dbc.NavItem(dcc.Link("绩效仪表盘", href="/performance", className="nav-link")),
            dbc.NavItem(dcc.Link("条件选股", href="/screener", className="nav-link")),
            dbc.NavItem(dcc.Link("实时监控", href="/monitor", className="nav-link")),
        ]
    ),
    
    html.Div(id='page-content', className='mt-4'),
    
    WebSocket(id='ws', url='ws://127.0.0.1:8050/ws'),
    
    dcc.Interval(id='interval', interval=1000),

])


# ========== 页面路由 ==========
@app.callback(
    Output('page-content', 'children'),
    Input('url', 'pathname')
)
def display_page(pathname):
    if pathname == '/':
        from web.pages.home import layout as home_layout
        return home_layout
    elif pathname == '/control':
        from web.pages.control import layout as control_layout
        return control_layout
    elif pathname == '/control/stock':
        from web.pages.control_stock import layout as control_stock_layout
        return control_stock_layout
    elif pathname == '/control/strategy':
        from web.pages.control_strategy import layout as control_strategy_layout
        return control_strategy_layout
    elif pathname == '/indicators':
        from web.pages.indicators import layout as indicators_layout
        return indicators_layout
    elif pathname == '/performance':
        from web.pages.performance import layout as performance_layout
        return performance_layout
    elif pathname == '/screener':
        from web.pages.screener import layout as screener_layout
        return screener_layout
    elif pathname == '/monitor':
        from web.pages.monitor import layout as monitor_layout
        return monitor_layout
    else:
        return html.H1("404 - 页面未找到")


# ========== 控制面板-股票页面回调 ==========
DATA_DIR = Path("data")
STOCK_LIST_FILE = DATA_DIR / "StockList.parquet"
STOCK_BASIC_INFO_FILE = DATA_DIR / "StockBasicInfo.parquet"
STOCK_BASIC_FILTERED_FILE = DATA_DIR / "StockBasicFiltered.parquet"


@app.callback(
    [Output("update-confirm-modal", "is_open"),
     Output("stock-list-display", "children", allow_duplicate=True),
     Output("stock-list-message", "children", allow_duplicate=True)],
    [Input("update-stock-list-btn", "n_clicks"),
     Input("confirm-update-btn", "n_clicks"),
     Input("cancel-update-btn", "n_clicks")],
    prevent_initial_call=True,
)
def update_stock_list(n_update_clicks, n_confirm_clicks, n_cancel_clicks):
    from web.pages.control_stock import update_stock_list as func
    return func(n_update_clicks, n_confirm_clicks, n_cancel_clicks, data_manager)


# 添加股票功能 - 显示输入框
@app.callback(
    Output('add-stock-input-container', 'children'),
    Input('add-stock-btn', 'n_clicks'),
)
def show_add_stock_input(n_clicks):
    from web.pages.control_stock import show_add_stock_input as func
    return func(n_clicks)


# 页面操作通过 control_stock.py 中的函数处理
# save_or_cancel_stock 和 remove_stocks 的逻辑在 control_stock.py 中


@app.callback(
    Output('stock-name-preview', 'children'),
    Input('add-stock-code-input', 'value'),
)
def show_stock_name(stock_code):
    from web.pages.control_stock import show_stock_name as func
    return func(stock_code)


@app.callback(
    [Output('stock-list-display', 'children', allow_duplicate=True), 
     Output('stock-list-message', 'children', allow_duplicate=True),
     Output('add-stock-input-container', 'children', allow_duplicate=True),
     Output('stock-name-preview', 'children', allow_duplicate=True)],
    Input('save-stock-btn', 'n_clicks'),
    Input('cancel-add-stock-btn', 'n_clicks'),
    State('add-stock-code-input', 'value'),
    prevent_initial_call=True,
)
def save_or_cancel_stock(n_save_clicks, n_cancel_clicks, stock_code):
    from web.pages.control_stock import save_or_cancel_stock as func
    return func(n_save_clicks, n_cancel_clicks, stock_code)


@app.callback(
    [Output('stock-list-display', 'children', allow_duplicate=True),
     Output('stock-list-message', 'children', allow_duplicate=True)],
    Input('remove-stock-btn', 'n_clicks'),
    State('stock-checklist', 'value'),
    prevent_initial_call=True,
)
def remove_stocks(n_clicks, selected_codes):
    from web.pages.control_stock import remove_stocks as func
    return func(n_clicks, selected_codes)


@app.callback(
    Output('download-progress', 'children'),
    Input('download-btn', 'n_clicks'),
    [State('download-symbols', 'value'), State('download-source', 'value'), State('download-period', 'value'), State('download-start-date', 'value'), State('download-end-date', 'value')],
)
def download_data(n_clicks, symbols, source, period, start_date, end_date):
    """下载历史数据"""
    if n_clicks and symbols and start_date and end_date:
        return dbc.Alert(f"开始下载 {symbols} 的数据...", color="info")
    return ""


def init_data_sources(config=None):
    """初始化数据源"""
    global data_manager, data_state_manager
    from data.data_state_manager import DataStateManager
    from data.data_manager import DataManager

    data_state_manager = DataStateManager(socketio=None)
    print("✓ DataStateManager 初始化完成")
    
    data_manager = DataManager(config)
    if not data_manager.connect_all():
        print("⚠ 警告: 数据管理器连接失败")
    else:
        print("✓ DataManager 连接成功")

    try:
        if 'futu_RT' in data_manager.clients:
            futu_rt_processor = data_manager.clients['futu_RT']
            futu_rt_processor.register_callback(data_state_manager.update_quote)
            print("✓ FutuRTProcessor 回调注册成功")
        else:
            print("⚠ 警告: 未找到 futu_RT 客户端，实时数据功能将不可用")
    except Exception as e:
        print(f"⚠ 警告: FutuRTProcessor 连接失败: {e}")
        print("  实时数据功能将不可用，但Web界面仍可使用")

    print("数据源初始化完成")


def start_server(host='0.0.0.0', port=8050, debug=True):
    """启动服务器"""
    init_data_sources() 
    print(f"\n🚀 服务器启动中: http://{host}:{port}")
    print("按 Ctrl+C 停止服务器\n")
    app.run(host=host, port=port, debug=debug)


if __name__ == '__main__':
    start_server()
