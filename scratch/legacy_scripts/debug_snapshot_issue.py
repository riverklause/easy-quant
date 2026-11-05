#!/usr/bin/env python3
"""
调试快照数据获取问题
"""
import asyncio
from utils.symbol_utils import convert_symbol_format, validate_symbol_format

async def debug_snapshot_issue():
    """调试快照数据获取问题"""
    print("🔍 调试快照数据获取问题")
    print("=" * 50)
    
    # 测试的股票代码
    test_symbols = ['HK.00700', 'HK.01951']
    data_source = 'futu'
    
    print(f"测试股票代码: {test_symbols}")
    print(f"数据源: {data_source}")
    print()
    
    for symbol in test_symbols:
        print(f"📊 处理股票代码: {symbol}")
        
        # 1. 转换股票代码格式
        converted_symbol = convert_symbol_format(symbol, data_source)
        print(f"   转换后代码: {converted_symbol}")
        
        # 2. 验证股票代码格式
        is_valid_format = validate_symbol_format(converted_symbol, data_source)
        print(f"   格式验证结果: {is_valid_format}")
        
        # 3. 检查转换前后是否相同
        if symbol == converted_symbol:
            print(f"   ✅ 转换前后代码相同")
        else:
            print(f"   ⚠️ 转换前后代码不同")
        
        print()
    
    # 测试错误信息
    print("🔧 测试错误信息生成:")
    for symbol in test_symbols:
        converted_symbol = convert_symbol_format(symbol, data_source)
        is_valid_format = validate_symbol_format(converted_symbol, data_source)
        
        if not is_valid_format:
            error_msg = f"股票代码{symbol}转换后的格式{converted_symbol}不符合{data_source}数据源要求"
            print(f"   {error_msg}")
        else:
            print(f"   ✅ {symbol} -> {converted_symbol} 格式验证通过")

if __name__ == '__main__':
    asyncio.run(debug_snapshot_issue())