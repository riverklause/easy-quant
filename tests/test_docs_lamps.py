"""DOC1：文档禁词灯——已删除的 API 不能回潮。"""

from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]

# 只禁"铁定不该再出现"的符号；"尚未实现"的说明不算漂移
FORBIDDEN = (
    "OrderExecutor",
    "SimpleOrderExecutor",
    "get_data_config",
    "utils.cache",
    "DataCache",
    "aiolimiter",
    "loguru",
    "FastAPI",
)


def test_DOC1_docs_do_not_mention_removed_symbols():
    paths = [*(_ROOT / "docs").glob("*.md"), _ROOT / "README.md"]

    for path in paths:
        text = path.read_text(encoding="utf-8")
        for token in FORBIDDEN:
            assert token not in text, f"{path.name} 仍提到已移除的 {token}"
