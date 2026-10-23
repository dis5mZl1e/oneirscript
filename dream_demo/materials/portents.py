"""征兆目录：材料接触/吸入效果与道具、异象带来的持续状态。

2026-10-07 核心循环改版（玩家定稿，详见 docs/combat-balance-review.md）：
- **镇静 / 忘忧分级**：镇静（blocks_mind_loss）只免环境来源心智流失；忘忧
  （mind_loss_factor=0.5）对一切来源（含异象战斗创伤）减半。
- **深度函数**：恢复类与伤害类征兆的每周期结算量 = ceil(定义值 × 深度因子)，
  因子是**连续平滑曲线**（锚点 1 区 ×1 / 2 区 ×1.5 / 3 区 ×2 / 4 区 ×2.5，锚点间线性
  插值，向上取整；见 core.constants.portent_depth_factor），梦中梦取进入时的主层数。
  定义表里保持**基础值**，缩放在结算处做。
- **附着层**：材料征兆被授予时挂 ATTACH_PORTENT_ROUNDS 回合附着（环境也附着），
  离开来源材料后附着期内全额续效且不走衰减。
"""

from __future__ import annotations

from dataclasses import replace

from .definitions import PortentDef


PORTENT_DEFINITIONS: dict[str, PortentDef] = {
    # ---- 液体接触 ----
    "charged": PortentDef(
        "过电", "负面", '每 4 回合：清醒 -0.5（越往深处越重）。离开材料还会缠 2 回合，再花 6 回合退净。静电尘中每回合额外清醒 −1。',
        "接触导电液态记忆", 6, "导电液态记忆", period=4, lucidity=-0.5, min_amount=8,
    ),
    "calmed": PortentDef(
        "镇静", "正面", "镇静溶液压住了惊惶：持续期间环境不再侵蚀心智（毒气/腐蚀/燃烧/下潜反噬等；异象的创伤仍作数）。",
        "接触镇静溶液", 10, "镇静溶液", blocks_mind_loss=True, affects_creatures=False, min_amount=6,
    ),
    "corroded": PortentDef(
        "腐蚀", "负面", '每 4 回合：心智 -0.5（越往深处越重）。离开材料还会缠 2 回合，再花 5 回合退净。',
        "接触酸蚀液", 5, "酸蚀液", period=4, mind=-0.5, min_amount=5,
    ),
    "sluggish": PortentDef(
        "迟滞", "负面", "粘稠的纸浆拖住脚步：移动额外耗时 +0.5，两步最多被拖慢 1 回合。",
        "接触纸浆", 8, "纸浆", move_time=0.5, min_amount=10,
    ),
    # 「显影」不再是征兆：显影液本身就是效果——液面浸过的格子由
    # _mark_developing_liquid 直接标记为永久显影，与是否沾染无关。
    "warmed": PortentDef(
        "温热", "正面", '每 2 回合：想象力 +0.5（越往深处越重）。离开材料还会缠 2 回合，再花 7 回合退净。',
        "接触稀释记忆", 7, "稀释记忆", period=2, imagination=0.5, affects_creatures=False, min_amount=8,
    ),
    "tear_warm": PortentDef(
        "回暖", "正面", '每 2 回合：心智 +0.5（越往深处越重）。离开材料还会缠 2 回合，再花 7 回合退净。',
        "接触泪滴溶液", 7, "泪滴溶液", period=2, mind=0.5, affects_creatures=False, min_amount=6,
    ),
    # ---- 气体吸入 ----
    # 2026-10-17：普通气体低浓度可用，强控制保留核心浓度门槛。
    # 液体、位面专属气体与燃爆/视线规则不随本次吸入阈值调整。
    "moist": PortentDef(
        "润泽", "正面", '每 3 回合：想象力 +0.5（越往深处越重）。离开材料还会缠 2 回合，再花 6 回合退净。',
        "吸入水蒸气", 6, "水蒸气", period=3, imagination=0.5, affects_creatures=False, min_amount=3,
    ),
    "poisoned": PortentDef(
        "中毒", "负面", '每 4 回合：心智 -0.5（越往深处越重）。离开材料还会缠 2 回合，再花 6 回合退净。',
        "吸入毒气", 6, "毒气", period=4, mind=-0.5, min_amount=3,
    ),
    "sedated": PortentDef(
        "迟钝", "负面", "麻醉雾压住动作：移动额外耗时 +1。",
        "吸入麻醉雾", 8, "麻醉雾", move_time=1.0, min_amount=5,
    ),
    "drunk": PortentDef(
        "醉意", "负面", '每 5 回合：清醒 -0.5（越往深处越重）。离开材料还会缠 2 回合，再花 6 回合退净。攻击耗时 +0.3。',
        "吸入酒气", 6, "酒气", period=5, lucidity=-0.5, attack_time=0.3, min_amount=3,
    ),
    "spirited": PortentDef(
        "酩酊", "负面", '每 4 回合：清醒 -0.5（越往深处越重）。离开材料还会缠 2 回合，再花 6 回合退净。攻击耗时 +0.5。',
        "吸入酒精蒸气", 6, "酒精蒸气", period=4, lucidity=-0.5, attack_time=0.5, min_amount=3,
    ),
    "obscured": PortentDef(
        "遮蔽", "中性", "弥散印象糊住视线：视野缩到 65%（比例跨族取最小倍率，不相乘）。",
        "吸入遮蔽弥散印象", 4, "遮蔽弥散印象",
        vision_ratio=0.65, round_max=6, min_amount=6,
    ),
    "charged_piezo": PortentDef(
        "蓄电", "负面", "身上积着压电地板的电荷：层数越高，离放电越近。",
        source="站在压电地板上", duration=0, affects_creatures=True,
    ),
    "shocked": PortentDef(
        "电痉挛", "负面", "短促电流绊住关节：移动额外耗时 +0.8，仅维持 1 回合。",
        source="被连通电场击中", duration=1, move_time=0.8, affects_creatures=True,
    ),
    "burning": PortentDef(
        "燃烧", "负面", '余火：离开火焰后每 2 回合清醒 −1；站在火焰中仅结算直接灼伤，入水熄灭。',
        source="站在火焰格上", duration=4, affects_creatures=True,
    ),
    "volatile": PortentDef(
        "可燃", "负面", "身上残留可燃气体：紧邻火焰时每回合额外承受 1 点清醒创伤。",
        "吸入可燃气体", 8, "可燃气体", min_amount=6,
    ),
    "dusty": PortentDef(
        "扬尘", "负面", '每 4 回合：清醒 -0.5（越往深处越重）。离开材料还会缠 2 回合，再花 5 回合退净。视野 -2（尘族同族取最大，不叠成全盲）。',
        "吸入灰尘云", 5, "灰尘云", period=4, lucidity=-0.5,
        vision=-2, vision_family="尘", min_amount=3,
    ),
    "echoing": PortentDef(
        "回声", "中性", "你的动静被雾放大：声音传播半径翻倍，异象更容易被引来。",
        "吸入回声雾", 8, "回声雾", sound_multiplier=2, min_amount=3,
    ),
    "scalded": PortentDef(
        "灼伤", "负面", '每 4 回合：清醒 -0.5（越往深处越重）。离开材料还会缠 2 回合，再花 5 回合退净。',
        "吸入灼热蒸汽", 5, "灼热蒸汽", period=4, lucidity=-0.5, min_amount=3,
    ),
    "numb": PortentDef(
        "麻痹", "负面", "静电让四肢发木：移动额外耗时 +0.5。",
        "吸入静电尘", 6, "静电尘", move_time=0.5, min_amount=3,
    ),
    "deep_sleep": PortentDef(
        "深眠", "中性", "催眠雾让你每一次行动都额外多沉 1 回合；雾中的异象同样被困住。",
        "吸入催眠雾", 6, "催眠雾", extra_turn=1, min_amount=6,
    ),
    # ---- 道具与异象 ----
    # 致盲（docs 261022 §14.1）：把「短暂完全失去普通视觉」与「长时间缩小视野」
    # 分开。它覆盖所有平减与比例，最终普通 V=0，光源延伸也不能把它复活；
    # 听觉、灵视与传信照常，背包／噪音／观察面板照常打开。
    "blinded": PortentDef(
        "致盲", "负面", "强光把眼前的字洗成一片白：普通视觉归零 2 回合，单轮最长 3 回合。听觉、灵视与传信不受影响，光源也照不回来。",
        "被强闪光或墨线正面命中", 2, blinds=True, round_max=3,
    ),
    "overclock": PortentDef(
        "过热余波", "负面", "浓缩咖啡因的还款期：持续 10 回合，每 2 回合清醒度 −1。",
        "使用浓缩咖啡因", affects_creatures=False,
    ),
    "viscous_debt": PortentDef(
        "迟滞沉积", "负面", "纸浆与静电尘的粘滞仍在积累，随时会拖慢你的下一步。",
        "接触纸浆或静电尘", affects_creatures=False,
    ),
    "double_exposure": PortentDef(
        "双重成像", "正面", "底片上的第二次成像先于时间完成：下一个动作不消耗时间。",
        "使用双重曝光底片", affects_creatures=False,
    ),
    "free_move": PortentDef(
        "无痕步", "正面", "下一次移动不耗时。",
        "使用松脱的缝线", affects_creatures=False,
    ),
    "liquid_glide": PortentDef(
        "液面滑行", "正面", "沿液体直线移动不耗时。",
        "使用湿折页", affects_creatures=False,
    ),
    "mirror_stance": PortentDef(
        "镜面架势", "正面", "镜面碎片架在你和梦之间：下一次指向你的打击将被原路退回。",
        "使用镜面碎片", affects_creatures=False, stacks=1,
    ),
    "hanged_stand_in": PortentDef(
        "挂载替身", "正面", "挂在梦的墙上的承载物将替你承受下一次打击。",
        "携带挂钩并携带易逝物", affects_creatures=False,
    ),
    "lens_afterglow": PortentDef(
        "透镜余晖", "正面", "灯塔透镜仍在替你照亮远处：视野 +3（下潜后的前 3 回合）。",
        "携带灯塔透镜并下潜", affects_creatures=False,
    ),
    "illumination": PortentDef(
        "照彻", "中性", "全图被照亮：你看得见所有异象，它们也看得见你（仅在本层生效）。",
        "解决空心灯塔", affects_creatures=False,
    ),
    # R03 留灯的避难圈「抵抗窗口」：不是会被材料管线赋予的真征兆，只作面板
    # 展示锚点（GameState.portent_ward_turns/portent_ward_id 驱动）。duration=0、
    # 无 material，确保不会被 material_portents/材料接触误赋。
    "refuge_ward": PortentDef(
        "留灯的抵抗", "正面",
        "留灯的避难圈把毒气挡在意识之外：新沾染的「中毒」时长减少 25%。",
        "在留灯的避难圈里连续安全 3 回合", affects_creatures=False,
    ),
    # ---- 《新材料》表：液体接触 ----
    # 遗忘（2026-09-17 改）：原是「禁用行囊与装配」，现改为**视野 −2**——
    # 忘川水漫过意识后分不清远近，看得见却看不清。禁用行囊那条整体搬去了
    # 无念黑渊（见下方 oblivion_strong 的「失忆」），两者不再重叠。
    "forgotten": PortentDef(
        "遗忘", "负面", "忘川水漫过意识：分不清周围，视野范围 −2。",
        "接触忘川水", 10, "忘川水", affects_creatures=False,
        vision=-2, vision_family="遗忘", min_amount=10,
    ),
    "moonlit": PortentDef(
        "月下", "正面", "流动月光替你照亮四周：视野 +4。",
        "接触流动月光", 8, "流动月光", affects_creatures=False, min_amount=6, vision=4,
    ),
    "enlarged": PortentDef(
        "放大", "中性", "身体被放大：无法穿过 1 格宽的缝隙和门，受到的心智创伤减半。",
        "接触彩虹牛奶", 10, "彩虹牛奶", affects_creatures=False, min_amount=6,
    ),
    "cursed_sight": PortentDef(
        "诅咒灵视", "中性", "看见所有意象的位置与形态——每个失控意识的位置与种类都如实显形"
        "（连伪装也看穿），代价是它们也同时看见了你的位置，且灵视的通道是双向的："
        "你的声响同样传得更远（声音半径 ×2）。",
        "接触灵视之血", 10, "灵视之血", affects_creatures=False, min_amount=10,
        # 洞见所有意象：视野外的异象在 render_map 里以真实字形 + 阵营色显形
        # （位置与类型都准确），观测面板也会把它们如实列出。
        reveal_anomalies=True, sound_multiplier=2,
    ),
    "honeyed": PortentDef(
        "蜜裹", "正面", "蜂蜜裹住伤口：每 2 回合恢复 1 点清醒度（随深度 ×1～×2.5，向上取整，每层上限 6）；上方生物移速减半。",
        "接触蜂蜜", 10, "蜂蜜", min_amount=6,
    ),
    "time_melted": PortentDef(
        "时间熔化", "负面", "熔化的时间拖住一切行动：所有行动耗时加倍。",
        "接触熔化的时间", 8, "熔化的时间", speed_multiplier=0.5, min_amount=9,
    ),
    # ---- 《新材料》表：气体吸入 ----
    "clarity": PortentDef(
        "清朗", "正面", "清醒香气驱散迷醉：免疫醉意/麻痹/迟钝/深眠/安眠/褪黑。",
        "吸入清醒香气", 6, "清醒香气", affects_creatures=False, min_amount=3,
    ),
    "poppy": PortentDef(
        "安眠", "中性", '每 2 回合：想象力 +0.5（越往深处越重）。离开材料还会缠 2 回合，再花 6 回合退净。额外耗时 +1。',
        "吸入安眠香", 6, "安眠香", period=2, imagination=0.5, extra_turn=1, min_amount=5,
    ),
    "melatonin": PortentDef(
        "褪黑", "中性", '每 5 回合：心智 +0.5（越往深处越重）。离开材料还会缠 2 回合，再花 6 回合退净。额外耗时 +1。',
        "吸入褪黑素雾", 6, "褪黑素雾", period=5, mind=0.5, extra_turn=1, min_amount=5,
    ),
    # 「沉重」不再是征兆：水银改为站位即触发（见 MERCURY_GAS_THRESHOLD_REDUCTION），
    # 站在水银液面上时本格气体的触发最小浓度被压低，离开即恢复正常。
    "frozen": PortentDef(
        "冻僵", "负面", "液氮冻住了关节：移动额外耗时 +1。",
        "接触液氮", 6, "液氮", move_time=1.0, min_amount=8,
    ),
    "irradiated": PortentDef(
        "辐射病", "负面", '每 4 回合：心智 -0.5、清醒 -0.5（越往深处越重）。离开材料还会缠 2 回合，再花 7 回合退净。',
        "吸入辐射尘埃", 7, "辐射尘埃", period=4, mind=-0.5, lucidity=-0.5, min_amount=3,
    ),
    "invigorated": PortentDef(
        "振奋", "正面", "特浓薄荷茶提神醒脑：持续期间每 2 回合恢复 1 点清醒度（随深度 ×1～×2.5，向上取整）。",
        "使用特浓薄荷茶", 28, period=2, lucidity=1, affects_creatures=False,
    ),
    "caffeinated": PortentDef(
        "咖啡因", "正面", '行动速度 ×1.5；不再造成清醒流失。离开材料后加速还会维持 5 回合。',
        "吸入咖啡因气", 5, "咖啡因气", speed_multiplier=1.5, min_amount=3,
    ),
    # ---- 无意识领域（21–27）：极端征兆 ----
    "nightmare": PortentDef(
        "噩梦", "负面", "梦的边缘在啃食意识：每 2 回合心智 −1（随深度 ×1～×2.5，向上取整）。",
        "贴近梦魇岩", 3, period=2, mind=-1,
    ),
    "nightmare_fiber": PortentDef(
        "噩梦", "负面", '每 4 回合：心智 -0.5（越往深处越重）。离开材料还会缠 2 回合，再花 3 回合退净。',
        "接触噩梦纤维", 3, "噩梦纤维", period=4, mind=-0.5, min_amount=6,
    ),
    "nightmare_breath": PortentDef(
        "噩梦", "负面", '每 4 回合：心智 -0.5（越往深处越重）。离开材料还会缠 2 回合，再花 3 回合退净。',
        "吸入噩梦气息", 3, "噩梦气息", period=4, mind=-0.5, min_amount=5,
    ),
    "chaotic": PortentDef(
        "混沌冲刷", "负面", '每 4 回合：心智 -0.5（越往深处越重）。离开材料还会缠 2 回合，再花 3 回合退净。',
        "接触原初混沌", 3, "原初混沌", period=4, mind=-0.5, min_amount=8,
    ),
    # 失忆（2026-09-17）：无念黑渊接管了原「遗忘」的效果——黑渊吞掉记忆，
    # 行囊与装配全部失效、物件名称只剩问号。名字与介绍都对得上无念黑渊
    # 原本的文案「浸进去连怎么用行囊都想不起来」。
    "oblivion_strong": PortentDef(
        "失忆", "负面", "无念黑渊吞掉了记忆：无法使用或装配行囊与携带意象，物品名称都变成问号。",
        "接触无念黑渊", 12, "无念黑渊", affects_creatures=False, min_amount=8,
    ),
    "mind_burn": PortentDef(
        "灼念", "负面", '每 4 回合：清醒 -0.5（越往深处越重）。离开材料还会缠 2 回合，再花 5 回合退净。',
        "接触熔念金属", 5, "熔念金属", period=4, lucidity=-0.5, min_amount=6,
    ),
    "stillness": PortentDef(
        "时滞", "负面", "静滞之泪拖住了一切：行动速度减半。",
        "接触静滞之泪", 8, "静滞之泪", speed_multiplier=0.5, min_amount=8,
    ),
    "starlit": PortentDef(
        "星辉", "正面", '每 2 回合：心智 +0.5（越往深处越重）。离开材料还会缠 2 回合，再花 7 回合退净。',
        "接触星辉露", 7, "星辉露", period=2, mind=0.5, affects_creatures=False, min_amount=6,
    ),
    "worry_free": PortentDef(
        "忘忧", "正面", "雏菊的香气托住念头：持续期间一切心智流失减半（含异象创伤）。",
        "拔除忘忧雏菊", 10, "", mind_loss_factor=0.5, affects_creatures=False,
    ),
    "whispering": PortentDef(
        "呢喃", "中性", "无意识的呢喃借你的声音扩散：声音传播半径 ×3。",
        "吸入呢喃", 8, "呢喃", sound_multiplier=3, min_amount=5,
    ),
    "voidness": PortentDef(
        "虚无", "负面", '每 4 回合：想象力 -0.5（越往深处越重）。离开材料还会缠 2 回合，再花 6 回合退净。视野缩到 50%（与遮蔽同类取最小倍率，不相乘至近零）。',
        "吸入虚无孢子", 6, "虚无孢子", period=4, imagination=-0.5,
        vision_ratio=0.5, min_amount=5,
    ),
    "dissolving": PortentDef(
        "溶梦", "负面", '每 4 回合：清醒 -0.5（越往深处越重）。离开材料还会缠 2 回合，再花 6 回合退净。崩解每回合 +1。',
        "吸入溶梦酸雾", 6, "溶梦酸雾", period=4, lucidity=-0.5, min_amount=5,
    ),
    "morning_frost": PortentDef(
        "晨霜", "正面", '每 3 回合：清醒 +0.5（越往深处越重）。离开材料还会缠 2 回合，再花 7 回合退净。',
        "吸入晨霜清气", 7, "晨霜清气", period=3, lucidity=0.5, affects_creatures=False, min_amount=3,
    ),
    "datura_sleep": PortentDef(
        "幻觉安眠", "负面", "曼陀罗的花香让人半梦半醒：每一次行动多沉 1 回合。",
        "贴近曼陀罗", 4, extra_turn=1,
    ),
    "styx_weight": PortentDef(
        "冥河之重", "负面", "冥河柳的影子浸着河水：移动额外耗时 +0.5。",
        "贴近冥河柳", 6, move_time=0.5,
    ),
    # 千禧园磁带墙（2026-10-10）：倒带迟滞——倒卷的吱嘎声拖住脚步。
    "rewind_lag": PortentDef(
        "倒带迟滞", "负面", "磁带倒卷的吱嘎声缠住脚步：移动额外耗时 +0.2。",
        "贴近磁带墙", 2, move_time=0.2,
    ),
    "queen_night": PortentDef(
        "月下", "正面", "夜皇后的幽光替你照亮四周：视野 +4。",
        "贴近夜皇后", 6, vision=4,
    ),
    "soul_bind": PortentDef(
        "缚魂", "负面", "缚魂藤缠住了脚踝：移动额外耗时 +0.5。",
        "踩过缚魂藤", 6, move_time=0.5,
    ),
    # ---- 内容扩展包 v1（2026-09-20）：新材料接触/吸入征兆 ----
    # 电解黏液：黏着（移动额外耗时），并微弱导电（与传导冲击联动，后续批次）。
    "electro_stick": PortentDef(
        "电解黏着", "负面", "黏液导电又拉丝：移动额外耗时 +0.6。",
        "蹚过电解黏液", 4, "电解黏液", move_time=0.6,
    ),
    # 液化的回声：声波脉冲半径 ×2（声音流核心增益）。
    "echo_amplify": PortentDef(
        "回声放大", "正面", "回声在液面下反复折叠：你的声响半径 ×2。",
        "蹚过液化的回声", 4, "液化的回声", sound_multiplier=2,
    ),
    # 凝固的尖叫：心智 −2/周期，但视野 +1（代价型警觉）。
    "scream_fear": PortentDef(
        "惊惧", "负面", '每 4 回合：心智 -0.5（越往深处越重）。离开材料还会缠 2 回合，再花 5 回合退净。视野 +1。',
        "蹚过凝固的尖叫", 5, "凝固的尖叫", period=4, mind=-0.5, vision=1,
    ),
    # 记忆粉尘（吸入）：视野 −1，但想象力恢复 +1/回合（取舍型）。
    "dust_haze": PortentDef(
        "恍惚", "中性", '每 2 回合：想象力 +0.5（越往深处越重）。离开材料还会缠 2 回合，再花 5 回合退净。视野 -1。',
        "吸入记忆粉尘", 5, "记忆粉尘", period=2, imagination=0.5,
        vision=-1, vision_family="尘",
    ),
    # 亢奋蒸汽（吸入）：与咖啡因同源的加速，代价清醒流失（用 period 结算）。
    "vapor_rush": PortentDef(
        "亢奋", "中性", '行动速度 ×1.4；不再造成清醒流失。离开材料后加速还会维持 5 回合。',
        "吸入亢奋蒸汽", 5, "亢奋蒸汽", speed_multiplier=1.4,
    ),
    # 死寂气团（吸入）：声音半径压到最小——潜行气（声音半径下限由结算保证）。
    "dead_silence": PortentDef(
        "静默", "正面", "空气吞掉了所有声响：你的声音半径降到最低。",
        "吸入死寂气团", 6, "死寂气团", sound_multiplier=1, min_amount=6,
    ),
    # ---- 梦中梦·门之回廊（2026-09-21）----
    # 门隙之风（吸入）：视野 −2——门缝里的风让眼前的门都变了形。
    # 风向标苔（拔除）：苔尖的方位感留在你眼里（视野 +1）。
    "vane_sense": PortentDef(
        "风向感应", "正面", "苔尖指过方向的直觉留在你眼里：视野 +1。",
        "拔起风向标苔", 8, vision=1,
    ),
    # 改造 v2：墨档员命中附加（每 3 回合清醒 −1、视野 −1）。
    "呛尘": PortentDef(
        "呛尘", "负面", "陈年档案的灰呛进肺里：每 3 回合清醒 −1（随深度 ×1～×2.5，向上取整）、视野 −1。",
        "被墨档员击中", 8, period=3, lucidity=-1, vision=-1, vision_family="尘",
    ),
    "door_vertigo": PortentDef(
        "门扉眩晕", "负面", "门缝里灌进来的风让你看什么都歪：视野 −2。",
        "吸入门隙之风", 5, "门隙之风", vision=-2, vision_family="眩晕",
    ),
    # 门之泪（接触）：圣所石台渗出的泪——想象力缓缓回流。
    "door_tears": PortentDef(
        "门之泪", "正面", '每 4 回合：想象力 +0.5（越往深处越重）。离开材料还会缠 2 回合，再花 6 回合退净。',
        "蹚过门之泪", 6, "门之泪", period=4, imagination=0.5,
    ),
    # 捕梦草缠绕：钉在原地一回合（move_time=99 在 1 回合寿命内即无法移动）。
    "snared": PortentDef(
        "缠住", "负面", "草叶卷住了脚踝：这一回合挪不动步。",
        "踩中捕梦草", 1, move_time=99,
    ),
    # ---- 异象主动技能（2026-10-08，梦层异象主动技能开发表）：非材料征兆 ----
    # 惊散（2026-10-17，docs §15.5 地图侧篡改「退散」）：挂在异象身上——
    # 不索敌、不攻击、主动远离玩家；被玩家攻击立即解除并转追踪（受击处）。
    "spooked": PortentDef(
        "惊散", "负面", "被突兀的文字惊散了：不再寻找你、不发起攻击，并主动与你拉开距离；挨一下打就会惊醒。",
        "被「退散」命中", 10, affects_creatures=False,
    ),
    # 软控制一族：只加移动耗时，不禁止攻击/道具/构想；可净化、随回合衰减；
    # 玩家在「软控制总移步加值上限 0.5」内取和（见 core/portents.py）。
    "sk_late_beat": PortentDef(
        "迟拍", "负面", "行动节奏放缓：移动额外耗时 +0.3（持续 2 回合）。",
        "被「迟到一拍」命中", 2, move_time=0.3, affects_creatures=False,
    ),
    "sk_seam_shadow": PortentDef(
        "缝影", "负面", "影子被缝在了原地：下一次移动额外耗时 +0.5。",
        "被缝影命中", 1, move_time=0.5, affects_creatures=False,
    ),
    "sk_drowsy": PortentDef(
        "倦意", "负面", "摇篮曲拖着脚踝：下一次移动额外耗时 +0.5。",
        "被断续摇篮曲命中", 1, move_time=0.5, affects_creatures=False,
    ),
    "sk_blur": PortentDef(
        "失焦", "负面", "标签贴错了位置：视野半径 −1（只有本项最多减到 3，持续 2 回合）。",
        "被错贴标签命中", 2, vision=-1, vision_family="失焦", vision_floor=3,
        affects_creatures=False,
    ),
    "sk_faded_ink": PortentDef(
        "淡墨", "负面", "遗忘的批注在消褪想象力：每回合想象力 −1（共 2 回合，不按深度放大）。",
        "被遗忘批注标记", 2, affects_creatures=False,
    ),
    "sk_rooted": PortentDef(
        "驻足", "负面", "句子被迫停顿：接下来 1 回合不能移动（道具、构想、攻击仍可用）。",
        "被未完停顿命中", 1, affects_creatures=False,
    ),
    # 硬控制保护窗（写在玩家 active_skill_state 里，不由本表驱动）。
    # 护折/护幕：减伤挡一刀（挂在异象身上，玩家命中时消耗，见 enemy_skills）。
    "sk_guard_fold": PortentDef(
        "护折", "正面", "折起的面挡在身前：下一次受击创伤 −1（最低 1）。",
        "折面护身", 2, affects_creatures=True,
    ),
    "sk_guard_choir": PortentDef(
        "护幕", "正面", "和声织成的幕：下一次受击创伤 −1（最低 1）。",
        "和声护幕", 2, affects_creatures=True,
    ),
    # 加速一族（挂在异象身上）：移动耗时 −0.2，下限由结算处的 0.8 保证。
    "sk_light_step": PortentDef(
        "轻步", "正面", "脚步卸掉了重量：移动耗时 −0.2（持续 2 回合）。",
        "无面潜步", 2, move_time=-0.2, affects_creatures=True,
    ),
    "sk_guidance": PortentDef(
        "引路", "正面", "牧梦者的指引：移动耗时 −0.2（持续 2 回合）。",
        "牧梦指引", 2, move_time=-0.2, affects_creatures=True,
    ),
    # 效果场缠身（玩家踩进迟帧/墨迹/根丝场时挂上，离开即不再续，可净化）。
    "sk_field_hamper": PortentDef(
        "缠身", "负面", "场里的介质缠着脚步：移动额外耗时 +0.2。",
        "踏入异象的效果场", 2, move_time=0.2, affects_creatures=False,
    ),
    "sk_frost": PortentDef(
        "寒痕", "负面", "冻嚎留下的痕：移动额外耗时 +0.3。",
        "踏入寒痕", 2, move_time=0.3, affects_creatures=False,
    ),
}

