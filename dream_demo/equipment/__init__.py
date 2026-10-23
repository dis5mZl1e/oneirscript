"""联想盘（携带意象认知盘）：形状、语法、事件与装配的统一入口。

设计依据：
- docs/equipment-dream-board-redesign.md（几何、事务、窄屏、所有权）
- docs/superpowers/specs/2026-10-09-equipment-grammar-design.md（生效合同以语句为权威）

模块划分（对应语法核心版 §10 的四个单元）：
- shapes / item_shapes：词义注册表之外的「有形词块」目录与端口几何
- board：8×6 盘面、合法性、握持焦点、装箱迁移
- semantics / senses：效果 → 语义、装备 → 可选词义（类型与原效果映射）
- grammar：语句编译（持有句／行动句／反应句），能力注册与未成句原因
- aggregation：同效果递减汇总
- links / events：根事件、端口图传播、插片反馈与因果预算
- view：EquipmentView，所有旧查询经它取装备、效果与焦点
"""

from __future__ import annotations

from .board import EquipmentBoard, Piece, Placement, Trace
from .view import EquipmentView

__all__ = [
    "EquipmentBoard",
    "EquipmentView",
    "Piece",
    "Placement",
    "Trace",
]
