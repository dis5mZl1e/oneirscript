"""世界层（重构方案 §13.1）：身份、事实、关系、任务、场景、行程与交易。

这里的模块**不得**依赖 Textual 或墙上时钟；入口一律由 ``GameState``／行动路由
调用，时间只通过既有的 ``_action_time`` 支付。
"""
from .facts import FACT_FIELDS, FACT_KINDS, facts_for, record, reset_listeners, subscribe
from .ledger import ActorRecord, FacilityRecord, TaskRecord, WorldLedger
# 关系模块导入即订阅事实管道（§4.4）：立场必须由事实驱动，不能靠调用方记得手动通知。
from . import relations  # noqa: F401  (import side effect: subscribe(observe))
from . import scenes
from . import tasks

__all__ = ["FACT_FIELDS", "FACT_KINDS", "ActorRecord", "FacilityRecord", "TaskRecord",
           "WorldLedger", "facts_for", "record", "relations", "reset_listeners",
           "scenes", "subscribe", "tasks"]
