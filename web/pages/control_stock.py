"""
股票与数据管理
包含：关注股票列表、历史数据下载
"""

from dash import html, dcc, callback, Input, Output, State
import dash_bootstrap_components as dbc
import pandas as pd
from pathlib import Path
from datetime import datetime

DATA_DIR = Path("data")

STOCK_LIST_FILE = DATA_DIR / "StockList.parquet"
STOCK_BASIC_INFO_FILE = DATA_DIR / "StockBasicInfo.parquet"
STOCK_BASIC_FILTERED_FILE = DATA_DIR / 'StockBasicFiltered.parquet'


def get_stock_list_display():
    """获取关注股票列表显示"""
    if STOCK_LIST_FILE.exists():
        try:
            df = pd.read_parquet(STOCK_LIST_FILE)
            if not df.empty:
                df = df.sort_values('code', ascending=True)
                options = [{'label': f"{row['code']} - {row.get('name', '')}", 'value': row['code']} for _, row in df.iterrows()]
                return html.Div([
                    dcc.Checklist(
                        id='stock-checklist',
                        options=options,
                        value=[],
                        inline=False,
                        labelStyle={'display': 'flex', 'alignItems': 'center', 'marginRight': '20px'},
                        style={'display': 'flex', 'flexWrap': 'wrap'},
                    ),
                ], style={'padding': '10px 0'})
        except:
            pass
    
    return html.P("暂无关注的股票，可点击添加股票按钮添加股票", className="text-muted")


def show_stock_name(stock_code):
    """显示股票名称预览"""
    if not stock_code or not STOCK_BASIC_FILTERED_FILE.exists():
        return ''
    
    stock_code = stock_code.strip().upper()
    
    try:
        filtered_df = pd.read_parquet(STOCK_BASIC_FILTERED_FILE)
        match = filtered_df[filtered_df['code'].str.upper() == stock_code]
        if not match.empty:
            name = match.iloc[0].get('name', '')
            return f'股票名称: {name}' if name else ''
    except:
        pass
    return ''


def show_add_stock_input(n_clicks):
    """显示添加股票输入框"""
    if n_clicks:
        return dbc.InputGroup([
            dbc.Input(
                id='add-stock-code-input', 
                placeholder='输入股票代码，如: HK.00700', 
                type='text', 
                style={'width': '70%'}
            ),
            dbc.Button('保存', id='save-stock-btn', color='primary', style={'width': '15%'}),
            dbc.Button('取消', id='cancel-add-stock-btn', color='secondary', style={'width': '15%'}),
        ], style={'width': '100%'})
    return ''


def save_or_cancel_stock(n_save_clicks, n_cancel_clicks, stock_code):
    """保存或取消股票"""
    import dash
    from dash import no_update, callback_context
    from datetime import datetime
    
    if not callback_context.triggered:
        return no_update, no_update, no_update, no_update
    
    triggered_id = callback_context.triggered[0]['prop_id'].split('.')[0]
    
    if triggered_id == 'cancel-add-stock-btn':
        return get_stock_list_display(), '', '', ''
    
    if triggered_id == 'save-stock-btn':
        if not stock_code:
            return no_update, dbc.Alert('请输入股票代码', color='warning'), no_update, no_update
        
        stock_code = stock_code.strip().upper()
        
        if not STOCK_BASIC_FILTERED_FILE.exists():
            return get_stock_list_display(), dbc.Alert('过滤股票列表文件不存在，请先更新股票列表', color='danger'), '', ''
        
        try:
            filtered_df = pd.read_parquet(STOCK_BASIC_FILTERED_FILE)
            valid_codes = set(filtered_df['code'].str.upper().tolist())
            
            if stock_code not in valid_codes:
                return get_stock_list_display(), dbc.Alert(f'股票代码 {stock_code} 不在允许的列表中', color='danger'), no_update, no_update
            
            name = ''
            match = filtered_df[filtered_df['code'].str.upper() == stock_code]
            if not match.empty:
                name = match.iloc[0].get('name', '')
            
            new_stock = pd.DataFrame([{'code': stock_code, 'name': name, 'added_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')}])
            
            if STOCK_LIST_FILE.exists():
                existing_df = pd.read_parquet(STOCK_LIST_FILE)
                existing_codes = existing_df['code'].str.upper().tolist()
                if stock_code in existing_codes:
                    return get_stock_list_display(), dbc.Alert(f'股票 {stock_code} 已存在', color='warning'), no_update, no_update
                updated_df = pd.concat([existing_df, new_stock], ignore_index=True)
            else:
                updated_df = new_stock
            
            updated_df.to_parquet(STOCK_LIST_FILE, index=False)
            return get_stock_list_display(), dbc.Alert(f'股票 {stock_code} ({name}) 添加成功', color='success'), '', ''
            
        except Exception as e:
            import traceback
            print(f'保存股票失败: {e}')
            traceback.print_exc()
            return get_stock_list_display(), dbc.Alert(f'保存失败: {str(e)}', color='danger'), '', ''
    
    return no_update, no_update, no_update, no_update


