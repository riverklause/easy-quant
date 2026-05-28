"""
股票筛选器演示脚本
"""

import sys
import os
import pandas as pd
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)) + '/..')


def generate_sample_stock_data(num_stocks: int = 20, num_days: int = 60) -> dict:
    stock_data = {}

    for i in range(num_stocks):
        dates = pd.date_range(start='2024-01-01', periods=num_days)
        np.random.seed(i)

        base_price = 50 + np.random.randn() * 30
        price = base_price + np.cumsum(np.random.randn(num_days) * 2)
        price = np.maximum(price, 1)

        df = pd.DataFrame({
            'open': price * (1 + np.random.randn(num_days) * 0.01),
            'high': price * (1 + np.random.rand(num_days) * 0.05),
            'low': price * (1 - np.random.rand(num_days) * 0.05),
            'close': price,
            'volume': np.random.randint(1000000, 10000000, num_days)
        }, index=dates)
        df.index.name = 'date'

        stock_data[f'STOCK_{i+1:03d}'] = df

    return stock_data


def demo():
    """演示"""
    print("=" * 60)
    print("演示: 股票筛选")
    print("=" * 60)

    from screener import StockScreener, PriceUp, RSIOversold, VolumeSpike, MACDGoldenCross

    stock_data = generate_sample_stock_data(20)

    screener = StockScreener()
    screener.add_condition(PriceUp())
    screener.add_condition(RSIOversold())
    screener.add_condition(VolumeSpike())
    screener.add_condition(MACDGoldenCross())

    print("过滤条件:")
    print("  1. 上涨")
    print("  2. RSI超卖")
    print("  3. 放量")
    print("  4. MACD金叉")

    results = screener.screen(stock_data)

    print("\n各条件过滤结果:")
    for name, stocks in results.items():
        print(f"  {name}: {len(stocks)}只")


if __name__ == "__main__":
    demo()
    print("\n" + "=" * 60)
    print("[DONE]")
    print("=" * 60)