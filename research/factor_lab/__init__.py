"""因子实验室：离线因子研究 / IC / 分档。

边界：research 层可以 import 生产包（indicators / data 等），但
生产包**不得**反向 import 本模块——见 FL0 边界灯。

公共子模块：
  adapter   — 把单 symbol 指标 calculate 结果拼成宽面板
  cross_section — 截面共用语义（paired_counts）
  ic        — 截面 RankIC + ic_summary
  decay     — IC 衰减（逐 horizon）
  labels    — 前瞻收益（标签层，因子侧严禁 import）
  panel     — per-symbol OHLCV → 宽表（to_panel + momentum）
  quantile  — 逐日分档平均前瞻收益
  factors   — 无量纲因子目录（rsi / atr_pct / bias / bollinger_pb …）
"""

from . import adapter, cross_section, decay, factors, ic, labels, panel, quantile

