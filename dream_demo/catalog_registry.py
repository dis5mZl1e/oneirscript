from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Iterable, Mapping

from .core import ANOMALY_DEFINITIONS, EVENT_DEFINITIONS, ITEM_DEFINITIONS
from .core.constants import SIGHT_OBSCURE_MIN
from .data.npcs import NPC_DEFINITIONS
from .i18n import tr
from .rarity_colors import apply_rarity, item_variant_color
from .materials import (
    CONTAINER_KINDS,
    FLOOR_DEFINITIONS,
    FEATURE_WALLS,
    GAS_DEFINITIONS,
    LIQUID_DEFINITIONS,
    SOLID_KINDS,
    WALKABLE_FEATURE_WALLS,
    WALL_DEFINITIONS,
    material_description,
    material_trigger_amount,
)
from .materials.reactions import REACTIONS
from .symbols import carried_slot_key, symbol
from .data.item_icons import item_icon


class CatalogCategory(str, Enum):
    CONSCIOUSNESS = "consciousness"
    MANIFESTATION = "manifestation"
    CARRIED_IMAGE = "carried_image"
    SITE = "site"
    POLYMER = "polymer"
    LIQUID_MEMORY = "liquid_memory"
    DIFFUSE_IMPRESSION = "diffuse_impression"
    # 环境物体反应表：材料 A + B → 产物的配方资料（默认全解锁）。
    REACTION = "reaction"
    # 梦中人（2026-10-11）：稳定意识 NPC 的图鉴分类（data/npcs.py，22 位委托人）。
    NPC = "npc"

    @property
    def label(self) -> str:
        return tr({
            CatalogCategory.CONSCIOUSNESS: "意识体",
            CatalogCategory.MANIFESTATION: "显化物",
            CatalogCategory.CARRIED_IMAGE: "携带意象",
            CatalogCategory.SITE: "异常地点",
            CatalogCategory.POLYMER: "聚合物",
            CatalogCategory.LIQUID_MEMORY: "液态记忆",
            CatalogCategory.DIFFUSE_IMPRESSION: "弥散印象",
            CatalogCategory.REACTION: "环境反应",
            CatalogCategory.NPC: "梦中人",
        }[self])

    @property
    def symbol_key(self) -> str:
        return f"category_{self.value}"

    @property
    def icon_color(self) -> str:
        """分类图标的专属色：图鉴分类页与主页分类按钮共用一色。

        ⚠️ 这些色会画在**面板**上（游戏内图鉴用区域面板色，最亮 #242e35），所以不能用
        命名色——命名色被 Textual 主题调色板解析成暗值（bright_magenta → `#f4005f` 3.30、
        bright_blue → `#9d65ff` 3.78）。这里的两处改用与 `ui.styles.PANEL_MAGENTA` /
        `PANEL_BLUE` 相同的 hex；其余命名色（bright_yellow/cyan/green/white）本身达标。
        """
        return {
            # 2026-10-09 消重：八类图标色必须两两可辨（此前意识体=携带意象同为
            # 金黄、显化物=环境反应同为浅青）。意识体改暖橙、环境反应改紫；
            # 对 #242e35 面板底的对比度实测 5.96 / 5.32（≥4.5 达标）。
            CatalogCategory.CONSCIOUSNESS: "#ff8a5c",
            CatalogCategory.MANIFESTATION: "bright_cyan",
            # 与地图上的 ♕ 同色（styles.CARRIED_IMAGE_STYLE 的金）。
            CatalogCategory.CARRIED_IMAGE: "#ffd166",
            CatalogCategory.SITE: "#ff8ad8",
            CatalogCategory.POLYMER: "bright_green",
            CatalogCategory.LIQUID_MEMORY: "#8ab4f8",
            CatalogCategory.DIFFUSE_IMPRESSION: "bright_white",
            CatalogCategory.REACTION: "#b18cff",
            # 梦中人：暖纸色（NPC 自带色系 #d6c79c 的分类化，与八类两两可辨）。
            CatalogCategory.NPC: "#c9b896",
        }[self]


# 材料三类：图鉴里的环境材料目录（聚合物地面/墙/固体、液态记忆、弥散印象）。
# 它们不依赖遭遇/交互进度——进图鉴即可翻阅，帮助玩家查资料。
MATERIAL_CATEGORIES = frozenset(
    {CatalogCategory.POLYMER, CatalogCategory.LIQUID_MEMORY, CatalogCategory.DIFFUSE_IMPRESSION}
)

# 聚合地面：十种聚合地面变体（六种常见 + 四种稀有连片）+ 承托墙体的坚实聚合物地基。
# 稀有的四种（木质/海绵/金属/灼热）由 generation._grow_rare_floors 成片铺出，
# 覆盖率合计约 3%；十种变体都不影响通行，各自带一点点不造成伤害的小效果
# （见 materials/floors.py 的 FloorDef）。
FLOOR_KINDS: tuple[str, ...] = (
    "普通聚合物",
    "柔软聚合物",
    "粗糙聚合物",
    "反光聚合物",
    "吸声聚合物",
    "空白聚合物",
    "木质聚合物",
    "海绵聚合物",
    "金属聚合物",
    "灼热聚合物",
    "梦境绒毯",
    "冰面",
    "星图地",
    "书页地",
    "月壤",
    "棋盘格地板",
    "绝热层",
    "压电地板",
    "坚实聚合物",
)

