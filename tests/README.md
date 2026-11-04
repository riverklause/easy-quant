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
| L4c | 策略未声明参数化的指标，引擎未装配 | 与 L4b/L4b2 共享缺失 | ✓ |
| L4c2 | 指标错误被逐 bar、逐策略两层 catch 吞掉 | 只有 L4c2 红 | ✓ |
| E1 | 失败计数未进结果、跨 run 累加 | 只有 E1 红（`2 == 1`） | ✓ |
| E2 / E3 | 结果未自报真实来源 / mock 回落无标记 | 只有 E2、E3 红 | ✓ |

R1 之后，L4b / L4b2 的绿依赖 L4c 的声明式装配；本表记录的是各自独立修复时的回退结果。

运行：

```powershell
python -m pytest tests -q
```
