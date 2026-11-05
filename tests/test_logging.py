"""LG0：utils/ 下的日志相关模块必须可导入。

今天红在模块级执行 `Logger()`，而 `Settings` 没有 `LOG_LEVEL` /
`DATA_BASE_PATH` 属性 → 导入 utils/logger.py 即抛 AttributeError。

`utils.date_utils` 不在灯里：它还有第二个红因（`holidays` 是未声明的
第三方依赖，当前环境未安装），混进来会让这盏灯有两个红因。
"""

import importlib

import pytest


@pytest.mark.parametrize("mod", [
    "utils.logger",
    "utils.validation",
    "utils.file_utils",
    "utils.data_utils",
])
def test_LG0_utils_modules_import(mod):
    importlib.import_module(mod)
