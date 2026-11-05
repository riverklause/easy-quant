"""
测试不允许 Dict 类型输入的修改
验证指标计算器和具体指标是否能正确拒绝单个字典输入
"""

import pandas as pd
from indicators.technical.trend.moving_average import SMA, EMA, MACD
from indicators.base.calculator import IndicatorCalculator

# 测试数据
single_dict_data = {'code': '600000', 'close': 10.0}
list_dict_data = [{'code': '600000', 'close': 10.0}, {'code': '600000', 'close': 11.0}]
df_data = pd.DataFrame(list_dict_data)

print("=== 测试单个指标直接计算（验证不支持 Dict 输入）===")

# 测试 SMA
sma = SMA(period=2)
print("\n1. SMA 单个字典输入（应该失败）:")
try:
    sma_result_dict = sma.calculate(single_dict_data)
    print(f"返回类型: {type(sma_result_dict)}")
    print(f"返回值: {sma_result_dict}")
    print("错误：应该拒绝 Dict 类型输入")
except Exception as e:
    print(f"预期的错误: {type(e).__name__}: {e}")

# 测试 EMA
ema = EMA(period=2)
print("\n2. EMA 单个字典输入（应该失败）:")
try:
    ema_result_dict = ema.calculate(single_dict_data)
    print(f"返回类型: {type(ema_result_dict)}")
    print(f"返回值: {ema_result_dict}")
    print("错误：应该拒绝 Dict 类型输入")
except Exception as e:
    print(f"预期的错误: {type(e).__name__}: {e}")

# 测试 MACD
macd = MACD()
print("\n3. MACD 单个字典输入（应该失败）:")
try:
    macd_result_dict = macd.calculate(single_dict_data)
    print(f"返回类型: {type(macd_result_dict)}")
    print(f"返回值: {macd_result_dict}")
    print("错误：应该拒绝 Dict 类型输入")
except Exception as e:
    print(f"预期的错误: {type(e).__name__}: {e}")

print("\n=== 测试允许的输入类型（应该成功）===")

# 测试 list[Dict] 输入
print("\n1. SMA list[Dict] 输入:")
sma_result_list = sma.calculate(list_dict_data)
print(f"返回类型: {type(sma_result_list)}")
print(f"是否包含 'code' 列: {'code' in sma_result_list.columns}")
print(f"是否包含 'sma' 列: {'sma' in sma_result_list.columns}")
print(sma_result_list)

# 测试 DataFrame 输入
print("\n2. SMA DataFrame 输入:")
sma_result_df = sma.calculate(df_data)
print(f"返回类型: {type(sma_result_df)}")
print(f"是否包含 'code' 列: {'code' in sma_result_df.columns}")
print(f"是否包含 'sma' 列: {'sma' in sma_result_df.columns}")
print(sma_result_df)

print("\n测试完成!")
