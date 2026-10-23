"""意识体（异象）定义表：全部失控意识/强烈异象/核心执念的数值与行为。

字段约定：integrity=血量；power=每次命中的创伤；layers=[起,止] 主生成层（起始层是硬下限，结束后按 region_falloff 衰减）；pool=False 或 spawn_realms 表示不进主层通用池（核心/深层/梦中梦专属等，由专属管线投放）。数值分区带（2026-09-19 平衡）：R1 浅层 hp2-6/伤1-5 · R2 幻觉 hp4-11/伤2-9 · R3 无意识 hp7-16/伤3-13 · 深层 28-30 单独缩放。"""

from __future__ import annotations

from typing import Any

ANOMALY_DEFINITIONS: dict[str, dict[str, Any]] = {
    "anomaly.page_hound": {
        "passive": "循迹重生｜被解决后有概率在远处重新凝聚成形。",
        "name": "纸页犬", "description": "由反复折叠的纸页聚成，会沿可辨认的边缘追逐声音。", "glyph": "𓃡",
        "anomaly_kind": "普通异象", "integrity": 2, "move_time": 1.0, "attack_time": 1.0,
        # §7.2「监视者的三页」：纸页犬咬走的是协会账页——掉落从折页弹改为
        # 留言板签名页，散页来路「从它身上取回一页」由此成立（另一路是
        # 档案馆编目台的拆页，两条不互相强迫）。
        "trauma_type": "心智创伤", "communicates": True, "drop_id": "guestbook_page", "dissolution_reward": 10, "vision": 6,
    "power": 1, "layers": [1, 5], "trait": "respawner",
    },
    "anomaly.folded_person": {
        "passive": "纸折护身｜受到的创伤 −1（至少 1 点）。",
        "name": "折页人", "description": "轮廓像一张被迫对折的人形说明书。", "glyph": "𓀠",
        "anomaly_kind": "普通异象", "integrity": 3, "move_time": 1.0, "attack_time": 1.0,
        "trauma_type": "心智创伤", "communicates": True, "drop_id": "folded_projectile", "dissolution_reward": 10, "vision": 6,
    "power": 2, "layers": [1, 6], "trait": "paper_fold",
    },
    "anomaly.reverse_drummer": {
        "skill": "敲击｜每 6 拍向以自身为中心 9×9 范围的异象告知你的位置。",
        "name": "倒放鼓手", "description": "先留下回声，随后才完成敲击。", "glyph": "◎",
        "anomaly_kind": "普通异象", "integrity": 4, "move_time": 1.0, "attack_time": 1.0,
        "trauma_type": "心智创伤", "communicates": True, "drop_id": "folded_projectile", "dissolution_reward": 10, "vision": 7,
    "power": 3, "layers": [4, 10], "trait": "drum_alert",
    },
    "anomaly.model_porter": {
        "passive": "顺势推挤｜攻击时 33% 概率把你沿攻击方向推开一格。",
        "name": "模型搬运工", "description": "不断移动不存在的模型零件，拒绝承认房间已经改变。", "glyph": "𓀃",
        "anomaly_kind": "普通异象", "integrity": 4, "move_time": 1.0, "attack_time": 1.0,
        "trauma_type": "清醒创伤", "communicates": True, "drop_id": "model_screw", "dissolution_reward": 9, "vision": 6,
    "power": 3, "layers": [5, 11], "trait": "pusher",
    },
    "anomaly.silent_audience": {
        "passive": "嘲讽｜它视野内的异象受到创伤时，伤害转移给它自己。",
        "name": "无声观众", "description": "它面向一处空白，等待并不存在的演出继续。", "glyph": "♙",
        "anomaly_kind": "普通异象", "integrity": 6, "move_time": 1.0, "attack_time": 1.0,
        "trauma_type": "心智创伤", "communicates": False, "drop_id": "quiet_ticket", "dissolution_reward": 8, "vision": 6,
    "power": 5, "layers": [7, 13], "trait": "taunt",
    },
    "anomaly.cooling_doll": {
        "passive": "迟缓行进｜每 2 回合移动 1 格，但攻击节奏正常。",
        "name": "冷却人偶", "description": "表面温度持续下降，动作缓慢却从不迟到。", "glyph": "♟",
        "anomaly_kind": "普通异象", "integrity": 5, "move_time": 2.0, "attack_time": 0.8,
        "trauma_type": "清醒创伤", "communicates": True, "drop_id": "warm_coffee", "dissolution_reward": 9, "vision": 6,
    "power": 4, "layers": [6, 12],
    },
    "anomaly.backlit_reader": {
        "passive": "追光｜一旦盯上你，失去视线也不会很快跟丢。",
        "name": "逆光读者", "description": "逆光里立着一个读者，脸看不清。它低着头，逐字读过你留下的足迹。", "glyph": "☻",
        "anomaly_kind": "普通异象", "integrity": 5, "move_time": 1.0, "attack_time": 1.0,
        "trauma_type": "清醒创伤", "communicates": True, "drop_id": "clear_glass", "dissolution_reward": 10, "vision": 8,
    "power": 4, "layers": [7, 13], "trait": "tracker",
    },
    "anomaly.echo_door": {
        "skill": "回声广播｜每 7 拍把你的位置告知它视野内的同伴。",
        "name": "回声门", "description": "一扇会自行游荡的门，门缝里还在小声转述它看见的东西。", "glyph": "⋂",
        "anomaly_kind": "普通异象", "integrity": 6, "move_time": 1.4, "attack_time": 1.2,
        "trauma_type": "心智创伤", "communicates": True, "drop_id": "headphone_coil", "dissolution_reward": 11, "vision": 8,
    "power": 5, "layers": [8, 14], "trait": "echo_pulse",
    },
    "anomaly.faceless_editor": {
        "passive": "自我修订｜每 5 拍恢复 1 点完整度。",
        "name": "强烈异象·无脸编辑", "description": "它删改周围对象的边界，却从不在批注里留下署名。", "glyph": "✍",
        "anomaly_kind": "强烈异象", "integrity": 6, "move_time": 1.0, "attack_time": 1.0,
        "trauma_type": "心智创伤", "communicates": True, "drop_id": "unfinished_editor", "dissolution_reward": 12, "vision": 8,
    "power": 5, "layers": [2, 14], "trait": "self_revise",
        "insight_id": "思维润滑",
    },
    "anomaly.folded_room": {
        "passive": "空间挪移｜受击后有概率挪移到附近另一处。",
        "name": "强烈异象·房间折叠体", "description": "两个不相邻的房间在它的轮廓内占据同一位置。", "glyph": "⚚",
        "anomaly_kind": "强烈异象", "integrity": 7, "move_time": 1.2, "attack_time": 0.9,
        "trauma_type": "清醒创伤", "communicates": True, "drop_id": "clear_glass", "dissolution_reward": 12, "vision": 8,
    "power": 6, "layers": [4, 16], "trait": "room_shift",
        "insight_id": "不燃体质",
    },
    "anomaly.unfinished_period": {
        "name": "核心执念·未完成句号", "description": "所有未完成的句子都试图在这里获得同一个结尾。", "glyph": "@",
        "anomaly_kind": "核心执念", "integrity": 45, "move_time": 1.0, "attack_time": 0.7,
        "trauma_type": "清醒创伤", "communicates": True, "drop_id": "unfinished_fullstop", "dissolution_reward": 20, "vision": 9,
    "power": 5, "layers": [20, 20], "pool": False,
        "insight_id": "蜜脉",
    },
    # ---- 内容扩展第一批（第 7–9 层储备 + 前 6 层扩池） ----
    "anomaly.clock_keeper": {
        "name": "挂钟守夜人", "description": "钟摆每摆过一个整点，就把整层梦境敲醒一次。", "glyph": "⧗",
        "anomaly_kind": "普通异象", "integrity": 5, "move_time": 1.2, "attack_time": 1.0,
        "trauma_type": "心智创伤", "communicates": True, "drop_id": "clockwork_half", "dissolution_reward": 10, "vision": 7,
    "power": 4, "layers": [6, 12],
        "trait": "clock_pulse", "color": "#f4d35e",
    },
    "anomaly.mirror_attendant": {
        "name": "镜像侍者", "description": "你向左，它便向右；你们共享一条看不见的对称轴。", "glyph": "⧉",
        "anomaly_kind": "普通异象", "integrity": 2, "move_time": 1.0, "attack_time": 1.0,
        "trauma_type": "清醒创伤", "communicates": True, "drop_id": "mirror_shard", "dissolution_reward": 9, "vision": 7,
    "power": 2, "layers": [3, 9],
        "trait": "mirror_step", "color": "#c0d8f0",
    },
    "anomaly.paper_fish": {
        "name": "纸鱼", "description": "折痕是它的鳍，液面是它的天空；上岸时几乎无法移动。", "glyph": "𓆟",
        "anomaly_kind": "普通异象", "integrity": 2, "move_time": 1.0, "attack_time": 1.0,
        "trauma_type": "心智创伤", "communicates": True, "drop_id": "wet_fold", "dissolution_reward": 8, "vision": 6,
    "power": 1, "layers": [1, 6],
        "trait": "liquid_swimmer", "color": "#9ad1c9",
    },
    "anomaly.sleepwalking_tailor": {
        # ✂(U+2702) 带 FE0E 强制文本呈现：与符号表同款，避免被字体按 emoji 渲染。
        "name": "梦游裁缝", "description": "它仍在为不存在的客人改衣，剪刀顺手剪走口袋里的东西。", "glyph": "✂︎",
        "anomaly_kind": "普通异象", "integrity": 4, "move_time": 1.0, "attack_time": 1.0,
        "trauma_type": "心智创伤", "communicates": True, "drop_id": "loose_thread", "dissolution_reward": 10, "vision": 6,
    "power": 3, "layers": [5, 11],
        "trait": "cutpurse", "color": "#e8a0bf",
    },
    "anomaly.human_coat_rack": {
        "name": "人形衣架", "description": "静止时它与家具没有区别，直到你走进它的影子。", "glyph": "☂",
        "anomaly_kind": "普通异象", "integrity": 3, "move_time": 1.0, "attack_time": 1.0,
        "trauma_type": "清醒创伤", "communicates": True, "drop_id": "bent_hook", "dissolution_reward": 9, "vision": 5,
    "power": 2, "layers": [2, 8],
        "trait": "disguise", "color": "#a3b18a",
    },
    "anomaly.stair_echo": {
        "name": "楼梯回声", "description": "一段没有尽头的脚步声，沿着固定的楼梯上下巡逻。", "glyph": "⌂",
        "anomaly_kind": "普通异象", "integrity": 5, "move_time": 1.0, "attack_time": 1.0,
        "trauma_type": "心智创伤", "communicates": True, "drop_id": "hollow_step", "dissolution_reward": 10, "vision": 6,
    "power": 2, "layers": [3, 20], "pool": False,
        "trait": "patrol", "color": "#d8b26e",
    },
    "anomaly.double_exposure": {
        "name": "强烈异象·双重曝光", "description": "同一张底片上站着两个它，哪一个都是真的。", "glyph": "❖",
        "anomaly_kind": "强烈异象", "integrity": 9, "move_time": 1.0, "attack_time": 1.0,
        "trauma_type": "心智创伤", "communicates": True, "drop_id": "double_frame", "dissolution_reward": 13, "vision": 8,
    "power": 8, "layers": [14, 20],
        "trait": "split_main", "color": "#b9a0f0", "insight_id": "残影直觉",
    },
    "anomaly.wet_choir": {
        "name": "强烈异象·湿透的合唱团", "description": "湿透的乐谱让每一个声部都急着追上另一个。", "glyph": "♬",
        "anomaly_kind": "强烈异象", "integrity": 8, "move_time": 1.1, "attack_time": 1.0,
        "trauma_type": "清醒创伤", "communicates": True, "drop_id": "choir_note", "dissolution_reward": 12, "vision": 7,
    "power": 7, "layers": [6, 21],
        "trait": "choir", "color": "#6ea8d8", "insight_id": "和声耐受",
    },
    "anomaly.moving_staircase": {
        "name": "强烈异象·迁徙的楼梯", "description": "一段楼梯决定去它从未连接过的楼层，途中不绕开任何人。", "glyph": "⌗",
        "anomaly_kind": "强烈异象", "integrity": 11, "move_time": 1.5, "attack_time": 0.8,
        "trauma_type": "清醒创伤", "communicates": False, "drop_id": "stair_bolt", "dissolution_reward": 14, "vision": 0,
    "power": 9, "layers": [16, 24],
        "trait": "staircase", "color": "#b8a28a", "insight_id": "深层耐性",
    },
    "anomaly.hollow_lighthouse": {
        "name": "核心执念·空心的灯塔", "description": "它照亮整片梦境，却照不进自己的空腔。", "glyph": "☼",
        "anomaly_kind": "核心执念", "integrity": 25, "move_time": 1.0, "attack_time": 0.7,
        "trauma_type": "清醒创伤", "communicates": True, "drop_id": "lighthouse_ember", "dissolution_reward": 20, "vision": 9,
    "power": 4, "layers": [10, 10], "pool": False,
        "trait": "lighthouse", "color": "#ffd97d", "insight_id": "灯塔共鸣",
    },
    # ---- 无意识领域（21–27）----
    "anomaly.sunken_bell": {
        "name": "无意识沉钟", "description": "沉在无意识之海的钟，每次摆动都把附近的梦震出涟漪。", "glyph": "◕",
        "anomaly_kind": "普通异象", "integrity": 7, "move_time": 1.2, "attack_time": 1.0,
        "trauma_type": "心智创伤", "communicates": True, "drop_id": "morning_dew", "dissolution_reward": 13, "vision": 7,
    "power": 6, "layers": [21, 27],
        "trait": "clock_pulse", "color": "#8a9ac8",
    },
    "anomaly.silent_mirror": {
        "name": "缄默映像", "description": "它不做任何决定，只精确地做你做过的事。", "glyph": "⇧",
        "anomaly_kind": "普通异象", "integrity": 7, "move_time": 1.0, "attack_time": 1.1,
        "trauma_type": "心智创伤", "communicates": False, "drop_id": "mirror_shard", "dissolution_reward": 12, "vision": 7,
    "power": 6, "layers": [21, 27],
        "trait": "mirror_step", "color": "#c8d8e8", "insight_id": "足音消音",
    },
    "anomaly.thought_worm": {
        "name": "噬念蠕虫", "description": "它咬穿念头取食，被咬中的想法再也想不起来。", "glyph": "𓆗",
        "anomaly_kind": "普通异象", "integrity": 9, "move_time": 1.0, "attack_time": 1.1,
        "trauma_type": "心智创伤", "communicates": True, "drop_id": "void_coagulant", "dissolution_reward": 13, "vision": 6,
    "power": 8, "layers": [24, 27], "trait": "mind_drain",
        "color": "#9aa86a",
    },
    "anomaly.faceless_watchman": {
        "name": "无面守夜人", "description": "无意识领域没有昼夜，它仍然守着一段不存在的更次。", "glyph": "☃",
        "anomaly_kind": "普通异象", "integrity": 9, "move_time": 1.0, "attack_time": 1.1,
        "trauma_type": "清醒创伤", "communicates": True, "drop_id": "night_lantern", "dissolution_reward": 14, "vision": 7,
    "power": 8, "layers": [24, 27],
        "trait": "disguise", "color": "#a8b8c8",
    },
    "anomaly.nightmare_weaver": {
        "passive": "织梦同调｜身旁有同伴时，造成的创伤 +1。",
        "name": "强烈异象·噩梦编织者", "description": "它把你的记忆织成噩梦，一针一线都很耐心。", "glyph": "❥",
        "anomaly_kind": "强烈异象", "integrity": 12, "move_time": 1.0, "attack_time": 0.9,
        "trauma_type": "心智创伤", "communicates": True, "drop_id": "morning_dew", "dissolution_reward": 15, "vision": 8,
        "power": 10, "layers": [22, 27], "trait": "pack_weave",
        "color": "#7a5a9a", "insight_id": "梦魇老主顾",
    },
    "anomaly.forgetter": {
        "passive": "逐客｜它不遭受任何迟缓、冻结类侵扰。",
        "skill": "遗忘之触｜命中你时，随机驱散你的一个正面征兆。",
        "name": "强烈异象·遗忘织者", "description": "它拆掉名字与事物之间的线，再织回错误的名字。", "glyph": "࿐",
        "anomaly_kind": "强烈异象", "integrity": 12, "move_time": 1.1, "attack_time": 1.0,
        "trauma_type": "心智创伤", "communicates": True, "drop_id": "deep_thought_tea", "dissolution_reward": 15, "vision": 8,
    "power": 10, "layers": [22, 27], "trait": "forget_touch",
        "color": "#a89ac8", "insight_id": "巧合收集",
    },
    "anomaly.blank_rift": {
        "name": "强烈异象·空白裂隙", "description": "梦在这里缺了一块，缺口的边缘会缓慢移动。", "glyph": "□",
        "anomaly_kind": "强烈异象", "integrity": 14, "move_time": 1.5, "attack_time": 0.8,
        "trauma_type": "清醒创伤", "communicates": False, "drop_id": "void_coagulant", "dissolution_reward": 17, "vision": 0,
    "power": 11, "layers": [23, 27],
        "trait": "staircase", "color": "#d8d8e8", "insight_id": "绝缘体质",
    },
    "anomaly.primordial_impulse": {
        "passive": "原初不息｜免疫迟缓与冻结，也不会被推动。",
        # ⚡(U+26A1) 是 Emoji_Presentation 字符：按 emoji 渲染（染不上阵营色）且
        # 独占两列，放进两列一格的排版会把整行挤错位。改用符号表同款的 ↯(U+21AF)。
        "name": "强烈异象·原初冲动", "description": "语言出现之前就存在的那个念头，从未学会停顿。", "glyph": "↯",
        "anomaly_kind": "强烈异象", "integrity": 16, "move_time": 0.7, "attack_time": 0.6,
        "trauma_type": "清醒创伤", "communicates": False, "drop_id": "deep_thought_tea", "dissolution_reward": 18, "vision": 6,
    "power": 13, "layers": [26, 27], "trait": "relentless",
        "color": "#e8c84a", "insight_id": "稳立不摇",
    },
    "anomaly.first_cry": {
        "passive": "初啼｜受到创伤时发出啼哭，惊动整层梦。",
        "name": "核心执念·初啼之核", "description": "无意识的最深处，是第一声啼哭之前的那片寂静。", "glyph": "ω",
        "anomaly_kind": "核心执念", "integrity": 64, "move_time": 1.0, "attack_time": 0.9,
        "trauma_type": "清醒创伤", "communicates": True, "drop_id": "first_cry_memory", "dissolution_reward": 24, "vision": 10,
    "power": 7, "layers": [27, 27], "trait": "cry_alert", "pool": False,
        "color": "#f0f0ff", "insight_id": "醒梦交界",
    },
    # ---- 深层边界（28–30）：终局核心执念 ----
    "anomaly.scribe": {
        "passive": "定稿免疫｜不会陷入失明，也不会被推动。",
        "skill": "校对、删稿、定稿｜完整度下降时进入三阶段；标记旧站位，两拍后造成清醒创伤。后两阶段召唤最多两个残影。",
        "name": "核心执念·执笔者", "description": "打字机长着人的形状，按键声细密如雨。它已经在替你写了——连结尾都替你挑好了。", "glyph": "✒",
        "anomaly_kind": "核心执念", "integrity": 80, "move_time": 1.2, "attack_time": 1.8,
        "trauma_type": "清醒创伤", "communicates": True, "drop_id": "first_cry_memory", "dissolution_reward": 30, "vision": 9,
        "power": 4, "layers": [30, 30], "trait": "author_pace", "pool": False,
        "color": "#e8e0d0",
    },
    # ---- 2026-09-19 深层边界（28-30）专属异象：数值单独调高，只在深层出现 ----
    "anomaly.dream_accountant": {
        "name": "梦的账房", "description": "拨着一把看不见的算盘：它记下你花掉的每一分清醒，并打算连本带利地收回去。",
        "glyph": "🮔", "anomaly_kind": "普通异象", "integrity": 12, "move_time": 1.0, "attack_time": 1.0,
        "trauma_type": "清醒创伤", "communicates": True, "drop_id": "old_keycap", "dissolution_reward": 12, "vision": 7,
        "power": 6, "layers": [28, 30], "pool": False, "trait": "mind_drain", "color": "#c8b890",
    },
    "anomaly.ink_archivist": {
        "name": "墨档员", "description": "浑身浸透墨水的登记员，替深层边界归档所有走失的名字。静止时与一摞档案没有区别。",
        # 2026-09-22：原 ✒ 与执笔者撞字形（异象字形全表唯一），改为 ▤（档案格架）。
        "glyph": "▤", "anomaly_kind": "普通异象", "integrity": 13, "move_time": 1.0, "attack_time": 1.0,
        "trauma_type": "心智创伤", "communicates": False, "drop_id": "torn_page", "dissolution_reward": 12, "vision": 5,
        "power": 7, "layers": [28, 30], "pool": False, "trait": "disguise", "color": "#8b8da8",
    },
    "anomaly.whole_choir": {
        "name": "全声合唱", "description": "许多张嘴挤在同一片阴影里，唱着被删去的台词。一声停下，另一声又接上。",
        "glyph": "⌇", "anomaly_kind": "强烈异象", "integrity": 16, "move_time": 1.0, "attack_time": 1.0,
        "trauma_type": "心智创伤", "communicates": True, "drop_id": "headphone_coil", "dissolution_reward": 14, "vision": 7,
        "power": 9, "layers": [28, 30], "pool": False, "trait": "choir", "color": "#c9a0ff",
        "insight_id": "抢拍",
    },
    "anomaly.null_witness": {
        "name": "虚无见证", "description": "那里一直有个空着的位置。你移开目光，再回头看，它仍在那里。",
        "glyph": "ø", "anomaly_kind": "强烈异象", "integrity": 18, "move_time": 1.2, "attack_time": 1.0,
        "trauma_type": "清醒创伤", "communicates": False, "drop_id": "clear_glass", "dissolution_reward": 14, "vision": 8,
        "power": 10, "layers": [28, 30], "pool": False, "trait": "relentless", "color": "#7ad0ff",
        "insight_id": "边界脚本",
    },
    # ---- 梦中梦·千禧园（2026-10-10，docs/millennium-garden-design.md §10）----
    # 11 个 realm 专属异象：主梦不生成（pool=False），只进 millennium_garden 的
    # anomaly_pool（§10.2 与主梦强烈异象按 2:1 混入）。glyph 全 emoji（M0 探针 SAFE）。
    # 数值锚：专属 hp 8–14 / 单次创伤 2–6；池内主梦混入项 hp 11–16（对标主梦 20 层 = 无意识区后段）。
    "anomaly.bsod_warden": {
        "skill": "蓝屏脉冲｜每 5 拍向周围一圈散出一次心智冲击。",
        "name": "蓝屏守夜人", "description": "它守着一块永远亮着的死屏，屏上的进度条一百年没走完。",
        "glyph": "💀", "anomaly_kind": "强烈异象", "integrity": 14, "move_time": 1.0, "attack_time": 1.2,
        "trauma_type": "心智创伤", "communicates": True, "drop_id": "pixel_scrap", "dissolution_reward": 12, "vision": 7,
        "power": 6, "layers": [11, 30], "pool": False, "trait": "mind_drain", "color": "#2050d0",
        "skills": ({"kind": "emanate", "every": 5, "radius": 1, "medium": "gas", "emit": "呢喃"},),
        "insight_id": "弹窗拦截",
    },
    "anomaly.rewind_ghost": {
        "passive": "倒带｜命中你时把你沿攻击方向推回两格。",
        "name": "倒带幽灵", "description": "一段倒着放的录像：它总在你到达之前，先回到你出发的地方。",
        "glyph": "⏪", "anomaly_kind": "普通异象", "integrity": 10, "move_time": 1.0, "attack_time": 1.1,
        "trauma_type": "心智创伤", "communicates": True, "drop_id": "pixel_scrap", "dissolution_reward": 10, "vision": 6,
        "power": 4, "layers": [11, 30], "pool": False, "trait": "pusher", "color": "#c8c8d8",
    },
    "anomaly.pager_sprite": {
        "skill": "传呼｜每 6 拍向视野内所有异象告知你的位置。",
        "name": "传呼精灵", "description": "腰间别着一台永远在震动的传呼机：哔——哔——找你有事。",
        "glyph": "📟", "anomaly_kind": "普通异象", "integrity": 8, "move_time": 0.8, "attack_time": 1.2,
        "trauma_type": "心智创伤", "communicates": True, "drop_id": "pixel_scrap", "dissolution_reward": 8, "vision": 8,
        "power": 3, "layers": [11, 30], "pool": False, "trait": "drum_alert", "color": "#e0c040",
    },
    "anomaly.disco_echo": {
        "passive": "频闪｜它视野内的你视野减半（迪斯科球在转）。",
        "name": "迪斯科残响", "description": "一场散场二十年的舞会还在它头顶继续，光斑扫过之处皆是碎彩。",
        "glyph": "🪩", "anomaly_kind": "普通异象", "integrity": 12, "move_time": 1.0, "attack_time": 1.0,
        "trauma_type": "心智创伤", "communicates": True, "drop_id": "pixel_scrap", "dissolution_reward": 11, "vision": 7,
        "power": 5, "layers": [11, 30], "pool": False, "trait": "mind_drain", "color": "#d070d0",
    },
    "anomaly.static_viewer": {
        "passive": "雪花屏｜你看向它时，它的雪花会糊住你的视线。",
        "name": "雪花观众", "description": "一台没有信号的电视里坐着一位观众，从头到尾没有换过台。",
        "glyph": "📺", "anomaly_kind": "普通异象", "integrity": 10, "move_time": 0.7, "attack_time": 1.0,
        "trauma_type": "心智创伤", "communicates": False, "drop_id": "pixel_scrap", "dissolution_reward": 10, "vision": 6,
        "power": 4, "layers": [11, 30], "pool": False, "trait": "mind_drain", "color": "#b8c4d8",
    },
    "anomaly.floppy_collector": {
        "passive": "存档｜静止时与一堆软盘没有区别；被击中后立刻读碟启动。",
        "name": "软盘收藏家", "description": "它收藏每一张写坏的软盘，并把坏档案归档到你的口袋里。",
        "glyph": "💾", "anomaly_kind": "普通异象", "integrity": 12, "move_time": 1.0, "attack_time": 1.0,
        "trauma_type": "清醒创伤", "communicates": False, "drop_id": "pixel_scrap", "dissolution_reward": 11, "vision": 5,
        "power": 4, "layers": [11, 30], "pool": False, "trait": "disguise", "color": "#404048",
    },
    "anomaly.screensaver_bubble": {
        "passive": "屏保｜无碰撞漂浮，碰到你和异象都会把双方弹开一小段。",
        "name": "屏保气泡", "description": "上世纪的屏幕保护程序还在漫天飘——里面偶尔闪过一行褪色的字。",
        "glyph": "🫧", "anomaly_kind": "普通异象", "integrity": 8, "move_time": 2.0, "attack_time": 2.0,
        "trauma_type": "心智创伤", "communicates": False, "drop_id": "pixel_scrap", "dissolution_reward": 8, "vision": 4,
        "power": 2, "layers": [11, 30], "pool": False, "color": "#c0e8f0",
    },
    "anomaly.cursor_hunter": {
        "passive": "指针锁定｜一旦进入追踪，移动耗时减半（箭头直奔目标）。",
        "name": "指针追猎者", "description": "一支没有主人的箭头光标，永远指向它决定要点击的东西。",
        "glyph": "🖱", "anomaly_kind": "普通异象", "integrity": 11, "move_time": 0.6, "attack_time": 1.2,
        "trauma_type": "清醒创伤", "communicates": False, "drop_id": "pixel_scrap", "dissolution_reward": 11, "vision": 9,
        "power": 6, "layers": [11, 30], "pool": False, "trait": "relentless", "color": "#f0f0f0",
    },
    "anomaly.startup_chorus": {
        "passive": "合唱｜与它同行的异象都不会轻易放弃追击。",
        "name": "开机音合唱", "description": "数十年前每一次开机的启动音，在这里叠成了永不停歇的和声。",
        "glyph": "🔊", "anomaly_kind": "强烈异象", "integrity": 10, "move_time": 1.0, "attack_time": 1.0,
        "trauma_type": "清醒创伤", "communicates": True, "drop_id": "pixel_scrap", "dissolution_reward": 10, "vision": 7,
        "power": 5, "layers": [11, 30], "pool": False, "trait": "choir", "color": "#f0e0a0",
        "insight_id": "磁头清洁",
    },
    "anomaly.deadlink_roamer": {
        "passive": "断链重连｜被解决后有概率在远处重新连线上线。",
        "name": "断链漫游者", "description": "404。它走过的链接全都失效，但它自己永远能重新加载。",
        "glyph": "🌐", "anomaly_kind": "普通异象", "integrity": 13, "move_time": 1.1, "attack_time": 1.0,
        "trauma_type": "心智创伤", "communicates": False, "drop_id": "pixel_scrap", "dissolution_reward": 12, "vision": 6,
        "power": 5, "layers": [11, 30], "pool": False, "trait": "respawner", "color": "#60a0c8",
    },
    "anomaly.popup_peddler": {
        "passive": "嘲讽｜它视野内的异象受到创伤时，伤害转移给它自己。",
        "name": "弹窗推销员", "description": "「恭喜您获得大奖！」——点掉一个，它还会再开三个。",
        "glyph": "🎁", "anomaly_kind": "普通异象", "integrity": 9, "move_time": 1.0, "attack_time": 1.1,
        "trauma_type": "清醒创伤", "communicates": True, "drop_id": "pixel_scrap", "dissolution_reward": 9, "vision": 6,
        "power": 3, "layers": [11, 30], "pool": False, "trait": "taunt", "color": "#f0a040",
    },
    # 核心执念（第 5 层零点体育场专属 BOSS；双路径召唤，只有敌对形态）。
    # 三阶段全召唤系：孵化请求🫧 → 进程繁殖📟 → 系统迁移📺+瞬移；
    # handler = trait "y2k_summon"（core/enemy_skills.py 的 realm 专属最小实装）。
    "anomaly.core_y2k_worm": {
        "skill": "孵化请求、进程繁殖、系统迁移｜完整度下降时进入三阶段，全程召唤千禧园的低阶异象护卫自己；末段还会瞬移脱战。",
        "name": "核心执念·千年虫", "description": "它害怕 2000 年，于是把梦停在了 1999 年 12 月 31 日。你是来送它过零点的。",
        "glyph": "🐛", "anomaly_kind": "核心执念", "integrity": 55, "move_time": 1.0, "attack_time": 0.8,
        "trauma_type": "心智创伤", "communicates": True, "drop_id": "broadband_grail", "dissolution_reward": 30, "vision": 9,
        "power": 4, "layers": [30, 30], "pool": False, "trait": "y2k_summon", "color": "#8fe060",
        "insight_id": "世纪清算",
    },
}
ORDINARY_ANOMALY_IDS = (
    "anomaly.page_hound",
    "anomaly.folded_person",
    "anomaly.reverse_drummer",
    "anomaly.model_porter",
    "anomaly.silent_audience",
    "anomaly.cooling_doll",
    "anomaly.backlit_reader",
    "anomaly.ticket_inspector", "anomaly.insomniac_alarm", "anomaly.potted_keeper",
    "anomaly.subtitle_group", "anomaly.echo_scribe", "anomaly.slow_projector",
    "anomaly.return_runner", "anomaly.oblivion_archivist", "anomaly.nightmare_herder",
    "anomaly.sleepless_watch", "anomaly.ink_bottle_guard", "anomaly.lullaby_hummer",
)
UNCONSCIOUS_ORDINARY_ANOMALY_IDS: tuple[str, ...] = (
    "anomaly.sunken_bell", "anomaly.silent_mirror",
    "anomaly.thought_worm", "anomaly.faceless_watchman",
    # 内容扩展包 v1
    "anomaly.projection_crew", "anomaly.long_take_director",
)
# ---- 梦中梦·门之回廊专属（2026-09-21）：只在支线层出现，不进主池 ----
ANOMALY_DEFINITIONS["anomaly.door_warden"] = {
    "pool": False, "spawn_realms": ("door_corridor",),
    "name": "门扉守卫", "description": "它记得每一扇门的锁孔形状，也记得每一个没敲门的人。",
    "glyph": "⌸", "anomaly_kind": "强烈异象", "integrity": 14, "move_time": 1.0,
    "attack_time": 1.0, "trauma_type": "清醒创伤", "communicates": True,
    "drop_id": "door_hinge", "dissolution_reward": 15, "vision": 9, "power": 7,
    "layers": [1, 3], "trait": "relentless", "color": "#d0e8ff",
}
ANOMALY_DEFINITIONS["anomaly.door_mimic"] = {
    "pool": False, "spawn_realms": ("door_corridor",),
    "name": "拟门", "description": "你以为那是出口。它也以为你是钥匙。",
    "glyph": "╫", "anomaly_kind": "普通异象", "integrity": 6, "move_time": 1.0,
    "attack_time": 0.8, "trauma_type": "心智创伤", "communicates": True,
    "drop_id": "bent_hook", "dissolution_reward": 12, "vision": 4, "power": 5,
    "layers": [1, 3], "trait": "disguise", "color": "#6a7a88",
}

