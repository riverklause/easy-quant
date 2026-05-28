#!/usr/bin/env python3
"""
yfinance数据获取测试程序 - 简化版本

直接使用DataManager类，按照实际使用方式调用
使用DataManager内置的默认配置（从utils/settings.py自动读取）
"""
import asyncio
import pandas as pd
from datetime import datetime, timedelta
from data.data_manager import DataManager


async def test_yfinance_simple():
    """简化版yfinance测试"""
    print("🚀 开始yfinance数据获取测试（简化版）")
    print("=" * 50)
    
    # 直接使用DataManager的默认构造函数
    # DataManager会自动从utils/settings.py读取配置
    data_manager = DataManager()
    
    # 连接数据源
    print("🔄 连接数据源...")
    connected = data_manager.connect_all()
    if not connected:
        print("❌ 连接失败，无法继续测试")
        return
    print("✅ 连接成功")
    
    try:
        # 1. 测试单个股票历史数据
        print("\n📊 测试单个股票历史数据")
        end_date = datetime.now().strftime('%Y-%m-%d')
        print(f"当前日期: {end_date}")
        start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        
        df = await data_manager.get_historical_data(
            symbol='HK.00700',
            start_date=start_date,
            end_date=end_date,
            data_source='yfinance',
            period='daily'
        )
        print(f"✅ 成功获取 {len(df)} 行数据")
        print(f"   数据列: {list(df.columns)}")
        
        # 2. 测试批量数据
        print("\n📦 测试批量数据获取")
        symbols = ['HK.01951', 'HK.02400', 'HK.00700']
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
        batch_data = await data_manager.get_batch_data(
            symbols=symbols,
            data_source='yfinance',
            start_date= start_date,#'2025-11-01'
            end_date= end_date,#'2025-11-10'
            period='daily'
        )
        print(f"✅ 批量获取成功: {len(batch_data)}/{len(symbols)} 个股票")
        print(batch_data)
        
        # 3. 测试数据源信息
        print("\nℹ️  测试数据源信息")
        info = data_manager.get_source_info('yfinance')
        print(f"✅ 支持的市场: {info['supported_markets']}")
        print(f"✅ 支持的周期: {info['supported_periods']}")
        
    except Exception as e:
        print(f"❌ 测试过程中出错: {e}")
    
    finally:
        # 断开连接
        print("\n🔄 断开数据源连接...")
        data_manager.disconnect_all()
        print("✅ 断开成功")
    
    print("\n" + "=" * 50)
    print("🎉 测试完成！")


async def test_multiple_markets():
    """测试多市场符号"""
    print("\n🌍 测试多市场符号")
    print("=" * 50)
    
    # 使用DataManager的默认配置
    data_manager = DataManager()
    
    data_manager.connect_all()
    
    # 测试不同市场的符号
    market_symbols = [
        ('美股', 'US.AAPL'),
        ('港股', 'HK.00700'), 
        ('深股', 'SZ.000001'),
        ('沪股', 'SH.600000')
    ]
    
    for market_name, symbol in market_symbols:
        try:
            df = await data_manager.get_historical_data(
                symbol=symbol,
                start_date='2024-01-01',
                end_date='2024-01-10',
                data_source='yfinance'
            )
            print(f"✅ {market_name}({symbol}): 成功获取 {len(df)} 行数据")
        except Exception as e:
            print(f"❌ {market_name}({symbol}): 失败 - {str(e)[:50]}")
    
    data_manager.disconnect_all()
    print("✅ 多市场测试完成")


async def main():
    """主函数"""
    # 运行基础测试
    await test_yfinance_simple()
    
    # 运行多市场测试
    # await test_multiple_markets()


if __name__ == '__main__':
    asyncio.run(main())