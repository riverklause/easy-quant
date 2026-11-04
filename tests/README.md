# tests/

`test_lamps.py`、`test_realtime_lamps.py`、`test_indicator_contracts.py`、
`test_datafeed_frequency.py`、`test_storage_layout.py` 可在 pytest 下运行。
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
| E2 | 真实 feed 未自报来源 | 只有 E2 红（`_SpyFeed != datafeed`），E3 仍绿 | ✓ |
| E3 | mock 回落无标记 | 只有 E3 红 | ✓ |
| F2 | `allow_mock=False` 仍静默造数据 | 只有 F2 红 | ✓ |
| L5 | 端到端链路（装配→计算→信号→撮合→结果） | 与 E2 共享 `data_source` 语义；其余断言独立 | ✓ |
| F1 | 频率算出来却未透传给 DataManager | 只有 F1 红 | ✓ |
| F1b | 单只股票取数失败静默消失 | 只有 F1b 红 | ✓ |
| F3 | 指标错误藏在返回值角落，calculator 不 fail-closed | 与 F3b 共享 calculator 缺失 | ✓ |
| F3b | executor 吞掉指标异常 | 只有 F3b 红（F3 仍绿） | ✓ |
| R1 | 失败 symbol 的陈旧指标进入策略评估 | **两种回退红因不同**：删隔离 → 异常穿出 `_realtime_tick`；删过滤 → `seen == {"A","B"}` | ✓ |
| R2 | 连续失败不熔断，循环无限运行 | 去掉熔断块 → `ticks == 4504 != 2` | ✓ |
| R4 | 取消被吞，`task.cancelled()` 永为 False | 去掉 `raise` → `DID NOT RAISE CancelledError` | ✓ |
| R4b | 用户取消后 `stopped_reason` 为空 | 去掉赋值 → `None != "用户取消"` | ✓ |
| R3 | 任务异常退出无留痕（保护性灯） | 去掉 `_on_realtime_task_done` 的赋值 → `stopped_reason` 为空 | ✓ |
| T1 | 技术指标回显输入列（13 个指标） | 只回退 RSI → 仅 `T1[RSI]` 红，其余 14 个通过 | ✓ |
| T2 | 基本面输出键与声明不符（保护性灯） | 当前即绿 | ✓ |
| LS1 | 存储路径退化成扁平布局 | 回退 `build_path`/`build_meta_path` → 3 个 LS1 全红，其余 40 个通过 | ✓ |
| L6 / L6b | 仓位预算被硬编码、无法注入 | 回退成 `initial_capital * 0.1` → 只有 L6b 红（`10000 != 5000`），L6 仍绿 | ✓ |

R1 之后，L4b / L4b2 的绿依赖 L4c 的声明式装配；本表记录的是各自独立修复时的回退结果。

运行：

```powershell
python -m pytest tests -q
```
