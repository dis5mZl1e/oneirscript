"""异常地点（复合事件）定义与逐层投放池。"""

from __future__ import annotations

from typing import Any

from .migration import held_event_ids

#: 每层异常地点的上限。**结构自带事件与随机零散事件共用这一个名额**（2026-10-27）：
#: 盖章期结构先占额（见 ``mapgen/forms.generate_solid_mask_with_vaults``），
#: 随机投放只在余额内补位（见 ``core/generation._seed_layer_contents``）。
#: 深层边界 28–30 由 ``mapgen/epilogue.py`` 整层接管，不受此约束。
EVENT_MAX_PER_LAYER = 2

EVENT_DEFINITIONS: tuple[dict[str, Any], ...] = (
    {"event_id": "event.coffee_ring", "name": "桌上的咖啡环", "description": "圆环里藏着一条没有写完的路线。", "reward_id": "warm_coffee", "catalog_id": "event.coffee_ring", "insight_id": "路线依赖",
     "kind": "compound",
     "dialogue": ["圆环里藏着一条没有写完的路线。"],
     "options": [
      {"label": "拿走那半罐咖啡", "reward_id": "warm_coffee"},
      {"label": "顺着圆环找路", "dissolution": 5, "imagination": 3},
      {"label": "不去动它", "leave": True}],
    },
    {"event_id": "event.missing_screw", "name": "缺少一颗螺丝的模型", "description": "它坚持自己已经完成。", "reward_id": "model_screw", "catalog_id": "event.missing_screw", "insight_id": "机械迷恋",
     "kind": "compound",
     "dialogue": ["它坚持自己已经完成。"],
     "options": [
      {"label": "拧下那颗螺丝", "reward_id": "model_screw"},
      {"label": "把模型拆开看", "dissolution": 4, "lucidity": 3},
      {"label": "让它保持完整", "leave": True}],
    },
    {"event_id": "event.silent_ticket", "name": "无人检票的站台", "description": "车票没有日期，站台却在催促。", "reward_id": "quiet_ticket", "catalog_id": "event.silent_ticket", "insight_id": "延迟抵达",
     "kind": "compound",
     "uses": 1,
     "dialogue": ["车票没有日期，站台却在催促。"],
     "options": [
      {"label": "收下那张票", "reward_id": "quiet_ticket"},
      {"label": "替它检一次票", "dissolution": 4, "mind": 3},
      {"label": "不理会催促", "leave": True}],
    },
    {"event_id": "event.glass_crack", "name": "玻璃里的第二个房间", "description": "清醒的裂纹指向一片看不见的区域。", "reward_id": "clear_glass", "catalog_id": "event.glass_crack", "insight_id": "透明边界",
     "kind": "compound",
     "dialogue": ["清醒的裂纹指向一片看不见的区域。"],
     "options": [
      {"label": "捡起清醒玻璃", "reward_id": "clear_glass"},
      {"label": "把手贴上玻璃", "dissolution": 3, "imagination": 4},
      {"label": "移开视线", "leave": True}],
    },
    {"event_id": "event.radio_rain", "name": "收音机的雨声", "description": "雨声来自没有天线的机器。", "reward_id": "rain_machine_memory_2", "catalog_id": "event.radio_rain", "insight_id": "噪声耐受",
     "kind": "compound",
     "uses": 1,
     "dialogue": ["雨声来自没有天线的机器。"],
     "options": [
      {"label": "取出那段机械声", "reward_id": "rain_machine_memory_2"},
      {"label": "调到没有雨的频率", "dissolution": 5, "mind": 2},
      {"label": "由它下着", "leave": True}],
    },
    {"event_id": "event.model_lamp", "name": "模型房间的灯", "description": "灯亮起时，某段记忆允许被携带。", "reward_id": "model_room_memory", "catalog_id": "event.model_lamp", "insight_id": "局部照明",
     "kind": "compound",
     "dialogue": ["灯亮起时，某段记忆允许被携带。"],
     "options": [
      {"label": "取下那盏灯", "reward_id": "model_room_memory"},
      {"label": "让灯照一会儿", "dissolution": 4, "imagination": 3},
      {"label": "关灯离开", "leave": True}],
    },
    {"event_id": "event.empty_score", "name": "空白乐谱", "description": "最后一行拒绝出现。", "reward_id": "unfinished_song_memory", "catalog_id": "event.empty_score", "insight_id": "留白",
     "kind": "compound",
     "dialogue": ["最后一行拒绝出现。"],
     "options": [
      {"label": "收下空白乐谱", "reward_id": "unfinished_song_memory"},
      {"label": "在末行补一句", "dissolution": 4, "imagination": 3},
      {"label": "合上它", "leave": True}],
    },
    {"event_id": "event.editor_note", "name": "编辑留下的批注", "description": "批注没有指向文字，而是指向你。", "reward_id": "draft_margin_memory", "catalog_id": "event.editor_note", "insight_id": "现实洞察",
     "kind": "compound",
     "dialogue": ["批注没有指向文字，而是指向你。", "红字写着：「此处节奏拖沓，建议删去一段。」"],
     "options": [{"label": "在批注下签名", "reward_id": "draft_margin_memory", "dissolution": 6},
      {"label": "把批注涂改成「保留」", "imagination": 4, "dissolution": 4},
      {"label": "合上稿纸", "leave": True}],
    },
    {"event_id": "event.gear_afternoon", "name": "齿轮停下的午后", "description": "机器停止后，时间才显出形状。", "reward_id": "plastic_gear_memory", "catalog_id": "event.gear_afternoon", "insight_id": "机械迷恋",
     "kind": "compound",
     "dialogue": ["机器停止后，时间才显出形状。"],
     "options": [
      {"label": "拾起那枚齿轮", "reward_id": "plastic_gear_memory"},
      {"label": "让它再转一圈", "dissolution": 4, "lucidity": 3},
      {"label": "保持静止", "leave": True}],
    },
    # ---- 内容扩展第一批事件（§6） ----
    {"event_id": "event.ash_lighter", "name": "灰烬下的打火机", "description": "打火机还在烫，灰烬却不记得烧过什么。", "reward_id": "whistle", "catalog_id": "event.ash_lighter", "insight_id": "灰烬记忆",
     "kind": "compound",
     "dialogue": ["打火机还在烫，灰烬却不记得烧过什么。"],
     "options": [
      {"label": "捡起那只汽笛", "reward_id": "whistle"},
      {"label": "吹响一声", "dissolution": 5, "mind": 2},
      {"label": "想象力 −5，换一支燃烧瓶（投掷引火）", "reward_id": "molotov", "imagination": -5},
      {"label": "心智 −6，换一枚雷管胶囊（投掷爆破）", "reward_id": "detonator_capsule", "mind": -6},
      {"label": "把手收回来", "leave": True}, {"label": "✦ 随机易逝物（稀有度随机）", "random_option": {"pool": "易逝物", "rarities": ["常见", "少见"]}}],
    },
    {"event_id": "event.polaroid_wall", "name": "拍立得墙", "description": "整面墙贴满晃动的拍立得，全都拍的是你的背影。", "reward_id": "old_keycap", "catalog_id": "event.polaroid_wall", "kind": "compound", "dialogue": ["整面墙贴满晃动的拍立得，全都拍的是你的背影。", "有一张的背面写着：别回头，继续走。"], "options": [{"label": "揭一张带走", "reward_id": "old_keycap", "dissolution": 4}, {"label": "在墙前站一会儿", "mind": 3}, {"label": "全部撕下来", "lucidity": -2, "dissolution": 8}, {"label": "不去看它们", "leave": True}]},
    {"event_id": "event.rusty_faucet", "name": "生锈的水龙头", "description": "水龙头拧不开，却在往外渗水——滴答声精确得像节拍器。", "reward_id": "glass_bottle", "catalog_id": "event.rusty_faucet", "kind": "compound", "dialogue": ["水龙头拧不开，却在往外渗水——滴答声精确得像节拍器。", "渗出的水在你脚边汇成一小片浅洼。"], "options": [{"label": "用玻璃瓶接一瓶", "reward_id": "glass_bottle", "lucidity": -1}, {"label": "对着滴答声发呆", "imagination": 4}, {"label": "把水龙头拧紧", "mind": 2, "leave": True}]},
    {"event_id": "event.broken_meter", "name": "走字的电表", "description": "一只电表在没人用电的房间里疯转，数字跳得像心跳。", "reward_id": "night_battery", "catalog_id": "event.broken_meter", "kind": "compound", "dialogue": ["一只电表在没人用电的房间里疯转，数字跳得像心跳。", "表盘上贴着便签：「别让它停下来。」"], "options": [{"label": "拆下电池", "reward_id": "night_battery", "mind": -2}, {"label": "陪它转到停", "lucidity": -3, "imagination": 6}, {"label": "合上电表箱", "leave": True}]},
    {"event_id": "event.paper_moon", "name": "纸月亮", "description": "窗外挂着一轮有折痕的月亮，光落在地上沙沙作响。", "reward_id": "torn_page", "catalog_id": "event.paper_moon", "kind": "compound", "dialogue": ["窗外挂着一轮有折痕的月亮，光落在地上沙沙作响。", "折痕把月面分成了四格，每一格都在慢慢鼓起来。"], "options": [{"label": "戳破它", "reward_id": "torn_page", "dissolution": 6, "mind": -1}, {"label": "把折痕抚平", "mind": 3}, {"label": "拉上窗帘", "leave": True}]},
    {"event_id": "event.lost_luggage", "name": "无主的行李", "description": "行李箱在走廊尽头转圈，像在等一个不会来认领它的人。", "reward_id": "morning_dew", "catalog_id": "event.lost_luggage", "kind": "compound", "dialogue": ["行李箱在走廊尽头转圈，像在等一个不会来认领它的人。", "锁是开的，它在邀请你。"], "options": [{"label": "翻找易逝物", "imagination": -3}, {"label": "✦ 随机易逝物（稀有度随机）", "random_option": {"pool": "易逝物", "rarities": ["少见", "稀有"]}}, {"label": "替它守一会儿", "mind": 3}, {"label": "走开", "leave": True}]},
    {"event_id": "event.fog_organ", "name": "雾中之琴", "description": "浓雾里有一架管风琴在自我演奏，音栓上刻着各种天气。", "reward_id": "clear_glass", "catalog_id": "event.fog_organ", "kind": "compound", "dialogue": ["浓雾里有一架管风琴在自我演奏，音栓上刻着各种天气。", "「雨」音栓被按下了，所以才有这层雾。"], "options": [{"label": "按下「晴」音栓", "reward_id": "clear_glass", "mind": -2}, {"label": "即兴弹一段", "imagination": 5, "lucidity": -2}, {"label": "悄悄退出去", "leave": True}]},
    {"event_id": "event.night_stand", "name": "抽屉之夜", "description": "床头柜的抽屉半开着，里面传出翻纸的声音。", "reward_id": "warm_water", "catalog_id": "event.night_stand", "kind": "compound", "dialogue": ["床头柜的抽屉半开着，里面传出翻纸的声音。", "抽屉里的东西比你记忆中多了一倍。"], "options": [{"label": "✦ 随机摄入物（稀有度随机）", "random_option": {"pool": "摄入物", "rarities": ["常见", "少见"]}}, {"label": "一杯一杯地喝", "reward_id": "warm_water", "lucidity": -1}, {"label": "把抽屉关好", "mind": 2, "leave": True}]},
    {"event_id": "event.post_to_waking", "name": "寄往醒处的邮筒", "description": "一只邮筒立在梦的裂缝旁，投递口朝着「醒」的方向。", "reward_id": "charge_clip", "catalog_id": "event.post_to_waking", "kind": "compound", "dialogue": ["一只邮筒立在梦的裂缝旁，投递口朝着「醒」的方向。", "信一格一格往下掉，落进醒来的世界。"], "options": [{"label": "寄一份礼物给醒着的自己", "reward_id": "charge_clip", "imagination": -4}, {"label": "读别人的来信", "mind": 3, "lucidity": -2}, {"label": "什么也不寄", "leave": True}]},
    {"event_id": "event.toolbox_grave", "name": "工具箱之墓", "description": "一只工具箱被郑重地埋在土里，墓碑是一把扳手。", "reward_id": "screwdriver", "catalog_id": "event.toolbox_grave", "kind": "compound", "dialogue": ["一只工具箱被郑重地埋在土里，墓碑是一把扳手。", "墓志铭：「它修好过一切，除了它自己。」"], "options": [{"label": "取走扳手墓碑", "reward_id": "wax_seal", "mind": -1}, {"label": "向工具箱致意", "mind": 2}, {"label": "添一撮土再离开", "dissolution": 4, "leave": True}]},
    {"event_id": "event.tide_clock", "name": "潮汐钟", "description": "一只挂钟的指针以潮水的节奏倒着走。", "reward_id": "whistle", "catalog_id": "event.tide_clock", "kind": "compound", "dialogue": ["一只挂钟的指针以潮水的节奏倒着走。", "每倒退一格，空气里的咸味就重一分。"], "options": [{"label": "把指针拨向涨潮", "reward_id": "molotov", "imagination": -5}, {"label": "把指针拨向退潮", "reward_id": "whistle", "mind": -3}, {"label": "让潮水自己决定", "leave": True}]},
    {"event_id": "event.bath_tide", "name": "浴缸里的退潮", "description": "水退向一个不存在的地漏。", "reward_id": "warm_water", "reward_count": 2, "catalog_id": "event.bath_tide", "insight_id": "液态亲和",
     "kind": "compound",
     "dialogue": ["浴缸里的水退向一个不存在的地漏。", "水面下映出另一个浴室：有人背对着你，在给一个空杯子接水。"],
     "options": [{"label": "伸手进漩涡", "reward_id": "warm_water", "reward_count": 2, "lucidity": -2},
      {"label": "对着水中的人说话", "mind": 2, "dissolution": 4},
      {"label": "拔掉不存在的塞子", "leave": True}, {"label": "✦ 随机摄入物（稀有度随机）", "random_option": {"pool": "摄入物", "rarities": ["常见", "少见"]}}],
    },
    {"event_id": "event.pill_box", "name": "药盒的最后一格", "description": "星期日的格子被拆走了。", "reward_id": "expired_pill", "catalog_id": "event.pill_box", "insight_id": "抗辐射体质",
     "kind": "compound",
     "dialogue": ["星期日的格子被拆走了。", "药盒内侧刻着一行小字：「别忘了今天不是星期日。」"],
     "options": [{"label": "吃掉剩下的药", "reward_id": "expired_pill", "lucidity": -3},
      {"label": "把整盒收进口袋", "reward_id": "expired_pill", "reward_count": 2, "mind": -2},
      {"label": "原样合上", "leave": True}],
    },
    {"event_id": "event.wet_score", "name": "晕开的休止符", "description": "乐谱泡在水里，休止符最先消失。", "reward_id": "choir_note", "catalog_id": "event.wet_score", "insight_id": "冷韧",
     "kind": "compound",
     "dialogue": ["乐谱泡在水里，休止符最先消失。"],
     "options": [
      {"label": "捞起那张乐谱", "reward_id": "choir_note"},
      {"label": "按住那个休止符", "dissolution": 3, "lucidity": 4},
      {"label": "让它继续泡着", "leave": True}],
    },
    {"event_id": "event.attic_staircase", "name": "阁楼的折叠梯", "description": "梯子放下来时，阁楼多出一层。", "reward_id": "hollow_step", "catalog_id": "event.attic_staircase", "insight_id": "疾行拾荒",
     "kind": "compound",
     "dialogue": ["梯子放下来时，阁楼多出一层。"],
     "options": [
      {"label": "带走空心的台阶", "reward_id": "hollow_step"},
      {"label": "顺着梯子爬上去", "dissolution": 6, "imagination": 3},
      {"label": "收回梯子", "leave": True}],
    },
    {"event_id": "event.last_train_window", "name": "末班车的窗", "description": "窗外的站台比车慢。", "reward_id": "last_window", "catalog_id": "event.last_train_window", "insight_id": "抗灼",
     "kind": "compound",
     "dialogue": ["窗外的站台比车慢。"],
     "options": [
      {"label": "取下那扇窗", "reward_id": "last_window"},
      {"label": "看站台慢慢落后", "dissolution": 5, "mind": 2},
      {"label": "拉上窗帘", "leave": True}],
    },
    {"event_id": "event.static_radio", "name": "静电里的电台", "description": "电流声排成了句子的形状。", "reward_id": "single_earphone", "catalog_id": "event.static_radio", "insight_id": "镜术精通",
     "kind": "compound",
     "dialogue": ["电流声排成了句子的形状。", "电台正在念一份名单，每一个名字都停顿两秒，像在等应答。"],
     "options": [{"label": "报上自己的名字", "reward_id": "single_earphone", "dissolution": 5},
      {"label": "跟着电流声哼下去", "imagination": 5, "dissolution": 4},
      {"label": "关掉电台", "leave": True}, {"label": "✦ 随机携带意象（稀有度随机）", "random_option": {"pool": "携带意象", "rarities": ["常见", "少见"]}}],
    },
    {"event_id": "event.tape_line", "name": "卷尺画出的房间的界线", "description": "卷尺拉到底，墙就照着它长。", "reward_id": "tape_measure", "catalog_id": "event.tape_line", "insight_id": "蜜脉",
     "kind": "compound",
     "dialogue": ["卷尺拉到底，墙就照着它长。"],
     "options": [
      {"label": "收起那把卷尺", "reward_id": "tape_measure"},
      {"label": "拉到底再画一条", "dissolution": 5, "imagination": 3},
      {"label": "不量了", "leave": True}],
    },
    {"event_id": "event.silent_library", "name": "无声的图书馆", "description": "书架之间没有脚步声，书页自己在翻。", "reward_id": "spellbook", "catalog_id": "event.silent_library",
     "dissolution_reward": 8,
     "kind": "compound",
     "dialogue": ["书架之间没有脚步声，书页自己在翻。", "翻到最后一页时，你看见自己的名字写在借阅卡上——归还日期是今天。", "一只由书脊拼成的手把一本书推到你面前。"],
     "options": [{"label": "接过那本书", "reward_id": "spellbook", "dissolution": 8},
      {"label": "把名字从借阅卡上擦掉", "mind": 3, "dissolution": 4},
      {"label": "轻轻放回，退出图书馆", "leave": True}, {"label": "✦ 随机易逝物（稀有度随机）", "random_option": {"pool": "易逝物", "rarities": ["常见", "稀有"]}}],
    },
    # ---- 无意识领域（21–27）----
    {"event_id": "event.first_echo", "name": "初啼的回声", "description": "最深处的第一声啼哭还悬在原地。", "reward_id": "morning_dew", "catalog_id": "event.first_echo", "insight_id": "初啼共鸣",
     "kind": "compound",
     "dialogue": ["最深处的第一声啼哭还悬在原地。"],
     "options": [
      {"label": "接住那滴晨露", "reward_id": "morning_dew"},
      {"label": "从回声里拎出那台脚步机", "reward_id": "expansion.sound.e13"},
      {"label": "拆下错接在一起的两只传声筒", "reward_id": "expansion.sound.e14"},
      {"label": "捡起回声里那把聚光把手", "reward_id": "expansion.light.e13"},
      {"label": "对着深渊听回声", "dissolution": 4, "mind": 4},
      {"label": "退出这片寂静", "leave": True}],
    },
    {"event_id": "event.sunken_bell", "name": "沉入无意识的钟", "description": "钟声早已被海水泡软。", "reward_id": "void_coagulant", "catalog_id": "event.sunken_bell", "insight_id": "静默惯习",
     "dissolution_reward": 10,
     "kind": "compound",
     "uses": 1,
     "dialogue": ["钟声早已被海水泡软。", "你伸手碰到钟壁的瞬间，整片海安静了一拍——它在等一个敲钟人。"],
     "options": [{"label": "撞响它", "reward_id": "void_coagulant", "dissolution": 10, "mind": -2},
      {"label": "把耳朵贴上去听", "mind": 3, "dissolution": 5},
      {"label": "松手，让钟继续沉睡", "leave": True}],
    },
    {"event_id": "event.blank_gallery", "name": "被遗忘的画廊", "description": "画框里空着，标题写着你的名字。", "reward_id": "night_lantern", "catalog_id": "event.blank_gallery", "insight_id": "留白",
     "kind": "compound",
     "dialogue": ["画框里空着，标题写着你的名字。"],
     "options": [
      {"label": "取下无光灯笼", "reward_id": "night_lantern"},
      {"label": "从空画框后抽出乐池的指挥棒", "reward_id": "expansion.sound.e15"},
      {"label": "搬走最后一排那张空椅", "reward_id": "expansion.sound.e16"},
      {"label": "扶起画框下那盏不肯熄灭的灯芯架", "reward_id": "expansion.light.e15"},
      {"label": "扯下画框上蒙着的那块黑披布", "reward_id": "expansion.light.e16"},
      {"label": "在标题下签名", "dissolution": 6, "lucidity": 2},
      {"label": "把画翻过去", "leave": True}],
    },
    {"event_id": "event.tide_of_names", "name": "名字的潮汐", "description": "潮水涨起时，无数名字浮出水面又沉下去。", "reward_id": "deep_thought_tea", "catalog_id": "event.tide_of_names", "insight_id": "冷韧",
     "kind": "compound",
     "uses": 1,
     "dialogue": ["潮水涨起时，无数名字浮出水面又沉下去。"],
     "options": [
      {"label": "捞起那杯茶", "reward_id": "deep_thought_tea"},
      {"label": "从退潮处捡起那件沉箱工作服", "reward_id": "expansion.terrain.e14"},
      {"label": "念出一个名字", "dissolution": 4, "mind": 3},
      {"label": "等潮水退去", "leave": True}],
    },
    # ---- 2026-09-18 复合事件扩展批次 ----
    {"event_id": "event.mirror_interview", "name": "镜子里的面试", "description": "镜中人递来一份没有问题的问卷。", "reward_id": "mirror_shard", "catalog_id": "event.mirror_interview", "kind": "compound", "dialogue": ["镜中人比你先抬手。它递来一份没有问题的问卷。", "表格末尾写着：请描述一个你没有做过的梦。"], "options": [{"label": "如实填写", "reward_id": "mirror_shard", "dissolution": 6}, {"label": "交白卷", "mind": 3, "dissolution": 5}, {"label": "打碎镜子离开", "leave": True}]},
    {"event_id": "event.clock_repairs", "name": "修表匠的遗摊", "description": "摊位上摆着一排都停在三点整的表。", "reward_id": "clockwork_half", "catalog_id": "event.clock_repairs", "kind": "compound", "dialogue": ["摊位上摆着一排都停在三点整的表。", "价签上写着：用一段记得的时间来换。"], "options": [{"label": "留下一段记忆换表", "reward_id": "clockwork_half", "dissolution": 5, "mind": -2}, {"label": "把所有表拨到四点", "lucidity": 3, "dissolution": 4}, {"label": "什么都不碰", "leave": True}]},
    {"event_id": "event.wet_letterbox", "name": "泡胀的信箱", "description": "信箱里塞满没有地址的信，墨迹在水里舒展。", "reward_id": "loose_thread", "catalog_id": "event.wet_letterbox", "kind": "compound", "dialogue": ["信箱里塞满没有地址的信，墨迹在水里舒展。", "其中一封的信封上写着你的笔迹，但你从不记得写过。"], "options": [{"label": "拆开那封自己写的信", "reward_id": "loose_thread", "dissolution": 5, "imagination": 3}, {"label": "把所有信投进不存在的邮筒", "mind": 2, "dissolution": 4}, {"label": "信还是让它泡着吧", "leave": True}]},
    {"event_id": "event.night_ward_round", "name": "夜班查房", "description": "走廊尽头的病房亮着一盏夜灯，护士站没有人。", "reward_id": "unlabeled_sedative", "catalog_id": "event.night_ward_round", "kind": "compound", "dialogue": ["走廊尽头的病房亮着一盏夜灯，护士站没有人。", "病历夹上写着你的名字，诊断那一栏被水渍晕开了。"], "options": [{"label": "按铃叫护士", "reward_id": "unlabeled_sedative", "dissolution": 4}, {"label": "替自己写下出院医嘱", "lucidity": 4, "dissolution": 3}, {"label": "轻轻带上门", "leave": True}]},
    {"event_id": "event.stargazer_desk", "name": "天文台的旧课桌", "description": "抽屉里的星图标注着一颗不存在的星。", "reward_id": "clear_glass", "catalog_id": "event.stargazer_desk", "kind": "compound", "dialogue": ["抽屉里的星图标注着一颗不存在的星。", "注释写着：只在闭上一只眼时可见。"], "options": [{"label": "闭上一只眼找它", "reward_id": "clear_glass", "dissolution": 4}, {"label": "把那颗星涂掉", "mind": 2, "dissolution": 4}, {"label": "合上抽屉", "leave": True}]},
    {"event_id": "event.dream_post_office", "name": "梦的邮局", "description": "柜台上盖着邮戳：昨日未达，退回。", "reward_id": "tape_measure", "catalog_id": "event.dream_post_office", "kind": "compound", "dialogue": ["柜台上盖着邮戳：昨日未达，退回。", "包裹单上寄件人一栏写着「以后的你自己」。"], "options": [{"label": "签收包裹", "reward_id": "tape_measure", "dissolution": 5}, {"label": "写一封投给过去的信", "imagination": 4, "dissolution": 4}, {"label": "把包裹留在柜台上", "leave": True}]},
    # ---- 2026-09-18 简单事件补充 ----
    {"event_id": "event.dry_fountain", "name": "干涸的许愿池", "description": "池底铺满硬币，每一枚都朝上。", "reward_id": "warm_water", "reward_count": 2, "catalog_id": "event.dry_fountain", "insight_id": "液态亲和",
     "kind": "compound",
     "uses": 1,
     "dialogue": ["池底铺满硬币，每一枚都朝上。"],
     "options": [
      {"label": "拿走那点温水", "reward_id": "warm_water", "reward_count": 2},
      {"label": "投一枚硬币下去", "dissolution": 4, "lucidity": 3},
      {"label": "留它们朝上", "leave": True}, {"label": "✦ 随机摄入物（稀有度随机）", "random_option": {"pool": "摄入物", "rarities": ["常见"]}}],
    },
    {"event_id": "event.elevator_music", "name": "电梯里的音乐", "description": "电梯停在两个楼层之间，音乐还在播。", "reward_id": "hollow_step", "catalog_id": "event.elevator_music", "insight_id": "延迟抵达",
     "kind": "compound",
     "dialogue": ["电梯停在两个楼层之间，音乐还在播。"],
     "options": [
      {"label": "带走空心台阶", "reward_id": "hollow_step"},
      {"label": "等音乐放完", "dissolution": 4, "lucidity": 3},
      {"label": "按开门键", "leave": True}],
    },
    {"event_id": "event.photo_booth", "name": "快照亭", "description": "幕布后面没有相机，照片却一张张吐出来。", "reward_id": "double_frame", "catalog_id": "event.photo_booth", "insight_id": "残影直觉",
     "kind": "compound",
     "uses": 1,
     "dialogue": ["幕布后面没有相机，照片却一张张吐出来。"],
     "options": [
      {"label": "取走那卷底片", "reward_id": "double_frame"},
      {"label": "再拍一张", "dissolution": 5, "imagination": 3},
      {"label": "从逆光的底片中取出裁纸刀", "reward_id": "expansion.light.e14"},
      {"label": "走出幕布", "leave": True}, {"label": "✦ 随机易逝物（稀有度随机）", "random_option": {"pool": "易逝物", "rarities": ["常见", "少见", "非常稀有"]}}],
    },
    {"event_id": "event.wardrobe_door", "name": "衣柜后的门", "description": "衣柜背面有一圈门铰链的印子。", "reward_id": "bent_hook", "catalog_id": "event.wardrobe_door", "insight_id": "疾行拾荒",
     "kind": "compound",
     "dialogue": ["衣柜背面有一圈门铰链的印子。"],
     "options": [
      {"label": "取下那只挂钩", "reward_id": "bent_hook"},
      {"label": "推一推铰链印子", "dissolution": 5, "mind": 2},
      {"label": "关上柜门", "leave": True}],
    },
    {"event_id": "event.mirror_rehearsal", "name": "排练中的镜子", "description": "镜子里的你在反复排练一句台词，还没有轮到你。", "reward_id": "single_earphone", "catalog_id": "event.mirror_rehearsal", "insight_id": "和声耐受", "kind": "compound", "dialogue": ["镜子里的你在反复排练一句台词。", "它排练得比你认真多了——认真到忘了词就会重头再来。"], "options": [{"label": "陪它排练一遍", "mind": 3, "dissolution": 4}, {"label": "抢过它的台词", "reward_id": "single_earphone", "imagination": 3}, {"label": "安静等它念完", "leave": True}]},
    {"event_id": "event.static_choir", "name": "合唱团的静电", "description": "电流声里藏着一支合唱团，正在调音。", "reward_id": "wet_fold", "catalog_id": "event.static_choir", "insight_id": "噪声耐受", "kind": "compound", "dialogue": ["电流声里藏着一支合唱团，正在调音。", "指挥转过头——它没有脸，只有一圈静电。"], "options": [{"label": "跟着哼一段", "reward_id": "wet_fold", "imagination": 4}, {"label": "录下这段调音", "reward_id": "old_keycap", "dissolution": 4}, {"label": "捂住耳朵快走", "leave": True}]},
    {"event_id": "event.rain_upside_down", "name": "倒着下的雨", "description": "雨从地面升回云端，每一滴都记得你来时的路。", "reward_id": "blue_match", "catalog_id": "event.rain_upside_down", "insight_id": "液态亲和", "kind": "compound", "dialogue": ["雨从地面升回云端。", "接住一滴，它会在掌心重演整场雨季。"], "options": [{"label": "接一滴", "reward_id": "blue_match", "lucidity": 2}, {"label": "在雨里站一会儿", "mind": 2, "dissolution": 3}, {"label": "躲开", "leave": True}]},
    {"event_id": "event.doors_within", "name": "门后的门", "description": "一排门在走廊两侧反复出现，每一扇都通向下一扇。", "reward_id": "hollow_step", "catalog_id": "event.doors_within", "insight_id": "延迟抵达", "kind": "compound", "dialogue": ["走廊两侧的门越走越多。", "每一扇门后还是这走廊——只有门把手温度不同。"], "options": [{"label": "敲敲最旧的那扇", "reward_id": "hollow_step", "dissolution": 5}, {"label": "把耳朵贴在门上听", "mind": 2}, {"label": "原路返回", "leave": True}]},
    {"event_id": "event.wax_tea_party", "name": "蜡像茶会", "description": "蜡化的客人们围坐一桌，茶壶里的蜡还在倒。", "reward_id": "warm_coffee", "catalog_id": "event.wax_tea_party", "kind": "compound", "dialogue": ["蜡化的客人们围坐一桌，姿势保持着举杯。", "茶壶还在倒——倒出的蜡在杯里堆成小山。"], "options": [{"label": "入席陪一杯", "reward_id": "warm_coffee", "lucidity": -2, "dissolution": 4}, {"label": "向客人们行礼", "mind": 3}, {"label": "不打扰了", "leave": True}, {"label": "✦ 随机摄入物（稀有度随机）", "random_option": {"pool": "摄入物", "rarities": ["常见"]}}]},
    {"event_id": "event.torn_library", "name": "撕页的图书馆", "description": "一本书在半空自己撕自己，纸页雪片般落下。", "reward_id": "torn_page", "catalog_id": "event.torn_library", "insight_id": "留白", "kind": "compound", "dialogue": ["一本书在半空自己撕自己，纸页雪片般落下。", "每一页落地前都闪过一段你没写完的段落。"], "options": [{"label": "把碎片拼回去", "reward_id": "torn_page", "imagination": 4}, {"label": "接住飘落的一页", "mind": 2}, {"label": "让书继续撕", "leave": True}]},
    {"event_id": "event.midnight_broadcast", "name": "午夜的广播", "description": "老式喇叭里在念一篇没有署名的稿件。", "reward_id": "old_keycap", "catalog_id": "event.midnight_broadcast", "insight_id": "噪声耐受", "kind": "compound", "dialogue": ["老式喇叭里在念一篇没有署名的稿件。", "稿子里提到的街道你全都认识——只是每条都少了路灯。"], "options": [{"label": "给电台拨个电话", "reward_id": "old_keycap", "dissolution": 4}, {"label": "跟着念最后一段", "imagination": 3, "lucidity": -1}, {"label": "关掉喇叭", "leave": True}]},
    {"event_id": "event.swimming_furniture", "name": "游泳的家具", "description": "房间进了半米深的梦水，家具们正在仰泳。", "reward_id": "wet_fold", "catalog_id": "event.swimming_furniture", "kind": "compound", "dialogue": ["房间进了半米深的梦水，家具们正在仰泳。", "一把椅子朝你游过来，像在邀请你下水。"], "options": [{"label": "下水陪它们游", "reward_id": "wet_fold", "lucidity": -1}, {"label": "把家具捞上岸", "mind": 2, "dissolution": 3}, {"label": "站在门口看", "leave": True}]},
    {"event_id": "event.star_clearance", "name": "星星大甩卖", "description": "天上贴着海报：星星十颗起步，概不退换。", "reward_id": "clear_glass", "catalog_id": "event.star_clearance", "kind": "compound", "dialogue": ["天上贴着海报：星星十颗起步，概不退换。", "摊主不在，摊位上只剩最后一颗样品。"], "options": [{"label": "买下最后一颗样品", "reward_id": "clear_glass", "mind": -2}, {"label": "帮摊主看一会儿摊", "imagination": 4}, {"label": "不买", "leave": True}, {"label": "✦ 随机易逝物（稀有度随机）", "random_option": {"pool": "易逝物", "rarities": ["常见", "少见", "稀有"]}}]},
    {"event_id": "event.puppet_rehearsal", "name": "木偶的彩排", "description": "木偶们自己排练一出没有观众的戏。", "reward_id": "loose_thread", "catalog_id": "event.puppet_rehearsal", "insight_id": "疾行拾荒", "kind": "compound", "dialogue": ["木偶们自己排练一出没有观众的戏。", "戏名写在幕布上：《等一个剪断我们的人》。"], "options": [{"label": "剪断一个木偶的线", "reward_id": "loose_thread", "dissolution": 5}, {"label": "为他们鼓掌", "mind": 3}, {"label": "悄悄退场", "leave": True}]},
    # 容器事件获取渠道（2026-09-19）：四件套只经事件/NPC 交易获取，不进自然掉落。
    {"event_id": "event.scrapper_case", "name": "拾荒者的提箱", "description": "桥洞下摆着一只上了锁的提箱，锁孔却被撬成了大开口——主人显然不打算再回来。", "catalog_id": "event.scrapper_case", "kind": "compound", "uses": 2, "dialogue": ["提箱里码着几件器物：耐热的瓶、隔层的管、绷紧的气球，还有一台说不清原理的容器。", "旁边的纸条写着：「拿点梦的原料来换。瓶子只认液体，气球只认气。」"], "options": [{"label": "想象力 −4，换一只玻璃瓶（单种液体 · 少见）", "reward_id": "glass_bottle", "imagination": -4}, {"label": "清醒 −3，换一只气球（单种气体 · 少见）", "reward_id": "balloon", "lucidity": -3}, {"label": "想象力 −8，换一支理想试管（多种液体 · 非常稀有）", "reward_id": "ideal_tube", "imagination": -8}, {"label": "心智 −8，换一台理想气体容器（多种气体 · 非常稀有）", "reward_id": "ideal_vessel", "mind": -8}, {"label": "轻轻带上箱盖", "leave": True}]},
    # ---- 梦中梦·玩具的回忆（2026-09-22）：10 层专属 vault 事件，不在随机事件池 ----
    {"event_id": "event.dream_bottle", "name": "瓶中之门", "description": "一只玻璃瓶立在门扉边，瓶口朝着你。", "catalog_id": "event.dream_bottle", "kind": "compound",
     "dialogue": ["玻璃瓶立在门扉边——瓶塞上刻着一行小字：打开我。"],
     "options": [
      {"label": "抱走玻璃瓶", "reward_id": "glass_bottle"},
      {"label": "贴耳听瓶中的水声", "imagination": 6},
      {"label": "不去动它", "leave": True}],
    },
    {"event_id": "event.dream_balloon", "name": "无风的气球", "description": "一只气球拴在门把手上，不升也不落。", "catalog_id": "event.dream_balloon", "kind": "compound",
     "dialogue": ["气球拴在门把手上，皮面随着你的呼吸微微鼓动。"],
     "options": [
      {"label": "解下气球", "reward_id": "balloon"},
      {"label": "放它飞走", "lucidity": 6},
      {"label": "不去动它", "leave": True}],
    },
    # §8 S23 青灯入口：旧「次数＋选项」协议整体退场，改由绑定场景结算（§12.1）。
    # ``scene`` 指向 data/scenes.py 的定义；``core.generation._spawn_bound_events``
    # 见到它会走 ``install_bound_scene``，把「未开启／等待支付／开启／已进入／已关闭」
    # 五态门机挂到 vault 指定的那格，不再用 uses=999 假装状态机。
    {"event_id": "event.lens_exchange", "name": "守门的青灯", "description": "一盏青色的小灯悬在石台上方，灯罩里缺一块透镜。", "catalog_id": "event.lens_exchange", "kind": "compound",
     "scene": "scene.lens_gate",
     "dialogue": ["青灯照着石台——灯罩里空出一块透镜的形状。"],
     "options": [
      {"label": "不去动它", "leave": True}],
    },
)