# 物品/携带意象的 effect 原始 id → 图鉴「作用」行的可读名称。
ITEM_EFFECT_LABELS: dict[str, str] = {
    "unlock_fire": "提供发射来源",
    "container": "容器：盛装/倒出",
    "spray_liquid": "液枪：喷射液态记忆",
    "spray_gas": "气枪：喷射弥散印象",
    "throw_master": "投掷强化：距离+3、威力+1",
    "sound_lure": "落点声波引怪",
    "smoke_cloud": "落点糊上黑烟",
    "fire_once": "一次性直线发射",
    "mirror_insight": "洞察三选一",
    "spray_boost": "喷射材料量 +6",
    "explosion": "爆发推离",
    "ignite": "点燃",
    "fireburst": "火海",
    "remote_switch": "远程按键",
    "tar_burst": "分层焦油",
    "ignite_burst": "十字引燃",
    "spark_rays": "八向火星",
    "ignite_strike": "攻击附燃",
    # 内容扩展包 v1
    "erase_strike": "命中删最近征兆",
    "liquid_ward": "液体征兆减半",
    "shock_aura": "受击反打冲击",
    "sleep_strike": "命中附加深眠",
    "wall_sense": "隔墙听轮廓",
    "wire_safe": "徒手操作机关",
    "enter_realm": "梦中梦入口",
    "fire_ward": "火焰护符",
    "blast_radius": "爆破扩径",
    "fire_affinity": "纵火亲和",
    "shock": "放电",
    "restore_imagination": "恢复想象力",
    "fullstop_reserve": "恢复想象与清醒；分期支付心智",
    "modem_buffer": "56k 握手：时序加速后迟滞",
    "projectile_charge": "弹体充能",
    "quiet_steps": "悄声无息",
    "memory": "记忆回响",
    "mind_guard": "心智守护",
    "repair": "修缮",
    "restore_mind": "恢复心智",
    "restore_lucidity": "恢复清醒",
    "hang": "挂载替身",
    "noise_cut": "屏蔽声响",
    "slow_aura": "迟缓光环",
    "lamp": "照明",
    "measure": "测距",
    "restore_split": "双重复原",
    "gamble": "未知药效",
    "overclock": "过热",
    "warm_restore": "温热恢复",
    "lucidity_regen": "清醒回复",
    "blast_lure": "声响诱引",
    "blind": "致盲闪光",
    "slick": "打滑",
    "ignite_liquid": "引燃液体",
    # 2026-10-22（P3 战术分工）：千梦铃改走真实声路，与发条半卷分开登记。
    "slow_burst": "迟缓爆发",
    "slow_ring": "迟缓铃音",
    "knockback": "击退",
    "parry": "格挡",
    "liquid_step": "液面滑行",
    "skip_turn": "落空一步",
    "free_action": "免费行动",
    "free_step": "免费移动",
    "weapon_damage": "武器伤害",
    "mind_armor": "心智护甲",
    "lucidity_armor": "清醒护甲",
    "coin_bonus": "崩解推进",
    "vision_up": "视野提升",
    "swift_pickup": "迅捷拾取",
    "repair_up": "修缮强化",
    "pierce_up": "穿透强化",
    "learn_ability": "习得构想",
    # ---- 无意识领域 T3 物品：2026-09-17 补齐登记 ----
    # 此前 entries 里只有 effect id，图鉴「作用」行会原样吐出英文 id。
    "develop_radius": "永久显影",
    "purge_void": "凝固虚空",
    # 无光斗篷 / 迅念指环：曾因「描述与实装不符」而只登记作用名、不给说明
    # （斗篷的清醒减免用了 power 而非 power_secondary；指环的「攻击 −0.2」
    # 实测反而更慢）。两处已对齐：指环修正了实装（见 portents._spend_attack_time），
    # 斗篷/订书机把描述改成了实装的样子。作用说明因此照实补上。
    "dual_armor": "双重护甲",
    "swift_strike": "迅捷攻击",
    # ---- 构筑桥接组件（2026-10-08，平衡方案 §6.1）----
    "refract_mark": "折射印记",
    "wet_conduct": "潮润传导",
    "ash_retreat": "灰烬撤步",
    "attach_hunt": "附着追猎",
    "echo_control": "回声控场",
    "blank_pass": "留白免单",
    # ---- 梦中梦支线·余烬廊桥与退潮厅（2026-10-08）----
    "blank_edge": "留白续写",
    "realm_igniter": "引火",
    "blast_padding": "缓冲冲击",
    # ---- A2 新增十件（2026-10-22）：部署类装置与终局珍品 ----
    "deploy_beacon": "夜灯：定时发声",
    "deploy_siphon": "虹吸：定点搬料",
    "deploy_wax_seal": "蜡封：临时隔断",
    "winter_sample": "液氮：低温冻结",
    "breach_spool": "线轴：定向破障",
    "deploy_escape_route": "折路：定点往返",
    "storm_accumulator": "蓄电：延时放电",
    "deploy_quiet_boundary": "静音圈：削弱声响",
    "waking_reserve": "储备：清醒与洗涤",
    "bottled_sunrise": "瓶装天亮：延时纵火",
}

