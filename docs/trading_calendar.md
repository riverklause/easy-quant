# 交易日历设计

> 状态：P0 已封版（能力层 + CAL-01～40 测试；尚未接入现有调用）
> 最后更新：2026-11-16
> 适用范围：港股（HK）、美股（US）、A 股（仅 SH/SZ，不含北交所）

## 1. 背景

项目此前判断交易日只有两种方式：

- `utils/date_utils.py` 用 `holidays` 在本地推算公众假期；
- 回测/数据层直接用行情数据里的日期，或用 `pd.date_range(freq='B')` 工作日。

两者都不等于交易所日历：港股佛诞、重阳、圣诞前夕，美股感恩节次日、平安夜提前收市，A 股春节/国庆调休，都可能被算错。本项目改为以富途 `request_trading_days` 为权威来源，并把结果缓存到本地，供回测和离线场景复用。

## 2. 结论摘要

- 唯一权威来源：富途 `OpenQuoteContext.request_trading_days`，缓存只能由它写入。
- 取数顺序：**本地缓存（完整覆盖；当年未过 TTL）→ futu → 本地缓存（仅完整覆盖，WARNING）→ 抛错**。不做任何自动兜底，也不做工作日降级；缓存覆盖不完整不得返回（未来侧按 §6.4 夹取是唯一例外）。
- 不使用 `holidays`、`yfinance` 指数历史、`exchange_calendars` 作为日历来源，也不做官方 CSV 灾备导入。
- 缓存按市场单文件保存，带 coverage 元数据，写路径加短文件锁。
- 日期语义为「市场 session date」：US 用 `America/New_York`，HK 用 `Asia/Hong_Kong`，CN 用 `Asia/Shanghai`。
- 半天市保留 `session_type` 与可空的 `close_time`，既覆盖港股「上午收市」，也覆盖美股「提前收市」。
- 回测引擎继续用行情数据日期并集，日历只做卫生过滤，不改变日轴生成方式。
- 限流只做进程内 pacing 与退避，不做跨进程锁；首次全量回填需避免多进程同时执行。

## 3. 接口约束（必须遵守）

富途 `request_trading_days` 的限制：

| 约束 | 数值 | 对设计的要求 |
|---|---|---|
| 频率 | 每 30 秒最多 30 次 | 进程内最小间隔 1.1 秒；失败指数退避；按年切块 |
| 历史范围 | 过去 10 年 | 请求前按 `today - 10 年` 校验；更早年份只读缓存 |
| 未来范围 | 到今年 12 月 31 日 | 部分越界夹到 12/31；整段越界或向未来跨年直接报错，不造日期 |

补充事实（futu 10.12.7208 源码确认；OpenD 实测见 §10.3）：

- 返回 `(RET_OK, list[dict])`，每项形如 `{"time": "2024-01-02", "trade_date_type": "WHOLE"}`；旧版本可能是 DataFrame，需要兼容。
- `trade_date_type` 取值：`WHOLE`（全天）、`MORNING`（上午交易、下午休市）、`AFTERNOON`（下午交易、上午休市）。
- `market` 取值：`HK` / `US` / `CN` / `NT` / `ST` / `SG` / `JP` / `MY` / `JP_FUTURE` / `SG_FUTURE`；没有 `SH`/`SZ`，需归一为 `CN`。
- 传 `code` 时富途会忽略 `market`，本设计不使用 `code` 路径。
- 失败返回 `RET_ERROR` 加错误描述字符串，必须显式转异常。
- 接口依赖 OpenD 常驻，离线环境拿不到。

请求预算（按自然年切块）：

| 场景 | 请求数 | pacing 后耗时 |
|---|---|---|
| 单市场 1 年 | 1 | 约 0 秒 |
| 单市场 10 年（跨 11 个自然年） | 11 | 约 12 秒 |
| 双市场 10 年 | 22 | 约 24 秒 |
| 三市场 10 年 | 33 | 约 36 秒 |
| 缓存命中 | 0 | 0 |

## 4. 术语与数据模型

### 4.1 session date

日历中的日期一律是「该市场本地日期」，不是上海日期。

- US：`America/New_York`；
- HK：`Asia/Hong_Kong`；
- CN：`Asia/Shanghai`。

换算规则：`session_date(market, as_of) = as_of.astimezone(市场时区).date()`。

入参时间规则：

