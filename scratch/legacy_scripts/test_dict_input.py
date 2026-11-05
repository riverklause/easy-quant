"""
测试 Dict 类型输入数据的处理
验证指标计算器和具体指标是否能正确处理单个字典输入
"""

import pandas as pd
from indicators.technical.trend.moving_average import SMA, EMA
from indicators.base.calculator import IndicatorCalculator

# 测试数据
single_dict_data = {'code': '600000', 'close': 10.0}

print("=== 测试单个指标直接计算（Dict 输入）===")

# 测试 SMA
sma = SMA(period=2)
print("\n1. SMA 单个字典输入:")
sma_result_dict = sma.calculate(single_dict_data)
print(f"返回类型: {type(sma_result_dict)}")
print(f"返回值: {sma_result_dict}")

# 测试 EMA
ema = EMA(period=2)
print("\n2. EMA 单个字典输入:")
ema_result_dict = ema.calculate(single_dict_data)
print(f"返回类型: {type(ema_result_dict)}")
print(f"返回值: {ema_result_dict}")

print("\n=== 测试指标计算器（Dict 输入）===")

# 初始化计算器
calculator = IndicatorCalculator()

# 注册指标
sma_id = calculator.register_indicator(SMA(period=2), 'sma')
ema_id = calculator.register_indicator(EMA(period=2), 'ema')

# 测试单个指标计算
print("\n1. 单个指标计算:")
sma_result = calculator.calculate(sma_id, single_dict_data)
print(f"SMA 结果: {sma_result}")

ema_result = calculator.calculate(ema_id, single_dict_data)
print(f"EMA 结果: {ema_result}")

# 测试批量计算
print("\n2. 批量计算:")
batch_result = calculator.batch_calculate(single_dict_data, [sma_id, ema_id])
print(f"批量计算结果: {batch_result}")

print("\n测试完成!")