# ---- 内容扩展包 v1：新增异象 16 只（2026-09-21 补完行为层）----
ANOMALY_DEFINITIONS["anomaly.ticket_inspector"] = {
    "name": "查票员", "description": "它不看你，只看你的票。没有票的人要从身上补一张出来。",
    "glyph": "𓀅", "anomaly_kind": "普通异象", "integrity": 3, "move_time": 1.0,
    "attack_time": 1.0, "trauma_type": "心智创伤", "communicates": True,
    "drop_id": "loose_thread", "dissolution_reward": 10, "vision": 6, "power": 2,
    "layers": [2, 7], "trait": "toll_check", "color": "#c8b060",
}
ANOMALY_DEFINITIONS["anomaly.insomniac_alarm"] = {
    "name": "失眠的闹钟", "description": "它自己也睡不着，所以谁也别想睡。",
    "glyph": "✇", "anomaly_kind": "普通异象", "integrity": 2, "move_time": 1.0,
    "attack_time": 1.0, "trauma_type": "清醒创伤", "communicates": True,
    "drop_id": "clockwork_half", "dissolution_reward": 10, "vision": 5, "power": 1,
    "layers": [1, 6], "trait": "snooze_pulse", "color": "#d08040",
}
ANOMALY_DEFINITIONS["anomaly.potted_keeper"] = {
    "name": "盆栽看守", "description": "它经过的地方草会长高。它也躲在长高的草里。",
    "glyph": "𓆰", "anomaly_kind": "普通异象", "integrity": 4, "move_time": 1.0,
    "attack_time": 1.0, "trauma_type": "心智创伤", "communicates": True,
    "drop_id": "mint_dew", "dissolution_reward": 11, "vision": 6, "power": 2,
    "layers": [3, 8], "trait": "gardener", "color": "#7aa860",
}
ANOMALY_DEFINITIONS["anomaly.subtitle_group"] = {
    "name": "字幕组", "description": "它给整个梦境配字幕——配得不太好。",
    "glyph": "₩", "anomaly_kind": "普通异象", "integrity": 5, "move_time": 1.0,
    "attack_time": 1.0, "trauma_type": "心智创伤", "communicates": True,
    "drop_id": "wet_fold", "dissolution_reward": 11, "vision": 7, "power": 3,
    "layers": [9, 18], "trait": "mislabel", "color": "#a0b8d0",
}
ANOMALY_DEFINITIONS["anomaly.echo_scribe"] = {
    "name": "回声抄写员", "description": "它抄写你的一举一动——连你的急躁也一起抄下来。",
    "glyph": "✐", "anomaly_kind": "普通异象", "integrity": 6, "move_time": 1.0,
    "attack_time": 1.0, "trauma_type": "心智创伤", "communicates": True,
    "drop_id": "bent_hook", "dissolution_reward": 11, "vision": 7, "power": 4,
    "layers": [10, 19], "trait": "echo_copy", "color": "#b8a0c8",
}
ANOMALY_DEFINITIONS["anomaly.slow_projector"] = {
    "name": "慢速放映机", "description": "它放映的每一帧都比现实慢半拍，你也被拖进了那帧。",
    "glyph": "𓊝", "anomaly_kind": "普通异象", "integrity": 7, "move_time": 0.8,
    "attack_time": 1.2, "trauma_type": "清醒创伤", "communicates": True,
    "drop_id": "wet_fold", "dissolution_reward": 12, "vision": 5, "power": 3,
    "layers": [11, 20], "trait": "slow_aura", "color": "#9098b0",
}
ANOMALY_DEFINITIONS["anomaly.return_runner"] = {
    "name": "折返跑者", "description": "它冲刺、折返、再冲刺——永远跑不完自己的往返跑。",
    "glyph": "𓍯", "anomaly_kind": "普通异象", "integrity": 5, "move_time": 0.7,
    "attack_time": 0.9, "trauma_type": "清醒创伤", "communicates": True,
    "drop_id": "coiled_spring", "dissolution_reward": 12, "vision": 6, "power": 5,
    "layers": [12, 21], "trait": "boomerang", "color": "#c87070",
}
ANOMALY_DEFINITIONS["anomaly.oblivion_archivist"] = {
    "name": "遗忘档案员", "description": "它归档一切——包括你刚刚还记得的名字。",
    "glyph": "𓎛", "anomaly_kind": "普通异象", "integrity": 9, "move_time": 1.0,
    "attack_time": 1.0, "trauma_type": "心智创伤", "communicates": True,
    "drop_id": "void_coagulant", "dissolution_reward": 12, "vision": 7, "power": 5,
    "layers": [21, 26], "trait": "forget_touch", "color": "#6a5a8a",
}
ANOMALY_DEFINITIONS["anomaly.nightmare_herder"] = {
    "name": "噩梦牧者", "description": "牧杖下挤着一群睡梦里的黑影，背脊起伏，喉间咕噜作响。",
    "glyph": "𓃭", "anomaly_kind": "普通异象", "integrity": 10, "move_time": 1.0,
    "attack_time": 1.1, "trauma_type": "清醒创伤", "communicates": True,
    "drop_id": "void_coagulant", "dissolution_reward": 12, "vision": 8, "power": 4,
    "layers": [23, 27], "trait": "pack_weave", "color": "#8a4a6a",
}
ANOMALY_DEFINITIONS["anomaly.sleepless_watch"] = {
    "name": "无眠更夫", "description": "它打更从不出错——所以你逃到哪它都敲得到。",
    "glyph": "𓀭", "anomaly_kind": "普通异象", "integrity": 8, "move_time": 1.0,
    "attack_time": 1.0, "trauma_type": "清醒创伤", "communicates": True,
    "drop_id": "morning_dew", "dissolution_reward": 12, "vision": 9, "power": 6,
    "layers": [22, 27], "trait": "relentless", "color": "#5a6a7a",
}
ANOMALY_DEFINITIONS["anomaly.ink_bottle_guard"] = {
    "name": "墨水瓶守卫", "description": "一只沉甸甸的墨水瓶，瓶口渗出的墨在地面洇开，不肯干。",
    "glyph": "⚘", "anomaly_kind": "普通异象", "integrity": 9, "move_time": 1.0,
    "attack_time": 1.0, "trauma_type": "心智创伤", "communicates": True,
    "drop_id": "void_coagulant", "dissolution_reward": 12, "vision": 6, "power": 5,
    "layers": [21, 26], "trait": "burst_liquid", "color": "#3a3a4f",
}
ANOMALY_DEFINITIONS["anomaly.lullaby_hummer"] = {
    "name": "摇篮曲哼唱者", "description": "曲子不难听，难的是在曲子里把念头集中起来。",
    "glyph": "𓅜", "anomaly_kind": "普通异象", "integrity": 8, "move_time": 1.1,
    "attack_time": 1.2, "trauma_type": "心智创伤", "communicates": True,
    "drop_id": "morning_dew", "dissolution_reward": 12, "vision": 7, "power": 3,
    "layers": [23, 27], "trait": "lullaby", "color": "#7a6a9a",
}
ANOMALY_DEFINITIONS["anomaly.projection_crew"] = {
    "name": "强烈异象·巡回放映队", "description": "放映机拖着一串小机器巡行，镜头转过来，票口里伸出一张皱巴巴的手。",
    "glyph": "𓊵", "anomaly_kind": "强烈异象", "integrity": 8, "move_time": 1.0,
    "attack_time": 1.0, "trauma_type": "清醒创伤", "communicates": True,
    "drop_id": "wet_fold", "dissolution_reward": 15, "vision": 8, "power": 6,
    "layers": [15, 21], "trait": "split_main", "color": "#d0a050",
}
ANOMALY_DEFINITIONS["anomaly.long_take_director"] = {
    "name": "强烈异象·长镜头导演", "description": "镜头始终没有停，细长的胶片拖在身后，连你的影子也录了进去。",
    "glyph": "𓎡", "anomaly_kind": "强烈异象", "integrity": 9, "move_time": 0.9,
    "attack_time": 1.1, "trauma_type": "心智创伤", "communicates": True,
    "drop_id": "wet_fold", "dissolution_reward": 15, "vision": 10, "power": 7,
    "layers": [18, 25], "trait": "ranged_gaze", "color": "#b07070",
}
ANOMALY_DEFINITIONS["anomaly.silent_proofreader"] = {
    "name": "强烈异象·无字校对员", "description": "指尖沾着浓墨，擦过的地方只剩一块黑色。纸上没有改正的字。",
    "glyph": "𓏲", "anomaly_kind": "强烈异象", "integrity": 12, "move_time": 1.0,
    "attack_time": 1.0, "trauma_type": "心智创伤", "communicates": True,
    "drop_id": "void_coagulant", "dissolution_reward": 15, "vision": 7, "power": 6,
    "layers": [21, 27], "trait": "redact", "color": "#8a8a9a",
}
ANOMALY_DEFINITIONS["anomaly.abyss_ruler"] = {
    "name": "强烈异象·深渊量尺", "description": "尺带从黑暗里抽出来，一格格贴近脚边。最远的刻度始终看不清。",
    "glyph": "𓌳", "anomaly_kind": "强烈异象", "integrity": 14, "move_time": 1.1,
    "attack_time": 1.0, "trauma_type": "清醒创伤", "communicates": True,
    "drop_id": "void_coagulant", "dissolution_reward": 15, "vision": 6, "power": 8,
    "layers": [26, 27], "trait": "pull", "color": "#4a5a7a",
}