- 日期型入参（`date` / `YYYY-MM-DD` 字符串 / **naive** 零点 `Timestamp`）：视为**市场本地日期**，不做时区换算；tz-aware 的零点 `Timestamp` 不算日期，一律按时刻换算；
- 带时分秒的 `datetime`：必须 tz-aware，直接换算到市场时区；
- **拒绝 naive 的带时分秒输入**（如 `datetime.now()`）：抛 `ValueError`。naive 一律按市场本地时间解释会埋雷——上海时间直接传给 US 会整体偏一天；
- `is_trading_time` 只接受 tz-aware 时刻，不接受 naive `datetime`；`session_date` 接受上面的日期型入参或 tz-aware 时刻，按上述规则换算；
- 对外返回的日期统一为 naive 的 session date（`datetime64[ns]`，零点），不带时区；时区换算只在边界层完成。

示例：上海 11-13 08:00，纽约为 11-12 19:00，美股 session date 是 11-12，不是 11-13。需要「下一个 session」时，对 session date 调用 `next_trading_day`，不要直接拿上海日期查。

### 4.2 日历行

| 字段 | 类型 | 说明 |
|---|---|---|
| `date` | `datetime64[ns]` | 市场 session date，归一到零点（naive，不带时区） |
| `session_type` | `WHOLE` / `MORNING` / `AFTERNOON` | 来自 futu 的 `trade_date_type` |
| `close_time` | `str` 或空 | 市场本地时间 `HH:MM`；只用于「全天但提前收市」，由 override 在查询层合并，不落缓存 |

行级不写 `source`：只有 futu 能写盘，溯源信息统一放在 meta 的 `source` 中。

非交易日不写入数据表，但「不在表中」只有在**已覆盖区间内**才等价于休市：

- `is_trading_day(day)` / `get_session_type(day)` / `get_trading_days` / `get_calendar_frame` / `next_trading_day` / `previous_trading_day`：先确保请求区间落在 `covered_intervals` 内（必要时按 §6/§7 补拉）；补拉后仍无覆盖时——窗口外抛 `CalendarOutOfRange`，窗口内取数失败抛 `CalendarUnavailable`。
- **未覆盖绝不能当成休市**；周六/周日是结构性休市，无需覆盖（见 §7.3）；`get_session_type` 返回 `None` 表示「已覆盖的休市日」或「结构性周末」。
- 读接口不得返回部分结果：请求区间缺一段就报错并列出缺失区间，不做静默截断。唯一例外是未来侧越界，按 §6.4 夹取到 12/31 并 WARNING。

### 4.3 交易时段

`is_trading_time` 根据 `session_type` 与 `close_time` 计算，市场默认时段如下：

| 市场 | 上午 | 午休 | 下午 | 默认收盘 |
|---|---|---|---|---|
| HK | 09:30–12:00 | 12:00–13:00 | 13:00–16:00 | 16:00 |
| US | 09:30–16:00 | 无 | 无 | 16:00 |
| CN | 09:30–11:30 | 11:30–13:00 | 13:00–15:00 | 15:00 |

每个市场的默认时段用 **segments 列表**表示，`close_time` 只截断最后一个 segment：

- HK：`[(09:30, 12:00), (13:00, 16:00)]`
- US：`[(09:30, 16:00)]`（无午休，实现时不要套用 HK 的午休字段）
- CN：`[(09:30, 11:30), (13:00, 15:00)]`

推导规则：

- `WHOLE`：使用全部 segments；若 `close_time` 非空，把最后一个 segment 的结束时间改为 `close_time`（美股提前收市走这条）；
- `MORNING`：只保留第一个 segment；`close_time` 非空时覆盖该 segment 的结束时间（港股半日默认 12:00，通常不需要 close_time）；
- `AFTERNOON`：保留午休结束后的 segment；
- 非交易日：空。

时段判断不包含开市前竞价与收市竞价，仅覆盖连续交易时段。

## 5. 来源与优先级

```
本地缓存（请求区间完整覆盖；当年未过 TTL）
        ↓ 未覆盖 / 已过期
futu request_trading_days
        ↓ 失败 / 不可用 / 限流
本地缓存（仅当请求区间完整覆盖，WARNING）
        ↓ 仍有缺失
抛 CalendarUnavailable（列出缺失区间）
```

明确不采用的方案及原因：

| 方案 | 不采用原因 |
|---|---|
| `holidays` | 只覆盖公众假期，不含交易所临时休市、半天市；错法不可控 |
| `yfinance.Calendars` | 只提供财报/IPO/经济事件/拆股日历，不提供交易日 |
| yfinance 指数历史反推 | 依赖网络/代理，Yahoo 缺一天会被误判为休市；没有未来日期 |
| `exchange_calendars` | 规则型日历，临时休市、临时改期、规则变更依赖包更新，仍可能静默算错 |
| 官方 CSV 手工导入 | 已决策不做自动/手工灾备；缓存是唯一离线来源 |

