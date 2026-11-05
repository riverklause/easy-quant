"""
测试KDJ指标的计算结果一致性
验证修改后的KDJ指标计算结果是否与预期一致
"""

import pandas as pd
import numpy as np
from indicators.technical.momentum.kdj import KDJ

# 创建测试数据
np.random.seed(42)
n_samples = 30

# 生成随机价格数据
dates = pd.date_range('2024-01-01', periods=n_samples, freq='D')
high = np.random.uniform(100, 110, n_samples)
low = np.random.uniform(90, 100, n_samples)
close = np.random.uniform(95, 105, n_samples)

# 确保价格关系：high >= close >= low
for i in range(n_samples):
    if high[i] < low[i]:
        high[i], low[i] = low[i], high[i]
    if close[i] < low[i]:
        close[i] = low[i] + np.random.uniform(0, 5)
    if close[i] > high[i]:
        close[i] = high[i] - np.random.uniform(0, 5)

# 创建DataFrame
df_data = pd.DataFrame({
    'date': dates,
    'high': high,
    'low': low,
    'close': close
})

# 创建list[Dict]格式数据
list_dict_data = []
for i in range(n_samples):
    list_dict_data.append({
        'date': dates[i],
        'high': high[i],
        'low': low[i],
        'close': close[i]
    })

print("=== 测试KDJ指标 (参数: k_period=9, d_period=3, smooth_period=3) ===")
kdj = KDJ(k_period=9, d_period=3, smooth_period=3)

# 测试DataFrame输入
print("\n1. DataFrame输入:")
kdj_result_df = kdj.calculate(df_data)
print(f"返回类型: {type(kdj_result_df)}")
print(f"形状: {kdj_result_df.shape}")
print(f"列名: {list(kdj_result_df.columns)}")
print(f"是否包含'k'列: {'k' in kdj_result_df.columns}")
print(f"是否包含'd'列: {'d' in kdj_result_df.columns}")
print(f"是否包含'j'列: {'j' in kdj_result_df.columns}")

# 显示前几行结果
print("\n前10行结果:")
print(kdj_result_df.head(10))

# 检查NaN值
print(f"\nNaN值统计:")
print(f"k列NaN数量: {kdj_result_df['k'].isna().sum()}")
print(f"d列NaN数量: {kdj_result_df['d'].isna().sum()}")
print(f"j列NaN数量: {kdj_result_df['j'].isna().sum()}")

# 测试list[Dict]输入
print("\n2. list[Dict]输入:")
kdj_result_list = kdj.calculate(list_dict_data)
print(f"返回类型: {type(kdj_result_list)}")
print(f"形状: {kdj_result_list.shape}")
print(f"列名: {list(kdj_result_list.columns)}")
print(f"是否包含'k'列: {'k' in kdj_result_list.columns}")
print(f"是否包含'd'列: {'d' in kdj_result_list.columns}")
print(f"是否包含'j'列: {'j' in kdj_result_list.columns}")

# 验证两种输入方式的结果是否一致
print("\n3. 验证结果一致性:")
if isinstance(kdj_result_list, pd.DataFrame) and isinstance(kdj_result_df, pd.DataFrame):
    # 比较数值列
    numeric_cols = ['k', 'd', 'j']
    all_match = True
    
    for col in numeric_cols:
        if col in kdj_result_list.columns and col in kdj_result_df.columns:
            # 处理NaN值
            list_vals = kdj_result_list[col].fillna(-999)
            df_vals = kdj_result_df[col].fillna(-999)
            
            # 比较数值
            if np.allclose(list_vals, df_vals, rtol=1e-10, atol=1e-10, equal_nan=True):
                print(f"  {col}列: 结果一致 ✓")
            else:
                print(f"  {col}列: 结果不一致 ✗")
                all_match = False
                # 显示差异
                diff_mask = ~np.isclose(list_vals, df_vals, rtol=1e-10, atol=1e-10, equal_nan=True)
                diff_indices = np.where(diff_mask)[0]
                print(f"    差异位置: {diff_indices[:5]}...")
                for idx in diff_indices[:3]:
                    print(f"    位置{idx}: list={list_vals.iloc[idx]}, df={df_vals.iloc[idx]}")
        else:
            print(f"  {col}列: 列不存在 ✗")
            all_match = False
    
    if all_match:
        print("\n✓ 所有结果一致！")
    else:
        print("\n✗ 存在不一致的结果！")