# 物品/携带意象「作用说明」：effect id → 一句机制描述（图鉴详情用）。
# 与 core 实际实现逐条对齐；quiet_steps / mind_guard 已在 2026-10-22 实装
# （enemies._step_noise_reduction_for／portents._lose_mind），但详情文案
# 故意缺席——图鉴里只显示「作用」名，不展开机制。
ITEM_EFFECT_DETAILS: dict[str, str] = {
    "fireburst": "使用与投掷都进入落点瞄准：落点十字五格先泼上燃油（中心 12、四邻 6）再一起点燃，斜角四格只烧本来就可燃的格——整片 3×3 火海。已有液体的地面不另铺油，防火层点不着；落点选在脚下即原地释放。",
    "ignite_burst": "落点（或脚下）十字五格点燃已有可燃材料的格子，干净地板不会自己烧起来；高浓度可燃气会被引爆。使用即进入落点瞄准，把落点选在自己脚下就是原地迸火星。",
    "remote_switch": "三格内（曼哈顿距离）最近的一个看得见的接收器机关按响一次：机关门开合、显影方尖点亮、囚笼栅栏升降、弹射座弹射、灌注阀灌注、共鸣报警器报警。同距离时优先当前朝向那一格；三格内没有这样的机关就拒绝，且不消耗键帽。",
    "tar_burst": "落点 3×3 点燃，十字五格的燃油不一次铺满：落地先淌一层 20 单位，之后第 1、2 回合各再淌一层，合计 60（每格约 12，火比燃烧瓶更匀更久）。后续几层只加燃油、不重复点燃，伤害只有落点那一次；异种液体的格子不会被焦油顶掉，防火层铺不上。",
    "spark_rays": "落点向八个方向各抛一束火星，最远 3 格，遇墙即止；不铺油，只点燃沿途本来就可燃的材料。与燃烧瓶的 3×3 火场分工不同：它靠半径覆盖，烟花靠方向穿透。",
    "ignite_strike": "近战与弹体命中后点燃目标所在格。",
    "fire_ward": "站在火焰格不再受到清醒创伤。",
    "blast_radius": "投掷爆炸物与烈焰新星的半径 +1。",
    "fire_affinity": "所有点燃来源的火焰强度 +1。",
    "unlock_fire": "装备后这件武器可作为发射来源；卸下即不再提供。",
    "explosion": "掷到落点才爆炸：半径内造成创伤、把目标推开一格、削弱坚实聚合物并引燃可燃材料；玩家自己站在半径里照样吃清醒创伤。",
    "ignite": "点燃脚下的液态记忆或弥散印象（需足量），原地升起火焰。",
    "shock": "站在导电介质上使用：沿四邻连通的介质放电（四格内、最多二十格），被击中的失控意识这一拍慢一步；余电在介质上停留五回合，敌我都要躲。",
    "restore_imagination": "使用后恢复与效力相等的想象力。",
    "fullstop_reserve": "使用后恢复 35 点想象力与 12 点清醒度；随后 10 回合内分 8 次支付心智 1 点。每份账单独立，旧债不被新药覆盖。",
    "projectile_charge": "使用后获得可再装的弹体充能。",
    "memory": "拾取时存进梦的记忆碎片，跨局保留（最多 3 条）；碎片是「可拆卸的洞察」，提供征兆免疫、环境适应或少量上限提升。",
    "repair": "使用后修补相邻受损的墙体。",
    "restore_mind": "使用后恢复与效力相等的心智。",
    "restore_lucidity": "使用后恢复与效力相等的清醒度。",
    "hang": "携带在依附物时，自动把第一件易逝物挂上梦的墙，替你承受下一次打击。",
    "noise_cut": "携带在自我表层：自身脚步与普通道具声径 −2、不再显示贴近提示；不改异象视野。",
    "slow_aura": "携带在依附物：3 格内的失控意识移动更迟缓。",
    "lamp": "携带在依附物：下潜后的前 3 回合获得「透镜余晖」（视野 +3）。",
    "measure": "使用后读出到悬停格的最短步数（按全知口径计算）。",
    "restore_split": "使用后同时恢复清醒度与想象力。",
    "gamble": "五五开：要么心智 +15，要么心智 −8 且清醒度 −3。",
    "overclock": "使用后想象力 +效力，但接下来 10 回合每 2 回合扣 1 点清醒度。",
    "warm_restore": "使用后恢复心智，并清空迟滞与麻痹的欠账。",
    "lucidity_regen": "使用后获得「振奋」：每 2 回合恢复 1 点清醒度。",
    "blast_lure": "使用后发出声波引诱周围的失控意识，近处 1 格的会被震停。",
    "blind": "让看得见这束光的失控意识视距减半五回合（使用那一拍也算在内）：墙挡住的不会被闪，不看眼睛的目标免疫。",
    "slick": "使用后把脚下格子变滑：踩上的失控意识移动更慢（持续到换层）。",
    "ignite_liquid": "使用后点燃相邻一格的可燃液体或气体。",
    "slow_burst": "使用后拖慢效力范围内失控意识的动作（持续时间按物品定义，发条半卷为 3 回合）；只作用于敌对关系，NPC 不受影响。",
    "slow_ring": "使用后铃声按真实声路传播（墙体衰减、听觉上限、阈值），听得到的失控意识慢 5 回合；听不到的不受影响。",
    "knockback": "使用后击退相邻的目标并造成 1 点创伤。",
    "parry": "使用后获得一次格挡。",
    "liquid_step": "使用后获得沿液面直线免费行走的步数。",
    "skip_turn": "使用后崩解度 −效力。",
    "free_action": "使用后获得一次免费行动。",
    "free_step": "使用后获得一次免费移动。",
    "weapon_damage": "携带在手中意象：攻击创伤 +效力。",
    "mind_armor": "携带后承受的心智创伤 −效力。",
    "lucidity_armor": "携带后承受的清醒创伤 −效力。",
    "coin_bonus": "携带后每次解决失控意识，崩解推进 +效力。",
    "vision_up": "携带后视野 +效力。",
    "swift_pickup": "携带后拾取不耗时。",
    "repair_up": "携带后修缮量 +效力。",
    "pierce_up": "携带后弹体穿透 +效力。",
    "learn_ability": "使用后习得一个尚未学会的主动构想；全部习得后化作 10 点想象力。",
    "develop_radius": "使用后以自身为中心、半径＝效力的地形永久显影：视野外也看得见地形。",
    "purge_void": "使用后清除噩梦、虚无与遗忘（含无念黑渊的失忆）一类的控制类负面征兆。",
    # 无光斗篷：实装两侧都读 power（enemies._take_hit 里 trauma 与
    # lucidity_trauma 减的是同一个 _effect_power("dual_armor")），
    # 定义里的 power_secondary 无人读——所以是「各 −效力」，不是 −2/−1。
    "dual_armor": "携带后承受的心智创伤与清醒创伤各 −效力。",
    # 迅念指环：基础耗时减 0.2×（效力÷2），零头进 round_debt 记账，
    # 所以体感是「平均每 5 次攻击省下 1 回合」，而非每次出手都变快一点。
    "swift_strike": "携带后攻击的基础耗时 −0.2×（效力÷2）：零头记账，平均每 5 次攻击省 1 回合。",
    # 沉重的订书机定义里的 power_secondary 同样无人读：移动惩罚读的是
    # weapon_weight 效果，而没有任何物品的 effect 是 weapon_weight，
    # 于是那个「移动更沉」从未生效——描述已改为只写伤害。
    # ---- 构筑桥接组件（2026-10-08，平衡方案 §6.1 的六种原型各补一环）----
    "refract_mark": "携带后，弹体经跳弹改向后命中会刻上折射印记（3 回合）；下一次从不同方向命中同一目标额外 +效力 创伤，印记随即消耗。",
    "wet_conduct": "你的放电（导电液态记忆、压电地板）在湿润目标之间多传一次：2 格内另一位浸在导电液态记忆里的意识受 效力 点完整度，每 6 回合限一次。",
    "ash_retreat": "每层第一次由你亲手点燃时：获得 1 次免费移动，3 格内处于「追踪」的意识降为「怀疑」。",
    "attach_hunt": "对身上仍挂着材料附着的意识，攻击创伤 +1（多件不叠加）；首次命中会报出它附着的是哪种材料。",
    "echo_control": "一次成功的声波引诱（有意识循声而去）会武装本层的下一次脉冲：声源 3 格内的意识当场震停 1 回合；武装跨层作废。",
    "blank_pass": "想象力为 0 时仍可展开一项已习得构想，免除它的想象成本（每层一次；冷却与行动时间照常）。与洞察「留白」共用这一次。",
    "blank_edge": "每个留白续写件只按自己那份次级强度生效；按实际经过的回合回流，合计额外回流每回合最多 3 点。",
    "blast_padding": "爆炸冲击造成的清醒创伤最多减少 1，至少承受 1；不叠加为爆炸免疫。",
    "realm_igniter": "使用后点燃身边八格内所有可燃液体与气体（不入掉落池，随余烬廊桥进出授予与收回）。",
    # ---- A2 新增十件（2026-10-22）----
    "deploy_beacon": "选 6 格内一处可见空地放下：灯芯照出半径 3 的弱光，落地即发声一次（声径 12），第 3／6／9 回合各再咳一次；灯会被火烧掉，光随之熄灭。",
    "deploy_siphon": "选两处可见格（源与出口，相距不超过 6 格），源须有液体或气体：液体每回合搬 8 单位、合计 64；气体每回合 4 单位、合计 32。出口装满或源被抽干即停转（不吞材料）；8 回合后撤下。",
    "deploy_wax_seal": "选 4 格内一处可见空地：挤出的 20 单位熔蜡堆成一堵完整度 60 的蜡墙，可挡住去路（唯一必经路不让封）。10 回合后逐步化回等量熔蜡；附近起火会提前融化。",
    "winter_sample": "掷出摔碎：落点放出 24 单位液氮（中心 8、四邻各 4），按既有冻结／凝结规则转化，地板不会被整层冻住；装不下的留在容器里。",
    "breach_spool": "选一个方向：沿线 6 格内至多 3 处非保护障碍被细线咬住，每回合合计侵蚀 60 点完整度（合计 180），按距近到远分配；线抽完即松。",
    "deploy_escape_route": "选两处可见空位（相距不超过 8 格）铺开：踩到一端就被送到另一端，最多 3 趟，每趟花一次正常移动；不跨层、不跳任务门、边界与禁行格一律不送。",
    "storm_accumulator": "掷出后分 4 回合倒出电荷（每回合 15 单位导电液态记忆、10 单位静电尘），最后放一次电：沿真实连通介质传播，同一回合每个目标只挨一次；介质不导电就散掉。",
    "deploy_quiet_boundary": "在脚下铺开半径 4 的静音圈，持续 6 回合：穿过边界的声响在既有传播损耗之外再衰减 6（每格最多计一次）；不清警戒，也不挡非声音的感知。",
    "waking_reserve": "喝下后清醒 +30、心智 +20，并洗掉一项可清洗的负面附着、把一项可清洗的负面征兆缩短至多 4 回合；正面征兆、混乱、债务与冷却都不动。",
    "bottled_sunrise": "掷出后留 2 回合可见引信，之后 3 回合向视线可达、半径 3 的范围分批放出合计 80 单位燃油并点燃；火与爆炸都走既有燃烧规则。",
}