def remove_stocks(n_clicks, selected_codes):
    """删除选中的股票"""
    if not selected_codes:
        return get_stock_list_display(), dbc.Alert('请先选择要删除的股票', color='warning')
    
    try:
        if not STOCK_LIST_FILE.exists():
            return get_stock_list_display(), dbc.Alert('股票列表文件不存在', color='danger')
        
        df = pd.read_parquet(STOCK_LIST_FILE)
        selected_codes_upper = [code.upper() for code in selected_codes]
        updated_df = df[~df['code'].str.upper().isin(selected_codes_upper)]
        
        if len(updated_df) == len(df):
            return get_stock_list_display(), dbc.Alert('未找到要删除的股票', color='warning')
        
        updated_df.to_parquet(STOCK_LIST_FILE, index=False)
        deleted_count = len(df) - len(updated_df)
        return get_stock_list_display(), dbc.Alert(f'成功删除 {deleted_count} 只股票', color='success')
        
    except Exception as e:
        import traceback
        print(f'删除股票失败: {e}')
        traceback.print_exc()
        return get_stock_list_display(), dbc.Alert(f'删除失败: {str(e)}', color='danger')


def update_stock_list(n_update_clicks, n_confirm_clicks, n_cancel_clicks, data_manager):
    """更新股票列表"""
    from dash import no_update, callback_context
    
    if not callback_context.triggered:
        return False, get_stock_list_display(), ""
    
    triggered = callback_context.triggered[0]
    triggered_id = triggered['prop_id'].split('.')[0]
    
    if triggered_id == "update-stock-list-btn":
        return True, get_stock_list_display(), ""
    
    if triggered_id == "cancel-update-btn":
        return False, get_stock_list_display(), ""
    
    if triggered_id == "confirm-update-btn":
        print("开始更新股票列表...")
        
        try:
            if data_manager is None:
                print("data_manager 为 None")
                return False, get_stock_list_display(), dbc.Alert("data_manager 未初始化", color="danger")
            
            futu_client = data_manager.clients.get('futu')
            if futu_client:
                print("获取股票基本信息...")
                success, stock_info = futu_client.get_stock_basicinfo()
                if success and not stock_info.empty:
                    stock_info.to_parquet(STOCK_BASIC_INFO_FILE, index=False)
                    print(f"股票基本信息已保存: {len(stock_info)} 条")
                else:
                    msg = "获取股票基本信息失败"
                    print(msg)
                    return False, get_stock_list_display(), dbc.Alert(msg, color="danger")
                
                print("获取过滤后股票列表...")
                filtered_result = futu_client.get_basicfiltered_stocks()
                if filtered_result and filtered_result[0]:
                    _, filtered_list, name_dict = filtered_result
                    filtered_df = pd.DataFrame({'code': filtered_list, 'name': [name_dict.get(c, '') for c in filtered_list]})
                    filtered_df.to_parquet(STOCK_BASIC_FILTERED_FILE, index=False)
                    print(f"过滤后股票列表已保存: {len(filtered_list)} 条")
                    return False, get_stock_list_display(), dbc.Alert(f"股票列表更新成功！共 {len(filtered_list)} 只股票", color="success")
                else:
                    return False, get_stock_list_display(), dbc.Alert("获取过滤后股票列表失败", color="warning")
            else:
                print("未找到 futu 客户端")
                return False, get_stock_list_display(), dbc.Alert("未找到 futu 客户端", color="danger")
        except Exception as e:
            import traceback
            print(f"更新股票列表失败: {e}")
            traceback.print_exc()
            return False, get_stock_list_display(), dbc.Alert(f"更新失败: {str(e)}", color="danger")
    
    return False, get_stock_list_display(), ""