# 手动计算验证
print("\n4. 手动计算验证:")
# 使用标准KDJ公式验证
def manual_kdj(high, low, close, k_period=9, d_period=3, smooth_period=3):
    n = len(close)
    raw_k_values = np.full(n, np.nan)
    k_values = np.full(n, np.nan)
    d_values = np.full(n, np.nan)
    j_values = np.full(n, np.nan)
    
    # 第一步：计算raw_k
    for i in range(k_period-1, n):
        # 计算周期内最高价和最低价
        period_high = np.max(high[i-k_period+1:i+1])
        period_low = np.min(low[i-k_period+1:i+1])
        
        if period_high != period_low:
            # 计算%K
            raw_k = 100 * (close[i] - period_low) / (period_high - period_low)
        else:
            raw_k = 50  # 避免除零
        
        raw_k_values[i] = raw_k
    
    # 第二步：平滑raw_k得到k值
    for i in range(k_period + smooth_period - 2, n):
        k_values[i] = np.mean(raw_k_values[i-smooth_period+1:i+1])
    
    # 第三步：计算d值（平滑k值）
    for i in range(k_period + smooth_period + d_period - 3, n):
        d_values[i] = np.mean(k_values[i-d_period+1:i+1])
    
    # 第四步：计算j值
    for i in range(k_period + smooth_period + d_period - 3, n):
        if not np.isnan(k_values[i]) and not np.isnan(d_values[i]):
            j_values[i] = 3 * k_values[i] - 2 * d_values[i]
    
    return k_values, d_values, j_values

manual_k, manual_d, manual_j = manual_kdj(high, low, close)

print(f"手动计算k值前10个: {manual_k[:10]}")
print(f"KDJ计算k值前10个: {kdj_result_df['k'].values[:10]}")

# 比较手动计算和KDJ计算的结果
# 首先检查非NaN值的数量
manual_k_non_nan = manual_k[~np.isnan(manual_k)]
kdj_k_non_nan = kdj_result_df['k'].values[~np.isnan(kdj_result_df['k'])]

print(f"\n非NaN值数量统计:")
print(f"  手动计算k值非NaN数量: {len(manual_k_non_nan)}")
print(f"  KDJ计算k值非NaN数量: {len(kdj_k_non_nan)}")
print(f"  手动计算d值非NaN数量: {len(manual_d[~np.isnan(manual_d)])}")
print(f"  KDJ计算d值非NaN数量: {len(kdj_result_df['d'].values[~np.isnan(kdj_result_df['d'])])}")
print(f"  手动计算j值非NaN数量: {len(manual_j[~np.isnan(manual_j)])}")
print(f"  KDJ计算j值非NaN数量: {len(kdj_result_df['j'].values[~np.isnan(kdj_result_df['j'])])}")

# 只比较共同的部分
min_len = min(len(manual_k_non_nan), len(kdj_k_non_nan))
if min_len > 0:
    k_match = np.allclose(manual_k_non_nan[:min_len], 
                          kdj_k_non_nan[:min_len], 
                          rtol=1e-10, atol=1e-10, equal_nan=True)
    
    manual_d_non_nan = manual_d[~np.isnan(manual_d)]
    kdj_d_non_nan = kdj_result_df['d'].values[~np.isnan(kdj_result_df['d'])]
    min_len_d = min(len(manual_d_non_nan), len(kdj_d_non_nan))
    d_match = np.allclose(manual_d_non_nan[:min_len_d], 
                          kdj_d_non_nan[:min_len_d], 
                          rtol=1e-10, atol=1e-10, equal_nan=True)
    
    manual_j_non_nan = manual_j[~np.isnan(manual_j)]
    kdj_j_non_nan = kdj_result_df['j'].values[~np.isnan(kdj_result_df['j'])]
    min_len_j = min(len(manual_j_non_nan), len(kdj_j_non_nan))
    j_match = np.allclose(manual_j_non_nan[:min_len_j], 
                          kdj_j_non_nan[:min_len_j], 
                          rtol=1e-10, atol=1e-10, equal_nan=True)
    
    print(f"\n手动计算验证:")
    print(f"  k值一致性: {'✓' if k_match else '✗'}")
    print(f"  d值一致性: {'✓' if d_match else '✗'}")
    print(f"  j值一致性: {'✓' if j_match else '✗'}")
    
    if k_match and d_match and j_match:
        print("\n✓ KDJ指标计算正确！")
    else:
        print("\n✗ KDJ指标计算可能存在问题！")
        
        # 显示具体差异
        if not k_match and min_len > 0:
            print(f"\nk值差异:")
            for i in range(min(min_len, 5)):
                diff = abs(manual_k_non_nan[i] - kdj_k_non_nan[i])
                print(f"  位置{i}: 手动={manual_k_non_nan[i]:.6f}, KDJ={kdj_k_non_nan[i]:.6f}, 差异={diff:.6f}")
else:
    print("\n⚠ 没有足够的非NaN值进行比较！")

print("\n测试完成！")