# 改造 v2（2026-09-21）：机制由前期向中后期迁移
_ANOM = ANOMALY_DEFINITIONS
_ANOM["anomaly.clock_keeper"]["pulse_radius"] = 5          # 脉冲 9×9 → 7×7（局部警报）
_ANOM["anomaly.sunken_bell"]["thorns_per_segment"] = True   # 荆棘：近战每段反 1 清醒
_ANOM["anomaly.sunken_bell"]["thorns_scope"] = "melee"
_ANOM["anomaly.sunken_bell"]["thorns_effect"] = "lucidity"
_ANOM["anomaly.silent_mirror"]["counter_every"] = 2         # 反击：近战镜面反打（承镜像侍者）
_ANOM["anomaly.silent_mirror"]["counter_scope"] = "melee"
_ANOM["anomaly.silent_mirror"]["counter_effect"] = "mind"
_ANOM["anomaly.thought_worm"]["segments"] = 2               # 多段（承纸鱼）
_ANOM["anomaly.primordial_impulse"]["segments"] = 2
# 注意：id 必须是 PORTENT_DEFINITIONS 的**键**（英文键），不是显示名；
# 2026-10-20 起 _apply_direct_portent 会查定义，查不到直接丢弃（过去写中文名
# 会静默留在 dict 里：不显示、不被净化道具清、不吃记忆碎片的免疫）。
_ANOM["anomaly.faceless_watchman"]["on_hit_portent"] = {"id": "obscured", "duration": 8}
_ANOM["anomaly.ink_archivist"]["on_hit_portent"] = {"id": "呛尘", "duration": 8}
_ANOM["anomaly.whole_choir"]["on_hit_portent"] = {"id": "whispering", "duration": 8}
_ANOM["anomaly.null_witness"]["on_hit_portent"] = {"id": "voidness", "duration": 8}
_ANOM["anomaly.blank_rift"]["time_steal"] = "adjacent"      # 相邻时行动上限 2
_ANOM["anomaly.dream_accountant"]["time_steal"] = "alert"