原则：**宁可失败，不静默算错**。调用方拿到 `CalendarUnavailable` 时必须明确失败或展示不可用，不能退回工作日。

## 6. 可取窗口

```
fetchable_start = today - 10 年
fetchable_end   = 今年 12 月 31 日
```

规则：

1. 请求前先按窗口校验 `[start, end]`；越界部分按下面第 3～6 条处理，不做静默截断。
2. 边界年份只请求窗口内那一段。例如 2026-11 时，2016 年只取 11 月之后的部分；coverage 记录实际区间，不假装覆盖全年。
3. 历史侧越界（`start` 早于 10 年窗口）：已有缓存则读缓存；缺缓存部分直接抛 `CalendarOutOfRange`，**不允许截断后继续**，否则回测会静默少算一段历史。
4. 未来侧越界（`end` 晚于今年 12/31）：部分越界夹到 12/31 并 WARNING「未来日历尚未发布」，不生成未来日期；整段都在 12/31 之后抛 `CalendarFutureUnavailable`。
5. 混合区间（`start` 早于 10 年且 `end` 晚于 12/31）：**先判历史侧**。历史缺缓存直接抛 `CalendarOutOfRange`，不再处理未来侧；错误信息同时说明「未来部分也不会返回」。
6. `previous_trading_day` 结果早于窗口起点且无缓存 → 抛 `CalendarOutOfRange`；`next_trading_day` 结果晚于 12/31 → 抛 `CalendarFutureUnavailable`，提示「跨年日历尚未发布，请次年 1 月 1 日后再计算」。两者都严格不含传入日期。
7. 缓存中的老数据即使滑出 10 年窗口，也永久保留只读；是否还能刷新由 futu 窗口决定。

## 7. 缓存

### 7.1 目录布局

```
data/cache/trading_calendar/
├── HK.parquet
├── HK.meta.json
├── HK.lock
├── US.parquet
├── US.meta.json
├── US.lock
├── CN.parquet
├── CN.meta.json
└── CN.lock
```

- 每个市场一个 parquet，列为 `date`、`session_type`；`close_time` 不落缓存，只在查询层由 override 合并。
- meta 与 parquet 分开存放，写入时成对更新。
- 目录已被 `.gitignore` 覆盖（`data/cache/`）。

### 7.2 meta 结构

```json
{
  "schema_version": 1,
  "market": "HK",
  "covered_intervals": [
    {"start": "2016-11-13", "end": "2016-12-31", "fetched_at": "2026-11-16T10:00:00+08:00"},
    {"start": "2017-01-01", "end": "2025-12-31", "fetched_at": "2026-11-16T10:00:00+08:00"}
  ],
  "future_probe_at": null,
  "source": "futu",
  "row_count": 2400,
  "parquet_sha256": "..."
}
```

- `covered_intervals` 是并集后的闭区间列表，每段带自己的 `fetched_at`，用于判断「请求区间是否已覆盖」与「今年那段区间是否过 TTL」；不使用单一市场级时间戳。
- 相邻区间仅当 `fetched_at` 相同才可合并为一段；不同则保持分段。「并集」只作用于同一次写入的段，跨次写入不得因相邻就合并，避免历史补拉改变当年的 TTL。
- `future_probe_at`：最近一次确认「未来日历尚未发布」的探测时间（ISO 8601，无则 `null`）；TTL 内未来查询直接快速失败，不发请求。
- `schema_version`：meta 结构变更时递增；当前为 1（尚未实现，无历史包袱）。
- `parquet_sha256` 用于读路径校验 parquet 与 meta 是否配套。
- 备份数据、override 数据都不写入这里。

### 7.3 刷新规则

| 年份 | 策略 |
|---|---|
| 早于今年 | 已定稿；**请求区间已被 `covered_intervals` 完整覆盖**才不刷新，缺区间按 §7.4 补拉 |
| 今年 | 覆盖今年那段的 `fetched_at` 超过 12 小时则重取今年窗口内区间；「今天」的实时判断建议更短 TTL（如 5 分钟）或开盘前强制 `refresh` |
| 晚于今年 | 不缓存；部分越界夹到 12/31，整段越界抛 `CalendarFutureUnavailable` |

