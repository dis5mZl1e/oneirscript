"""启动期性能调参（目前只有 GC 一项）。

单独成模块的原因：调参必须在**模块导入完成之后、应用开跑之前**执行一次，而
调用点有两个（``run_demo.main`` 与性能探针 ``scripts/perf_probe.py``）——放在
这里两头都能 import，且天然幂等（重复调用只生效一次）。
"""

from __future__ import annotations

import gc

# (threshold0, threshold1, threshold2)：CPython 默认 (700, 10, 10)。
# - 2000：gen0 回收次数降到默认的约 1/3。特效循环 20fps 的每帧临时量（numpy
#   中间数组、叠加层 dict、Text 样式串）本来就活不过一帧，晚一点回收只是让它
#   们多活几毫秒，代价极小；
# - 15 / 15：gen1 每 15 次 gen0 才跑（默认 10），gen2 每 15 次 gen1 才跑。
#   gen2 是**全量扫描**（含启动阶段的那几万个长期对象），是可见顿卡的主要来源，
#   这样一改它的触发频率降到默认的约 1/22。
GC_THRESHOLD: tuple[int, int, int] = (2000, 15, 15)

_installed = False


def install_gc_tuning() -> None:
    """GC 调参（性能 P0-3）：冻住启动期对象 + 放宽分代门槛。只生效一次。

    1. ``gc.freeze()``：把此刻所有被追踪的对象（模块、颜色 LUT、常量表、配置、
       已导入的第三方库……几万个几乎永不释放的对象）整体移进「永久代」。
       它们从此不参与 gen0/gen1/gen2 的扫描——这本来是每帧都要付的固定开销
       （对象越多越贵），冻上就一次性省掉。冻结**不等于**永不回收：这些对象
       里若出现循环垃圾依然会被清掉，只是不再频繁被扫。
    2. ``gc.set_threshold(*GC_THRESHOLD)``：见该常量的说明。

    ⚠️ 必须在**模块导入完成之后**调用：这之后才 import 的模块会被当成新对象
    重新纳入回收，等于前面白冻一部分。``run_demo.main`` 里的调用点满足这一点
    （它自己已经在文件头把 dream_demo.app 整条依赖树导入完了）。
    """
    global _installed
    if _installed:
        return
    _installed = True
    try:
        gc.freeze()
    except Exception:  # pragma: no cover - 极老版本/嵌入式解释器没有 freeze
        pass
    gc.set_threshold(*GC_THRESHOLD)
