"""
Dash Web应用 - 使用 dash-extensions 实现实时推送
"""

import os
import socket
import sys
from pathlib import Path

# 支持在资源管理器中直接双击运行：双击时工作目录是 web/，
# 需把项目根目录加入 sys.path 并切换过去，否则 web 包导入和
# ./.cache、data 等相对路径都会失败
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))
os.chdir(_PROJECT_ROOT)

from dash import Dash, html, dcc, Input, Output, callback, callback_context, State, no_update
from dash import DiskcacheManager
import dash_bootstrap_components as dbc
from dash_extensions import WebSocket
from datetime import datetime
import diskcache
import pandas as pd

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
    
    WebSocket(id='ws', url=''),
    
    dcc.Interval(id='interval', interval=1000),

])


# 根据浏览器当前地址动态生成 WebSocket URL，避免硬编码 127.0.0.1
# 导致通过域名/IPv6 访问时 WS 连接失败
app.clientside_callback(
    """
    function(href) {
        if (!href) return '';
        const url = new URL(href);
        const protocol = url.protocol === 'https:' ? 'wss:' : 'ws:';
        return protocol + '//' + url.host + '/ws';
    }
    """,
    Output('ws', 'url'),
    Input('url', 'href')
)


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
# 元数据路径统一由 LocalStorageManager 决定：data/meta/{name}.parquet
from data.storage.local_storage import LocalStorageManager

STOCK_LIST_FILE = LocalStorageManager().build_meta_path("StockList")


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
    prevent_initial_call=True,
)
def download_data(n_clicks, symbols, source, period, start_date, end_date):
    """下载历史数据"""
    if not n_clicks:
        return ""

    if not start_date or not end_date:
        return dbc.Alert("请填写开始日期和结束日期", color="warning")

    if data_manager is None:
        return dbc.Alert("数据管理器未初始化，请重启服务", color="danger")

    # 1) 连接所选数据源
    client = data_manager.clients.get(source)
    if client is None:
        return dbc.Alert(f"数据源 {source} 未配置或不可用", color="danger")
    if not getattr(client, 'connected', False):
        try:
            if not client.connect():
                return dbc.Alert(f"数据源 {source} 连接失败，请检查后重试", color="danger")
        except Exception as e:
            return dbc.Alert(f"数据源 {source} 连接失败: {e}", color="danger")

    # 不填股票代码时，默认下载关注股票列表中的所有股票
    if symbols and symbols.strip():
        symbol_list = [s.strip() for s in symbols.split(',') if s.strip()]
    else:
        stock_list_file = STOCK_LIST_FILE
        if not stock_list_file.exists():
            return dbc.Alert("未填写股票代码，且关注股票列表为空，请先添加关注股票", color="warning")
        stock_df = pd.read_parquet(stock_list_file)
        symbol_list = stock_df['code'].dropna().astype(str).str.strip().tolist()
        symbol_list = [s for s in symbol_list if s]
        if not symbol_list:
            return dbc.Alert("未填写股票代码，且关注股票列表为空，请先添加关注股票", color="warning")

    import asyncio
    from data.storage.local_storage import LocalStorageManager

    storage = LocalStorageManager()
    # 存储键：股票代码 + K线类型 + 数据源（不含日期），
    # 便于对同一标的同一周期的历史数据做替换式增量更新
    data_type = f'historical_{period}'
    results = []

    for sym in symbol_list:
        try:
            # 2) 按K线类型、股票代码、起止日期获取数据
            df = asyncio.run(data_manager.get_historical_data(
                symbol=sym,
                start_date=start_date,
                end_date=end_date,
                data_source=source,
                period=period,
            ))
            if df.empty:
                results.append(dbc.Alert(f"{sym}: 未获取到数据", color="warning"))
                continue

            # 3) 存放数据：本地无该K线类型文件则新建，
            #    已有则替换重叠日期、追加新增日期
            ok = storage.update_data(
                new_data=df,
                symbol=sym,
                data_type=data_type,
                source=source,
            )
            if not ok:
                results.append(dbc.Alert(f"{sym}: 数据保存失败", color="danger"))
                continue
            results.append(dbc.Alert(
                f"{sym}: 下载成功，本次获取 {len(df)} 条", color="success"))
        except Exception as e:
            results.append(dbc.Alert(f"{sym}: 下载失败 - {e}", color="danger"))

    return html.Div(results)


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


def start_server(host='::', port=8050, debug=True):
    """启动服务器"""
    init_data_sources()

    # Windows 默认对 IPv6 socket 启用 IPV6_V6ONLY，导致绑定 '::' 时仅监听
    # IPv6，IPv4 请求无法连接。此处 monkey-patch server_bind 以关闭该
    # 选项，实现 IPv4/IPv6 双栈监听。
    from werkzeug.serving import BaseWSGIServer

    _orig_server_bind = BaseWSGIServer.server_bind

    def _dualstack_server_bind(self):
        if self.address_family == socket.AF_INET6:
            self.socket.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)
        _orig_server_bind(self)

    BaseWSGIServer.server_bind = _dualstack_server_bind

    print(f"\n🚀 服务器启动中: http://[::]:{port} (IPv4/IPv6 双栈)")
    print("按 Ctrl+C 停止服务器\n")
    app.run(host=host, port=port, debug=debug)


if __name__ == '__main__':
    try:
        start_server()
    except Exception:
        import traceback
        traceback.print_exc()
        # 双击运行时窗口会随进程退出而关闭，暂停以便查看报错
        print("\n启动失败，按回车键退出...")
        input()