@dataclass(frozen=True)
class CatalogDefinition:
    catalog_id: str
    category: CatalogCategory
    name: str
    symbol_key: str
    description: str
    stats: Mapping[str, Any]
    # 条目图标的专属色：显化物用物品自身色，聚合物/液态记忆/弥散印象用
    # 材料定义色（十六进制），异常地点与意识体用分类默认色。
    color: str = "bright_yellow"
    # 条目自带的图标（书卷 📚 / 残页 📜 一类）：非空时**取代** symbol_key
    # 查出来的通用字形（◆/♕）。与地图、行囊共用符号表 symbols.drop_glyph，
    # 因此图鉴里的图标永远跟着物品定义走，不会各写一份而走偏。
    icon: str = ""


@dataclass(frozen=True)
class StatDef:
    key: str
    label: str
    categories: frozenset[CatalogCategory]
    fmt: Callable[[Any], str]
    unlock: str = "seen"
    source: str = "definition"


@dataclass(frozen=True)
class CatalogDiagnostic:
    catalog_id: str
    stat_key: str
    error_type: str


def _plain(value: Any) -> str:
    if isinstance(value, bool):
        return tr("是") if value else tr("否")
    return tr(str(value))


# 珍品机会的来源标签（2026-10-22 A2 P5）：grant_source 里的 event:treasure.*
# 是渠道 id，图鉴「获取来源」行要显示玩家读得懂的名字。
TREASURE_SOURCE_LABELS = {
    "treasure.breach": "拆迁珍品机会",
    "treasure.storm": "雷暴珍品机会",
    "treasure.dawn": "天亮珍品机会",
}