layout = html.Div([
    dbc.Row([
        dbc.Col([
            html.H4("股票与数据管理", className="mb-3"),
        ])
    ]),
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("关注股票列表，关注股票列表用于策略执行"),
                dbc.CardBody([
                    dbc.Button("更新股票列表", id="update-stock-list-btn", color="primary", className="me-2"),
                    dbc.Button("添加股票", id="add-stock-btn", color="success", className="me-2"),
                    dbc.Button("删除股票", id="remove-stock-btn", color="danger", className="me-2"),
                    html.Hr(),
                    html.Div(id="add-stock-input-container", className="mt-2"),
                    html.Div(id="stock-name-preview", className="mt-1 text-muted", style={'font-size': '0.9em'}),
                    html.Hr(),
                    html.Div(id="stock-list-message"),
                    html.Div(id="stock-list-display", children=get_stock_list_display()),
                ])
            ], className="mb-3")
        ])
    ]),

    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("历史数据下载"),
                dbc.CardBody([
                    dbc.Row([
                        dbc.Col([
                            html.Label("股票代码（逗号分隔）"),
                            dcc.Input(id="download-symbols", type="text", placeholder="如: 00700,00001", className="form-control"),
                        ], width=6),
                        dbc.Col([
                            html.Label("数据源"),
                            dbc.Select(
                                id="download-source",
                                options=[
                                    {"label": "Futu", "value": "futu"},
                                    {"label": "yfinance", "value": "yfinance"},
                                ],
                                value="futu",
                            ),
                        ], width=3),
                        dbc.Col([
                            html.Label("周期"),
                            dbc.Select(
                                id="download-period",
                                options=[
                                    {"label": "日线", "value": "daily"},
                                    {"label": "周线", "value": "weekly"},
                                    {"label": "月线", "value": "monthly"},
                                ],
                                value="daily",
                            ),
                        ], width=3),
                    ]),
                    html.Hr(),
                    dbc.Row([
                        dbc.Col([
                            html.Label("开始日期"),
                            dcc.Input(id="download-start-date", type="text", placeholder="YYYY-MM-DD", className="form-control"),
                        ], width=6),
                        dbc.Col([
                            html.Label("结束日期"),
                            dcc.Input(id="download-end-date", type="text", placeholder="YYYY-MM-DD", className="form-control"),
                        ], width=6),
                    ]),
                    html.Hr(),
                    dbc.Button("开始下载", id="download-btn", color="primary"),
                    html.Div(id="download-progress"),
                ])
            ], className="mb-3")
        ])
    ]),
    
    dbc.Modal([
        dbc.ModalHeader(dbc.ModalTitle("确认更新")),
        dbc.ModalBody("确定要更新股票列表吗？这将从富途获取最新的股票基本信息。"),
        dbc.ModalFooter([
            dbc.Button("取消", id="cancel-update-btn", color="secondary", className="me-2"),
            dbc.Button("确认", id="confirm-update-btn", color="primary"),
        ]),
    ],
    id="update-confirm-modal",
    is_open=False,
    centered=True,
    ),
])
