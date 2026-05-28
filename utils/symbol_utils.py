"""
股票代码处理工具模块
支持不同数据源之间的股票代码格式转换和验证
"""
from typing import Optional, Tuple
import re
from .settings import settings


def convert_symbol_format(symbol: str, data_source: str, from_format: str = 'futu') -> str:
    """
    将股票代码从Futu格式转换为指定数据源格式
    
    Args:
        symbol: 股票代码（Futu格式，如：HK.00700, SZ.000001, US.AAPL）
        data_source: 目标数据格式类型 比如：'futu', 'futu_RT', 'yfinance'
        from_format: 输入股票代码的格式 比如：'futu', 'futu_RT', 'yfinance'，默认是futu格式
        
    Returns:
        转换后的股票代码
    """
    if data_source not in settings.data.available_data_sources['available_data_sources']:
        raise ValueError(f"不支持的数据源: {data_source}")

    if data_source == 'futu' or data_source == 'futu_RT':
        if from_format == 'futu' or from_format == 'futu_RT':
            # Futu数据源直接使用原格式
            return symbol
        elif from_format == 'yfinance':
            # yfinance数据源需要转换格式
            success, futu_symbol = _yfinance_to_Futu_format(symbol)
            if success:
                return futu_symbol
            else:
                print(f"股票代码 {symbol} 转换为 Futu 格式失败,返回原格式")
                return symbol
        else:
            raise ValueError(f"不支持的输入格式: {from_format}")
    elif data_source == 'yfinance':
        if from_format == 'futu':
            # Futu数据源需要转换格式
            success, yfinance_symbol = _Futu_to_yfinance_format(symbol)
            if success:
                return yfinance_symbol
            else:
                print(f"股票代码 {symbol} 转换为 yfinance 格式失败,返回原格式")
                return symbol
        elif from_format == 'yfinance':
            # yfinance数据源直接使用原格式
            return symbol

def convert_symbols_format(symbols: list, data_source: str, from_format: str = 'futu') -> list:
    """
    将股票代码从Futu格式转换为指定数据源格式
    
    Args:
        symbols: 股票代码列表（Futu格式，如：['HK.00700', 'SZ.000001', 'US.AAPL']）
        data_source: 目标数据格式类型 比如：'futu', 'futu_RT', 'yfinance'
        from_format: 输入股票代码的格式 比如：'futu', 'futu_RT', 'yfinance'，默认是futu格式
        
    Returns:
        转换后的股票代码
    """
    if data_source not in settings.data.available_data_sources['available_data_sources']:
        raise ValueError(f"不支持的数据源: {data_source}")

    if data_source == 'futu' or data_source == 'futu_RT':
        if from_format == 'futu' or from_format == 'futu_RT':
            # Futu数据源直接使用原格式
            return symbols
        elif from_format == 'yfinance':
            # yfinance数据源需要转换格式
            futu_symbols = []
            for symbol in symbols:
                success, futu_symbol = _yfinance_to_Futu_format(symbol)
                if success:
                    futu_symbols.append(futu_symbol)
                else:
                    print(f"股票代码 {symbol} 转换为 Futu 格式失败,返回原格式")
                    return symbols
            return futu_symbols
        else:
            raise ValueError(f"不支持的输入格式: {from_format}")
    elif data_source == 'yfinance':
        if from_format == 'futu':
            # Futu数据源需要转换格式
            yfinance_symbols = []
            for symbol in symbols:
                success, yfinance_symbol = _Futu_to_yfinance_format(symbol)
                if success:
                    yfinance_symbols.append(yfinance_symbol)
                else:
                    print(f"股票代码 {symbol} 转换为 yfinance 格式失败,返回原格式")
                    return symbols
            return yfinance_symbols
        elif from_format == 'yfinance':
            # yfinance数据源直接使用原格式
            return symbols

def _Futu_to_yfinance_format(symbol: str) -> str:
    """
    将Futu格式转换为yfinance格式
    
    Args:
        symbol: Futu格式股票代码 (如: HK.00700, US.AAPL, SZ.000001, SH.600000)
        
    Returns:
        Tuple[bool, str]: (是否成功, yfinance格式股票代码)
    """
    if not symbol or '.' not in symbol:
        return False,symbol
    
    # 分割市场和代码部分
    parts = symbol.split('.')
    if len(parts) != 2:
        return False,symbol
        
    market_part, code_part = parts
    if market_part not in settings.data.Futu_yf_MarketMap:
        print(f"{market_part}市场不在支持范围中")
        return False,symbol
    # 使用配置中的映射表进行转换
    yfinance_suffix = settings.data.Futu_yf_MarketMap[market_part]
        
    # 去掉港股的前导零
    if market_part == 'HK' and code_part.startswith('0'):
        code_part = code_part[1:]
        # 如果全部是零，保留一个零
        if not code_part:
            code_part = '0'
        
    # 美股直接返回代码部分
    if market_part == 'US':
        return True,code_part
    else:
        return True,f"{code_part}.{yfinance_suffix}"

