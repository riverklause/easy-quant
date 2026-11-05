"""日志配置：统一到 stdlib logging。

约定：
- 库代码用 `logging.getLogger(__name__)`，**不要**在这里拿单例；
- 入口（web/app.py、各 `__main__`）调一次 `configure_logging()`；
- import 阶段不做任何配置（否则测试会建 logs/、装 handler）。
"""

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional

from .settings import settings

_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
_DATEFMT = "%Y-%m-%d %H:%M:%S"

_CONFIGURED = False


def configure_logging(level: Optional[str] = None,
                      log_dir: Optional[str] = None,
                      max_size_mb: Optional[int] = None,
                      backup_count: Optional[int] = None,
                      force: bool = False) -> logging.Logger:
    """配置 root logger（幂等）。

    只挂 root：各模块的 `getLogger(__name__)` 靠传播拿到 handler。
    """
    global _CONFIGURED
    root = logging.getLogger()
    if _CONFIGURED and not force:
        return root

    resolved = str(level or settings.log.level or "INFO").upper()
    root.setLevel(getattr(logging, resolved, logging.INFO))

    for handler in list(root.handlers):
        root.removeHandler(handler)
        handler.close()

    formatter = logging.Formatter(_FORMAT, datefmt=_DATEFMT)

    stream = logging.StreamHandler(sys.stdout)
    stream.setFormatter(formatter)
    root.addHandler(stream)

    directory = Path(log_dir or settings.log.dir or "logs")
    directory.mkdir(parents=True, exist_ok=True)
    file_handler = RotatingFileHandler(
        directory / "easy_quant.log",
        maxBytes=int(max_size_mb or settings.log.max_size) * 1024 * 1024,
        backupCount=backup_count or settings.log.backup_count,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    root.addHandler(file_handler)

    _CONFIGURED = True
    return root


if __name__ == "__main__":
    configure_logging(level="DEBUG")
    logging.getLogger(__name__).info("日志配置完成")