def _grant_source(value: Any) -> str:
    """把 enemy:/npc:/event: 来源 id 还原为玩家可读名称。"""
    text = str(value or "")
    kind, _, key = text.partition(":")
    if kind == "enemy":
        return tr(ANOMALY_DEFINITIONS.get(key, {}).get("name", key))
    if kind == "npc":
        return tr(NPC_DEFINITIONS.get(key, {}).get("name", key))
    if kind == "event":
        return tr(TREASURE_SOURCE_LABELS.get(key, text))
    return tr(text)


def _trait_list(value: Any) -> str:
    """特性摘要：逐项取词后再连接，保证英文包能逐词翻译。"""
    if isinstance(value, (list, tuple)):
        return " · ".join(tr(str(part)) for part in value)
    return _plain(value)


def _floor_effect(value: Any) -> str:
    from .materials.descriptions import material_effect_description
    return material_effect_description(str(value))


def _time(value: Any) -> str:
    return f"{float(value):g} {tr('回合')}"


def _item_name(value: Any) -> str:
    definition = ITEM_DEFINITIONS.get(str(value))
    return tr(definition["name"]) if definition else str(value)


def _item_names(value: Any) -> str:
    if not isinstance(value, (list, tuple, set)):
        raise TypeError("observed drops must be a collection")
    return "、".join(_item_name(item_id) for item_id in value) or tr("无")


CONSCIOUSNESS = frozenset({CatalogCategory.CONSCIOUSNESS})
MANIFESTATION = frozenset({CatalogCategory.MANIFESTATION})
CARRIED_IMAGE_CATS = frozenset({CatalogCategory.CARRIED_IMAGE})
SITE = frozenset({CatalogCategory.SITE})
POLYMER_ONLY = frozenset({CatalogCategory.POLYMER})
LIQUID_ONLY = frozenset({CatalogCategory.LIQUID_MEMORY})
GAS_ONLY = frozenset({CatalogCategory.DIFFUSE_IMPRESSION})
LIQUID_OR_GAS = LIQUID_ONLY | GAS_ONLY

