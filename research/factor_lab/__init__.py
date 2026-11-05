"""因子实验室：离线因子研究 / IC / 分档。

边界：research 层可以 import 生产包（indicators / data 等），但
生产包**不得**反向 import 本模块——见 FL0 边界灯。
"""
