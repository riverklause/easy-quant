"""离线研究模块。

边界：research 可以 import 生产包（backtest / data / indicators /
screener / strategy / web），但反过来**生产包不得 import research**
——见 tests/test_factor_lab.py::test_FL0_production_does_not_import_research。
"""