# ---- 珍品机会（2026-10-22 A2 P5，方案 §6.1）----
# 22／24／26 层各一次高成本机会（覆盖 22—23／24—25／26—27 三个深度带）。
# 定义表里只放**静态外壳**（名字、描述、对话、代价），真正的选项在生成时由
# core/treasure_offers.py 按本局已拿过什么现算——「始终提供未拿过的合法物」
# 要按局状态决定，写死在表里就会把上一处拿过的件再摆一次。
# 事件 id 带 ``treasure.`` 前缀：池轮转会跳过这一族（见 spawnable_event_ids），
# 珍品机会只由 core/generation.py 在 22／24／26 层投放。
TREASURE_EVENT_DEFINITIONS: tuple[dict[str, Any], ...] = (
    {"event_id": "treasure.breach", "name": "拆到一半的工事",
     "description": "脚手架还立着，墙上有三道旧切口——有人试过把它拆开。",
     "catalog_id": "treasure.breach", "kind": "compound", "uses": 1,
     "dissolution_reward": 15,
     "dialogue": ["脚手架上的线还绷着，切口是新的。",
                  "工具箱没上锁：里面只够带走一样。"],
     "options": [
      {"label": "不去动它", "leave": True}],
    },
    {"event_id": "treasure.storm", "name": "压在旧气压计下的信",
     "description": "一封没有寄出的信压在气压计底下，纸角已经发潮。",
     "catalog_id": "treasure.storm", "kind": "compound", "uses": 1,
     "dissolution_reward": 15,
     "dialogue": ["气压计的指针在抖，信封上写着「暂勿投递」。",
                  "信里的东西还没散出来，但封口已经在渗。"],
     "options": [
      {"label": "不去动它", "leave": True}],
    },
    {"event_id": "treasure.dawn", "name": "留着天亮的抽屉",
     "description": "抽屉没关严，缝里漏出一线不刺眼的光。",
     "catalog_id": "treasure.dawn", "kind": "compound", "uses": 1,
     "dissolution_reward": 15,
     "dialogue": ["抽屉深处有一只还没开封的瓶子，瓶壁是温的。",
                  "里面的东西只够拿一样；拿了，另一样就留在原处。"],
     "options": [
      {"label": "不去动它", "leave": True}],
    },
)
EVENT_DEFINITIONS += TREASURE_EVENT_DEFINITIONS