- 只有 futu 返回的数据能写盘。
- 断网/失败时如果已有缓存且请求区间被完整覆盖，读缓存并 WARNING，`cache_stale=true`；否则抛错。
- 当前年请求 `end > today` 时，按返回内容分两种情况：
  - **未发布**：返回不含任何晚于 `today` 的日期 → futu 未来日历尚未发布，WARNING；coverage 右端记到 max(已确认右端, 最后一个返回日期)，**不扩到 `today`**；已确认的 coverage 永不缩小，收敛只作用于尚未确认的尾部；同时记录 `future_probe_at`。后续查询超出 coverage：工作日抛 `CalendarFutureUnavailable`，不得当成休市；周六/周日仍返回 `False`。
  - **已发布（接口契约信任）**：返回含至少一个晚于 `today` 的日期 → 视为 futu 对 `[start, min(end, 今年 12/31)]` 已完整发布，coverage 右端记到 max(已确认右端, min(end, 12/31))；该区间内不在表中的日期即休市。此假设的风险见 §15；不做启发式截断（长假附近易误判）。
- 周六/周日是结构性休市，无需覆盖即可由 `is_trading_day` 返回 `False`；工作日缺覆盖按方向报错：未来侧抛 `CalendarFutureUnavailable`，历史侧（早于 10 年窗口且无缓存）抛 `CalendarOutOfRange`，窗口内空洞补拉失败抛 `CalendarUnavailable`。
- 未来不可用负缓存：`future_probe_at` 起 `future_probe_ttl` 内（默认 12 小时，可配）再查询未来工作日直接抛 `CalendarFutureUnavailable`，不发请求——`is_trading_day` / `get_session_type` 的单日查询、`get_trading_days` / `get_calendar_frame` 的未来区间、`next_trading_day` 跨年，全部受它约束；`refresh=True` 或 TTL 过期后重新探测。避免 12 月末每次调度都打 futu。
- `future_probe_at` 只在同一自然年内有效：跨年后视为失效并清空，避免 12/31 的探测压住 1/1 的新日历；**已发布分支成功、`refresh=True`、`prewarm` 成功时都必须清空**。
- 查询顺序固定：先判 coverage（完整覆盖且未过 TTL → 直接用缓存）→ 再判负缓存 → 最后才回源。
- futu 返回空（一条数据都没有）：只写 `future_probe_at`，不创建任何 `covered_intervals`；禁止写入 `start > end` 的零长度区间。
- coverage 写入不变量：按 `start` 排序、互不重叠；已发布分支扩右端时必须裁剪或替换旧段；相邻区间仅 `fetched_at` 相同才合并。强制区间（`refresh` / `prewarm` / TTL 刷新）可能包含周末，coverage 是否完整一律按工作日语义判断（周末结构性休市，不要求覆盖）。
- 缓存损坏（读失败、缺列、sha 不匹配）：WARNING 后重新请求。
- `fetched_at` 按区间记录：只有覆盖今年那一段的 `fetched_at` 参与 TTL，补拉历史区间不会刷新当年的新鲜度。

### 7.4 写入与并发

- 每市场一个锁文件（`HK.lock` 等）；Windows 用 `msvcrt.locking`，POSIX 用 `fcntl.flock`。
- 写路径：拿锁 → 读旧 parquet/meta → 合并 → 写临时文件 → `os.replace` 原子替换 → 更新 meta → 释放锁。
- 锁只覆盖「读—合并—写」，不覆盖 API 请求；临界区为毫秒级。
- 读路径：无锁读 parquet/meta，校验 `parquet_sha256`；不匹配则拿锁重读一次。
- 进程退出时 OS 自动释放锁，不需要处理过期锁。
- 不提供跨进程限流；并发首次回填靠文档约束，见第 14 节。

## 8. 限流

- 进程内全局最小间隔 **1.1 秒**（30 次/30 秒留余量）。
- 必须启用进程内 token bucket：25 次/30 秒；与 1.1 秒最小间隔取更严格者。
- 同一 `(market, 请求区间)` 做 single-flight：并发只发一次，其余等结果。
- 频率类错误：指数退避 1s → 2s → 4s → … → 30s，最多 3 次；仍失败抛 `CalendarRateLimited`。
- 非频率类错误：不重试，直接抛。
- 不做跨进程令牌桶；两个进程同时回填会叠加请求数，需在运维层避免。

## 9. 接口契约

### 9.1 FutuAPIClient

```text
get_trading_days(market: str, start: str | None = None, end: str | None = None,
                 code: str | None = None) -> DataFrame[date, session_type]
```

职责：只调接口、归一返回、转异常；不做缓存、不做兜底、不做限流。`close_time` 由 `TradingCalendar` 合并 override 后补出。

### 9.2 TradingCalendar

