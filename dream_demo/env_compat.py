"""环境变量命名迁移：ONEIRSCRIPT_* 优先，旧 DREAM_STRATA_* 继续兼容。

改名前的启动脚本、快捷方式和验证脚本仍会设置旧名；读取端只在这里做一次
回退，避免每个调用点各写一份 os.environ 判断。两者同时存在时新名优先。
"""
from __future__ import annotations

import os

NEW_PREFIX = "ONEIRSCRIPT_"
LEGACY_PREFIX = "DREAM_STRATA_"


def name(suffix: str) -> str:
    """当前规范的环境变量全名，供生成配置或设置变量时使用。"""
    return NEW_PREFIX + suffix


def get(suffix: str, default: str | None = None) -> str | None:
    """读取变量；新名存在即用新名，否则回退旧名，两者都没有时返回 default。"""
    value = os.environ.get(NEW_PREFIX + suffix)
    if value is not None:
        return value
    return os.environ.get(LEGACY_PREFIX + suffix, default)


def flag(suffix: str, default: bool = False) -> bool:
    value = get(suffix)
    if value is None:
        return default
    return value.strip().lower() in ("1", "true", "yes", "on")