# 水银（站位即触发，非征兆，也不再减速）：站在水银液面上时，本格气体的
# 触发最小浓度 −5（至少 1）——汞蒸气让气体更容易渗进意识。
# 水银自身的存在下限沿用全局接触下限 PORTENT_CONTACT_MIN（core/constants）。
MERCURY_GAS_THRESHOLD_REDUCTION = 5


PORTENT_DEFINITIONS.update({
    'library_ink_slow': PortentDef('墨痕迟滞', '负面', '湿墨拖住鞋底：移动额外耗时 +0.15，短时生效。',
        source='踩入湿墨', material='湿墨', duration=2, min_amount=6, move_time=.15),
    'library_glue_slow': PortentDef('胶痕迟滞', '负面', '书脊胶短暂粘住鞋底：移动额外耗时 +0.15，持续2回合。',
        source='踩入书脊胶', material='书脊胶', duration=2, min_amount=6, move_time=.15),
    'library_observation': PortentDef('借阅视窗', '正面', '借阅证记下新的接触，四周清楚了一点：视野增加两格，持续四回合；同类视野加成只保留最高的一份。',
        source='蝶梦借阅证成立语句', duration=4, vision=2, affects_creatures=False),
    'hospital_diagnosed': PortentDef('轮廓显形', '中性', '短时诊断标记，仅正常视线内识别伪装。',
        source='诊断玻片或白昼面罩', duration=3),
    'hospital_ether_liquid': PortentDef('醚迟', '负面', '轻迟滞，移步额外0.15；与梦醚气取最大。',
        source='接触梦醚', material='梦醚', duration=3, min_amount=4, move_time=.15),
    'hospital_ether_gas': PortentDef('醚迟', '负面', '轻迟滞，移步额外0.15；与梦醚液取最大。',
        source='吸入梦醚气', material='梦醚气', duration=3, min_amount=6, move_time=.15),
    'hospital_fibrin': PortentDef('胶迟', '负面', '胶液拖住脚底：每步多耗时 0.15 回合；各种迟滞合计最多多耗时 0.5 回合。',
        source='接触纤维蛋白胶', material='纤维蛋白胶', duration=3, min_amount=8, move_time=.15),
    'hospital_spore': PortentDef('胞尘附着', '负面', '每5世界回合心智创伤1；同族不叠加。',
        source='吸入胞尘', material='胞尘', duration=3, min_amount=8, period=5, mind=-1),
    'hospital_awake': PortentDef('晨视', '正面', '视距+1，不产生免费行动。',
        source='吸入醒素薄气', material='醒素薄气', duration=3, min_amount=6, vision=1),
    'hospital_silver': PortentDef('银盐显形', '中性', '视线内短时隐匿显形，不显示视野外目标。',
        source='接触银盐悬液', material='银盐悬液', duration=4, min_amount=6),
    'hospital_steam': PortentDef('薄湿', '中性', '湿润条件，不恢复资源。',
        source='接触无垢蒸汽', material='无垢蒸汽', duration=3, min_amount=8),
    'hospital_oxygen': PortentDef('载氧', '正面', '棉糖里的空气撑住呼吸，胞尘不再追加创伤；其他毒气、火焰和敌人的创伤仍会到来。',
                                 source='摄入载氧棉糖', duration=4),
    'hospital_sensitive': PortentDef('梦敏', '正面', '一种意识指标真正恢复时，药粒也替另一种未满的指标补上至多三点；补过一次就结束。',
                                    source='摄入梦敏颗粒', duration=6),
    'hospital_lymph_hit': PortentDef('淋巴素', '正面', '下一次直接命中病原体附加2点创伤，触发一次。',
                                    source='摄入淋巴素软胶囊', duration=6),
    'hospital_immune_once': PortentDef('免疫球', '正面', '下一项新负面征兆初始持续减2，至少1回合。',
                                      source='摄入免疫球蛋白锭', duration=6),
    'hospital_fluent': PortentDef('流畅', '正面', '念头比平时流得快，想象力自然恢复变为一点二五倍；与脑脊液同用，只取较快的一份。',
                                 source='摄入脑脊滴', duration=6),
    'hospital_gel_buffer': PortentDef('缓释', '正面', '凝片替你垫住下一次创伤，少受一点，随即消散。',
                                     source='摄入缓释凝片', duration=6),
    'hospital_pain_buffer': PortentDef('停痛', '正面', '首次心智创伤抵扣2点，不减免清醒创伤。',
                                      source='摄入停痛糖衣', duration=6),
})