# ---- 改造 v3（2026-09-22）：异象技能组——远程/范围(带渲染预警)/地形改造 ----
# 说明：定义表新增 "skills" 元组（每项 {"kind": ...}），由
# core/enemies.py 的 _enemy_skills 周期结算；"skill" 字符串供图鉴展示。
_ANOM["anomaly.cooling_doll"]["skill"] = "冷凝抽干｜每 8 拍抽干身边 3×3 的气体与液体。"
_ANOM["anomaly.cooling_doll"]["skills"] = ({"kind": "clear_terrain", "every": 8, "radius": 1},)
_ANOM["anomaly.backlit_reader"]["skill"] = "阅读射线｜每 3 拍沿视线打击 4 格内的你。"
_ANOM["anomaly.backlit_reader"]["skills"] = ({"kind": "ranged", "every": 3, "range": 4, "power": 3},)
_ANOM["anomaly.sunken_bell"]["skill"] = "沉钟震波｜每 9 拍蓄力 2 拍后震荡身边 3×3（红底预警，快跑）。"
_ANOM["anomaly.sunken_bell"]["skills"] = (
    {"kind": "aoe_burst", "every": 9, "radius": 1, "power": 5, "cast_range": 3, "windup": 2},
)
_ANOM["anomaly.moving_staircase"]["skill"] = "破墙续行｜挡路的低硬度墙体被它直接撞碎（「不绕开任何人」是字面意思）。"
_ANOM["anomaly.moving_staircase"]["skills"] = ({"kind": "wall_break", "hardness_max": 2},)
_ANOM["anomaly.blank_rift"]["skill"] = "边缘侵蚀｜每 7 拍侵蚀身边 5×5 的墙体，剥落至塌。"
_ANOM["anomaly.blank_rift"]["skills"] = ({"kind": "erode_walls", "every": 7, "radius": 2, "damage": 40},)
_ANOM["anomaly.ink_bottle_guard"]["skill"] = "渗墨｜身边不断积起黑墨（打碎它同样满地是墨）。"
_ANOM["anomaly.ink_bottle_guard"]["skills"] = (
    {"kind": "emanate", "every": 5, "radius": 1, "medium": "liquid", "emit": "黑墨"},
)
_ANOM["anomaly.long_take_director"]["skill"] = "长镜凝视｜每 2 拍沿视线打击 4 格内的你。"
_ANOM["anomaly.long_take_director"]["skills"] = ({"kind": "ranged", "every": 2, "range": 4, "power": 5},)