def _yfinance_to_Futu_format(symbol: str) -> Tuple[bool, str]:
    """
    将yfinance格式转换为Futu格式
    
    Args:
        symbol: yfinance格式股票代码 (如: AAPL, 0700.HK, 000001.SZ, 600000.SS)
        
    Returns:
        Tuple[bool, str]: (是否成功, Futu格式股票代码)
    """
    if not symbol or not symbol.strip():
        return False, symbol
    
    # 检查是否包含有效的市场后缀
    valid_markets = list(settings.data.Futu_yf_MarketMap.values())
    has_valid_suffix = any(symbol.endswith(market) for market in valid_markets)
    
    if has_valid_suffix:
        # 分割代码和后缀
        parts = symbol.rsplit('.', 1)
        if len(parts) != 2:
            return False, symbol
            
        code_part, market_part = parts
        
        # 验证代码部分
        if not code_part or not code_part.strip():
            return False, symbol
        
        # 使用反向映射表查找Futu市场前缀
        futu_market = None
        for futu_prefix, yf_suffix in settings.data.Futu_yf_MarketMap.items():
            if yf_suffix == market_part:
                futu_market = futu_prefix
                break
        
        if not futu_market:
            return False, symbol
        
        # 处理港股代码（需要添加前导零）
        if futu_market == 'HK':
            # 港股：确保是5位数字，不足5位在前面补零
            if code_part.isdigit():
                # 港股在Futu格式中需要5位数字（包含前导零）
                code_part = code_part.zfill(5)
            else:
                return False, symbol
        
        # A股验证
        elif futu_market in ['SZ', 'SH']:
            # A股应该是6位数字
            if not code_part.isdigit() or len(code_part) != 6:
                return False, symbol
        
        # 注意：美股代码（如AAPL.US）在yfinance中不存在，所以不需要美股验证
        # 有后缀的代码只可能是港股或A股
        
        return True, f"{futu_market}.{code_part}"
    
    else:
        # 无后缀：默认为美股
        if symbol.isalpha():
            return True, f"US.{symbol}"
        else:
            return False, symbol

def validate_symbol_format(symbol: str, data_source: str) -> bool:
    """
    验证股票代码格式是否符合数据源要求
    
    Args:
        symbol: 股票代码
        data_source: 数据源类型 ('futu', 'yfinance')
        
    Returns:
        bool: 格式是否有效
    """
    if data_source not in settings.data.available_data_sources['available_data_sources']:
        raise ValueError(f"不支持的数据源: {data_source}")
        
    if data_source == 'futu':
        return _validate_futu_format(symbol)
    elif data_source == 'yfinance':
        return _validate_yfinance_format(symbol)

def validate_symbols_format(symbols: list, data_source: str) -> bool:
    """
    验证股票代码格式是否符合数据源要求
    
    Args:
        symbols: 股票代码列表
        data_source: 数据源类型 ('futu', 'yfinance')
        
    Returns:
        bool: 格式是否有效
    """
    if data_source not in settings.data.available_data_sources['available_data_sources']:
        raise ValueError(f"不支持的数据源: {data_source}")
        
    if data_source == 'futu':
        return all(_validate_futu_format(symbol) for symbol in symbols)
    elif data_source == 'yfinance':
        return all(_validate_yfinance_format(symbol) for symbol in symbols)

def _validate_futu_format(symbol: str) -> bool:
    """
    验证Futu格式股票代码
    
    Futu格式要求:
    - 格式: 市场.代码 (如: HK.00700, US.AAPL, SZ.000001, SH.600000)
    - 市场部分: HK, US, SZ, SH
    - 代码部分不能为空
    """
    if not symbol or '.' not in symbol:
        return False
    
    parts = symbol.split('.')
    if len(parts) != 2:
        return False
    
    market_part, code_part = parts
    
    # 检查市场部分
    valid_markets = list(settings.data.Futu_yf_MarketMap.keys())
    if market_part not in valid_markets:
        return False
    
    # 检查代码部分
    if not code_part or not code_part.strip():
        return False
    
    # 根据市场进行格式验证
    if market_part == 'HK':
        # 港股: 5位数字
        return len(code_part) == 5 and code_part.isdigit()
    elif market_part in ['SZ', 'SH']:
        # A股: 6位数字
        return len(code_part) == 6 and code_part.isdigit()
    elif market_part == 'US':
        # 美股: 字母
        return code_part.isalpha()
    
    return False


def _validate_yfinance_format(symbol: str) -> bool:
    """
    验证yfinance格式股票代码
    
    yfinance格式要求:
    - 支持的市场后缀: .HK, .SZ, .SS, .US
    - 代码部分不能为空
    - 无后缀的代码默认为美股
    """
    if not symbol or not symbol.strip():
        return False
    
    # 检查是否包含有效的市场后缀
    valid_markets = list(settings.data.Futu_yf_MarketMap.values())
    has_valid_suffix = any(symbol.endswith(market) for market in valid_markets)
    
    if has_valid_suffix:
        # 分割代码和后缀
        parts = symbol.rsplit('.', 1)
        if len(parts) != 2:
            return False
            
        code_part, market_part = parts

        # 验证代码部分
        if not code_part or not code_part.strip():
            return False
            
        # 基本验证：代码部分应该只包含字母和数字
        if not code_part.replace(' ', '').isalnum():
            return False
        
        if market_part == 'HK':
            # 港股: 4位数字
            return len(code_part) == 4 and code_part.isdigit()
        elif market_part in ['SZ', 'SH']:
            # A股: 6位数字
            return len(code_part) == 6 and code_part.isdigit() 
            
        return True
    else:
        # 无后缀: 默认为美股，直接判断是否字母组成
        return symbol.isalpha()