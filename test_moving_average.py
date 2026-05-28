"""
测试移动平均线指标的修改
验证 list[Dict] 输入时是否返回包含股票代码的完整 DataFrame
"""

import pandas as pd
from indicators.technical.trend.moving_average import SMA, EMA, MACD

# 测试数据
list_dict_data = [
    {'code': '600000', 'close': 10.0},
    {'code': '600000', 'close': 11.0},
    {'code': '600000', 'close': 12.0},
    {'code': '600000', 'close': 13.0},
    {'code': '600000', 'close': 14.0}
]

df_data = pd.DataFrame(list_dict_data)
series_data = df_data['close']

print("=== 测试 SMA ===")
sma = SMA(period=2)

# 测试 list[Dict] 输入
print("\n1. list[Dict] 输入:")
sma_result_list = sma.calculate(list_dict_data)
print(f"返回类型: {type(sma_result_list)}")
print(f"是否包含 'code' 列: {'code' in sma_result_list.columns}")
print(f"是否包含 'sma' 列: {'sma' in sma_result_list.columns}")
print(sma_result_list)

# 测试 DataFrame 输入
print("\n2. DataFrame 输入:")
sma_result_df = sma.calculate(df_data)
print(f"返回类型: {type(sma_result_df)}")
print(f"是否包含 'code' 列: {'code' in sma_result_df.columns}")
print(f"是否包含 'sma' 列: {'sma' in sma_result_df.columns}")
print(sma_result_df)

# 测试 Series 输入
print("\n3. Series 输入:")
sma_result_series = sma.calculate(series_data)
print(f"返回类型: {type(sma_result_series)}")
print(sma_result_series)

print("\n=== 测试 EMA ===")
ema = EMA(period=2)

# 测试 list[Dict] 输入
print("\n1. list[Dict] 输入:")
ema_result_list = ema.calculate(list_dict_data)
print(f"返回类型: {type(ema_result_list)}")
print(f"是否包含 'code' 列: {'code' in ema_result_list.columns}")
print(f"是否包含 'ema' 列: {'ema' in ema_result_list.columns}")
print(ema_result_list)

print("\n=== 测试 MACD ===")
macd = MACD()

# 测试 list[Dict] 输入
print("\n1. list[Dict] 输入:")
macd_result_list = macd.calculate(list_dict_data)
print(f"返回类型: {type(macd_result_list)}")
print(f"是否包含 'code' 列: {'code' in macd_result_list.columns}")
print(f"是否包含 'macd' 列: {'macd' in macd_result_list.columns}")
print(f"是否包含 'signal' 列: {'signal' in macd_result_list.columns}")
print(f"是否包含 'histogram' 列: {'histogram' in macd_result_list.columns}")
print(macd_result_list)

print("\n测试完成!")
