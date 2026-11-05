"""
Futu客户端数据获取功能测试脚本
测试get_historical_data和get_batch_data方法
"""
import asyncio
import pandas as pd
from datetime import datetime, timedelta
from data.sources.futu_client import FutuAPIClient
from utils.settings import settings


async def test_connection():
    """测试Futu客户端连接功能"""
    print("=== 测试Futu客户端连接 ===")
    
    # 创建Futu客户端
    config = {
        'host': settings.data.Futu_Host,
        'port': settings.data.Futu_Port,
        'trd_env': settings.data.Futu_TrdEnv
    }
    
    client = FutuAPIClient(config)
    
    # 测试连接
    print("正在连接Futu API...")
    connected = await client.connect()
    
    if connected:
        print("✅ Futu客户端连接成功")
        return client
    else:
        print("❌ Futu客户端连接失败")
        return None


async def test_get_historical_data(client):
    """测试单个股票历史数据获取"""
    print("\n=== 测试单个股票历史数据获取 ===")
    
    # 测试股票代码（腾讯控股 - 港股）
    test_symbols = [
        'HK.00700',  # 腾讯控股
        'US.AAPL',   # 苹果公司
        'SZ.000001'  # 平安银行
    ]
    
    # 设置测试日期范围
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    
    for symbol in test_symbols:
        print(f"\n📊 测试股票: {symbol}")
        print(f"日期范围: {start_date} 到 {end_date}")
        
        try:
            # 获取不复权数据
            print("获取不复权数据...")
            data = await client.get_historical_data(
                symbol=symbol,
                start_date=start_date,
                end_date=end_date,
                adjusted=False,
                period='daily'
            )
            
            if data is not None and not data.empty:
                print(f"✅ 成功获取数据，数据行数: {len(data)}")
                print(f"数据列: {list(data.columns)}")
                print(f"数据预览:")
                print(data.head())
                
                # 检查数据完整性
                print(f"数据统计信息:")
                print(data.describe())
            else:
                print("❌ 获取数据失败或数据为空")
                
        except Exception as e:
            print(f"❌ 获取数据时出错: {e}")
            
        # 测试复权数据
        try:
            print("\n获取复权数据...")
            adjusted_data = await client.get_historical_data(
                symbol=symbol,
                start_date=start_date,
                end_date=end_date,
                adjusted=True,
                period='daily'
            )
            
            if adjusted_data is not None and not adjusted_data.empty:
                print(f"✅ 成功获取复权数据，数据行数: {len(adjusted_data)}")
                print(f"复权数据预览:")
                print(adjusted_data.head())
            else:
                print("❌ 获取复权数据失败或数据为空")
                
        except Exception as e:
            print(f"❌ 获取复权数据时出错: {e}")


async def test_get_batch_data(client):
    """测试批量股票数据获取"""
    print("\n=== 测试批量股票数据获取 ===")
    
    # 测试股票组合
    symbol_groups = {
        '港股组合': ['HK.00700', 'HK.00941', 'HK.00005'],  # 腾讯、中国移动、汇丰
        '美股组合': ['US.AAPL', 'US.MSFT', 'US.GOOGL'],   # 苹果、微软、谷歌
        'A股组合': ['SZ.000001', 'SH.600036', 'SZ.000858']  # 平安、招商、五粮液
    }
    
    # 设置测试日期范围
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    
    for group_name, symbols in symbol_groups.items():
        print(f"\n📈 测试{group_name}: {symbols}")
        print(f"日期范围: {start_date} 到 {end_date}")
        
        try:
            # 批量获取数据
            batch_data = await client.get_batch_data(
                symbols=symbols,
                start_date=start_date,
                end_date=end_date,
                adjusted=False
            )
            
            if batch_data:
                print(f"✅ 批量获取成功，获取到 {len(batch_data)} 只股票的数据")
                
                # 检查每只股票的数据
                for symbol, data in batch_data.items():
                    if data is not None and not data.empty:
                        print(f"   {symbol}: {len(data)} 行数据")
                        # 检查数据列
                        print(f"     数据列: {list(data.columns)}")
                    else:
                        print(f"   {symbol}: 数据获取失败或为空")
                        
                # 显示第一只股票的详细数据
                first_symbol = list(batch_data.keys())[0]
                first_data = batch_data[first_symbol]
                if first_data is not None and not first_data.empty:
                    print(f"\n📋 {first_symbol} 数据预览:")
                    print(first_data.head())
                    
            else:
                print("❌ 批量获取数据失败")
                
        except Exception as e:
            print(f"❌ 批量获取数据时出错: {e}")


async def test_different_periods(client):
    """测试不同周期的数据获取"""
    print("\n=== 测试不同周期数据获取 ===")
    
    test_symbol = 'HK.00700'  # 腾讯控股
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')  # 最近7天
    
    periods = ['1min', '5min', '15min', '30min', '60min', 'daily', 'weekly']
    
    for period in periods:
        print(f"\n⏰ 测试周期: {period}")
        
        try:
            data = await client.get_historical_data(
                symbol=test_symbol,
                start_date=start_date,
                end_date=end_date,
                adjusted=False,
                period=period
            )
            
            if data is not None and not data.empty:
                print(f"✅ 成功获取{period}数据，数据行数: {len(data)}")
                print(f"   数据时间范围: {data.index.min()} 到 {data.index.max()}")
            else:
                print(f"❌ 获取{period}数据失败或数据为空")
                
        except Exception as e:
            print(f"❌ 获取{period}数据时出错: {e}")


async def test_error_handling(client):
    """测试错误处理功能"""
    print("\n=== 测试错误处理功能 ===")
    
    # 测试无效股票代码
    invalid_symbols = ['INVALID.SYMBOL', 'HK.99999', 'US.INVALID']
    
    for symbol in invalid_symbols:
        print(f"\n测试无效股票代码: {symbol}")
        
        try:
            data = await client.get_historical_data(
                symbol=symbol,
                start_date='2023-01-01',
                end_date='2023-01-31',
                adjusted=False
            )
            
            if data is not None:
                print(f"⚠️  意外成功获取数据: {len(data)} 行")
            else:
                print("✅ 正确处理无效股票代码")
                
        except Exception as e:
            print(f"✅ 正确抛出异常: {e}")
    
    # 测试无效日期范围
    print(f"\n测试无效日期范围")
    
    try:
        data = await client.get_historical_data(
            symbol='HK.00700',
            start_date='2023-12-31',  # 结束日期在开始日期之后
            end_date='2023-01-01',
            adjusted=False
        )
        
        if data is not None:
            print(f"⚠️  意外成功获取数据: {len(data)} 行")
        else:
            print("✅ 正确处理无效日期范围")
            
    except Exception as e:
        print(f"✅ 正确抛出异常: {e}")


async def main():
    """主测试函数"""
    print("🚀 开始Futu客户端数据获取功能测试")
    print("=" * 50)
    
    # 测试连接
    client = await test_connection()
    
    if client is None:
        print("❌ 连接失败，无法继续测试")
        return
    
    try:
        # 执行各项测试
        await test_get_historical_data(client)
        await test_get_batch_data(client)
        await test_different_periods(client)
        await test_error_handling(client)
        
        print("\n" + "=" * 50)
        print("🎉 所有测试完成")
        
    except Exception as e:
        print(f"❌ 测试过程中出现错误: {e}")
        
    finally:
        # 断开连接
        print("\n断开Futu连接...")
        await client.disconnect()
        print("✅ 连接已断开")


if __name__ == "__main__":
    # 运行测试
    asyncio.run(main())