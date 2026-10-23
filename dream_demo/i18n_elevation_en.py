"""英文补漏：地势观察层与局部查看（docs/261019方案合集.md §15.4—§15.5）。

图例档位名与来源名会被 `tr(变量)` 查到，模板里带花括号的实参必须与中文原文
一一对应；`tests/test_i18n_coverage.py` 会同时检查这两件事，并断言译文里不含中文。
"""
from __future__ import annotations

EN_ELEVATION = {
    # 右栏读数
    "地势未知": "Elevation unknown",
    "地势未记录": "Elevation not recorded",
    "地势未知，无法判断流向": "Elevation unknown, so the flow cannot be judged.",
    "地势 {value} · 来源 {source}": "Elevation {value} · source: {source}",
    "相对脚下 {value}": "Compared with your footing: {value}",
    "等高": "Level",
    "高 {n} 档": "{n} tier(s) higher",
    "低 {n} 档": "{n} tier(s) lower",
    # 四邻坡向
    "四邻 更高 {high} · 等高 {same} · 更低 {low} · 未知 {unknown}": (
        "Neighbours: {high} higher · {same} level · {low} lower · {unknown} unknown"
    ),
    # 液面与流向
    "液面 {surface} ＝ 地势 {tier} 档 × {step} ＋ 液量 {amount}": (
        "Liquid surface {surface} = elevation {tier} × {step} + amount {amount}"
    ),
    "可能流向 {dirs}（邻格地势档更低）": "May flow {dirs} (a neighbouring elevation tier is lower)",
    "可能流向 {dirs}（地势相同，按液面摊平）": "May flow {dirs} (same elevation, levelled by liquid surface)",
    "可知邻格都不更低": "No known neighbour is lower",
    "{n} 格被固体挡住": "{n} cell(s) blocked by solids",
    "{n} 格地势未知": "{n} cell(s) have unknown elevation",
    "“较低”不等于一定马上流入：液量、实际液面、墙体、地板流速与每拍节奏都会改变结果。": (
        "\"Lower\" does not mean it flows at once: amount, actual liquid surface, walls, "
        "floor flow rate and per-tick rhythm all change the result."
    ),
    # 局部示意与固定图例
    "局部示意（[ ] 为光标格，? 为未知或未记录）": (
        "Local sketch ([ ] is the cursor cell, ? means unknown or unrecorded)"
    ),
    "固定图例（不随本层已知高低自动缩放）": (
        "Fixed legend (never rescaled to this floor's known highs and lows)"
    ),
    # 图例档位名（ELEVATION_SCALE）
    "深洼": "Deep hollow",
    "低地": "Low ground",
    "基准": "Datum",
    "高地": "High ground",
    "高台": "High plateau",
    # 来源名（CellKnowledge.sources）
    "当前可见": "Currently visible",
    "上次观察": "Last observed",
    "显影遗留": "Developer residue",
    "地形增强授权": "Terrain enhancement",
    "初始图鉴": "Starting codex",
    "恒显类别": "Always-visible category",
    # 同格内容分组（accessory_layer_lines）：其余分组名早已登记，只补这两个。
    "火焰": "Flame",
    "预警": "Telegraph",
    # 格子详情的地势介绍行（不再把 0—3 写成所有地图与改造后的绝对范围）。
    "地势是本格的整数档位（常见 0—3，地形改造与特殊位面会有负值或更高）：液体按地势与液面高低流动，低洼处更容易积液。": (
        "Elevation is this cell's whole-tier count in integer steps (usually 0-3, though "
        "terrain editing and special realms can reach negatives or higher): liquid flows by "
        "elevation and liquid surface, so hollows collect more of it."
    ),
    # ---- §15.6 操作预览（ui/terrain_preview.py）----
    "预览 · {name}": "Preview · {name}",
    "作用区 {n} 格 · 中心 {pos}": "Area: {n} cell(s), centre {pos}",
    "目标 {pos}": "Target {pos}",
    "本格 {pos}（倒在本格）": "This cell {pos} (poured here)",
    "地势 {changes}": "Elevation {changes}",
    "{n} 格被钉住，不会改变": "{n} cell(s) are pinned and will not change",
    "{n} 格地势未知，改了也读不出档位": (
        "{n} cell(s) have unknown elevation: they still change, but no tier can be read"
    ),
    "脚下 {pos} 不在作用区": "Your footing {pos} is outside the area",
    "脚下 {pos} 就在作用区里": "Your footing {pos} is inside the area",
    "脚下 {pos} 一起改变：地势 {old}→{new}": (
        "Your footing {pos} changes with it: elevation {old} to {new}"
    ),
    "脚下 {pos} 也在作用区，但这一格地势读不出": (
        "Your footing {pos} is in the area, but this cell's elevation cannot be read"
    ),
    "脚下 {pos} 被钉住，不会改变": "Your footing {pos} is pinned and will not change",
    "{kind}（{pos}）：{flow}": "{kind} at {pos}: {flow}",
    "另有 {n} 格带液，未逐格预测流向": "{n} more wet cell(s) with no per-cell flow forecast",
    "这一格在视野外，只标出会被改变的位置。": (
        "This cell is out of sight, so only the position it would change is marked."
    ),
    "本格现有 {kind} ×{amount}": "This cell holds {kind} x{amount}",
    "倒入 {kind} ×{amount}": "Pouring in {kind} x{amount}",
    "预计 {kind} ×{amount}": "Expected {kind} x{amount}",
    "混合不稳定：这一格不会留下一摊液体。": (
        "The mix is unstable: this cell will not keep a pool of liquid."
    ),
    "目标 {pos}：地势 {tier} 档 · 液面 {surface} → 清空": (
        "Target {pos}: elevation {tier}, liquid surface {surface}, then drained"
    ),
    "目标 {pos}：这一格的地势或液面读不出": (
        "Target {pos}: this cell's elevation or liquid surface cannot be read"
    ),
    "抽干 {n} 点液态记忆，想象力 +2。": "Drains {n} points of liquid memory; imagination +2.",
    "液面清空，地面结成冰面。": "The surface drains and the ground freezes into an ice sheet.",
    "原地蒸腾成 {gas} ×{amount}。": "It transpires in place into {gas} x{amount}.",
}
