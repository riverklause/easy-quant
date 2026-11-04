# tests/

当前只有 `test_lamps.py` 与 `test_datafeed_frequency.py` 可在 pytest 下运行。
其余历史脚本已移至 `scratch/legacy_scripts/`。

## 灯与回退矩阵

| 灯 | 钉住的 bug | 只回退对应修复时的结果 | 已验证 |
|---|---|---|---|
| L1 | 买入记账 | —（保护性灯） | ✓ |
| L2 / L2b | 平仓盈亏、毛/净费用语义 | 只有 L2、L2b 红 | ✓ |
| L3a | SELL 分支的 `.get()` | 只有 L3a 红 | ✓ |
| L3b | `try` 包住整个信号循环 | 只有 L3b 红，L3a 仍绿 | ✓ |
| L4a | 取数未委托 datafeed | 只有 L4a 红 | ✓ |
| L4b | 引擎未把指标喂给策略 | 只有 L4b 红 | ✓ |
| L4b2 | 信号列表被整包塞进 signal 字段 | 只有 L4b2 红 | ✓ |

运行：

```powershell
python -m pytest tests -q
```