# 2026-10-18 材料效果补齐：此前只有扩散/遮蔽、没有可感知接触/吸入效果
# 的几种气体与液体，补一组轻量、可读的征兆。
PORTENT_DEFINITIONS.update({
    'bone_ache': PortentDef('骨酸', '负面', '蚀骨瘴黏在关节上：移动额外耗时 +0.15。',
                            '吸入蚀骨瘴', 4, '蚀骨瘴', move_time=.15, min_amount=5),
    'void_murmur': PortentDef('低语缠耳', '中性', '无意识低语放大你的动静：声音传播半径 ×2。',
                              '吸入无意识低语', 5, '无意识低语', sound_multiplier=2, min_amount=5),
    'plasma_tingle': PortentDef('电麻', '负面', '电浆雾的余电钻进指尖：移动额外耗时 +0.15。',
                                '吸入电浆雾', 3, '电浆雾', move_time=.15, min_amount=5),
    'clear_mist': PortentDef('清兆', '正面', '消兆薄雾把杂念洗淡：每 4 回合恢复 0.5 点清醒（随深度）。',
                             '吸入消兆薄雾', 4, '消兆薄雾', period=4, lucidity=.5,
                             min_amount=5, affects_creatures=False),
    'sterile_air': PortentDef('无菌隔护', '正面', '过滤后的载气隔开侵蚀：心智流失减少 20%。',
                              '吸入无菌载气', 4, '无菌载气', mind_loss_factor=.8,
                              min_amount=5, affects_creatures=False),
    'wine_haze': PortentDef('酒雾', '负面', '红酒的香气缠上来：每 5 回合清醒 -0.5（随深度），攻击耗时 +0.2。',
                            '接触红酒', 5, '红酒', period=5, lucidity=-.5,
                            attack_time=.2, min_amount=6),
    'oil_film': PortentDef('油膜', '负面', '燃油在鞋底打滑：移动额外耗时 +0.15。',
                           '接触燃油', 4, '燃油', move_time=.15, min_amount=6),
    'honey_heal': PortentDef('蜜愈', '正面', '蜜酿润过喉咙：每 4 回合恢复 0.5 点心智（随深度）。',
                             '接触蜜酿', 4, '蜜酿', period=4, mind=.5,
                             min_amount=6, affects_creatures=False),
    'lymph_flow': PortentDef('淋巴暖流', '正面', '淋巴液推着循环：每 4 回合恢复 0.5 点清醒（随深度）。',
                             '接触淋巴液', 4, '淋巴液', period=4, lucidity=.5,
                             min_amount=6, affects_creatures=False),
    'wake_tonic': PortentDef('晨醒', '正面', '晨醒溶液让人一下坐直：每 4 回合恢复 0.5 点清醒。',
                             '接触晨醒溶液', 4, '晨醒溶液', period=4, lucidity=.5,
                             min_amount=6, affects_creatures=False),
    'dream_infusion': PortentDef('梦液滋养', '正面', '注射用梦水缓缓渗入：每 4 回合恢复 0.5 点心智。',
                                 '接触注射用梦水', 4, '注射用梦水', period=4, mind=.5,
                                 min_amount=6, affects_creatures=False),
    'gel_slow': PortentDef('凝胶滞足', '负面', '凝胶基液黏住脚步：移动额外耗时 +0.2。',
                           '接触凝胶基液', 3, '凝胶基液', move_time=.2, min_amount=6),
})

