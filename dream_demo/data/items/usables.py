"""惯用物：被动增益的常驻件。"""

from __future__ import annotations

from typing import Any

ITEMS = {
    "model_screw": {
        "name": "模型盒里多出的螺丝", "category": "惯用物", "slot": "惯用物",
        "rarity": "常见",
        "description": "拧紧一个错误，也许会松开另一个。", "color": "bright_white", "effect": "repair",
    },
    "stair_bolt": {
        "name": "楼梯铆钉", "category": "惯用物", "slot": "惯用物",
        "rarity": "常见",
        "description": "把一段楼梯重新拧回原位，也能修好别的墙。", "color": "bright_white",
        "effect": "repair", "power": 30, "max_stack": 3,
    },
    "tape_measure": {
        "name": "卷尺", "category": "惯用物", "slot": "惯用物",
        "rarity": "少见",
        "description": "拉到悬停的格子，读出你们之间最短的谎言。", "color": "bright_white",
        "effect": "measure", "power": 2,
    },
    # ---- 梦中梦·千禧园（2026-10-10）----
    "usb_drive": {
        "name": "闪存盘", "category": "惯用物", "slot": "惯用物",
        "rarity": "少见", "loot": False,   # 容器不进自然掉落（test_containers 不变式）
        "description": "拔下来之前先「安全弹出」。能随身灌一点液体带走。",
        "color": "bright_cyan", "effect": "container",
        "container": {"medium": "liquid", "multi": False, "cap": 12},
    },
    "guestbook_page": {
        # 2026-10-26（平衡审计 §11.4）：恢复心智 5 → 6。5 低于「单资源 6–12」
        # 标尺下限；文案不含数字，无需同步英文描述。
        "name": "留言板签名", "category": "易逝物",
        "rarity": "少见",
        "description": "在梦的留言板上签个名：「到此一游」。写完心里踏实一点。",
        "color": "bright_yellow", "effect": "restore_mind", "power": 6, "max_stack": 2,
    },
}

# 投掷手套 / 调焦环 / 投石索已迁往 equipment.py：
# 2026-10-09 联想盘改版——常驻被动件属于「携带意象」，需要 slot 才能上盘装配
# （同 equipment.py 里 2026-10-07 对绝缘手套/多功能军刀/听诊器的对齐）。
# 惯用物这一档只留真正被「使用」掉的一次性工具（螺丝、铆钉、卷尺）。
