"""记忆碎片：跨局继承的可拆卸效果（稀有度走 MEMORY_RARITY）。"""

from __future__ import annotations

from typing import Any

ITEMS = {
    "lighthouse_keeper_memory": {
        "name": "守塔人的夜班表", "category": "记忆碎片", "slot": "记忆槽",
        "description": "记得某人替整片海守过夜。", "color": "bright_cyan",
        "effect": "memory", "memory_effect": "守夜的余温",
    },
    "frost_letter_memory": {
        "name": "结霜的信封", "category": "记忆碎片", "slot": "记忆槽",
        "description": "记得一封没敢拆的信在窗台上过了整个冬天。", "color": "#9ad1ff",
        "effect": "memory", "memory_effect": "低温的迟钝",
    },
    "paint_smell_memory": {
        "name": "油漆味的走廊", "category": "记忆碎片", "slot": "记忆槽",
        "description": "记得一条刚刷过漆、亮得晃眼的走廊。", "color": "bright_yellow",
        "effect": "memory", "memory_effect": "常亮的房间",
    },
    "shared_umbrella_memory": {
        "name": "共伞的雨声", "category": "记忆碎片", "slot": "记忆槽",
        "description": "记得半边肩膀湿透的距离。", "color": "#a7a9c7",
        "effect": "memory", "memory_effect": "雨声的钝化",
    },
    "rain_machine_memory": {
        "name": "雨夜的机械声", "category": "记忆碎片", "slot": "记忆槽",
        "description": "记得某种不会停机的雨。", "color": "bright_green",
        "effect": "memory", "memory_effect": "机械的耐性",
    },
    "rain_machine_memory_2": {
        "name": "收音机里的雨", "category": "记忆碎片", "slot": "记忆槽",
        "description": "有人把天气录成了背景音。", "color": "bright_green",
        "effect": "memory", "memory_effect": "雨声的遮蔽",
    },
    "model_room_memory": {
        "name": "模型房间的灯", "category": "记忆碎片", "slot": "记忆槽",
        "description": "每一盏灯都照着尚未拼完的部分。", "color": "bright_green",
        "effect": "memory", "memory_effect": "常亮的房间",
    },
    "unfinished_song_memory": {
        "name": "没有结尾的歌", "category": "记忆碎片", "slot": "记忆槽",
        "description": "副歌之后仍有一段空白。", "color": "bright_green",
        "effect": "memory", "memory_effect": "未尽的余韵",
    },
    "draft_margin_memory": {
        "name": "草稿边缘的折痕", "category": "记忆碎片", "slot": "记忆槽",
        "description": "纸张最外侧也曾经是正文。", "color": "bright_green",
        "effect": "memory", "memory_effect": "边缘的容差",
    },
    "plastic_gear_memory": {
        "name": "塑料齿轮的午后", "category": "记忆碎片", "slot": "记忆槽",
        "description": "齿轮没有带动机器，只带动了时间。", "color": "bright_green",
        "effect": "memory", "memory_effect": "空转的间隙",
    },
    "choir_note": {
        "name": "受潮的乐谱页", "category": "记忆碎片", "slot": "记忆槽",
        "description": "墨迹晕开的地方，原本写着休止符。", "color": "bright_green",
        "effect": "memory", "memory_effect": "休止的静默",
    },
    "attic_dust": {
        "name": "阁楼的灰尘", "category": "记忆碎片", "slot": "记忆槽",
        "description": "每一层灰都记得自己落下的年份。", "color": "bright_green",
        "effect": "memory", "memory_effect": "陈年的积累",
    },
    "last_window": {
        "name": "末班车的窗", "category": "记忆碎片", "slot": "记忆槽",
        "description": "窗外的东西移动得比车快。", "color": "bright_green",
        "effect": "memory", "memory_effect": "移动的视窗",
    },
    "salt_crust": {
        "name": "盐渍的护目片", "category": "记忆碎片", "slot": "记忆槽",
        "description": "戴久了眼角会结晶，但不再被强光刺穿。", "color": "bright_green",
        "effect": "memory", "memory_effect": "眩光的钝化",
    },
    "dry_gloves": {
        "name": "干涸的手套", "category": "记忆碎片", "slot": "记忆槽",
        "description": "它记得上一次把手伸进液氮里是什么感觉。", "color": "bright_green",
        "effect": "memory", "memory_effect": "低温的迟钝",
    },
    "burn_scar": {
        "name": "火燎的旧疤", "category": "记忆碎片", "slot": "记忆槽",
        "description": "灼伤结痂之后，热就不再是新的。", "color": "bright_green",
        "effect": "memory", "memory_effect": "灼痕的硬壳",
    },
    "leaden_marrow": {
        "name": "铅沉的骨髓", "category": "记忆碎片", "slot": "记忆槽",
        "description": "身体比谁都先学会和辐射共处。", "color": "bright_green",
        "effect": "memory", "memory_effect": "辐射的钝感",
    },
    "walker_habit": {
        "name": "走路的惯性", "category": "记忆碎片", "slot": "记忆槽",
        "description": "地面是干的还是湿的，脚踝比脑子清楚。", "color": "bright_green",
        "effect": "memory", "memory_effect": "湿滑的经验",
    },
    "wide_lung": {
        "name": "撑开的肺叶", "category": "记忆碎片", "slot": "记忆槽",
        "description": "呼吸被记得太久，就成了一种储备。", "color": "bright_green",
        "effect": "memory", "memory_effect": "扩大的肺活",
    },
    "calm_pulse": {
        "name": "平稳的脉搏", "category": "记忆碎片", "slot": "记忆槽",
        "description": "它记得自己从没有真正慌过。", "color": "bright_green",
        "effect": "memory", "memory_effect": "扩大的清醒",
    },
    "deep_reserve": {
        "name": "深埋的储备", "category": "记忆碎片", "slot": "记忆槽",
        "description": "总有一部分想象力被留在更深的地方。", "color": "bright_green",
        "effect": "memory", "memory_effect": "扩大的想象",
    },
    "first_cry_memory": {
        "name": "初啼的余温", "category": "记忆碎片", "slot": "记忆槽",
        "description": "啼哭散尽后留在襁褓里的最后一点温度。它替你记着你的名字（免疫失忆，跨局保留）。",
        "color": "bright_white", "effect": "memory", "memory_effect": "初啼的余地",
    },
    # ---- 内容扩展包 v2（2026-10-11）：+12 条（千禧园 4 / 门之回廊 2 / 深层边界 2 / 通用 4）----
    "usb_drive_memory": {
        "name": "随身听的旧歌单", "category": "记忆碎片", "slot": "记忆槽",
        "description": "一张写满歌名的清单，每一首都还停在播放键按下之前。",
        "color": "#8fe060", "effect": "memory", "memory_effect": "满格的存档",
    },
    "tape_hiss_memory": {
        "name": "磁带的底噪", "category": "记忆碎片", "slot": "记忆槽",
        "description": "倒带时的沙沙声里，有一段属于你的安静。",
        "color": "#8a6a4a", "effect": "memory", "memory_effect": "倒带的静音",
    },
    "dial_tone_memory": {
        "name": "忙音的下午", "category": "记忆碎片", "slot": "记忆槽",
        "description": "电话那头没人接，你却记得整个下午的心跳。",
        "color": "#e0c040", "effect": "memory", "memory_effect": "忙音的间距",
    },
    "pixel_pet_memory": {
        "name": "像素宠物的墓碑", "category": "记忆碎片", "slot": "记忆槽",
        "description": "屏幕暗下去的时候，它还保持着奔跑的姿势。",
        "color": "#c0e8f0", "effect": "memory", "memory_effect": "像素的寻路",
    },
    "bubble_wrap_memory": {
        "name": "气泡膜的解压", "category": "记忆碎片", "slot": "记忆槽",
        "description": "每一个气泡破掉的声音都恰到好处。",
        "color": "#d8e8f8", "effect": "memory", "memory_effect": "气泡的卸压",
    },
    "doorbell_memory": {
        "name": "门铃的半声", "category": "记忆碎片", "slot": "记忆槽",
        "description": "按了一半就缩回的手，和永远没说完的拜访。",
        "color": "#b8a26a", "effect": "memory", "memory_effect": "门风的驯服",
    },
    "grass_slip_memory": {
        "name": "草叶的松脱", "category": "记忆碎片", "slot": "记忆槽",
        "description": "从草丛里挣脱出来的那个下午，腿上还留着草的划痕。",
        "color": "#7ab86a", "effect": "memory", "memory_effect": "草叶的松动",
    },
    "poison_vial_memory": {
        "name": "空药瓶的回甘", "category": "记忆碎片", "slot": "记忆槽",
        "description": "苦过之后，舌根泛起的一点甜特别诚实。",
        "color": "#a0c890", "effect": "memory", "memory_effect": "毒雾的失敏",
    },
    "elevator_memory": {
        "name": "三十层的电梯按钮", "category": "记忆碎片", "slot": "记忆槽",
        "description": "最高那一层的按钮亮过一次，之后再没亮过。",
        "color": "#d0d8e8", "effect": "memory", "memory_effect": "机械的耐性",
    },
    "scribe_ink_memory": {
        "name": "执笔者的一滴墨", "category": "记忆碎片", "slot": "记忆槽",
        "description": "它替你写结尾时，一滴墨落在稿纸边缘——像一颗不肯熄灭的星。",
        "color": "#e8e0d0", "effect": "memory", "memory_effect": "醒着的顶层",
    },
    "echo_ring_memory": {
        "name": "回响戒指的颤动", "category": "记忆碎片", "slot": "记忆槽",
        "description": "戒指还记得每一声撞在门上的回音。",
        "color": "#c9a0ff", "effect": "memory", "memory_effect": "回响的储备",
    },
    "circuit_hum_memory": {
        "name": "电路板的嗡鸣", "category": "记忆碎片", "slot": "记忆槽",
        "description": "通电的那一瞬间，整个玩具都在小声唱歌。",
        "color": "#90c8b0", "effect": "memory", "memory_effect": "电路的辨音",
    },
}