STAT_REGISTRY: tuple[StatDef, ...] = (
    StatDef("anomaly_kind", "异象层级", CONSCIOUSNESS, _plain),
    StatDef("skill", "主动技能", CONSCIOUSNESS, _trait_list),
    StatDef("passive", "特性", CONSCIOUSNESS, _plain),
    StatDef("integrity", "完整度", CONSCIOUSNESS, _plain),
    StatDef("move_time", "移动速度", CONSCIOUSNESS, _time),
    StatDef("attack_time", "攻击速度", CONSCIOUSNESS, _time),
    StatDef("trauma_type", "主要创伤", CONSCIOUSNESS, _plain),
    StatDef("vision", "观测范围", CONSCIOUSNESS, _plain),
    StatDef("communicates", "传递目击", CONSCIOUSNESS, _plain),
    StatDef("dissolution_reward", "崩解推进", CONSCIOUSNESS, _plain, "resolved"),
    StatDef("drop_id", "可能遗留", CONSCIOUSNESS, _item_name, "resolved"),
    StatDef("drops_seen", "已观测遗留", CONSCIOUSNESS, _item_names, "resolved", "progress"),
    StatDef("rarity", "稀有度", MANIFESTATION, _plain),
    StatDef("category", "显化类别", MANIFESTATION, _plain),
    StatDef("effect", "作用", MANIFESTATION, _plain),
    StatDef("effect_detail", "作用说明", MANIFESTATION, _plain),
    StatDef("min_depth", "最早主梦层", MANIFESTATION, _plain),
    StatDef("run_limit", "每局最多获得", MANIFESTATION, _plain),
    StatDef("grant_source", "获取来源", MANIFESTATION, _grant_source),
    StatDef("slot", "承载位", MANIFESTATION, _plain),
    StatDef("max_stack", "单格叠放", MANIFESTATION, _plain),
    StatDef("power", "效力", MANIFESTATION, _plain),
    StatDef("projectile_template", "弹体构想", MANIFESTATION, _plain),
    StatDef("penetration", "穿透", MANIFESTATION, _plain),
    StatDef("push", "推动", MANIFESTATION, _plain),
    StatDef("explosion_radius", "爆发范围", MANIFESTATION, _plain),
    # ---- 携带意象（能装进栏位的物品，与「显化物」同字段、单独成类） ----
    StatDef("rarity", "稀有度", CARRIED_IMAGE_CATS, _plain),
    StatDef("category", "显化类别", CARRIED_IMAGE_CATS, _plain),
    StatDef("effect", "作用", CARRIED_IMAGE_CATS, _plain),
    StatDef("effect_detail", "作用说明", CARRIED_IMAGE_CATS, _plain),
    StatDef("min_depth", "最早主梦层", CARRIED_IMAGE_CATS, _plain),
    StatDef("run_limit", "每局最多获得", CARRIED_IMAGE_CATS, _plain),
    StatDef("grant_source", "获取来源", CARRIED_IMAGE_CATS, _grant_source),
    StatDef("slot", "承载位", CARRIED_IMAGE_CATS, _plain),
    StatDef("max_stack", "单格叠放", CARRIED_IMAGE_CATS, _plain),
    StatDef("power", "效力", CARRIED_IMAGE_CATS, _plain),
    StatDef("projectile_template", "弹体构想", CARRIED_IMAGE_CATS, _plain),
    StatDef("penetration", "穿透", CARRIED_IMAGE_CATS, _plain),
    StatDef("push", "推动", CARRIED_IMAGE_CATS, _plain),
    StatDef("explosion_radius", "爆发范围", CARRIED_IMAGE_CATS, _plain),
    StatDef("insight_id", "现实洞察", SITE, _plain),
    StatDef("reward_id", "可能形成", SITE, _item_name),
    StatDef("dissolution_reward", "崩解推进", SITE, _plain),
    # ---- 聚合物（地面 / 墙 / 固体） ----
    StatDef("solid_type", "种类", POLYMER_ONLY, _plain),
    StatDef("floor_effect", "作用说明", POLYMER_ONLY, _floor_effect),
    StatDef("hardness", "硬度", POLYMER_ONLY, _plain),
    StatDef("height", "高度", POLYMER_ONLY, _plain),
    StatDef("thickness", "厚度", POLYMER_ONLY, _plain),
    StatDef("wall_integrity", "完整度", POLYMER_ONLY, _plain),
    StatDef("proximity_effect", "贴近效果", POLYMER_ONLY, _plain),
    StatDef("traits", "特性", POLYMER_ONLY, _trait_list),
    # ---- 液态记忆 ----
    StatDef("liquid_flow", "流动速度", LIQUID_ONLY, _plain),
    StatDef("viscosity", "黏度", LIQUID_ONLY, _plain),
    StatDef("contact_effect", "接触效果", LIQUID_ONLY, _plain),
    StatDef("trigger_amount", "触发浓度", LIQUID_OR_GAS, _plain),
    StatDef("flammable", "易燃", LIQUID_OR_GAS, _plain),
    # ---- 弥散印象 ----
    StatDef("max_diffusion", "扩散速度", GAS_ONLY, _plain),
    StatDef("dissipation", "消散速度", GAS_ONLY, _plain),
    StatDef("opacity", "遮蔽强度", GAS_ONLY, _plain),
    StatDef("inhalation_effect", "吸入效果", GAS_ONLY, _plain),
    # ---- 梦中人（NPC）：数据来自 data/npcs.py 的定义字段 ----
    StatDef("relation", "关系", CatalogCategory.NPC, _plain),
    StatDef("trauma_type", "创伤", CatalogCategory.NPC, _plain),
    StatDef("integrity", "完整度", CatalogCategory.NPC, _plain),
)


def _wall_traits(name: str) -> tuple[str, ...]:
    """墙体/固体的特性摘要（图鉴与详情共用一条口径）。

    返回**逐项**而非拼好的字符串：``_trait_list`` 只对序列逐项取词翻译，
    若在这里就用「、」连成整句，英文包查不到整句、只能原样吐出中文。
    """
    definition = WALL_DEFINITIONS[name]
    traits = []
    if name in CONTAINER_KINDS:
        traits.append("封存内容物")
    if name in WALKABLE_FEATURE_WALLS:
        traits.append("可直接穿行")
    if definition.hand_breakable:
        traits.append("可徒手推倒")
    if definition.transparent:
        traits.append("不遮挡视线")
    return tuple(traits)


def _floor_color(name: str) -> str:
    """聚合地面的图标色：用**面板专用**表（图鉴既能从主页看、也能在游戏内面板看）。

    地图渲染用的是 `AGGREGATE_STYLES`（黑底上刻意压暗的几个色在那没问题），
    而图鉴的文字落在面板上，必须用面板安全的那张表（见 styles.AGGREGATE_PANEL_STYLES）。

    延迟导入 ui.styles：ui 包的 __init__ 会引回 app → menu_pages →
    catalog_registry，顶层导入会在启动时成环。
    """
    from .ui.styles import AGGREGATE_PANEL_STYLES

    return AGGREGATE_PANEL_STYLES.get(name, "white")


def _floor_catalog_entry(name: str) -> CatalogDefinition:
    from .materials.descriptions import material_effect_description
    return CatalogDefinition(
        f"material.floor.{name}",
        CatalogCategory.POLYMER,
        name,
        "floor",
        material_description(name),
        {"solid_type": "地面", **({"floor_effect": name}
                                  if material_effect_description(name) else {})},
        _floor_color(name),
    )


def _wall_catalog_entry(name: str, solid_type: str) -> CatalogDefinition:
    definition = WALL_DEFINITIONS[name]
    stats: dict[str, Any] = {
        "solid_type": solid_type,
        "hardness": definition.hardness,
        "height": definition.height,
        "thickness": definition.thickness,
        "wall_integrity": definition.integrity,
    }
    if definition.proximity_effect:
        stats["proximity_effect"] = definition.proximity_effect
    traits = _wall_traits(name)
    if traits:
        stats["traits"] = traits
    return CatalogDefinition(
        f"material.{solid_type}.{name}",
        CatalogCategory.POLYMER,
        name,
        definition.symbol_key,
        material_description(name),
        stats,
        definition.color,
    )


