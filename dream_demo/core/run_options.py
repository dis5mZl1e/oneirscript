"""开局选项：滑条指标、布尔开关、难度评分与落地结算（2026-10-09）。

设计口径（升级文档见 docs/run-options-upgrade-verification.md）：

- **没有固定难度档位**。难度由六项五档滑条 + 十二个开关**加权求和**得出，
  顶部难度条显示数值与区间命名；默认（全居中、开关全关）= 中等。
- 所有修正集中在 ``resolve_mods`` 一个出口，落到 ``GameState.run_mods``
  （纯数值 dict），运行期各系统只读数值、不知道选项存在——与「征兆 /
  装备效果」同一套「数值与机制分离」的架构纪律。
- 默认选择（全居中、无开关）解析出**完全中性**的修正（倍率 1.0 / 加值 0），
  旧存档缺省兼容的基准就是这份中性表。
- 跨局记忆碎片继承已删除（2026-10-09 玩家定稿）：开局改为从全部碎片里
  随机三枚、玩家择一携带；初啼之核专属碎片「first_cry_memory」不进池。
"""

from __future__ import annotations

import random
from typing import Any

from ..data.memory import MEMORY_RARITY

# ---------------------------------------------------------------------------
# 滑条定义（每项 5 档，default=2 即「中」）
# ---------------------------------------------------------------------------
# tiers: (档位名, 难度权重, 效果 dict)。效果键与 resolve_mods 的输出一致。
SLIDER_DEFS: dict[str, dict[str, Any]] = {
    "anomaly": {
        "name": "异象强度",
        "hint": "异象的完整度与造成的创伤",
        "tiers": [
            ("沉寂", -3, {"enemy_integrity": 0.80, "enemy_trauma": 0.80}),
            ("偏弱", -1, {"enemy_integrity": 0.90, "enemy_trauma": 0.90}),
            ("标准", 0, {"enemy_integrity": 1.00, "enemy_trauma": 1.00}),
            ("活跃", 2, {"enemy_integrity": 1.15, "enemy_trauma": 1.15}),
            ("狂暴", 4, {"enemy_integrity": 1.30, "enemy_trauma": 1.30}),
        ],
    },
    "inspiration": {
        "name": "想象灵感",
        "hint": "想象力上限、回流速度、构想效力与成本",
        "tiers": [
            ("枯竭", 4, {"max_imagination": 30, "imagination_regen": -0.5, "ability_cost": 1.20, "ability_power": 0.80}),
            ("稀薄", 2, {"max_imagination": 40, "imagination_regen": -0.25, "ability_cost": 1.10, "ability_power": 0.90}),
            ("常流", 0, {"max_imagination": 50, "imagination_regen": 0, "ability_cost": 1.00, "ability_power": 1.00}),
            ("丰盈", -2, {"max_imagination": 65, "imagination_regen": 0.25, "ability_cost": 0.90, "ability_power": 1.10}),
            ("涌泉", -4, {"max_imagination": 80, "imagination_regen": 0.5, "ability_cost": 0.80, "ability_power": 1.20}),
        ],
    },
    "consciousness": {
        "name": "意识强度",
        "hint": "心智/清醒上限与抗击打能力",
        "tiers": [
            ("脆弱", 4, {"max_mind": 80, "max_lucidity": 80, "resilience": 1.15}),
            ("单薄", 2, {"max_mind": 90, "max_lucidity": 90, "resilience": 1.075}),
            ("稳健", 0, {"max_mind": 100, "max_lucidity": 100, "resilience": 1.0}),
            ("坚韧", -2, {"max_mind": 115, "max_lucidity": 115, "resilience": 0.925}),
            ("不朽", -4, {"max_mind": 130, "max_lucidity": 130, "resilience": 0.85}),
        ],
    },
    "fluency": {
        "name": "思维流畅",
        "hint": "刷新物品时的运气（稀有度权重）",
        "tiers": [
            ("凝滞", 2, {"loot_luck": -2.0}),
            ("涩滞", 1, {"loot_luck": -1.0}),
            ("常态", 0, {"loot_luck": 0.0}),
            ("流畅", -1, {"loot_luck": 1.0}),
            ("泉思", -2, {"loot_luck": 2.0}),
        ],
    },
    "density": {
        "name": "异象密度", "hint": "普通梦层的常规异象数量；机关与首领保持原编排",
        "tiers": [("疏落", -2, {"enemy_density": 0.8}), ("偏疏", -1, {"enemy_density": 0.9}),
                  ("常态", 0, {"enemy_density": 1.0}), ("密集", 1, {"enemy_density": 1.1}),
                  ("簇拥", 2, {"enemy_density": 1.2})],
    },
    "tempo": {
        "name": "构想节律", "hint": "主动构想冷却时间；不缩短施放行动或异象预警",
        "tiers": [("迟缓", 2, {"ability_cooldown": 1.2}), ("偏慢", 1, {"ability_cooldown": 1.1}),
                  ("常态", 0, {"ability_cooldown": 1.0}), ("轻快", -1, {"ability_cooldown": 0.9}),
                  ("灵动", -2, {"ability_cooldown": 0.8})],
    },
}

