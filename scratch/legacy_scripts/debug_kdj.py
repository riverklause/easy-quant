"""
调试KDJ指标计算过程
详细分析每一步的计算结果
"""

import pandas as pd
import numpy as np
from indicators.technical.momentum.kdj import KDJ

# 创建简单的测试数据，便于手动验证
n_samples = 15
dates = pd.date_range('2024-01-01', periods=n_samples, freq='D')

# 创建有规律的数据，便于手动计算
high = [105, 108, 110, 107, 109, 112, 115, 113, 111, 114, 116, 118, 117, 119, 120]
low = [95, 98, 100, 97, 99, 102, 105, 103, 101, 104, 106, 108, 107, 109, 110]
close = [100, 103, 105, 102, 104, 107, 110, 108, 106, 109, 111, 113, 112, 114, 115]

# 创建DataFrame
df_data = pd.DataFrame({
    'date': dates,
    'high': high,
    'low': low,
    'close': close
})

print("=== 测试数据 ===")
print(df_data)
print()

# 创建KDJ指标实例
kdj = KDJ(k_period=5, d_period=3, smooth_period=3)  # 使用较小的周期便于调试

# 手动计算每一步
print("=== 手动计算步骤 ===")

# 步骤1: 计算5周期内最高价和最低价
df = df_data.copy()
df['rolling_high'] = df['high'].rolling(window=5).max()
df['rolling_low'] = df['low'].rolling(window=5).min()

print("1. 滚动窗口计算:")
print(df[['date', 'high', 'low', 'close', 'rolling_high', 'rolling_low']])
print()

# 步骤2: 计算 high_minus_low 和 close_minus_low
df['high_minus_low'] = df['rolling_high'] - df['rolling_low']
df['close_minus_low'] = df['close'] - df['rolling_low']

print("2. 差值计算:")
print(df[['date', 'close', 'rolling_low', 'close_minus_low', 'rolling_high', 'high_minus_low']])
print()

# 步骤3: 计算 raw_k
df['raw_k'] = 100 * (df['close_minus_low'] / df['high_minus_low'])

print("3. raw_k计算:")
print(df[['date', 'close_minus_low', 'high_minus_low', 'raw_k']])
print()

# 步骤4: 平滑k值
df['k'] = df['raw_k'].rolling(window=3).mean()

print("4. k值平滑:")
print(df[['date', 'raw_k', 'k']])
print()

# 步骤5: 计算d值
df['d'] = df['k'].rolling(window=3).mean()

print("5. d值计算:")
print(df[['date', 'k', 'd']])
print()

# 步骤6: 计算j值
df['j'] = 3 * df['k'] - 2 * df['d']

print("6. j值计算:")
print(df[['date', 'k', 'd', 'j']])
print()

# 使用KDJ类计算
print("=== KDJ类计算结果 ===")
kdj_result = kdj.calculate(df_data)
print(kdj_result[['date', 'k', 'd', 'j']])
print()

# 比较结果
print("=== 结果比较 ===")
print("手动计算 vs KDJ类计算:")

for i in range(len(df)):
    manual_k = df['k'].iloc[i] if not pd.isna(df['k'].iloc[i]) else 'NaN'
    kdj_k = kdj_result['k'].iloc[i] if not pd.isna(kdj_result['k'].iloc[i]) else 'NaN'
    
    manual_d = df['d'].iloc[i] if not pd.isna(df['d'].iloc[i]) else 'NaN'
    kdj_d = kdj_result['d'].iloc[i] if not pd.isna(kdj_result['d'].iloc[i]) else 'NaN'
    
    manual_j = df['j'].iloc[i] if not pd.isna(df['j'].iloc[i]) else 'NaN'
    kdj_j = kdj_result['j'].iloc[i] if not pd.isna(kdj_result['j'].iloc[i]) else 'NaN'
    
    print(f"行{i}: k={manual_k}/{kdj_k}, d={manual_d}/{kdj_d}, j={manual_j}/{kdj_j}")

# 检查KDJ类内部计算
print("\n=== 分析KDJ类内部计算 ===")

# 重新读取KDJ类代码，分析计算逻辑
print("从kdj.py分析计算逻辑:")
print("1. high_minus_low = df['high'].rolling(window=self.k_period).max() - df['low'].rolling(window=self.k_period).min()")
print("2. close_minus_low = df['close'] - df['low'].rolling(window=self.k_period).min()")
print("3. raw_k = 100 * (close_minus_low / high_minus_low)")
print("4. k = raw_k.rolling(window=self.smooth_period).mean()")
print("5. d = k.rolling(window=self.d_period).mean()")
print("6. j = 3 * k - 2 * d")

# 检查是否有除零处理
print("\n检查除零处理:")
print("当前代码中没有显式的除零处理，当high_minus_low为0时会产生inf或nan")

# 验证一个具体位置的计算
print("\n=== 验证第9行计算（索引8）===")
print(f"数据: high={high[8]}, low={low[8]}, close={close[8]}")

# 计算5周期窗口（索引4-8）
window_high = max(high[4:9])  # 索引4,5,6,7,8
window_low = min(low[4:9])
print(f"5周期窗口(4-8): 最高价={window_high}, 最低价={window_low}")

if window_high != window_low:
    raw_k = 100 * (close[8] - window_low) / (window_high - window_low)
    print(f"raw_k = 100 * ({close[8]} - {window_low}) / ({window_high} - {window_low}) = {raw_k}")
else:
    print("窗口最高价等于最低价，无法计算raw_k")

print("\n调试完成！")