def _liquid_catalog_entry(name: str) -> CatalogDefinition:
    definition = LIQUID_DEFINITIONS[name]
    stats: dict[str, Any] = {
        "liquid_flow": definition.max_flow,
        "viscosity": definition.viscosity,
        "trigger_amount": material_trigger_amount(name) or "无",
        "contact_effect": definition.contact_effect or "无",
        "flammable": definition.flammable,
    }
    return CatalogDefinition(
        f"material.liquid.{name}",
        CatalogCategory.LIQUID_MEMORY,
        name,
        "liquid.medium",
        material_description(name),
        stats,
        definition.color,
    )


def _gas_trigger_amount(name: str, definition: Any) -> int | None:
    """气体的触发浓度：征兆最低门槛；无征兆的遮蔽类气体按遮蔽强度折算。

    与格子详情面板（panels._cd_trigger_text）保持同一条口径：
    遮蔽强度 = 浓度 × opacity / 100 ≥ SIGHT_OBSCURE_MIN。
    """
    threshold = material_trigger_amount(name)
    if threshold is None and (definition.blocks_sight or definition.sight_attenuation < 1.0):
        threshold = math.ceil(SIGHT_OBSCURE_MIN * 100 / definition.opacity)
    return threshold


def _gas_catalog_entry(name: str) -> CatalogDefinition:
    definition = GAS_DEFINITIONS[name]
    trigger = _gas_trigger_amount(name, definition)
    stats: dict[str, Any] = {
        "max_diffusion": definition.max_diffusion,
        "dissipation": definition.dissipation,
        "opacity": definition.opacity,
        "trigger_amount": trigger if trigger is not None else "无",
        "inhalation_effect": definition.inhalation_effect or "无",
        "flammable": definition.flammable,
    }
    return CatalogDefinition(
        f"material.gas.{name}",
        CatalogCategory.DIFFUSE_IMPRESSION,
        name,
        "gas.mid",
        material_description(name),
        stats,
        definition.color,
    )


def _reaction_icon(recipe) -> str:
    """反应条目图标 = 产物材料在地图上的字形（机制类用「⟲」）。"""
    if recipe.product_type == "气体" and recipe.product in GAS_DEFINITIONS:
        return symbol("gas.mid", "themed")
    if recipe.product_type == "墙体" and recipe.product in WALL_DEFINITIONS:
        return symbol(WALL_DEFINITIONS[recipe.product].symbol_key, "themed")
    if recipe.product_type == "地板" and recipe.product in FLOOR_DEFINITIONS:
        return symbol(FLOOR_DEFINITIONS[recipe.product].symbol_key, "themed")
    if recipe.product_type == "液体":
        return symbol("liquid.medium", "themed")
    return "⟲"


def _reaction_color(recipe) -> str:
    if recipe.product_type == "液体" and recipe.product in LIQUID_DEFINITIONS:
        return LIQUID_DEFINITIONS[recipe.product].color
    if recipe.product_type == "气体" and recipe.product in GAS_DEFINITIONS:
        return GAS_DEFINITIONS[recipe.product].color
    if recipe.product_type == "墙体" and recipe.product in WALL_DEFINITIONS:
        return WALL_DEFINITIONS[recipe.product].color
    return "#9ad1ff"