# 三层信息（未知黑幕/暗色记忆/当前视野）的发布开关（docs 第 1 节第四批）：
# 2026-10-22 玩家反馈默认进入就知道全图、黑暗探索没生效，已切换为默认开启。
# 开局选项仍可手动关闭；旧档保持存档里的原值。
MAP_MEMORY_NEW_GAME_DEFAULT = True

# ---------------------------------------------------------------------------
# 布尔开关（强化 = 负权重降低难度；挑战 = 正权重提高难度）
# ---------------------------------------------------------------------------
TOGGLE_DEFS: dict[str, dict[str, Any]] = {
    "slow_decay": {
        "name": "迟滞崩解", "kind": "boon",
        "desc": "崩解度增速 −25%",
        "weight": -3, "mods": {"dissolution": 0.75},
    },
    "steady_nerves": {
        "name": "坚韧自我", "kind": "boon",
        "desc": "受到异象的创伤再 −15%",
        "weight": -3, "mods": {"resilience": 0.85},
    },
    "clear_conceive": {
        "name": "明晰构想", "kind": "boon",
        "desc": "构想的想象成本再 −20%",
        "weight": -2, "mods": {"ability_cost": 0.80},
    },
    "restless_dream": {
        "name": "躁动之梦", "kind": "challenge",
        "desc": "崩解度增速 +25%",
        "weight": 3, "mods": {"dissolution": 1.25},
    },
    "keen_eyes": {
        "name": "百目紧盯", "kind": "challenge",
        "desc": "异象的视野 +2",
        "weight": 3, "mods": {"alert_bonus": 2},
    },
    "fragile_wake": {
        "name": "浅眠", "kind": "challenge",
        "desc": "心智/清醒上限 −15",
        "weight": 2, "mods": {"max_stat_penalty": 15},
    },
    # 增强项（2026-10-18，docs/261018方案合集.md 第 1 节）：不是难度开关——
    # 权重 0、不产生数值修正；只把「全图地形已知」的开局选择写进 state。
    # 默认关闭；开启后仅授予当前层地形类型，不公开视野外生物/物品/环境读数，
    # 也不写入普通探索快照（见 core/vision/knowledge.py）。
    "full_terrain": {
        "name": "全图地形", "kind": "enhance",
        "desc": "整层地形布局与类型已知（仅地形，不含生物、物品与环境细读）",
        "hint": "开启后可按当前层地形规划路线；不授予攻击或交互资格，不伪造普通探索进度。",
        "weight": 0, "mods": {},
    },
    # 三层信息显示（docs 第 1 节）：未知黑幕 + 暗色记忆 + 当前视野。
    # 2026-10-22 起默认开启（见 MAP_MEMORY_NEW_GAME_DEFAULT）；选项本身不改变难度。
    "map_memory": {
        "name": "三层信息", "kind": "enhance",
        "desc": "未探索区域显示黑幕，已探索区域保留暗色地形记忆，当前视野保持完整。",
        "hint": "不改世界规则与难度；只改变地图与格子详情显示的信息权限，可随存档保存。",
        "weight": 0, "mods": {},
    },
}

