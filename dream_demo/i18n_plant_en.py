"""植物地形（可穿行植物）玩家可见文本的英文补译（2026-10-27）。

覆盖 core/plant_notes.py、core/plant_release.py、core/portents.py（拔除释出）
与 core/tamper_world.py（催生/枯萎）里仍以中文键取词的字面量。
键必须与源码里的 tr("…") 原文逐字一致；占位符与中文原文保持一致。
"""
from __future__ import annotations

EN_PLANT: dict[str, str] = {
    # ---- 一格植物释出配方的量词（core/plant_notes.py） ----
    "{name} {n} 单位": "{name} ×{n}",
    "点燃最多 {n} 格": "ignites up to {n} cells",
    "放出 ≤{n} 格、1 回合的静电场": "releases a 1-round static field over ≤{n} cells",
    "{n} 格的响声": "sound with radius {n} cells",
    "刮掉最多 3 格地形各 {n} 点耐久": "scrapes up to 3 terrain cells for {n} durability each",
    "把本格 {n} 单位气体推向朝向邻格": "pushes {n} units of gas from this cell toward the facing neighbour",
    "把触发者缠住 1 回合": "entangles the triggerer for 1 round",
    # ---- 格子详情：常驻 / 进入 / 踩踏 / 拔除 ----
    "相邻一圈": "the adjacent ring",
    "本格": "this cell",
    "（本格有光时失效）": " (fails while this cell is lit)",
    "脚步：{scope}内声径 −{n}{suffix}": "Footsteps: noise radius −{n} in {scope}{suffix}",
    "常驻：本格是可导电介质（自己不发电）":
        "Passive: this cell is a conductive medium (it generates no power itself)",
    "常驻：每回合吸 1 单位{names}，共 {n}":
        "Passive: absorbs 1 unit of {names} per round, up to {n}",
    "常驻：每回合把本格 1 单位气体按朝向推走，共 {n}":
        "Passive: pushes 1 unit of gas from this cell along its facing each round, up to {n}",
    "常驻：每回合把附近一项可洗征兆缩短 1 回合，共 {n}":
        "Passive: shortens one nearby washable omen by 1 round each round, up to {n}",
    "常驻：本格与相邻一圈的照明视距加值 {v}":
        "Passive: lighting sight bonus {v} for this cell and the adjacent ring",
    "常驻：本格向外扩散的气体预算 ÷{n}":
        "Passive: gas spread budget from this cell ÷{n}",
    "状态：已经用尽（空壳）": "Status: spent (empty husk)",
    "进入：本格与相邻一圈 +{v} 世界回合":
        "Entering: +{v} world rounds for this cell and the adjacent ring",
    "进入：本格 +{v} 世界回合": "Entering: +{v} world rounds for this cell",
    "踩踏：踩碎会释出 {detail}": "Trample: crushing it releases {detail}",
    "拔除：拔起会释出 {detail}": "Uproot: pulling it up releases {detail}",
    "一次用尽：踩与拔共用同一次释出":
        "One use: trampling and uprooting share the same release",
    "，拔起会释出 {detail}（落点在这株脚下，不是你的脚下）":
        ", and pulling it up releases {detail} (the drop lands at the plant's feet, not yours)",
    # ---- 释出播报（core/plant_release.py / core/portents.py） ----
    "{name}被破坏：{detail}。": "{name} is destroyed: {detail}.",
    "{kind} {amount} 单位": "{kind} ×{amount}",
    "推出 {amount} 单位气体": "pushes out {amount} units of gas",
    "点燃 {n} 处": "ignites {n} spots",
    "放电 {n} 格": "discharges across {n} cells",
    "发出 {n} 格声响": "emits sound with radius {n} cells",
    "刮损 {n} 处地形": "scrapes {n} terrain spots",
    "缠住触发者": "entangles the triggerer",
    "释出{detail}": "Releases {detail}",
    "贤者之苔吸走了「{name}」的一小段。":
        "Sage's Moss siphons away a little of “{name}”.",
    # ---- 篡改：催生 / 枯萎（core/tamper_world.py） ----
    "「{name}」立起来了，这一格开始挡住视线。":
        "“{name}” rises; this cell now blocks sight.",
    "「{name}」早就干透了。": "“{name}” dried out long ago.",
    "它本来就点不着，干枯也没用。":
        "It cannot burn in the first place; drying it out does nothing.",
}
