# legacy_scripts

这些是从 `tests/` 移出的历史手工脚本，不是 pytest 用例：

- `test_data_expiry.py`
- `test_fundamental_data.py`
- `test_fundamental_indicators.py`
- `test_market_snapshot.py`

保留原因：其中仍有可复用的手工验证逻辑。要重新纳入套件，需要先补上
`indicators.fundamental` 的缺失模块并配置 pytest 的 async 支持。