```text
get_trading_days(market, start=None, end=None, refresh=False) -> DatetimeIndex
get_calendar_frame(market, start=None, end=None, refresh=False) -> DataFrame
is_trading_day(day, market, refresh=False) -> bool
get_session_type(day, market, refresh=False) -> str | None
is_trading_time(dt, market, refresh=False) -> bool   # dt 必须 tz-aware
next_trading_day(day, market) -> Timestamp
previous_trading_day(day, market) -> Timestamp
refresh(market, start=None, end=None) -> DatetimeIndex
prewarm(market, start, end) -> None
```

默认区间与语义：

- `get_trading_days(start=None, end=None)`：`end` 缺省取 `session_date(market, now)`，`start` 缺省取 `end - 365 天`；
- `get_trading_days` / `get_calendar_frame`：请求区间全为周六/周日（如周六到周日）→ 直接返回空结果，不触发请求与补拉；
- `next_trading_day(day)` / `previous_trading_day(day)`：严格不含 `day`；
- `refresh(market, start, end)`：绕过缓存与 TTL，强制回源，仍受窗口与限流约束；
- `prewarm(market, start, end)`：绕过 TTL 与缓存，只回源与写缓存，返回 `None`，用于开盘前/历史区间预热；次年区间需 1 月 1 日后再预热。

构造参数：`client`、`cache_dir`、`refresh_ttl`（默认 12 小时）、`future_probe_ttl`（默认 12 小时）、`now_provider`（测试注入时钟）。
`last_source` 暴露最近一次取数的来源（`futu` / `cache` / `None`）；
`cache_stale` 表示本次是否回退了过期/旧缓存；`last_fetched_at` 暴露对应区间的取数时间。

### 9.3 异常

| 异常 | 含义 |
|---|---|
| `CalendarUnavailable` | futu 不可用且缓存无法完整覆盖（含窗口内的覆盖空洞） |
| `CalendarOutOfRange` | 工作日早于 10 年窗口且无缓存（周六/周日按结构性休市返回 `False`，不抛此异常）；含 `previous_trading_day` 越界；未覆盖区间不得当作休市 |
| `CalendarFutureUnavailable` | 整段请求超出今年 12/31、未来侧未覆盖（工作日）、负缓存命中，或 `next_trading_day` 结果跨年；部分越界只夹取 + WARNING |
| `CalendarRateLimited` | 退避重试后仍被限流 |

另有 `ValueError`：带时分秒的 naive `datetime` 入参（见 §4.1）。

异常信息必须包含：市场、请求区间、支持窗口、缓存覆盖区间、缺失区间。

## 10. 会话与半天市

### 10.1 来源

- HK：用 futu 的 `trade_date_type`；`MORNING` 即上午收市（圣诞前夕、除夕、农历年廿九等）。
- US：futu 大概率只返回 `WHOLE`，不表达 13:00 提前收市；用 override 补 `close_time`。若 futu 对 US 意外返回 `MORNING`/`AFTERNOON`，WARNING 并按 `WHOLE` 处理。
- CN：无半天市，全部 `WHOLE`。

### 10.2 override 表

```
data/calendars/<MARKET>/overrides.csv   # 入库；不要放进 data/cache/
date,close_time,source,note
2025-11-28,13:00,NYSE,感恩节次日提前收市
2025-12-24,13:00,NYSE,平安夜提前收市
```

规则：

- override **只补 `close_time`**，不能增加或删除交易日，不能改 `session_type`。
- 只在查询层合并，不写入 futu 缓存。
- futu 说休市时，override 直接忽略并 WARNING。
- 默认只有 US 需要维护；HK/CN 留空表或不建表。
- override 属人工知识，纳入版本库；`data/cache/trading_calendar/` 被 `.gitignore` 覆盖，只放 futu 写出的缓存。
- 解析校验：日期必须 `YYYY-MM-DD`；`close_time` 必须 `HH:MM` 且落在该日 `session_type` 对应的最后一个 segment 内（US `WHOLE` 即 `(09:30, 16:00)`，HK `MORNING` 即 `(09:30, 12:00)`）；重复日期只保留第一条并 WARNING；非交易日或无法解析的行忽略并 WARNING；文件缺失视为空表。

### 10.3 待实测

OpenD 可用时，用下列日期查一次 `trade_date_type`：

- US：2025-11-28、2025-12-24。若返回 `WHOLE`，按本设计用 override 补 `close_time`；若返回 `MORNING`/`AFTERNOON`，override 可省略。
- HK：2025-12-24、2025-12-31、农历除夕（如 2026-02-16，以交易所公告为准）。确认 futu 是否真的返回 `MORNING`；若返回 `WHOLE`，§10.1 的断言不成立，需要改走 HK override 或改用 `close_time`。

