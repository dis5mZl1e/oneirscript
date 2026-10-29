"""可选 Cython 内核开关（CY-1..CY-5，2026-10-27）。

内核模块与纯 Python 回退路径**同时存在**：默认调用已编译的内核（raster、
knowledge 除外）；未编译、内核缺失或环境变量关闭时，调用方保留的原实现继续生效。
这样同一份源码既能做 A/B（切换环境变量即可），也能在负优化时整段禁用而不删代码。

    ONEIRSCRIPT_CY_KERNELS=0            关闭全部内核
    ONEIRSCRIPT_CY_KERNEL_SAVE=0        只关闭指定内核
    可用名称：save / fx / sight / gas / raster / knowledge

raster 默认关闭：2026-10-27 复测（101 帧同进程配对，中位差 0.0ms、均值
−0.05ms）属噪声内无实际改善；保留源码与开关，但不再默认走内核。

knowledge 默认关闭（CY-6，2026-10-27）：compiled 内核相对纯 Python 只快约
0.24ms/步（1056 格视口、121 轮配对中位差，约 −11%），低于「每步 p50 降低
≥1ms」的保留线，已移出 build_cython_ext.MODULES；源码、回退路径与
ONEIRSCRIPT_CY_KERNEL_KNOWLEDGE=1 复测开关保留。
"""
from __future__ import annotations

from .env_compat import get

_NAMES = frozenset({"save", "fx", "sight", "gas", "raster", "knowledge"})
_FALSE = frozenset({"0", "false", "no", "off"})
# 逐项默认值：未列出的默认开启。
_DEFAULT_OFF = frozenset({"raster", "knowledge"})


def enabled(name: str) -> bool:
    if name not in _NAMES:
        raise ValueError(f"unknown cython kernel: {name}")
    if (get("CY_KERNELS", "1") or "1").strip().lower() in _FALSE:
        return False
    raw = get("CY_KERNEL_" + name.upper(), "1" if name not in _DEFAULT_OFF else "0")
    return (raw or "1").strip().lower() not in _FALSE
