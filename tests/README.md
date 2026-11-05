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
| E4 | 落盘丢 `execution_failures` / `data_source` | 只回退 `data_source` 一行 → 仅 E4 红（`'' != 'mock'`） | ✓ |
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
| T1 | 技术指标回显输入列（14 个指标） | 只回退 RSI → 仅 `T1[RSI]` 红，其余 14 个通过 | ✓ |
| T2 | 基本面输出键与声明不符（保护性灯） | 当前即绿 | ✓ |
| T3 | 指标用了未来数据（全序列统计量） | 14 个技术指标全绿；`_LookAheadIndicator` 自检在 t=10 判红 | ✓ |
| LS1 | 存储路径退化成扁平布局 | 回退 `build_path`/`build_meta_path` → 3 个 LS1 全红，其余全绿 | ✓ |
| L6 / L6b | 仓位预算被硬编码、无法注入 | 回退成 `initial_capital * 0.1` → 只有 L6b 红（`10000 != 5000`），L6 仍绿 | ✓ |
| L7 | 指标取 batch 第一个 key，拿错股票 | 回退成 `next(iter(...))` → 只有 L7 红（`11700.0 != 11.7`） | ✓ |
| L8 | 每 bar 重算整个历史窗口（O(T²)） | 回退预计算 → 只有 L8 红（`775 != 40`），L8a 仍绿 | ✓ |
| L8a | 预计算切片越界（看到未来 / 值不符） | 保护性灯（当前即绿） | ✓ |
| L9 | ADX 条件取整行 Series 而非 `adx` 列 | 回退成 `result.iloc[-1]` → 只有 L9 红（Series 歧义布尔） | ✓ |
| LG0 | `utils/` 下模块导入即崩（`settings.LOG_LEVEL` / `DATA_BASE_PATH`） | 回退 `utils/logger.py` → 4 个 LG0 全红（`AttributeError: LOG_LEVEL`）；回退 `file_utils` 的两处引用 → 只有 LG0[file_utils] 红（`DATA_BASE_PATH`） | ✓ |
| LG1 | `configure_logging` 重复调用叠加 handler（保护性灯） | 去掉 handler 清理 → `assert 6 == 2`（pytest 自有 4 个 + 我们的 2 个）；只去掉 `_CONFIGURED` 仍绿 | ✓ |
| LG1b | 摘掉 handler 未 `close()`，泄漏文件句柄（保护性灯） | 去掉 `handler.close()` → 只有 LG1b 红（`stream is None` 断言失败），LG1 仍绿 | ✓ |
| LG2 | utils/ 下第三方 import 必须在 requirements.txt 里声明 | 删掉 `holidays` 行 → 只有 LG2 红；反向（requirements 写了没人用）暂未覆盖 | ✓ |
| LG3 | `utils.date_utils` 可导入（依赖 `holidays`） | 装包后自动生效；目前以 skipped 形式存在，不藏着 | ✓（skipped）|
| S1 | `StockScreener` 暴露条件失败（不静默吞） | 去掉 `logger.exception` + `condition_errors` 计数 + `fail_fast` 开关 → S1 两测试红（AttributeError / TypeError） | ✓ |
| S2 | `StochasticOversold/Overbought` 可评估（复用 KDJ） | 回退成原 `Stochastic` 不存在的 import → S2 两测试都是 ModuleNotFoundError 红 | ✓ |
| M1 | `run()` / `run_async()` 两条入口产出相同结果（合并后成同一实现） | 保护性灯；当前即绿，合并后仍绿（证明"结果一致"而不是"实现方式"） | ✓ |
| M2 | `run_async(symbols=None)` 回落到默认标的（async 路径以前绕过 `_load_data`） | 合并前红（`TypeError: 'NoneType' object is not iterable`），合并修掉；回退 `_load_data` 里的 `symbols is None` 解析 → 只有 M2 红，M1 不受影响 | ✓ |
| P1 | 三个预定义组合是配置草稿——必须可导入且声明策略槽位 | 保护性灯；删除某个 preset 或改 `_build_portfolio` 为空 → 只有 P1 红 | ✓ |
| FL0 | 生产包（backtest/data/indicators/screener/strategy/web）不得 import research | 保护性；今天即绿；在生产包里写 `import research.xxx` → 只有 FL0 红 | ✓ |
| FL1 | 因子面板因果性——t 列只依赖 ≤t 的数据（与 T3 同范式） | 回退 `momentum` 加 `.shift(-1)` 泄漏未来 → 只有 FL1 红（位置 5 第一次 diff，`nan != 0.0495...`） | ✓ |
| FL1b | `to_panel` 按日期并集对齐、缺失保留 NaN | 回退为 inner join → 只有 FL1b 红（`assert 39 == 40`） | ✓ |
| FL2 | 同序因子/标签 → RankIC 恒为 1（守方向/符号） | 与 FL2b 同回退：去掉 rank 变 Pearson → FL2 仍绿（Pearson 对同序也是 1）、FL2b 红 | ✓ |
| FL2b | 单调变换不改变秩 → RankIC 不变（钉住 Spearman 秩相关） | 去掉 `.rank(axis=1)` → 只有 FL2b 红（Pearson 对 `exp` 敏感，Series 100% 不同），FL2 不受影响 | ✓ |
| FL3 | 3 只股票 + min_stocks=5 → 全部丢弃 + 必须留下 warning 日志 | 回退 1（不做 min_stocks 过滤）→ FL3 和 FL3b 都红；FL3b 守单位 | ✓ |
| FL3b | 10 列但某日成对有效只有 2 → 该日丢弃（钉住有效样本单位） | 回退 2（counts = len(common) 数列数）→ **只有 FL3b 红**（assert 5 == 4），FL3 仍绿（common=3 本来就 < 5） | ✓ |
| FL4 | 标签随因子单调递增 ⇒ 五档平均前瞻收益必须单调递增（含 Q5-Q1 > 0） | 与 FL4c 同回退：method="average" → FL4 仍绿（连续值无并列）、FL4c 红 | ✓ |
| FL4b | 10 列但某日成对有效只有 2 → 该日整行丢弃（与 rank_ic 同一 min_stocks 语义） | 删掉 `result.where(~too_small)` 过滤 → **只有 FL4b 红**（该行被保留在 q.index 里），FL4/FL4c 不受影响 | ✓ |
| FL4c | 全并列值 + method="first" → 按列顺序切五档，无空档 | 改成默认 method="average" → **只有 FL4c 红**（Q2/Q3/Q4/Q5 NaN），FL4/FL4b 不受影响 | ✓ |
| FL5 | adapter 拼宽面板 + 因果性（截断重算与全量切片一致） | T3 已钉住每个指标因果，adapter 只循环调用，这盏灯是保护性的（今天直接绿） | ✓ |
| FL5b | field 不在 output_fields → ValueError（不是 pandas KeyError） | 去掉 check → 只有 FL5b 红（抛出 `KeyError: 'bogus'`，pytest.raises(ValueError) 不匹配） | ✓ |
| FL6 | 目录内每个因子：价格整体乘 100 → 因子面板不变（尺度不变）；参数化到 `factors.__all__`，新增因子自动继承 | atr_pct_factor 去掉 /close → **只有 `[atr_pct_factor]` 红**（ATR 正好乘 100，`0.144` vs `14.47`）；cci_factor 混入 `+close` → **只有 `[cci_factor]` 红**，其余 7 个参数绿（参数化按因子隔离，不是一个大 assert） | ✓ |
| FL6-macd | 同上，覆盖 `macd_hist_pct_factor`（价格量纲必须归一化） | 先 `return hist`（不除 close）→ **只有 `[macd_hist_pct_factor]` 红**（缩放后数值正好 100 倍）；补 `/ close` → 绿。这是参数化后第一次抓到新因子漏归一化 | ✓ |
| FL7 | `ic_summary` 精确算术钉住 ddof=1 与 IR 定义 | `ic.std(ddof=1)` → `ddof=0` → **只有 FL7 红**（std 0.1027 vs 期望 0.1258，IR 差 22%） | ✓ |
| FL7b | `ic_decay` 结构：h=1 时 IC=1 且随 horizon 严格下降（`diff()<0`），n 递减 | 所有 horizon 固定成 1 → **只有 FL7b 红**（mean_ic 全等 `1.0 1.0 1.0 1.0`，严格下降失败） | ✓ |
| FL7c | `ic_summary` 空序列不抛：n=0、其余 NaN | —（保护性灯，未单独立回退） | ✓ |
| FL8 | 因子相关性矩阵的秩语义：单调变换 → 1、`f` 与 `-f` → −1、矩阵对称、对角为 1 | 去掉 `.rank(axis=1)` 变 Pearson → **只有 FL8 红**（0.9254 vs `1.0`），FL8b/FL8c 绿 | ✓ |
| FL8b | 逐日截面相关**再取均值**，不等于把面板堆起来算（钉住"不混时间维度"） | 改成对整面板算 Spearman（n 仍按逐日）→ **只有 FL8b 红**（0.1959 vs 0.2952），FL8/FL8c 绿 | ✓ |
| FL8c | 复用 `min_stocks`：某日成对样本 2 < 5 → 该日不进平均、n 少 1、矩阵对称 | 去掉 `.where(paired_counts(...) >= min_stocks)` → **只有 FL8c 红**（`6 != 5`），FL8/FL8b 绿 | ✓ |
| FL9 | `rank_ic` 的秩在**成对支撑集**上取（A 全支撑 [1..6]、B 只 3 只且反向 → 必须是 −1.0） | `paired_rank_corr` 去掉 `.where(mask)` → FL9/FL9b 红（回到 −0.9934），其余 105 绿 | ✓ |
| FL9b | `factor_correlation` 与 `rank_ic` 共用**同一份**实现，不是各自恰好算对 | `_cross_section_rank_corr` 改回自己取秩 → **只有 FL9b 红**、FL9 绿 | ✓ |
| FL10 | `ACTIVE` 剪枝名单非空、无重复、每个名字都在 `__all__` 里 | —（保护性灯：名单本身是数据，没有对应可回退的实现） | ✓ |

R1 之后，L4b / L4b2 的绿依赖 L4c 的声明式装配；本表记录的是各自独立修复时的回退结果。

### 已知缺口

- `utils/date_utils.py` 依赖 `holidays`，已在 `requirements.txt` 声明但当前环境未安装：`LG3` 以 skipped 形式存在，装包后自动启用，届时 `LG0` 可把该模块加回导入清单。

运行：

```powershell
python -m pytest tests -q
```