## 11. 接入点

### 11.1 DataManager

- `get_trading_calendar()`：懒创建，复用 `clients['futu']` 与同一份缓存。
- `get_trading_days(market, start, end)`：透传。
- `save_realtime_data_to_local()`：`trading_day` 缺省取 `session_date(market, now)`；非交易日不落盘，返回失败并 WARNING，不能默认按上海日期打标，也不自动归到上一交易日；日历不可用时同样失败，不落盘。

### 11.2 HistoricalDataFeed

- `get_trading_dates(start, end, market)` 走日历；真实数据路径日历不可用直接抛错，不回 `freq='B'`。只有 `calendar is None` 且 `data_manager` 没有 `get_trading_calendar` 入口时才降级；入口存在但失败必须抛。
- `market` 默认 `hk` 只为兼容旧的两参数调用；调用方必须按标的市场显式传入，不得依赖默认值。
- mock 日线：单一市场可推断时用日历；日历不可用、推断不出市场或跨市场时，回落到工作日并 WARNING，仅限 mock。
- 真实数据路径不允许任何工作日降级。

### 11.3 BacktestEngine

- 保持「数据日期并集」为日轴，不改成日历驱动。
- 加载数据后按标的市场分别过滤：日期不在该市场日历中的 bar 剔除，并计数。
- 混合市场必须逐标的过滤，不能用单一日历。
- 日历不可用（缺覆盖）→ 直接失败，不跳过过滤继续跑。
- 半天市仍是交易日，不剔除。
- 结果写入 `BacktestResult.config`：
  - `calendar_source`：按市场记录 `futu` / `cache`；mock 跳过过滤时为 `{"mock": "none"}`；
  - `calendar_stale`：是否回退了过期缓存（任一市场 stale 即为 true）；
  - `calendar_dropped_bars`：按标的计数；
  - `calendar_range`：按市场记录实际查询区间。
- mock 数据没有市场事实来源，日历缺失或标的无法推断市场时允许跳过过滤；真实数据路径不允许。
- 剔除比例超过阈值（默认 5%）时 WARNING。

### 11.4 Web / 实时

- 页面与定时任务统一走 `DataManager.get_trading_calendar()`。
- 捕获 `CalendarUnavailable` / `CalendarOutOfRange` / `CalendarFutureUnavailable` / `CalendarRateLimited`，展示「交易日历不可用」或「跨年日历未发布」，不崩溃、不静默降级。

## 12. 测试计划

全部离线，用 fake client + 注入时钟；不打网络、不依赖 OpenD。

| 编号 | 钉住的行为 |
|---|---|
| CAL-01 | futu list[dict] 解析、排序、去重、`trade_date_type` 保留 |
| CAL-02 | 旧版 DataFrame 返回兼容；`RET_ERROR` 转异常；未连接转 `ConnectionError` |
| CAL-03 | `SH`/`SZ` → `CN`；`Timestamp` → `YYYY-MM-DD` |
| CAL-04 | 缓存命中不再请求；跨实例读盘；sha 不匹配重读 |
| CAL-05 | 当年 TTL 刷新；`refresh=True` 绕过缓存 |
| CAL-06 | 边界年 coverage 只覆盖窗口段；缺区间触发补拉 |
| CAL-07 | 10 年外：有缓存可读，无缓存抛 `CalendarOutOfRange` |
| CAL-08 | `end` 超过 12/31 被夹取；明年日期不出现 |
| CAL-09 | 跨年 `next_trading_day` 抛 `CalendarFutureUnavailable` |
| CAL-10 | 限流 pacing：任意 30 秒窗口内请求数 ≤ 25（假时钟） |
| CAL-11 | 频率错误指数退避且最多 3 次；非频率错误不重试 |
| CAL-12 | single-flight：并发同区间只请求一次 |
| CAL-13 | 时区：US `session_date` 与上海日期不同的场景 |
| CAL-14 | 港股 `MORNING` 时段；美股 `WHOLE + close_time=13:00` 时段；CN 午休 |
| CAL-15 | override 只能补 `close_time`；休市日 override 被忽略 |
| CAL-16 | 引擎过滤：逐标的剔除、计数、混合市场、日历缺失时失败 |
| CAL-17 | 已知日期 fixture：2024 港股休市日集合（放 `tests/fixtures/`，仅测试用，不参与运行时兜底） |
| CAL-18 | 缓存写锁：并发写入不丢 coverage |
| CAL-19 | 未覆盖区间：`is_trading_day` / `get_session_type` 必须抛异常，不得返回 `False` / `None`；周六/周日结构性休市例外（可返回 `False` / `None`） |
| CAL-20 | 部分越界：历史侧缺缓存抛错，未来侧夹到 12/31 且 WARNING |
| CAL-21 | futu 失败但缓存完整覆盖 → 返回缓存，`cache_stale=true`，WARNING |
| CAL-22 | 当年请求无未来日期（未发布分支）→ 未被已确认覆盖的尾部收敛到最后一个已返回日期，已确认区间永不缩小；之后的工作日抛 `CalendarFutureUnavailable`（不返回 `False`），周六/周日仍返回 `False` |
| CAL-23 | `previous_trading_day` 早于 10 年窗口 → `CalendarOutOfRange` |
| CAL-24 | 混合区间（历史缺缓存 + 未来越界）→ 历史侧错误优先 |
| CAL-25 | naive 带时分秒时间入参 → `ValueError`；tz-aware 零点 `Timestamp` 按时刻换算，不当成日期 |
| CAL-26 | override 格式错误/重复/非交易日 → 忽略 + WARNING；`close_time` 按 `session_type` 对应 segment 校验（HK `MORNING` 的 11:30 合法） |
| CAL-27 | 真实数据路径日历不可用 → 抛错，绝不回落到工作日；仅 mock 允许 |
| CAL-28 | 已发布分支：返回含未来日期 → coverage 记到 max(已确认右端, min(end, 12/31))，尾部缺失按休市；未发布分支：收敛到最后一个返回日期 |
| CAL-29 | 未来负缓存：`future_probe_at` TTL 内重复查询未来工作日不再请求 futu，直接抛 `CalendarFutureUnavailable`；`refresh=True` 或 TTL 过期后重新探测 |
| CAL-30 | 纯周末区间（周六至周日）→ 返回空结果，不触发请求 |

