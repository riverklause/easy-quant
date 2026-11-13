"""不上 venv：用当前解释器已安装的元数据生成精确版本锁文件。

只包含 pyproject 声明的依赖及其传递闭包；环境里其它包（与本项目无关的
150 多个）不会进入，所以"环境脏"不影响这份文件的正确性。

用法：
    python scripts/lock_requirements.py            # 写 requirements.lock
    python scripts/lock_requirements.py --dry-run  # 只打印

注意：它锁的是"当前实际装着的版本"。生成之后必须先跑一遍 pytest，
确认这套版本是通过的，这份锁才有意义。
"""

import argparse
import platform
import sys
import tomllib
from datetime import date
from importlib.metadata import PackageNotFoundError, requires, version
from pathlib import Path

from packaging.requirements import Requirement

ROOT = Path(__file__).resolve().parent.parent


def canonical(name: str) -> str:
    return name.lower().replace("_", "-").replace(".", "-")


def resolve(roots: list[str]) -> tuple[dict[str, str], list[str]]:
    seen: dict[str, str] = {}
    extras: dict[str, set[str]] = {}
    missing: list[str] = []
    queue: list[tuple[str, set[str]]] = [(r, set()) for r in roots]

    while queue:
        spec, wanted = queue.pop()
        req = Requirement(spec)
        name = canonical(req.name)
        merged = extras.get(name, set()) | set(req.extras)

        if name in seen and merged == extras.get(name, set()):
            continue
        extras[name] = merged

        if name not in seen:
            try:
                seen[name] = version(req.name)
            except PackageNotFoundError:
                missing.append(req.name)
                continue

        for raw in requires(req.name) or []:
            dep = Requirement(raw)
            if dep.marker is not None:
                ok = any(
                    dep.marker.evaluate({"extra": extra})
                    for extra in [None, *sorted(merged)]
                )
                if not ok:
                    continue
            queue.append((str(dep), set()))

    return seen, missing


def main() -> int:
    p = argparse.ArgumentParser(description="生成 requirements.lock")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--out", default="requirements.lock")
    args = p.parse_args()

    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    roots = list(project.get("dependencies", []))
    for extra in project.get("optional-dependencies", {}).values():
        roots.extend(extra)

    pinned, missing = resolve(roots)

    header = [
        "# 由 scripts/lock_requirements.py 生成，请勿手改",
        f"# python: {platform.python_version()}  platform: {platform.system()}-{platform.machine()}",
        f"# generated: {date.today().isoformat()}",
        "# 包含 pyproject 依赖的完整传递闭包；生成后须跑一遍 pytest 才算通过",
        "# 定位：本机复现锁（见上方 python/platform），非通用锁",
        '# CI 使用 Python 3.12 + pip install -e ".[dev]"，不读取本文件',
        "",
    ]
    lines = header + [f"{name}=={ver}" for name, ver in sorted(pinned.items())]

    if missing:
        print("未安装（未写入）:", ", ".join(sorted(missing)), file=sys.stderr)

    text = "\n".join(lines) + "\n"
    if args.dry_run:
        print(text)
        return 0

    (ROOT / args.out).write_text(text, encoding="utf-8")
    print(f"已写入 {args.out}：{len(pinned)} 个包")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