def build_catalog_definitions() -> dict[str, CatalogDefinition]:
    from .data.anomaly_skills import bindings_for, SKILL_DEFINITIONS
    definitions: dict[str, CatalogDefinition] = {}
    for catalog_id, source in ANOMALY_DEFINITIONS.items():
        stats = dict(source)
        bindings = bindings_for(catalog_id)
        if bindings:
            stats['skill'] = tuple(SKILL_DEFINITIONS[binding.skill_id].name_zh
                                   for binding in bindings)
        definitions[catalog_id] = CatalogDefinition(
            catalog_id,
            CatalogCategory.CONSCIOUSNESS,
            source["name"],
            # 用异象自己的符号（与地图渲染同一把），不再用通用的圆环。
            catalog_id,
            source.get("description", ""),
            stats,
        )
    for definition_id, source in ITEM_DEFINITIONS.items():
        catalog_id = f"item.{definition_id}"
        stats = dict(source)
        effect = source.get("effect")
        if effect:
            # 作用行给可读名称，原始 effect id 只留在游戏数据层。
            stats["effect"] = ITEM_EFFECT_LABELS.get(str(effect), str(effect))
            detail = source.get('effect_description') or ITEM_EFFECT_DETAILS.get(str(effect))
            if detail:
                stats["effect_detail"] = detail
        # 能装进栏位的物品在「显化物」之外单独成类（分类图标 ♕），判据只看 slot；
        # 无槽位的消耗品/易逝物/交互道具仍归「显化物」（图标 ◆）。
        # 条目自身的图标按**栏位**取（✎/♖/⚜︎/⚒︎），与地图/行囊共用同一个
        # symbols.carried_slot_key，不会各处各写一份而走偏。
        equippable = bool(source.get("slot"))
        category = CatalogCategory.CARRIED_IMAGE if equippable else CatalogCategory.MANIFESTATION
        entry_color = source.get("color", "bright_yellow")
        if source.get("rarity"):
            # 稀有度配色：以本类颜色为中心的四档微调（ui.styles.apply_rarity）。
            entry_color = apply_rarity(entry_color, source["rarity"])
        # 图鉴与地图/行囊同源：稀有度之后再取家族图标的稳定变体色。
        entry_color = item_variant_color(definition_id, entry_color)
        definitions[catalog_id] = CatalogDefinition(
            catalog_id,
            category,
            source["name"],
            carried_slot_key(source.get("slot")) if equippable else "manifestation",
            source.get("description", ""),
            stats,
            entry_color,
            # 物品自带的图标（有则取代上面那把通用字形），与地图/行囊同一来源。
            item_icon(definition_id, source),
        )
    for source in EVENT_DEFINITIONS:
        catalog_id = source["catalog_id"]
        definitions[catalog_id] = CatalogDefinition(
            catalog_id,
            CatalogCategory.SITE,
            source["name"],
            catalog_id,
            source.get("description", ""),
            source,
            CatalogCategory.SITE.icon_color,
        )
    # ---- 梦中人（2026-10-11）：稳定意识 NPC（data/npcs.py）----
    # 条目 id 即 NPC_DEFINITIONS 的键（npc.circuit_keeper 形式），与地图实体 id
    # 同一命名空间；解锁判据 = 与该 NPC 交谈过一次（_record_catalog_interaction）。
    for npc_id, source in NPC_DEFINITIONS.items():
        definitions[npc_id] = CatalogDefinition(
            npc_id,
            CatalogCategory.NPC,
            source["name"],
            "npc",
            source.get("description", ""),
            source,
            CatalogCategory.NPC.icon_color,
            # 图标用 NPC 自己的地图字形（⌁/☰/✍…），glyph_for 会补齐两列。
            icon=str(source.get("glyph", "")),
        )
    # ---- 环境物体反应表：配方资料（默认全解锁） ----
    StatDef("reactant_a", "材料甲", CatalogCategory.REACTION, _plain),
    StatDef("reactant_b", "材料乙", CatalogCategory.REACTION, _plain),
    StatDef("product", "产物", CatalogCategory.REACTION, _plain),
    StatDef("product_type", "产物形态", CatalogCategory.REACTION, _plain),
    StatDef("mechanism", "机制", CatalogCategory.REACTION, _plain),
    # ---- 材料三类：聚合物（地面/墙/固体）、液态记忆、弥散印象 ----
    for name in FLOOR_KINDS:
        entry = _floor_catalog_entry(name)
        definitions[entry.catalog_id] = entry
    for name in WALL_DEFINITIONS:
        # 台子（木桌子/石台）与容器是摆在场上的**物件**，图鉴归「固体」而不是
        # 「墙」（2026-09-18）；判据见 materials.walls.SOLID_KINDS。
        solid_type = "固体" if name in SOLID_KINDS else "墙"
        entry = _wall_catalog_entry(name, solid_type)
        definitions[entry.catalog_id] = entry
    for name in LIQUID_DEFINITIONS:
        entry = _liquid_catalog_entry(name)
        definitions[entry.catalog_id] = entry
    for name in GAS_DEFINITIONS:
        entry = _gas_catalog_entry(name)
        definitions[entry.catalog_id] = entry
    # 环境物体反应表（2026-09-19）：一条配方一个条目，图鉴即资料库。
    # 图标/颜色 = 产物材料的地图字形与色（见模块级 _reaction_icon/_reaction_color）。

    for index, recipe in enumerate(REACTIONS):
        # 名称直接写出反应结果：材料甲 + 材料乙 → 产物。
        definitions[f"reaction.{index}"] = CatalogDefinition(
            f"reaction.{index}",
            CatalogCategory.REACTION,
            f"{recipe.reactant_a} + {recipe.reactant_b} → {recipe.product}",
            "site",
            recipe.note,
            {
                "reactant_a": recipe.reactant_a,
                "reactant_b": recipe.reactant_b,
                "product": recipe.product,
                "product_type": recipe.product_type,
                "mechanism": recipe.mechanism,
            },
            _reaction_color(recipe),
            icon=_reaction_icon(recipe),
        )
    return definitions


def _stage_unlocked(category: CatalogCategory, progress: Mapping[str, Any], stage: str) -> bool:
    if category in MATERIAL_CATEGORIES:
        return True  # 材料图鉴不依赖进度：进图鉴即可查全部数值与介绍
    if stage == "resolved":
        return int(progress.get("kills", 0)) > 0 if category is CatalogCategory.CONSCIOUSNESS else int(progress.get("interactions", 0)) > 0
    return int(progress.get("encounters", 0)) > 0 if category is CatalogCategory.CONSCIOUSNESS else int(progress.get("interactions", 0)) > 0


def catalog_stat_rows(
    definition: CatalogDefinition,
    progress: Mapping[str, Any],
    *,
    registry: Iterable[StatDef] = STAT_REGISTRY,
    diagnostics: list[CatalogDiagnostic] | None = None,
) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    for stat in registry:
        values = progress if stat.source == "progress" else definition.stats
        if definition.category not in stat.categories or stat.key not in values:
            continue
        if not _stage_unlocked(definition.category, progress, stat.unlock):
            continue
        try:
            value = stat.fmt(values[stat.key])
        except Exception as error:
            value = "资料异常"
            if diagnostics is not None:
                diagnostics.append(
                    CatalogDiagnostic(definition.catalog_id, stat.key, type(error).__name__)
                )
        rows.append((tr(stat.label), tr(value) if isinstance(value, str) else value))
    return rows

# Portable clinical and literary meanings retain readable codex labels.
from .i18n_realms import REALM_EFFECT_LABELS
ITEM_EFFECT_LABELS.update(REALM_EFFECT_LABELS)
