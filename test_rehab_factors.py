#!/usr/bin/env python3
"""
测试Futu客户端复权因子功能
"""

import asyncio
import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from data.sources.futu_client import FutuAPIClient

async def test_rehab_factors():
    """测试获取复权因子功能"""
    client = FutuAPIClient()
    
    try:
        # 连接Futu API
        print("正在连接Futu API...")
        await client.connect()
        print("连接成功!")
        
        # 测试获取腾讯控股的复权因子
        symbol = "HK.00700"
        print(f"\n获取 {symbol} 的复权因子数据...")
        
        rehab_factors = await client.get_rehab_factors(symbol)
        
        print(f"成功获取 {len(rehab_factors)} 条复权因子记录")
        print("\n复权因子数据预览:")
        print(rehab_factors.head())
        
        # 显示关键字段
        if not rehab_factors.empty:
            print("\n关键字段信息:")
            print(f"除权除息日范围: {rehab_factors.index.min()} 到 {rehab_factors.index.max()}")
            print(f"总记录数: {len(rehab_factors)}")
            
            # 显示最新的复权因子
            latest_factors = rehab_factors.iloc[-1]
            print("\n最新复权因子:")
            print(f"前复权因子A: {latest_factors.get('forward_adj_factorA', 'N/A')}")
            print(f"前复权因子B: {latest_factors.get('forward_adj_factorB', 'N/A')}")
            print(f"后复权因子A: {latest_factors.get('backward_adj_factorA', 'N/A')}")
            print(f"后复权因子B: {latest_factors.get('backward_adj_factorB', 'N/A')}")
            
            # 测试复权价格计算
            raw_price = 100.0
            
            # 使用最新复权因子计算
            forward_price_latest = await client.get_adjusted_price(symbol, raw_price, None, 'forward')
            backward_price_latest = await client.get_adjusted_price(symbol, raw_price, None, 'backward')
            
            print(f"\n复权价格计算示例 (原始价格: {raw_price}):")
            print(f"使用最新复权因子:")
            print(f"  前复权价格: {forward_price_latest:.2f}")
            print(f"  后复权价格: {backward_price_latest:.2f}")
            
            # 如果有历史复权因子，测试按日期计算
            if len(rehab_factors) > 1:
                # 使用倒数第二个复权因子对应的日期
                historical_date = rehab_factors.index[-2].strftime('%Y-%m-%d')
                forward_price_historical = await client.get_adjusted_price(symbol, raw_price, historical_date, 'forward')
                backward_price_historical = await client.get_adjusted_price(symbol, raw_price, historical_date, 'backward')
                
                print(f"\n使用历史日期 {historical_date} 的复权因子:")
                print(f"  前复权价格: {forward_price_historical:.2f}")
                print(f"  后复权价格: {backward_price_historical:.2f}")
                
                # 测试早于所有复权因子的日期
                early_date = "2000-01-01"
                early_price = await client.get_adjusted_price(symbol, raw_price, early_date, 'forward')
                print(f"\n使用早于所有复权因子的日期 {early_date}:")
                print(f"  返回原始价格: {early_price:.2f}")
        
    except Exception as e:
        print(f"测试失败: {e}")
        
    finally:
        # 断开连接
        if client.connected:
            await client.disconnect()
            print("\n已断开Futu API连接")

async def test_features():
    """测试客户端特性信息"""
    client = FutuAPIClient()
    
    print("Futu客户端特性信息:")
    print(f"名称: {client.features['name']}")
    print(f"描述: {client.features['description']}")
    print(f"支持的市场: {client.features['supported_markets']}")
    print(f"数据类型: {client.features['data_types']}")
    print(f"支持的K线周期: {client.features['supported_periods']}")
    print(f"复权类型: {client.features['adjust_types']}")

if __name__ == "__main__":
    print("=== Futu客户端复权因子功能测试 ===\n")
    
    # 测试特性信息
    asyncio.run(test_features())
    
    print("\n" + "="*50 + "\n")
    
    # 测试复权因子功能
    asyncio.run(test_rehab_factors())