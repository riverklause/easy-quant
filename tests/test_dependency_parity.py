"""DP1：requirements.txt 与 pyproject 的依赖清单必须一致。

两份清单是同一份事实的两个视图；漂移的典型后果是"pip install -e . 装不上"
或"CI 过了但用户按 requirements 装缺包"。
"""

import re
import tomllib
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]


def _dist_name(spec: str) -> str:
    """'dash[diskcache]>=2.14.0 ; python_version>="3.10"' → 'dash'。"""
    name = spec.split(";")[0]
    name = re.split(r"\[|<|>|=|!|~", name)[0]
    return name.strip().lower().replace("_", "-")


def _requirements_names() -> set[str]:
    names = set()
    for line in (_ROOT / "requirements.txt").read_text(encoding="utf-8").splitlines():
        line = line.split("#")[0].strip()
        if line:
            names.add(_dist_name(line))
    return names


def _pyproject_names() -> set[str]:
    data = tomllib.loads((_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    project = data["project"]
    specs = list(project.get("dependencies", []))
    for extra in project.get("optional-dependencies", {}).values():
        specs.extend(extra)
    return {_dist_name(s) for s in specs}


def test_DP1_requirements_and_pyproject_agree():
    only_pyproject = _pyproject_names() - _requirements_names()
    only_requirements = _requirements_names() - _pyproject_names()

    assert not only_pyproject and not only_requirements, (
        f"依赖不一致：仅 pyproject 有 {sorted(only_pyproject)}；"
        f"仅 requirements 有 {sorted(only_requirements)}"
    )