## 13. 实施阶段

### P0：能力层，不改行为

- `FutuAPIClient.get_trading_days`；
- `TradingCalendar`、缓存、coverage、限流、异常；
- CAL-01～CAL-30 中与能力层相关的测试；
- CN 本阶段只提供日历能力，不接 A 股行情与标的解析。

验收：不改任何现有调用；单测全绿。

### P1：数据层接入

- `DataManager.get_trading_calendar` / `get_trading_days`；
- `HistoricalDataFeed.get_trading_dates` 与 mock 日轴；
- 实时落盘的 `trading_day` 取 session date。

验收：日历不可用时回测/取数明确失败；缓存命中时零请求。

### P2：回测引擎卫生过滤

- 逐标的过滤、计数、结果字段、阈值告警。

验收：构造含假日 bar 的数据，回测结果剔除计数正确；日历缺失时回测失败而不是继续。

### P3：半天市与展示

- `is_trading_time`、US override、Web 不可用状态。

验收：港股半日、美股提前收市、A 股午休三组时段测试通过。

## 14. 运维约束

1. **缓存是唯一离线档案。** 10 年窗口外的历史日历一旦缓存丢失就无法重建；`data/cache/trading_calendar/` 必须纳入日常备份。override 文件在版本库中，随代码备份。
2. **次年日历只能等 1 月 1 日后再取。** futu 不返回次年数据，12 月无法预热；12 月末调用跨年的 `next_trading_day` 会抛 `CalendarFutureUnavailable`，属预期行为，调度需容错并顺延到次年 1 月 1 日后重试；`future_probe_at` 负缓存（§7.3）可避免每次调度都打 futu。
3. **不要同时跑两个首次全量回填。** 不做跨进程限流，两个进程会叠加请求数；Web 启动预热一次，回测复用缓存。
4. **OpenD 必须在线才能补新数据。** 离线时只能读缓存；没有缓存就失败，这是设计意图。
5. **临时休市要手动刷新。** 台风/黑雨、临时休市可能盘中才公告；当年缓存 12 小时 TTL 不够及时，实时判断建议开盘前 `refresh` 或使用更短 TTL。futu 是否更新这类日历需实测。

## 15. 风险与待验证

