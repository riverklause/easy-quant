"""LG0–LG3：utils/ 导入契约与 requirements 声明契约。

LG0 今天红在模块级执行旧 Logger()，而 Settings 没有 LOG_LEVEL /
DATA_BASE_PATH 属性 → 导入 utils/logger.py 即抛 AttributeError。
修复后 LG0 覆盖 4 个模块（date_utils 暂不在内，见 LG2/LG3）。

LG2/LG3 是 utils/ 目录的依赖健康网：
  - LG2 红灯：第三方 import 在 requirements.txt 里没声明；
  - LG3 红灯（目前 skipped）：holidays 装完后自动覆盖 date_utils。
"""

import ast
import importlib
import importlib.util
import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parent.parent
_REQUIREMENTS = _ROOT / "requirements.txt"

# import 名 → 分发名（只列与包名不一致的）
_IMPORT_TO_DIST = {
    "sklearn": "scikit-learn",
    "futu": "futu-api",
    "dash_extensions": "dash-extensions",
    "dash_bootstrap_components": "dash-bootstrap-components",
}


def _third_party_imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            names.add(node.module.split(".")[0])
    return names


# ===== LG0 / LG1 / LG1b =====

@pytest.mark.parametrize("mod", [
    "utils.logger",
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
    """保护性灯：被摘掉的 handler 必须 close()，否则文件句柄泄漏。"""
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


# ===== LG2 / LG3：依赖声明契约 =====

def test_LG2_utils_third_party_deps_are_declared():
    """utils/ 下每个第三方 import 都必须在 requirements.txt 里声明。"""
    declared = _REQUIREMENTS.read_text(encoding="utf-8").lower()
    missing = []
    for path in (_ROOT / "utils").glob("*.py"):
        for name in _third_party_imports(path):
            if name in sys.stdlib_module_names or name == "utils" or name.startswith("_"):
                continue
            dist = _IMPORT_TO_DIST.get(name, name)
            if dist.lower() not in declared:
                missing.append(f"{path.name}: {name} (需声明 {dist})")
    assert not missing, "未声明的第三方依赖: " + "; ".join(sorted(missing))


@pytest.mark.skipif(
    importlib.util.find_spec("holidays") is None,
    reason="holidays 未安装；装好后本灯自动启用（见 requirements 交易日历段）",
)
def test_LG3_date_utils_imports():
    importlib.import_module("utils.date_utils")