# ---- 改造 v3 新增异象（3 只）：火焰制造 / 爆炸制造 / 气体呼出 ----
ANOMALY_DEFINITIONS["anomaly.pyre_singer"] = {
    "skill": "引燃咏叹｜每 6 拍点燃它最后一次看见你的地方（3×3）。",
    "name": "焚焰歌者", "description": "它唱到高音处，梦境就跟着着一点火。它以为那是掌声。",
    "glyph": "♨", "anomaly_kind": "普通异象", "integrity": 6, "move_time": 1.0,
    "attack_time": 1.0, "trauma_type": "心智创伤", "communicates": True,
    "drop_id": "lighthouse_ember", "dissolution_reward": 12, "vision": 7, "power": 4,
    "layers": [11, 18], "trait": "firebrand", "color": "#e07840",
    "skills": ({"kind": "ignite", "every": 6, "radius": 1, "anchor": "hunt"},),
}
ANOMALY_DEFINITIONS["anomaly.unopened_gift"] = {
    "skill": "拆封投掷｜每 8 拍朝你扔一份会炸的礼盒（落点橙底预警，两拍后爆炸）。",
    "name": "未拆的礼盒", "description": "每个盒子里都是没拆开的失望——拆开的那一下格外响。",
    "glyph": "✿", "anomaly_kind": "普通异象", "integrity": 7, "move_time": 1.1,
    "attack_time": 1.0, "trauma_type": "清醒创伤", "communicates": True,
    "drop_id": "coiled_spring", "dissolution_reward": 12, "vision": 6, "power": 5,
    "layers": [14, 20], "trait": "gift_thrower", "color": "#d078a0",
    "skills": ({"kind": "bomb", "every": 8, "cast_range": 5, "windup": 2, "radius": 1, "power": 2},),
}
ANOMALY_DEFINITIONS["anomaly.fog_breather"] = {
    "skill": "浊雾呼吸｜身边不断积起回声雾（走进去就会被它摸到位置）。",
    "name": "雾喘", "description": "它的每一次呼吸都比上一口更潮，梦里因此有了雾。",
    "glyph": "≋", "anomaly_kind": "普通异象", "integrity": 5, "move_time": 1.0,
    "attack_time": 1.0, "trauma_type": "心智创伤", "communicates": True,
    "drop_id": "morning_dew", "dissolution_reward": 11, "vision": 6, "power": 3,
    "layers": [8, 14], "trait": "fog_breath", "color": "#8ab0b8",
    "skills": ({"kind": "emanate", "every": 4, "radius": 1, "medium": "gas", "emit": "回声雾"},),
}
# 三只新异象进主梦通用池（按各自 layers 分区生成）。
ORDINARY_ANOMALY_IDS = tuple(ORDINARY_ANOMALY_IDS) + (
    "anomaly.pyre_singer", "anomaly.unopened_gift", "anomaly.fog_breather",
)

UNCONSCIOUS_STRONG_ANOMALY_IDS: tuple[str, ...] = (
    "anomaly.nightmare_weaver", "anomaly.forgetter",
    "anomaly.blank_rift", "anomaly.primordial_impulse",
    # 内容扩展包 v1
    "anomaly.silent_proofreader", "anomaly.abyss_ruler",
)

from .hospital import HOSPITAL_ANOMALIES
ANOMALY_DEFINITIONS.update(HOSPITAL_ANOMALIES)
from .library import LIBRARY_ANOMALIES
ANOMALY_DEFINITIONS.update(LIBRARY_ANOMALIES)
# 漏字者只由篡改风险召唤：定义带 spawn_only='tamper'，投放池按该标记排除。
from .tamper_anomalies import TAMPER_ANOMALIES
ANOMALY_DEFINITIONS.update(TAMPER_ANOMALIES)
from .environment_prose import ANOMALY_NOTE_PROSE
for (_anomaly_id, _field), (_prose, _english_prose) in ANOMALY_NOTE_PROSE.items():
    ANOMALY_DEFINITIONS[_anomaly_id][_field] = _prose