TOGGLE_DEFS.update({
    "wide_memory": {"name": "宽阔记忆", "kind": "boon", "desc": "记忆碎片容量 +1", "weight": -2,
                    "mods": {"memory_slots": 1}, "group": "memory"},
    "sealed_memory": {"name": "封存记忆", "kind": "challenge", "desc": "记忆碎片容量 −1", "weight": 2,
                      "mods": {"memory_slots": -1}, "group": "memory"},
    "rich_conceive": {"name": "余响构想", "kind": "boon", "desc": "构想效力再 +15%", "weight": -2,
                      "mods": {"ability_power": 1.15}, "group": "power"},
    "faint_conceive": {"name": "淡薄构想", "kind": "challenge", "desc": "构想效力再 −15%", "weight": 2,
                       "mods": {"ability_power": 0.85}, "group": "power"},
    "drowsy_anomalies": {"name": "迟滞异象", "kind": "boon", "desc": "异象主动技能冷却 +15%", "weight": -2,
                        "mods": {"enemy_skill_cooldown": 1.15}, "group": "enemy_tempo"},
    "swift_anomalies": {"name": "躁急异象", "kind": "challenge", "desc": "异象主动技能冷却 −15%；预警不变", "weight": 2,
                       "mods": {"enemy_skill_cooldown": 0.85}, "group": "enemy_tempo"},
})
TOGGLE_DEFS['slow_decay']['group'] = TOGGLE_DEFS['restless_dream']['group'] = 'decay'

DEFAULT_SLIDER_INDEX = 2

# 中性修正：默认选择解析结果，也是旧档缺省兼容的基准。
NEUTRAL_MODS: dict[str, Any] = {
    "enemy_integrity": 1.0,
    "enemy_trauma": 1.0,
    "max_mind": 100,
    "max_lucidity": 100,
    "max_imagination": 50,
    "resilience": 1.0,
    "imagination_regen": 0,
    "ability_cost": 1.0,
    "loot_luck": 0.0,
    "dissolution": 1.0,
    "alert_bonus": 0,
    "enemy_density": 1.0,
    "ability_power": 1.0,
    "ability_cooldown": 1.0,
    "enemy_skill_cooldown": 1.0,
    "memory_slots": 0,
}

# 难度区间命名（score < 下限 即落入该区间，按分数升序）：
# ≤-9 轻松 / -8~-3 偏轻 / -2~3 中等 / 4~9 偏重 / 10~15 沉重 / ≥16 噩梦。
DIFFICULTY_BANDS: tuple[tuple[int, str], ...] = (
    (-8, "轻松"),
    (-2, "偏轻"),
    (4, "中等"),
    (10, "偏重"),
    (16, "沉重"),
    (10**9, "噩梦"),
)

# 开局碎片候选池：初啼之核专属不进池（终局奖励的唯一性保留）。
STARTING_MEMORY_EXCLUDE = ("first_cry_memory",)


def default_selection() -> dict[str, Any]:
    """默认开局选项：全部居中、开关全关（= 中等难度）。

    三层信息由 MAP_MEMORY_NEW_GAME_DEFAULT 预选（2026-10-22 起默认开启）；
    未探索区域保持黑幕，已探索区域显示暗色记忆，当前视野完整。
    """
    return {
        "sliders": {key: DEFAULT_SLIDER_INDEX for key in SLIDER_DEFS},
        "toggles": ["map_memory"] if MAP_MEMORY_NEW_GAME_DEFAULT else [],
    }


def normalize_selection(selection: dict | None) -> dict[str, Any]:
    """把任意来源（存档/界面状态）的选项规整成合法形状。

    未知键丢弃、滑条越界钳制、开关去重——读档时旧数据或手改存档都不会炸。
    """
    if not isinstance(selection, dict):
        return default_selection()
    sliders = selection.get("sliders")
    if not isinstance(sliders, dict):
        sliders = {}
    clean_sliders = {}
    for key, spec in SLIDER_DEFS.items():
        try:
            index = int(sliders.get(key, DEFAULT_SLIDER_INDEX))
        except (TypeError, ValueError, OverflowError):
            index = DEFAULT_SLIDER_INDEX
        clean_sliders[key] = max(0, min(len(spec["tiers"]) - 1, index))
    raw_toggles = selection.get("toggles")
    toggles = [
        key for key in (raw_toggles if isinstance(raw_toggles, (list, tuple)) else [])
        if isinstance(key, str) and key in TOGGLE_DEFS
    ]
    accepted = []
    for key in toggles:
        group = TOGGLE_DEFS[key].get('group')
        if group:
            accepted = [other for other in accepted if TOGGLE_DEFS[other].get('group') != group]
        if key not in accepted:
            accepted.append(key)
    return {"sliders": clean_sliders, "toggles": sorted(accepted)}