| 风险 | 说明 | 处理 |
|---|---|---|
| 限流按账号还是连接 | 假设 30/30s 按 OpenD 账号计 | 首次回填单进程执行；必要时再补文件锁 |
| 美股提前收市表达 | futu 可能只返回 `WHOLE` | 用 override 补 `close_time`；上线前实测 |
| 10 年窗口边界 | 「过去 10 年」按滚动日期还是自然年由 futu 决定 | 请求前按滚动 `today - 10 年` 校验；以 futu 返回为准 |
| CN 覆盖范围 | 仅 SH/SZ；不含北交所 | 标的解析层同步限制 |
| 缓存损坏/丢失 | 老数据不可重建 | 备份 + sha 校验 + 损坏重建 |
| 时区/DST | 美股 EST/EDT 切换 | 使用 `America/New_York`，不写死 UTC 偏移 |
| naive 时间入参 | 调用方把上海 `now()` 直接传给 US | 带时分秒强制 tz-aware；naive 抛 `ValueError` |
| 未来日历未发布 | futu 未返回任何晚于 `today` 的日期（未发布分支） | coverage 尾部收敛 + `future_probe_at` 负缓存；未来工作日抛 `CalendarFutureUnavailable`，不把未来当休市（D20） |
| 未来日历部分缺失 | futu 返回含未来日期但未到 12/31（已发布分支） | 接口契约信任：coverage 记到 `min(end, 12/31)`，尾部缺失按休市（D23） |
| 过期缓存 | futu 失败时回退旧缓存 | `cache_stale=true` + WARNING，回测结果留痕 |
| 新机器无 OpenD | `data/cache/` 不入库，且无网络时拿不到任何日历 | 用 CAL-17 fixture 跑测试回归；生产机首次使用仍需在线预拉并备份缓存 |
| 12 月末跨年 | 次年日历未发布，任何向未来跨年的推算都会失败 | 属预期行为，见 §14.2；调用方需容错 |

## 16. 决策记录

| 编号 | 决策 | 结论 |
|---|---|---|
| D1 | 兜底链 | 缓存（完整覆盖；当年未过 TTL）→ futu → 缓存（仅完整覆盖，WARNING）→ 报错；无自动兜底 |
| D2 | A 股 | 纳入，仅 SH/SZ；`SZ/SH → CN` |
| D3 | 时区 | US=`America/New_York`，HK=`Asia/Hong_Kong`，CN=`Asia/Shanghai` |
| D4 | 10 年外 | 只读缓存；无缓存报错 |
| D5 | 引擎日轴 | 数据日期并集 + 日历卫生过滤 |
| D6 | 半天市 | HK 用 `trade_date_type`；US 提前收市用 `close_time` |
| D7 | 代码位置 | `utils/trading_calendar.py`，client 注入 |
| D8 | 缓存 | 每市场单 parquet + coverage meta |
| D9 | 跨进程限流 | 不做跨进程锁；进程内 1.1s pacing + 25/30s bucket + 指数退避 |
| D10 | 未来/跨年 | 部分越界夹取 + WARNING；整段越界或 `next_trading_day` 跨年抛 `CalendarFutureUnavailable`；`previous_trading_day` 越历史窗口抛 `CalendarOutOfRange` |
| D11 | 自动兜底 | 无；也不做官方 CSV 灾备 |
| D12 | 美股 early close | `overrides.csv`，只补 `close_time` |
| D13 | 缓存一致性 | parquet + 短文件锁，锁只包读—合并—写 |
| D14 | 未覆盖区间 | 所有读接口（`is_trading_day` / `get_session_type` / `get_trading_days` / `get_calendar_frame` / next / previous）抛异常，不把未覆盖当休市；周六/周日结构性休市除外 |
| D15 | override 存放 | `data/calendars/<MARKET>/overrides.csv` 入库；缓存目录只放 futu 写出内容 |
| D16 | 时段模型 | 市场默认用 segments 列表，`close_time` 只截断最后一个 segment |
| D17 | 时间入参 | 日期型按市场本地日期；带时分秒必须 tz-aware，naive 拒绝 |
| D18 | 缓存新鲜度 | 回退旧缓存时 `cache_stale=true`，调用方与回测结果可感知 |
| D19 | 部分返回 | 仅未来侧越界允许夹取 + WARNING；历史/缓存侧缺一段即报错 |
| D20 | coverage 收敛 | 未发布分支：收敛到最后一个已返回日期，不扩到 `today`，已确认区间永不缩小；已发布分支：按契约信任记到 max(已确认右端, `min(end, 12/31)`)。后果：`today` 为工作日且超出 coverage 时抛 `CalendarFutureUnavailable`（负缓存内快速失败），今天不一定可查 |
| D21 | meta 时间戳 | `covered_intervals` 每段带 `fetched_at`，历史补拉不影响当年 TTL |
| D22 | 未来负缓存 | `future_probe_at` + TTL（默认 12h）；TTL 内未来查询直接抛错不发请求，`refresh=True` 绕过；跨自然年失效，已发布成功/refresh/prewarm 成功均清空 |
| D23 | 接口契约信任 | 返回含至少一个未来日期即视为已发布到 12/31；不做启发式截断（长假附近易误判） |