# Timed catalogue effects are washable; charges and derived displays are not.
from ..data.environment_prose import PORTENT_PROSE
for _portent_id, (_effect, _english_effect) in PORTENT_PROSE.items():
    PORTENT_DEFINITIONS[_portent_id] = replace(PORTENT_DEFINITIONS[_portent_id], effect=_effect)

PORTENT_DEFINITIONS = {
    pid: replace(definition, washable=definition.duration > 0)
    for pid, definition in PORTENT_DEFINITIONS.items()
}


def portent_def(portent_id: str) -> PortentDef | None:
    return PORTENT_DEFINITIONS.get(portent_id)


def material_portents(material: str) -> tuple[str, ...]:
    """返回某种液体/气体接触时赋予的征兆 id。"""
    return tuple(
        portent_id
        for portent_id, definition in PORTENT_DEFINITIONS.items()
        if definition.material == material
    )


def material_trigger_amount(material: str) -> int | None:
    """材料接触/吸入征兆的最小触发浓度（多个征兆取最低门槛）。

    返回 None 表示该材料不赋予任何征兆——它的效果要么只是环境描述
    （水是清洗材料；黑烟、灰尘云等是遮蔽/站位类机制），要么是站位/遮蔽类机制（水银、黑烟、灰尘云的遮蔽），
    不存在「浓度达标才触发」的门槛。
    """
    amounts = [
        definition.min_amount
        for definition in PORTENT_DEFINITIONS.values()
        if definition.material == material
    ]
    return min(amounts) if amounts else None


# 清洗材料：接触时**洗掉**的征兆（不赋予任何征兆）。
# 水是最典型的一种——把身上的可燃气体浇灭冲净；它本身不赋任何征兆，
# 所以踩进水里既不会中毒也不会获得增益，只会甩掉火气。
# 值是该材料洗掉的征兆 id 集合。
CLEANSING_MATERIALS: dict[str, frozenset[str]] = {
    "水": frozenset({"volatile", "corroded"}),
    "稀释记忆": frozenset({"volatile"}),
}


def material_cleanses(material: str) -> frozenset[str]:
    """该材料接触时会洗掉的征兆 id 集合（无则空集）。"""
    return CLEANSING_MATERIALS.get(material, frozenset())
