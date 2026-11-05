"""LG0 / LG1：日志模块的导入契约与配置契约。

LG0 今天红在模块级执行 `Logger()`，而 `Settings` 没有 `LOG_LEVEL` /
`DATA_BASE_PATH` 属性 → 导入 utils/logger.py 即抛 AttributeError。

`utils.date_utils` 不在 LG0 里：它还有第二个红因（`holidays` 是未声明的
第三方依赖，当前环境未安装），混进来会让这盏灯有两个红因。
"""

import importlib
import logging
from logging.handlers import RotatingFileHandler

import pytest


@pytest.mark.parametrize("mod", [
    "utils.logger",
    "utils.validation",
    "utils.file_utils",
    "utils.data_utils",
])
def test_LG0_utils_modules_import(mod):
    importlib.import_module(mod)


def test_LG1_configure_logging_is_idempotent(tmp_path):
    """保护性灯：_CONFIGURED 是防叠加 handler 的实现细节，当前即绿。"""
    from utils.logger import configure_logging

    root = logging.getLogger()
    saved_handlers, saved_level = root.handlers[:], root.level
    try:
        configure_logging(level="DEBUG", log_dir=tmp_path, force=True)
        assert root.level == logging.DEBUG
        assert len(root.handlers) == 2
        assert any(isinstance(h, RotatingFileHandler) for h in root.handlers)

        configure_logging(level="DEBUG", log_dir=tmp_path)  # 第二次
        assert len(root.handlers) == 2, "重复调用叠加了 handler"

        logging.getLogger("eq.probe").debug("x")
        assert (tmp_path / "easy_quant.log").exists()
    finally:
        root.handlers[:] = saved_handlers
        root.setLevel(saved_level)


def test_LG1b_force_close_does_not_leak_handlers(tmp_path):
    """保护性灯：被摘掉的 handler 必须 close()，否则文件句柄泄漏。

    removeHandler() 只摘不关，force=True 每调一次就丢一个打开的文件。
    """
    from utils.logger import configure_logging

    root = logging.getLogger()
    saved_handlers, saved_level = root.handlers[:], root.level
    try:
        configure_logging(level="DEBUG", log_dir=tmp_path, force=True)
        removed = []
        for _ in range(3):
            removed.extend(root.handlers[:])
            configure_logging(level="DEBUG", log_dir=tmp_path, force=True)
        assert len(root.handlers) == 2
        file_handlers = [h for h in removed if isinstance(h, RotatingFileHandler)]
        assert len(file_handlers) == 3
        assert all(h.stream is None for h in file_handlers), \
            "摘掉的 handler 未关闭，文件句柄泄漏"
    finally:
        root.handlers[:] = saved_handlers
        root.setLevel(saved_level)