def difficulty_score(selection: dict | None) -> int:
    """难度分 = Σ 滑条档位权重 + Σ 开关权重。默认选择 = 0。"""
    selection = normalize_selection(selection)
    total = 0
    for key, index in selection["sliders"].items():
        total += int(SLIDER_DEFS[key]["tiers"][index][1])
    for key in selection["toggles"]:
        total += int(TOGGLE_DEFS[key]["weight"])
    return total


def option_rows():
    return ([('slider', key) for key in SLIDER_DEFS]
            + [('toggle', key) for kind in ('boon', 'challenge', 'enhance')
               for key, spec in TOGGLE_DEFS.items() if spec['kind'] == kind]
            + [('confirm', None)])


def difficulty_bounds():
    return (sum(min(t[1] for t in spec['tiers']) for spec in SLIDER_DEFS.values())
            + sum(min(0, spec['weight']) for spec in TOGGLE_DEFS.values()),
            sum(max(t[1] for t in spec['tiers']) for spec in SLIDER_DEFS.values())
            + sum(max(0, spec['weight']) for spec in TOGGLE_DEFS.values()))


def difficulty_band(score: int) -> str:
    """难度区间命名：取第一个「下限 ≤ score」的区间。"""
    for low, name in DIFFICULTY_BANDS:
        if score < low:
            return name
    return DIFFICULTY_BANDS[-1][1]


def resolve_mods(selection: dict | None) -> dict[str, Any]:
    """把选项解析成纯数值修正表（run_mods）。唯一出口。"""
    selection = normalize_selection(selection)
    mods: dict[str, Any] = dict(NEUTRAL_MODS)
    for key, index in selection["sliders"].items():
        effect = SLIDER_DEFS[key]["tiers"][index][2]
        for mod_key, value in effect.items():
            mods[mod_key] = value
    penalty = 0
    for key in selection["toggles"]:
        for mod_key, value in TOGGLE_DEFS[key]["mods"].items():
            if mod_key == "max_stat_penalty":
                penalty += int(value)
                continue
            if mod_key in ("enemy_integrity", "enemy_trauma", "resilience", "ability_cost", "dissolution",
                           "ability_power", "enemy_skill_cooldown", "ability_cooldown"):
                # 乘区开关：与滑条倍率相乘（叠乘不叠加）。
                mods[mod_key] = float(mods[mod_key]) * float(value)
            else:
                mods[mod_key] = value
    if penalty:
        mods["max_mind"] = max(10, int(mods["max_mind"]) - penalty)
        mods["max_lucidity"] = max(10, int(mods["max_lucidity"]) - penalty)
    return mods


def apply_run_options(state, selection: dict | None) -> None:
    """把开局选项落到 GameState：存档原始选择 + 解析修正 + 上限类即时生效。

    上限调低时当前值同步钳制（不额外扣血式惩罚）；调高不回填（与记忆碎片
    「上限提升立即回填」区分开——开局选项不是奖励，是起点设定）。
    """
    selection = normalize_selection(selection)
    mods = resolve_mods(selection)
    state.run_options = selection
    state.run_mods = mods
    # 信息权限开关（不是数值修正）：只写 state 字段，不进 run_mods。
    state.terrain_known = 'full_terrain' in selection['toggles']
    state.map_memory_enabled = 'map_memory' in selection['toggles']
    from .settlement import REASON_MAX_CHANGE, apply_max_change
    apply_max_change(state, "mind", int(mods["max_mind"]),
                     reason=REASON_MAX_CHANGE, source="开局调律")
    apply_max_change(state, "lucidity", int(mods["max_lucidity"]),
                     reason=REASON_MAX_CHANGE, source="开局调律")
    apply_max_change(state, "imagination", int(mods["max_imagination"]),
                     reason=REASON_MAX_CHANGE, source="开局调律")
    state.imagination_regen_credit = 0.0


def roll_starting_memories(rng: random.Random, count: int = 3) -> list[str]:
    """开局碎片候选：从全部碎片（除终局专属）里随机 count 枚不重复。"""
    pool = [key for key in MEMORY_RARITY if key not in STARTING_MEMORY_EXCLUDE]
    count = max(1, min(count, len(pool)))
    return rng.sample(pool, count)