from .vault_events import VAULT_EVENT_DEFINITIONS

EVENT_DEFINITIONS += VAULT_EVENT_DEFINITIONS

LAYER_EVENT_IDS: dict[int, tuple[str, ...]] = {
    3: ("event.wet_score", "event.editor_note"),
    4: ("event.ash_lighter", "event.static_radio", "event.scrapper_case"),
    5: ("event.bath_tide", "event.pill_box", "event.last_train_window", "event.paper_moon"),
    6: ("event.attic_staircase", "event.tape_line", "event.scrapper_case", "event.polaroid_wall"),
    8: ("event.silent_library", "event.wet_score", "event.mirror_interview"),
    9: ("event.clock_repairs", "event.wet_letterbox", "event.rusty_faucet"),
    11: ("event.silent_library", "event.ash_lighter", "event.wet_letterbox"),
    13: ("event.night_ward_round", "event.clock_repairs", "event.broken_meter"),
    14: ("event.silent_library", "event.static_radio", "event.mirror_interview", "event.lost_luggage"),
    16: ("event.stargazer_desk", "event.dream_post_office", "event.fog_organ"),
    17: ("event.silent_library", "event.bath_tide", "event.night_ward_round", "event.night_stand"),
    19: ("event.dream_post_office", "event.photo_booth"),
    # 无意识领域（21–27）
    21: ("event.first_echo", "event.blank_gallery", "event.post_to_waking"),
    23: ("event.sunken_bell", "event.tide_of_names", "event.toolbox_grave"),
    25: ("event.blank_gallery", "event.first_echo", "event.tide_clock"),
    27: ("event.tide_of_names", "event.sunken_bell"),
}


def spawnable_event_ids() -> tuple[str, ...]:
    """池轮转用的全部候选（迁移开关之后）。

    珍品机会一族（``treasure.`` 前缀）不在轮转池里：它们只在 22—27 层
    由 core/generation.py 按深度带投放，混进浅层轮转会把 26 层才开放的
    珍品提前摆出来。
    """
    held = held_event_ids()
    return tuple(entry["event_id"] for entry in EVENT_DEFINITIONS
                 if entry["event_id"] not in held
                 and not entry["event_id"].startswith("treasure."))


def event_candidates(depth: int) -> tuple[str, ...]:
    """本层异常地点候选池——投放的唯一入口（§15 P1 的迁移开关在这里生效）。

    3 层以后用作者排好的分层池，其余层沿用池轮转；两条路都过一遍
    :func:`dream_demo.data.migration.held_event_ids`：已被场景实现顶掉的族，
    它那几条旧事件不再和场景在同一层各跑一套结算。
    """
    layer_ids = LAYER_EVENT_IDS.get(depth)
    if layer_ids:
        held = held_event_ids()
        return tuple(event_id for event_id in layer_ids if event_id not in held)
    pool = spawnable_event_ids()
    return (pool[(depth - 1) % len(pool)],)
