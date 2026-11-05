# 归档的手工脚本

这些是归档的手工脚本，**不是 pytest 用例**，不保证可直接运行；需要时在仓库根执行并临时设置
`PYTHONPATH=.`。重新纳入 `tests/` 前必须先补断言与 `pytest-asyncio`。

`pytest.ini` 已把 `testpaths` 固定为 `tests`，所以在这里 `pytest` 不会收集它们。

| 脚本 | 用途 |
|---|---|
| `test_futu_connection.py` | Futu 连接与数据订阅 |
| `test_futu_client.py` | Futu 客户端数据获取 |
| `test_futu_basic.py` / `test_futu_official.py` | Futu API 基础/官方示例对齐 |
| `test_hk00700_realtime.py` / `_v2.py` | HK.00700 实时 K 线（两版并存，保留 v2 即可） |
| `test_kdj.py` / `debug_kdj.py` | KDJ 计算一致性 / 过程调试 |
| `test_moving_average.py` | 均线指标改动验证 |
| `test_dict_input.py` / `test_no_dict_input.py` | Dict 输入允许/禁止的一对实验 |
| `test_get_basicfiltered.py` | `get_basicfiltered_stocks()` 返回值 |
| `test_realtime_data.py` | 实时数据管理演示 |
| `test_rehab_factors.py` | 复权因子 |
| `test_output.py` | 输出格式验证 |
| `debug_futu_detailed.py` / `debug_snapshot_issue.py` | 连接细节 / 快照问题排查 |
| `futu_official_demo.py` | Futu 官方文档模式演示 |

## 其它历史脚本

以下更早迁入、且没有 `sys.path` 处理，只能从仓库根用 `PYTHONPATH=.` 运行：

`test_strategy_executor.py`、`test_fundamental_data.py`、`test_fundamental_indicators.py`、`test_data_expiry.py`、`test_market_snapshot.py`。

## Notebook

临时探索用的 notebook 归档在 `scratch/notebooks/`：`test-1.ipynb`、`testfutu.ipynb`、`Untitled-1.ipynb`。