class RunOptionsMixin:
    """run_mods 读取入口（各系统只读数值，不知道选项存在）。

    全部 ``getattr(self, "run_mods", None)`` 防御：旧档经 persistence 补默认
    后必有 dict，但直接 ``GameState(...)`` 构造的测试对象可能没有——缺省按
    中性处理，保证「没设过选项 = 旧行为」这条不变式处处成立。
    """

    def _run_mod(self, key: str, default: Any) -> Any:
        mods = getattr(self, "run_mods", None)
        if not isinstance(mods, dict):
            return default
        return mods.get(key, default)

    def _enemy_integrity_mult(self) -> float:
        return float(self._run_mod("enemy_integrity", 1.0))

    def _enemy_trauma_mult(self) -> float:
        return float(self._run_mod("enemy_trauma", 1.0))

    def _player_resilience(self) -> float:
        return float(self._run_mod("resilience", 1.0))

    def _ability_cost_mult(self) -> float:
        return float(self._run_mod("ability_cost", 1.0)) * self._dream_aptitude_mult('conceive')

    def _dream_aptitude_mult(self, axis: str) -> float:
        """Saved birth contributions; absent fields keep old saves neutral."""
        return float(self.dream_type_mods.get(axis, 1.0))

    def _dream_action_time(self, base: float, axis: str) -> float:
        return base * self._dream_aptitude_mult(axis)

    def _loot_luck(self) -> float:
        return float(self._run_mod("loot_luck", 0.0))

    def _dissolution_mult(self) -> float:
        return float(self._run_mod("dissolution", 1.0))

    def _alert_bonus(self) -> int:
        return int(self._run_mod("alert_bonus", 0))

    def _imagination_regen_bonus(self) -> float:
        return float(self._run_mod("imagination_regen", 0))

    def _scaled_ability_power(self, value: int) -> int:
        return max(1, int(value * float(self._run_mod('ability_power', 1.0)) + 0.5)) if value > 0 else 0

    def _scaled_ability_cooldown(self, value: int) -> int:
        if value <= 0:
            return 0
        scaled = int(value * float(self._run_mod('ability_cooldown', 1.0)) + 0.5)
        # 思维润滑（扩展包 v2）：所有构想冷却 -1（最低 1）。
        if self.insight_active("思维润滑"):
            scaled = max(1, scaled - 1)
        return max(1, scaled)

    def _ordinary_anomaly_count(self, value: int) -> int:
        return max(0, int(value * float(self._run_mod('enemy_density', 1.0)) + 0.5))

    def _memory_slot_bonus(self) -> int:
        return int(self._run_mod("memory_slots", 0))

    # ---- 结算辅助 ----

    def _suffer_lucidity(self, amount: int, *, source_id: str = '') -> None:
        """异象造成的清醒创伤统一入口（与 _lose_mind 的 combat 口径对称）。

        旧代码 `self.lucidity = max(0, self.lucidity - n)` 散落在各战斗结算点，
        这里收成一条：先过「意识强度」韧性倍率，再扣。环境消耗（液体/材料）
        不走这里，保持原样——意识强度只对抗异象创伤。
        """
        if amount > 0:
            factor = self._player_resilience()
            if factor != 1.0:
                amount = max(0, int(amount * factor + 0.5))
        from .settlement import REASON_COMBAT, record_settled_value
        requested = float(amount)
        amount = self._consume_hospital_buffer(amount, 'lucidity')
        tier_before = self.lucidity_tier
        before = self.lucidity
        if amount <= 0:
            record_settled_value(
                self, 'lucidity', requested=requested, before=before, after=before,
                reason=REASON_COMBAT, source=source_id, blocked='buffered',
            )
            return
        from .settlement import write_resource
        write_resource(self, 'lucidity', max(0, before - amount))
        record_settled_value(
            self, 'lucidity', requested=requested, before=before, after=self.lucidity,
            reason=REASON_COMBAT, source=source_id,
        )
        self._note_board_hurt('lucidity', before-self.lucidity, source_id=source_id)
        # 2026-10-15 混乱化改造：跌档横幅——想象越低，环境越失控，看得见。
        if before - self.lucidity > 0:
            self._announce_tier_drop("lucidity", tier_before)

    def _scaled_ability_cost(self, cost: int) -> int:
        """构想想象成本经「想象灵感/明晰构想」倍率折算后的实付值。"""
        if cost <= 0:
            return 0
        return max(1, int(cost * self._ability_cost_mult() + 0.5))
