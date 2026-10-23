# -*- coding: utf-8 -*-
"""地图侧语句篡改（docs §15）：目标收集、句子生成、效果执行与提交。

句子 = 固定模板 + 名称槽（规格 §3.1：不在运行时猜测中文含义——字词 →
效果是写死的映射表，运行时只填空）。句子是界面态不入存档；持久的是
效果（警觉、完整度、死亡、征兆），全部走既有系统。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..data.ids import stable_seed
from ..data.tamper_schema import RiskOutcome, TamperRequest, TamperTarget
from ..data.tamper_world import (
    BRITTLE_WALLS,
    CATEGORY_LABELS,
    CONDITION_DEFS,
    CONDITION_ORDER,
    DEGREE_IDS,
    DEGREE_VARIANTS,
    DELETE_ANOMALY_CHAOS_EXTRA,
    DELETE_ANOMALY_IMAGINATION_EXTRA_DIVISOR,
    DELETE_WALL_CHAOS_EXTRA,
    DELETE_WALL_IMAGINATION_EXTRA_DIVISOR,
    FIBER_WALLS,
    GAS_SETTLE_LIQUIDS,
    MAX_DELETES_PER_LAYER,
    PLANT_GROWTH,
    SENTENCE_TEMPLATES,
    SENTENCE_TEMPLATES_EN,
    SLOT_CATEGORY_COLORS,
    SOLIDIFY_WALLS,
    WITHER_FUEL,
    WORD_DEFS,
    WORD_ORDER,
)
from ..i18n import tr
from ..materials import gas_def, liquid_def, portent_def
from ..materials.walls import WALKABLE_FEATURE_WALLS, wall_def
from . import tamper_pipeline as pipeline
from .chaos import chaos_risk_tier, clamp_chaos
from .entities import ActionResult


@dataclass
class WorldSlot:
    """一个可操作名称槽：类别 + 显示名 + 目标引用。"""

    category: str  # anomaly / terrain / object / liquid / gas / ground
    label: str  # 已翻译名称（含颜色码的渲染由 UI 层处理）
    enemy: Any = None  # 异象主体（category=anomaly 时非空）
    x: int = -1
    y: int = -1
    # 第二批指代（docs §8.4）：打开草稿时固定的方位、距离与显示引用；
    # 身份仍由 enemy 引用/坐标决定，显示文本不参与查找。
    direction: str = ""
    reference: str = ""
    number: int = 0
    distance: int = 0
    # 第三批：液气区域（空元组 = 普通单格槽）。标签不含每格数量，
    # 格数/存量走范围提示与详情；身份是物态+材料+排序成员集合。
    region_members: tuple[tuple[int, int], ...] = ()
    region_amount: float = 0.0
    region_clipped: bool = False
    region_kind: str = ""

    def display_name(self) -> str:
        return self.reference or self.label

    @property
    def color(self) -> str:
        return SLOT_CATEGORY_COLORS.get(self.category, "#c8c8d0")


@dataclass
class WorldSentence:
    """一次面板打开时生成的完整句子（同一回合内稳定）。"""

    text: str
    slots: list[WorldSlot]
    word_ids: tuple[str, ...] = WORD_ORDER
    context: tuple = ()
    signatures: tuple = ()
    consumed: bool = False
    result_message: str = ''
    # 视野里还能命名、但没被写进这一句的处数（§15 第三批）。句子只点名 4 处，
    # 多出来的不能当作不存在——面板要如实说明，玩家才知道该不该换目标。
    overflow: int = 0


# ---- 目标收集（docs §15.4 收集口径）----

def _named_cell(state: Any, x: int, y: int, *, include_ground: bool = False) -> WorldSlot | None:
    """把一个格子解析成可命名槽；无可命名对象返回 None。"""
    if not (0 <= x < state.width and 0 <= y < state.height):
        return None
    cell = state.cell(x, y)
    if cell.solid and cell.wall_kind:
        if state._protected_wall(cell.wall_kind):
            return None
        name = tr(wall_def(cell.wall_kind).name)
        return WorldSlot("terrain", name, x=x, y=y)
    if cell.liquid > 0 and cell.liquid_kind:
        from .tamper_regions import region_at, region_range_text, region_reference
        region = region_at(state, x, y, "liquid")
        if region is not None:
            name = tr(liquid_def(region.material).name)
            reference = region_reference(state, region, name)
            slot = WorldSlot("liquid", reference, x=x, y=y, reference=reference)
            slot.region_members = region.members
            slot.region_amount = region.amount
            slot.region_clipped = region.clipped
            slot.region_kind = "liquid"
            return slot
        return WorldSlot("liquid", tr(liquid_def(cell.liquid_kind).name), x=x, y=y)
    if cell.gas > 0 and cell.gas_kind:
        from .tamper_regions import region_at, region_reference
        region = region_at(state, x, y, "gas")
        if region is not None:
            name = tr(gas_def(region.material).name)
            reference = region_reference(state, region, name)
            slot = WorldSlot("gas", reference, x=x, y=y, reference=reference)
            slot.region_members = region.members
            slot.region_amount = region.amount
            slot.region_clipped = region.clipped
            slot.region_kind = "gas"
            return slot
        return WorldSlot("gas", tr(gas_def(cell.gas_kind).name), x=x, y=y)
    if cell.plant:
        from ..materials.plants import plant_def_for
        return WorldSlot("terrain", tr(plant_def_for(cell.plant).name), x=x, y=y)
    for entry in state.world_items:
        if (entry.x, entry.y) == (x, y):
            return WorldSlot("object", tr(entry.item.name), x=x, y=y)
    if cell.wall_kind in WALKABLE_FEATURE_WALLS:
        # 云块／枕木在数据上是墙种但可穿行（solid=False），此前被当成普通地面，
        # 导致「浸透枕木」只能直接造槽测试、真实面板刷不到。它们有真实材质交互
        # （枕木吸声吸液、云块挡液），因此作为地形进入名称槽（docs §七）。
        return WorldSlot("terrain", tr(wall_def(cell.wall_kind).name), x=x, y=y)
    if include_ground and not cell.solid:
        return WorldSlot('ground',tr('地面（{x},{y}）',x=x,y=y),x=x,y=y)
    return None


def collect_sentence(state: Any, *, pinned: tuple[int, int] | None = None,
                     hover: tuple[int, int] | None = None,
                     facing: tuple[int,int] | None = None) -> WorldSentence | None:
    """收集目标并组装一句话；视野内既无异象也无可命名地形时返回 None。

    主语优先级：锁定格 > 悬停格 > 视野内最近的异象（docs §15.4）。
    环境字段优先保留明确悬停的另一目标，再补相邻格与朝向前方 1—4 格（最多 3 个）。
    """
    subject: WorldSlot | None = None
    for point in (pinned, hover):
        if point is None:
            continue
        cx, cy = point
        enemy = _enemy_at(state, cx, cy)
        if enemy is not None and state.is_visible(cx, cy):
            subject = WorldSlot("anomaly", tr(enemy.label), enemy=enemy, x=cx, y=cy)
            break
        slot = _named_cell(state, cx, cy,include_ground=True)
        if slot is not None and state.is_visible(cx, cy):
            subject = slot
            break
    if subject is None:
        nearest = _nearest_visible_anomaly(state)
        if nearest is not None:
            subject = WorldSlot("anomaly", tr(nearest.label), enemy=nearest,
                                x=nearest.x, y=nearest.y)
    fields: list[WorldSlot] = []
    overflow = 0
    seen: set[tuple[int, int]] = set()
    if subject is not None:
        seen.add((subject.x, subject.y))
        candidates: list[tuple[int, int]] = [
            (subject.x + dx, subject.y + dy)
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))
        ]
    else:
        candidates = []
    if hover is not None and hover not in seen:
        candidates.insert(0,hover)
    facing = facing if facing is not None else getattr(state, "facing", (0, 1))
    px, py = state.player.x, state.player.y
    for step in range(1, 5):
        candidates.append((px + facing[0] * step, py + facing[1] * step))
    for cx, cy in candidates:
        if (cx, cy) in seen:
            continue
        seen.add((cx, cy))
        # 多对象场景句（docs §8.2/§8.4）：主语是异象时，相邻/朝向内的其他可见
        # 异象也可以作为「句中提到的对象」，但它们不是提交对象——提交仍用
        # slot_index 指向明确槽位，绝不按显示文本推测。
        enemy = _enemy_at(state, cx, cy)
        candidate: WorldSlot | None = None
        if (subject is not None and subject.category == 'anomaly'
                and enemy is not None and state.is_visible(cx, cy)):
            candidate = WorldSlot("anomaly", tr(enemy.label), enemy=enemy, x=cx, y=cy)
        else:
            named = _named_cell(state, cx, cy, include_ground=(cx, cy) == hover)
            if named is not None and state.is_visible(cx, cy):
                # 去重按对象身份（坐标），不能按显示名：两处同名墙/同种液体是不同
                # 对象，合并会让提交对象与句面不一致（docs §8.2/§8.4）。
                candidate = named
        if candidate is None:
            continue
        if len(fields) < 3:
            fields.append(candidate)
        else:
            # 句子只点名「主语 + 3 个字段」，多出来的却仍然能在眼前看见。
            # 静默丢掉会让玩家以为视野里只有这四处（§15 第三批）。
            overflow += 1
    if subject is None and not fields:
        return None
    return build_sentence(state, subject, fields, overflow=overflow)


def nearest_sentence(state: Any, radius: int = 6) -> WorldSentence | None:
    """视野内最近的可改写目标；用作 C 键的兜底入口。

    正常句子收集仍只认锁定格/悬停格/最近异象；当眼前正对空地、没有任何
    可命名目标时，C 键不应无声失败——在可见范围内找最近一个至少有一个
    合法字词的目标，生成同一套句子。
    """
    px, py = state.player.x, state.player.y
    candidates: list[tuple[int, int, int]] = []
    for y in range(max(0, py - radius), min(state.height, py + radius + 1)):
        for x in range(max(0, px - radius), min(state.width, px + radius + 1)):
            if (x, y) == (px, py) or not state.is_visible(x, y):
                continue
            candidates.append((abs(x - px) + abs(y - py), x, y))
    candidates.sort()
    for _distance, x, y in candidates:
        enemy = _enemy_at(state, x, y)
        if enemy is not None:
            slot = WorldSlot("anomaly", tr(enemy.label), enemy=enemy, x=x, y=y)
        else:
            slot = _named_cell(state, x, y)
        if slot is None:
            continue
        sentence = build_sentence(state, slot, [])
        if sentence is not None and sentence_word_ids(sentence, state):
            return sentence
    return None


def _enemy_at(state: Any, x: int, y: int) -> Any | None:
    for enemy in state.enemies:
        if enemy.integrity > 0 and enemy.relation == "失控意识" and (enemy.x, enemy.y) == (x, y):
            return enemy
    return None


def _nearest_visible_anomaly(state: Any) -> Any | None:
    px, py = state.player.x, state.player.y
    best, best_distance = None, None
    for enemy in state.enemies:
        if enemy.integrity <= 0 or enemy.relation != "失控意识":
            continue
        if not state.is_visible(enemy.x, enemy.y):
            continue
        distance = abs(enemy.x - px) + abs(enemy.y - py)
        if best_distance is None or distance < best_distance:
            best, best_distance = enemy, distance
    return best


# ---- 句子生成（同一回合稳定，docs §15.4 稳定性）----

def build_sentence(state: Any, subject: WorldSlot | None,
                   fields: list[WorldSlot], *, overflow: int = 0) -> WorldSentence | None:
    slots: list[WorldSlot] = []
    if subject is not None:
        slots.append(subject)
    slots.extend(fields)
    if not slots:
        return None
    from .tamper_compass import enrich_slots
    enrich_slots(state, slots[:4])
    if subject is not None and subject.category == "anomaly":
        bucket = "anomaly_terrain" if fields else "anomaly_only"
    else:
        bucket = "env_only"
    identity = "|".join(
        f"{slot.category}:{slot.label}:{slot.x},{slot.y}" for slot in slots
    )
    pick = stable_seed("world-tamper", state.seed, state.depth, state.time, identity)
    from .tamper_views import language_of
    templates = SENTENCE_TEMPLATES_EN if language_of() == 'en' else SENTENCE_TEMPLATES
    pool = [t for t in templates if t[0] == bucket and len(t[2]) == min(4,len(slots))]
    _bucket, text, _slot_kinds = pool[pick % len(pool)]
    # 槽顺序与模板一致：主语槽填 n0，环境字段依次填 n1、n2…
    filled = text
    for index, slot in enumerate(slots[:4]):
        filled = filled.replace(f"〔n{index}〕", slot.display_name())
    selected = slots[:4]
    return WorldSentence(filled, selected, context=_context(state),
                         signatures=tuple(_signature(state, slot) for slot in selected),
                         overflow=max(0, int(overflow)))


def _context(state: Any) -> tuple:
    return state.seed, state.layer_key(), state.time, state.paid_action_seq


def _signature(state: Any, slot: WorldSlot) -> tuple:
    if slot.region_members:
        # 区域身份与成员存量一起进入签名：成员增减、扩散/相变/被搬走都会
        # 让旧草稿失效，提交前不会静默换到另一片同名材料。
        cells = []
        for mx, my in slot.region_members:
            cell = state.cell(mx, my)
            if slot.region_kind == 'liquid':
                cells.append((mx, my, str(cell.liquid_kind or ''), cell.liquid))
            else:
                cells.append((mx, my, str(cell.gas_kind or ''), cell.gas))
        return (slot.region_kind, slot.region_members, tuple(cells))
    if slot.category == 'anomaly':
        enemy = slot.enemy
        return (id(enemy), enemy.x, enemy.y, enemy.integrity, enemy.relation,
                enemy.anomaly_kind, enemy.alert_state)
    cell = state.cell(slot.x, slot.y)
    items = tuple(id(entry) for entry in state.world_items
                  if (entry.x, entry.y) == (slot.x, slot.y))
    return (cell.solid, cell.wall_kind, cell.integrity, cell.hardness, cell.plant,
            cell.floor, cell.aggregate_variant, cell.elevation, cell.light_radius, cell.light_on,
            cell.liquid_kind, cell.liquid, cell.gas_kind, cell.gas, items)


def _preview_current(state: Any, sentence: WorldSentence, slot_index: int) -> bool:
    if sentence.context != _context(state) or len(sentence.signatures) != len(sentence.slots):
        return False
    for index,slot in enumerate(sentence.slots):
        if not (0 <= slot.x < state.width and 0 <= slot.y < state.height):
            return False
        if not state.is_visible(slot.x, slot.y):
            return False
        if slot.region_members:
            from .tamper_regions import region_at
            region = region_at(state, slot.x, slot.y, slot.region_kind)
            if region is None or region.members != slot.region_members:
                return False
        if slot.category == 'anomaly':
            if not any(enemy is slot.enemy for enemy in state.enemies):
                return False
            if slot.enemy.integrity <= 0 or slot.enemy.relation != '失控意识':
                return False
        if sentence.signatures[index] != _signature(state,slot):
            return False
    return True


# ---- 字词合法性与效果 ----

def word_ids() -> tuple[str, ...]:
    return WORD_ORDER


def sentence_word_ids(sentence: WorldSentence,
                      state: Any | None = None) -> tuple[str, ...]:
    """句子当前可用的字词；给了 ``state`` 时同时按目标材质过滤（材料专属字词）。"""
    def usable(word: str, slot: WorldSlot) -> bool:
        if state is not None:
            return word_available(state, word, slot, sentence)
        return word_allowed(word, slot, sentence)

    return tuple(word for word in WORD_ORDER
                 if any(usable(word, slot) for slot in sentence.slots))


def word_available(state: Any, word_id: str, slot: WorldSlot,
                   sentence: WorldSentence | None = None) -> bool:
    """字词在**当前目标材质**上是否进入可选列表（docs §六：非纤维不显示浸透）。

    保护矩阵不在这里过滤：受保护对象仍要显示成灰项并给出原因（docs §二），
    因此材料不满足才从列表里隐去，保护只由 :func:`word_blocked_reason` 置灰。
    """
    if not word_allowed(word_id, slot, sentence):
        return False
    if word_id == 'ignite':
        return not _ignite_requirement_reason(state, slot)
    if word_id == 'soak':
        return not _soak_requirement_reason(state, slot)
    if word_id == 'brittle':
        return not _brittle_requirement_reason(state, slot)
    if word_id in ('spill', 'scatter'):
        return not _spread_requirement_reason(state, slot, word_id)
    if word_id == 'uproot':
        return not _uproot_requirement_reason(state, slot)
    if word_id in ('gather_liquid', 'gather_gas'):
        return not _gather_requirement_reason(state, slot, word_id)
    if word_id == 'grow':
        return not _grow_requirement_reason(state, slot)
    if word_id == 'wither':
        return not _wither_requirement_reason(state, slot)
    if word_id == 'evaporate':
        return not _evaporate_requirement_reason(state, slot)
    if word_id == 'solidify':
        return not _solidify_requirement_reason(state, slot)
    if word_id == 'settle':
        return not _settle_requirement_reason(state, slot)
    return True


def degree_options(word_id: str) -> tuple[str | None, ...]:
    variants = DEGREE_VARIANTS.get(word_id, {})
    return (*(('gently',) if 'gently' in variants else ()), None,
            *(('forcefully',) if 'forcefully' in variants else ()))


def resolved_word_id(word_id: str, combo: tuple[str, ...] = ()) -> str:
    variants = DEGREE_VARIANTS.get(word_id, {})
    return next((variants[degree] for degree in DEGREE_IDS
                 if degree in combo and degree in variants), word_id)


def _word_effect_amount(word_id: str,
                        condition_ids: tuple[str, ...] | str | None = None) -> int:
    """字词的实际数值（伤害／时长／份数），条件组合在这里改变真实结算。"""
    if isinstance(condition_ids, str):
        condition_ids = (condition_ids,)
    combo = tuple(condition_ids or ())
    definition = WORD_DEFS[resolved_word_id(word_id, combo)]
    verb = definition.get('verb', word_id)
    if verb == 'break':
        amount = int(definition.get('damage', 40))
    elif verb == 'dispel':
        amount = int(definition.get('duration', 10))
    else:
        amount = int(definition.get('fraction', 40))
    if 'exploit_crack' in combo and verb == 'break':
        amount = amount * 3 // 2
    elif 'catch_unaware' in combo and verb == 'dispel':
        amount = amount * 2
    return amount


def insertion_preview(sentence: WorldSentence, word_id: str, slot_index: int,
                      condition_id: str | None = None, *,
                      condition_ids: tuple[str, ...] | None = None,
                      state: Any | None = None) -> tuple[str, str, str]:
    """插入点、改后完整句、合并后的效果说明；不写状态（docs §15.7 预览要求）。

    ``condition_id``（单项，旧入口）与 ``condition_ids``（组合）都接受；
    ``state`` 只用于需要读真实格子的字词（如脆裂按当前完整度算一半）。
    """
    slot = sentence.slots[slot_index]
    definition = WORD_DEFS[word_id]
    verb = definition.get('verb', word_id)
    combo = _normalize_conditions(condition_id, condition_ids)
    if combo and not condition_combo_allowed(combo, word_id, slot, sentence):
        combo = ()
    definition = WORD_DEFS[resolved_word_id(word_id, combo)]
    amount = _word_effect_amount(word_id, combo)
    if verb == 'lure_to':
        actor = next(s for s in sentence.slots if s.category == 'anomaly')
        point = tr('去向')
        replacement = tr('〔{actor}〕将前往〔{destination}〕调查。',
                         actor=actor.display_name(), destination=slot.display_name())
        effect = tr(definition['note'])
    elif verb == 'echo_here':
        point = tr('声源')
        replacement = tr('〔{name}〕将响起声音，引来附近的注意。', name=slot.display_name())
        effect = tr(definition['note'])
    elif verb == 'ignite':
        point = tr('燃点')
        replacement = tr('〔{name}〕将被点燃', name=slot.display_name())
        effect = tr(definition['note'])
    elif verb == 'soak':
        point = tr('湿度')
        replacement = tr('〔{name}〕将被水浸透', name=slot.display_name())
        effect = tr(definition['note'])
    elif verb == 'brittle':
        point = tr('结构')
        if state is not None:
            replacement = tr('〔{name}〕将沿着裂纹碎开（失去 {n} 点完整度）',
                             name=slot.display_name(), n=_brittle_damage(state, slot))
        else:
            replacement = tr('〔{name}〕将沿着裂纹碎开', name=slot.display_name())
        effect = tr(definition['note'])
    elif verb == 'spread':
        point = tr('流向') if word_id == 'spill' else tr('气流')
        replacement = tr('〔{name}〕将向相邻格散开一半', name=slot.display_name())
        effect = tr(definition['note'])
    elif verb == 'uproot':
        point = tr('根须')
        replacement = tr('〔{name}〕将被连根拔起', name=slot.display_name())
        effect = tr(definition['note'])
    elif verb == 'gather':
        point = tr('流向') if word_id == 'gather_liquid' else tr('气流')
        replacement = tr('〔{name}〕将把相邻的流体收拢过来', name=slot.display_name())
        effect = tr(definition['note'])
    elif verb == 'grow':
        point = tr('长势')
        replacement = tr('〔{name}〕将长高成丛', name=slot.display_name())
        effect = tr(definition['note'])
    elif verb == 'wither':
        point = tr('干枯')
        replacement = tr('〔{name}〕将提前干枯', name=slot.display_name())
        effect = tr(definition['note'])
    elif verb == 'evaporate':
        point = tr('形态')
        replacement = tr('〔{name}〕将按自己的蒸发产物化气', name=slot.display_name())
        effect = tr(definition['note'])
    elif verb == 'solidify':
        point = tr('形态')
        replacement = tr('〔{name}〕将凝成一堵新墙', name=slot.display_name())
        effect = tr(definition['note'])
    elif verb == 'settle':
        point = tr('形态')
        replacement = tr('〔{name}〕将沉降回液体', name=slot.display_name())
        effect = tr(definition['note'])
    else:
        point = {'whisper': '行动', 'call': '行动', 'clamor': '行动', 'dispel': '意志',
                 'break': '完整度', 'thin': '浓度', 'delete': '存在'}[verb]
        phrase = {
            'whisper': '〔{name}〕将循着低语调查', 'call': '〔{name}〕将循声靠近',
            'clamor': '〔{name}〕将应着尖声追来', 'dispel': '〔{name}〕将惊散 {n} 回合',
            'break': '〔{name}〕将失去 {n} 点完整度', 'thin': '〔{name}〕将只剩原量的 1/{n}',
            'delete': '〔{name}〕将被抹去',
        }[verb]
        replacement = tr(phrase, name=slot.display_name(), n=amount)
        effect = tr(definition['note'])
    from .tamper_prose import assemble_sentence
    from .tamper_views import language_of
    language = language_of()
    degree = next((cid for cid in combo if cid in DEGREE_IDS), None)
    clauses: list[str] = []
    if combo:
        # 条件组合把插入点与效果说明合并进同一份预览；数字差异（伤害/时长）已在上面的
        # amount 里体现，这里补每条条件的“为什么变了”与附加后果。
        point = '＋'.join(tr(CONDITION_DEFS[condition_id_]['insertion'])
                          for condition_id_ in combo)
        effect = tr('{base} {extra}', base=tr(definition['note']),
                    extra=tr(condition_combo_notes(combo, word_id)))
        for condition_id_ in combo:
            clause = _condition_clause(condition_id_, word_id, verb)
            if clause and clause not in clauses:
                clauses.append(clause)
    # 统一最终标点/语序（2026-10-18 docs §8 第一批）：动作子句、程度与条件
    # 只在末尾组一次句，不再各自补标点或使用「词名：句子」的菜单格式。
    replacement = assemble_sentence(
        replacement,
        degree=tr(definition['name']) if degree else None,
        clauses=tuple(clauses),
        language=language,
    )
    return tr(point), replacement, effect


def after_text(sentence: WorldSentence, word_id: str, slot_index: int,
               condition_id: str | None = None, *,
               condition_ids: tuple[str, ...] | None = None,
               state: Any | None = None) -> str:
    """面板「改后」整句：原句语篇 + 变更子句（§15 第三批）。

    ``insertion_preview`` 给的是**变更子句**（「〔北侧的砖墙〕将被点燃，用的是
    『崩碎』的力道」）；直接把它当改后句，原句里点到的其他对象就消失了。这里把
    原句原样保留、变更子句接在后面，玩家能看出这一笔动的是哪一处，也能看出别的
    东西没被提到。
    """
    from .tamper_prose import compose_after
    from .tamper_views import language_of

    _point, change, _effect = insertion_preview(
        sentence, word_id, slot_index, condition_id,
        condition_ids=condition_ids, state=state)
    return compose_after(sentence.text, change, language=language_of())


def _condition_clause(condition_id: str, word_id: str, verb: str) -> str:
    """条件对改后整句的附加说明（已翻译；标点由 tamper_prose 统一）。

    数字差异由 _word_effect_amount 落地；这里只补「为什么变了」的自然语言。
    """
    if condition_id == 'pay_with_noise':
        return tr('你所在的位置也会发出声音')
    if condition_id == 'pay_with_thought':
        return tr('可这一声没能传出去')
    if condition_id == 'force_lure':
        return tr('半径内听见的都会径直追来')
    if condition_id == 'catch_unaware' and verb == 'lure_to':
        return tr('它仍不会察觉')
    return ''


def word_allowed(word_id: str, slot: WorldSlot, sentence: WorldSentence | None = None) -> bool:
    definition = WORD_DEFS.get(word_id)
    if definition is None or slot is None:
        return False
    allowed = definition["slot"]
    if allowed == 'ignite':
        # 材料专属（docs §六/§十）：可烧的墙/植物地形、可燃液气、地上可燃物。
        return slot.category in ('terrain', 'gas', 'liquid', 'object')
    if allowed == 'soak':
        # 只对地形（纤维墙/植物）；对 ground/anomaly/liquid/gas/object 一律不出现。
        return slot.category == 'terrain'
    if allowed == 'brittle':
        # 只对地形（玻璃/瓷/晶/盐类墙种），实际脆性由材质名单判定。
        return slot.category == 'terrain'
    if allowed == 'liquid_only':
        return slot.category == 'liquid'
    if allowed == 'gas_only':
        return slot.category == 'gas'
    if allowed == 'plant_only':
        # 植物在地形槽里（与墙/植物共用 terrain 类别），实际由要求判定。
        return slot.category == 'terrain'
    if allowed == 'destination':
        return (slot.category!='anomaly' and sentence is not None
                and any(s.category=='anomaly' for s in sentence.slots))
    if allowed == 'environment':
        return slot.category!='anomaly'
    if allowed == "both":
        return slot.category!='ground'
    if allowed == 'fluid':
        return slot.category in ('liquid','gas')
    if allowed == "terrain":
        return slot.category == 'terrain'
    return slot.category == allowed


def _delete_target_integrity(state: Any, slot: WorldSlot) -> int:
    """删除目标用于加价的完整度：异象读自身，墙体读格子，物件没有完整度记 0。

    （2026-10-22 平衡修复：旧口径只给「删除异象」加价，墙体/物件按基础价一刀抹掉，
    硬墙反而不如「崩碎」两次贵；这里把实体目标的完整度也纳入加价。）
    """
    if slot.category == "anomaly" and slot.enemy is not None:
        return max(0, int(slot.enemy.integrity))
    if slot.category == "terrain":
        cell = state.cell(slot.x, slot.y)
        if cell.solid and cell.wall_kind:
            return max(0, int(cell.integrity))
    return 0


def _delete_uses_quota(state: Any, slot: WorldSlot) -> bool:
    """这次删除是否占用「每层删除额度」：异象、墙体、物件共用同一份额度。"""
    if slot.category == "anomaly":
        return True
    if slot.category == "object":
        return True
    if slot.category == "terrain":
        cell = state.cell(slot.x, slot.y)
        return bool(cell.solid and cell.wall_kind)
    return False


def word_cost(state: Any, word_id: str, slot: WorldSlot) -> tuple[int, int]:
    """返回 (想象力, 混乱度)；删除按目标完整度加价（docs §15.6，2026-10-22 修订）。

    异象：+2 + ceil(完整度/4) 想象力、+4 混乱度（原口径）；
    墙体／物件：+ceil(完整度/60) 想象力、+4 混乱度（新增：抹硬墙不再是最省的一刀）。
    物件没有完整度字段，按 0 计，只吃 +4 混乱度。
    """
    definition = WORD_DEFS[word_id]
    imagination = int(definition["imagination"])
    chaos = int(definition["chaos"])
    if word_id == "delete":
        integrity = _delete_target_integrity(state, slot)
        if slot.category == "anomaly":
            imagination += 2 + (integrity + DELETE_ANOMALY_IMAGINATION_EXTRA_DIVISOR - 1) // DELETE_ANOMALY_IMAGINATION_EXTRA_DIVISOR
            chaos += DELETE_ANOMALY_CHAOS_EXTRA
        elif _delete_uses_quota(state, slot):
            imagination += (integrity + DELETE_WALL_IMAGINATION_EXTRA_DIVISOR - 1) // DELETE_WALL_IMAGINATION_EXTRA_DIVISOR
            chaos += DELETE_WALL_CHAOS_EXTRA
    return imagination, chaos


def _ignite_requirement_reason(state: Any, slot: WorldSlot) -> str:
    """点燃要求：格子本身可燃，或该格有可燃地上物（docs §六）；空串 = 可用。"""
    cell = state.cell(slot.x, slot.y)
    if state._cell_is_flammable(cell):
        return ''
    from .content import item_is_flammable
    if any((entry.x, entry.y) == (slot.x, slot.y) and item_is_flammable(entry.item)
           for entry in state.world_items):
        return ''
    return tr('这里没有可以点燃的东西。')


def _soak_requirement_reason(state: Any, slot: WorldSlot) -> str:
    """浸透要求：吸水／纤维材质（docs §六）或 1 格高的植物；空串 = 可用。

    吸液是**材质属性**（FIBER_WALLS），不按墙高一刀切；高度只约束植物——
    高过 1 格的植株水浇不透。
    """
    cell = state.cell(slot.x, slot.y)
    if str(cell.wall_kind or '') in FIBER_WALLS:
        return ''
    if cell.plant and int(cell.height) <= 1:
        return ''
    if int(cell.height) > 1:
        return tr('这个东西太高，水浸不透。')
    return tr('这种材质吸不住水。')


def _brittle_requirement_reason(state: Any, slot: WorldSlot) -> str:
    """脆裂要求：目标格是登记过的脆性墙种；空串 = 可用。"""
    cell = state.cell(slot.x, slot.y)
    if not (cell.solid and str(cell.wall_kind or '') in BRITTLE_WALLS):
        return tr('这种材质不会沿着裂纹碎开。')
    return ''


def _brittle_damage(state: Any, slot: WorldSlot) -> int:
    """脆裂伤害：当前完整度的一半（向上取整），至少 1 点。"""
    cell = state.cell(slot.x, slot.y)
    return max(1, (max(1, int(cell.integrity)) + 1) // 2)


def _spread_targets(state: Any, slot: WorldSlot) -> list[tuple[int, int]]:
    """流体可摊到的相邻格：四向、格内无实心墙；液/气都不进实心格。"""
    cells: list[tuple[int, int]] = []
    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        x, y = slot.x + dx, slot.y + dy
        if 0 <= x < state.width and 0 <= y < state.height and not state.cell(x, y).solid:
            cells.append((x, y))
    return cells


def _uproot_word(state: Any, slot: WorldSlot) -> tuple[str, str]:
    """拔除：走真实拔植物结算（含稀有植物收益），只是落点是句子里选的格子。"""
    cell = state.cell(slot.x, slot.y)
    if int(cell.plant) <= 0:
        return '', tr('这里没有可以拔起的植物。')
    name = slot.label
    # 先按植物定义结算收益（奖励读取格子里的植物码），再真正拔掉。
    reward = state.uproot_plant_reward(slot.x, slot.y)
    state.set_plant_at(cell, 0)
    state._material_index_ready = False
    message = tr('你把「{name}」连根拔起。', name=name)
    if reward:
        message += reward
    return message, ''


def _gather_word(state: Any, slot: WorldSlot, word_id: str) -> tuple[str, str]:
    """聚流/聚气：区域槽走守恒计划；单格旧槽保留真实混合反应口径。"""
    if not getattr(slot, "region_members", ()):
        return _gather_word_legacy(state, slot, word_id)
    from .tamper_fluid import apply_fluid_plan, build_fluid_plan
    plan = build_fluid_plan(state, word_id, slot,
                            destination=getattr(slot, "gather_destination", None))
    if isinstance(plan, str):
        return '', plan
    _note, error = apply_fluid_plan(state, plan)
    if error:
        return '', error
    name = slot.display_name()
    if word_id == 'gather_liquid':
        return tr('「{name}」把相邻的液态记忆聚了过来。', name=name), ''
    return tr('「{name}」把相邻的弥散印象聚了过来。', name=name), ''


def _gather_word_legacy(state: Any, slot: WorldSlot, word_id: str) -> tuple[str, str]:
    """单格旧口径：相邻任何同类流体都搬进本格，交给真实混合/反应表处理。"""
    liquid = word_id == 'gather_liquid'
    if liquid:
        protected = _gather_protected_reason(state, slot)
        if protected:
            return '', tr(protected)
    moved = 0
    for x, y in _spread_targets(state, slot):
        source = state.cell(x, y)
        amount = int(source.liquid if liquid else source.gas)
        if amount <= 0:
            continue
        if liquid:
            kind = str(source.liquid_kind or '')
            source.liquid = 0
            source.liquid_kind = ''
            if kind:
                state._add_liquid(state.cell(slot.x, slot.y), kind, amount)
        else:
            kind = str(source.gas_kind or '')
            source.gas = 0
            source.gas_kind = ''
            if kind:
                state._add_gas(state.cell(slot.x, slot.y), kind, amount)
        moved += amount
    if moved <= 0:
        return '', tr('相邻没有可以聚拢的东西。')
    state._material_index_ready = False
    name = slot.label.split(' ')[0]
    if liquid:
        return tr('「{name}」把相邻的液态记忆聚了过来。', name=name), ''
    return tr('「{name}」把相邻的弥散印象聚了过来。', name=name), ''


def _grow_word(state: Any, slot: WorldSlot) -> tuple[str, str]:
    """催生：低草长成高丛（真实改 plant 码，遮挡视线与踩踏规则随之改变）。"""
    cell = state.cell(slot.x, slot.y)
    code = int(cell.plant)
    if code not in PLANT_GROWTH:
        return '', _grow_requirement_reason(state, slot)
    state.set_plant_at(cell, PLANT_GROWTH[code])
    state._material_index_ready = False
    return tr('「{name}」长高了一截。', name=slot.label), ''


def _wither_word(state: Any, slot: WorldSlot) -> tuple[str, str]:
    """枯萎：把植株的燃烧燃料抬高到干枯档，植物本身保留；日后更耐烧。"""
    cell = state.cell(slot.x, slot.y)
    if int(cell.plant) <= 0:
        return '', _wither_requirement_reason(state, slot)
    cell.plant_fuel = max(int(cell.plant_fuel), WITHER_FUEL)
    state._material_index_ready = False
    return tr('「{name}」提前干枯了——烧起来会更久。', name=slot.label), ''


def _evaporate_word(state: Any, slot: WorldSlot) -> tuple[str, str]:
    """蒸发：按液体定义自己的蒸发产物与比例化为气体。"""
    from ..materials import liquid_def

    cell = state.cell(slot.x, slot.y)
    definition = liquid_def(str(cell.liquid_kind or ''))
    gas_kind = definition.evaporation_gas
    if int(cell.liquid) <= 0 or not gas_kind:
        return '', _evaporate_requirement_reason(state, slot)
    ratio = max(1, int(definition.evaporation_ratio or 1))
    amount = int(cell.liquid)
    evaporated = max(1, amount // ratio)
    cell.liquid = max(0, amount - evaporated)
    if int(cell.liquid) <= 0:
        cell.liquid_kind = ''
    state._add_gas(cell, gas_kind, evaporated)
    state._material_index_ready = False
    return tr('「{name}」蒸起一缕{gas}。', name=slot.label, gas=tr(gas_kind)), ''


def _solidify_word(state: Any, slot: WorldSlot) -> tuple[str, str]:
    """凝固：按材料表把液体换成一堵真实新墙；液体消失。"""
    reason=_solidify_requirement_reason(state,slot)
    if reason:return '',reason
    cell = state.cell(slot.x, slot.y)
    wall_kind = SOLIDIFY_WALLS.get(str(cell.liquid_kind or ''))
    if wall_kind is None or int(cell.liquid) < 10:
        return '', _solidify_requirement_reason(state, slot)
    cell.liquid = 0
    cell.liquid_kind = ''
    state.configure_wall(cell, wall_kind)
    state._material_index_ready = False
    return tr('「{name}」凝成了一堵{wall}。', name=slot.label, wall=tr(wall_kind)), ''


def _settle_word(state: Any, slot: WorldSlot) -> tuple[str, str]:
    """沉降：按材料表把部分气体凝回液体。"""
    cell = state.cell(slot.x, slot.y)
    pair = GAS_SETTLE_LIQUIDS.get(str(cell.gas_kind or ''))
    if pair is None or int(cell.gas) < 4:
        return '', _settle_requirement_reason(state, slot)
    liquid_kind, ratio = pair
    amount = int(cell.gas)
    settled = max(1, amount // max(1, ratio))
    cell.gas = max(0, amount - settled)
    if int(cell.gas) <= 0:
        cell.gas_kind = ''
    state._add_liquid(cell, liquid_kind, settled)
    state._material_index_ready = False
    return tr('「{name}」沉下一层{liquid}。', name=slot.label, liquid=tr(liquid_kind)), ''


def _spread_word(state: Any, slot: WorldSlot, word_id: str) -> tuple[str, str]:
    """泼开/扬散：按守恒计划把一部分摊到相邻可容纳格，余量留在来源。"""
    from .tamper_fluid import apply_fluid_plan, build_fluid_plan
    plan = build_fluid_plan(state, word_id, slot)
    if isinstance(plan, str):
        return '', plan
    _note, error = apply_fluid_plan(state, plan)
    if error:
        return '', error
    name = slot.display_name()
    suffix = ''
    if plan.residual:
        suffix = tr('（实际移动 {moved}，来源剩 {residual}）',
                    moved=plan.moved, residual=plan.residual)
    if word_id == 'spill':
        return tr('「{name}」向相邻的地面摊开了一半。', name=name) + suffix, ''
    return tr('「{name}」向相邻的空间扬散了一半。', name=name) + suffix, ''


def _spread_requirement_reason(state: Any, slot: WorldSlot, word_id: str) -> str:
    """泼开/扬散的要求：目标流体够分，且至少有一个相邻可摊格；空串 = 可用。"""
    cell = state.cell(slot.x, slot.y)
    amount = int(cell.liquid) if word_id == 'spill' else int(cell.gas)
    if amount < 2:
        return tr('这里的分量太少，摊不开。')
    if not _spread_targets(state, slot):
        return tr('周围没有可以摊开的格子。')
    return ''


def _uproot_requirement_reason(state: Any, slot: WorldSlot) -> str:
    """拔除要求：目标格长着植物；空串 = 可用。"""
    if int(state.cell(slot.x, slot.y).plant) <= 0:
        return tr('这里没有可以拔起的植物。')
    return ''


def _gather_requirement_reason(state: Any, slot: WorldSlot, word_id: str) -> str:
    """聚流/聚气要求：至少一个相邻格有同类流体；空串 = 可用。"""
    liquid = word_id == 'gather_liquid'
    for x, y in _spread_targets(state, slot):
        cell = state.cell(x, y)
        if (int(cell.liquid) > 0) if liquid else (int(cell.gas) > 0):
            return ''
    return tr('相邻没有可以聚拢的东西。')


def _liquid_protected_reason(state: Any, slot: WorldSlot) -> str:
    """目标液体本身是否受任务保护（蒸发/凝固会永久减少它）。"""
    from .tamper_protection import liquid_reason

    return liquid_reason(str(state.cell(slot.x, slot.y).liquid_kind or ''))


def _gather_protected_reason(state: Any, slot: WorldSlot) -> str:
    """聚流会把相邻液体搬进目标格：任务要求的液体一律不许被这样搬走。"""
    from .tamper_protection import liquid_reason

    reason = liquid_reason(str(state.cell(slot.x, slot.y).liquid_kind or ''))
    if reason:
        return reason
    for x, y in _spread_targets(state, slot):
        reason = liquid_reason(str(state.cell(x, y).liquid_kind or ''))
        if reason:
            return reason
    return ''


def _grow_requirement_reason(state: Any, slot: WorldSlot) -> str:
    """催生要求：目标格的低草还能长高；空串 = 可用。"""
    cell = state.cell(slot.x, slot.y)
    if int(cell.plant) <= 0:
        return tr('这里没有可以催生的植物。')
    if int(cell.plant) not in PLANT_GROWTH:
        return tr('这株植物已经长到头了。')
    return ''


def _wither_requirement_reason(state: Any, slot: WorldSlot) -> str:
    """枯萎要求：目标格有植物；空串 = 可用。"""
    if int(state.cell(slot.x, slot.y).plant) <= 0:
        return tr('这里没有可以枯萎的植物。')
    return ''


def _evaporate_requirement_reason(state: Any, slot: WorldSlot) -> str:
    """蒸发要求：该液体定义里有自己的蒸发产物；空串 = 可用。"""
    from ..materials import liquid_def

    cell = state.cell(slot.x, slot.y)
    if int(cell.liquid) <= 0:
        return tr('这里没有可以蒸发的液体。')
    if not liquid_def(str(cell.liquid_kind or '')).evaporation_gas:
        return tr('这种液体不会自然蒸发。')
    return ''


def _solidify_requirement_reason(state: Any, slot: WorldSlot) -> str:
    """凝固要求：该液体在可凝固材料表里，且分量够立起墙体。"""
    from .tamper_protection import construction_reason
    reason=construction_reason(state,slot.x,slot.y)
    if reason:return tr(reason)
    cell = state.cell(slot.x, slot.y)
    if int(cell.liquid) <= 0:
        return tr('这里没有可以凝固的液体。')
    if str(cell.liquid_kind or '') not in SOLIDIFY_WALLS:
        return tr('这种液体凝不住。')
    if int(cell.liquid) < 10:
        return tr('分量太少，凝不成一堵墙。')
    return ''


def _settle_requirement_reason(state: Any, slot: WorldSlot) -> str:
    """沉降要求：该气体在沉降材料表里且分量足够；空串 = 可用。"""
    cell = state.cell(slot.x, slot.y)
    if int(cell.gas) <= 0:
        return tr('这里没有可以沉降的气体。')
    if str(cell.gas_kind or '') not in GAS_SETTLE_LIQUIDS:
        return tr('这种气体不会沉下来。')
    if int(cell.gas) < 4:
        return tr('分量太少，沉不出东西来。')
    return ''


# ---- 条件词（docs §四/五/六/七）----

def condition_ids() -> tuple[str, ...]:
    return CONDITION_ORDER


def condition_note(condition_id: str, word_id: str) -> str:
    """条件在该字词上的效果说明；同一条件对不同字词可覆盖通用文案。"""
    definition = CONDITION_DEFS.get(condition_id)
    if definition is None:
        return ''
    if condition_id in DEGREE_IDS:
        return tr(WORD_DEFS[resolved_word_id(word_id, (condition_id,))]['note'])
    return (definition.get('note_by_word') or {}).get(word_id) or definition['note']


def condition_allowed(condition_id: str, word_id: str, slot: WorldSlot,
                      sentence: WorldSentence | None = None) -> bool:
    """条件在结构上能否配这个字词与名称槽；不读世界状态（要求见下一函数）。"""
    definition = CONDITION_DEFS.get(condition_id)
    if definition is None or slot is None:
        return False
    if not word_allowed(word_id, slot, sentence):
        return False
    words = definition['words']
    return not words or word_id in words


def condition_ids_for(sentence: WorldSentence, word_id: str,
                      slot: WorldSlot) -> tuple[str, ...]:
    """当前字词＋名称槽可显示的条件（顺序即 CONDITION_ORDER）。"""
    return tuple(condition_id for condition_id in CONDITION_ORDER
                 if condition_allowed(condition_id, word_id, slot, sentence))


def _condition_subject(slot: WorldSlot, sentence: WorldSentence | None) -> Any | None:
    """条件要检查的异象：目标槽本身，或句子里那名被招引的异象（关系词）。"""
    enemy = getattr(slot, 'enemy', None)
    if enemy is not None:
        return enemy
    if sentence is None:
        return None
    return next((entry.enemy for entry in sentence.slots
                 if entry.category == 'anomaly'), None)


def condition_requirement_reason(state: Any, condition_id: str,
                                 slot: WorldSlot,
                                 sentence: WorldSentence | None = None) -> str:
    """条件的世界要求是否满足；空串 = 满足。"""
    definition = CONDITION_DEFS.get(condition_id)
    if definition is None:
        return tr('没有这个条件。')
    requirement = definition['requirement']
    if requirement == 'cracked_wall':
        cell = state.cell(slot.x, slot.y)
        if not (cell.solid and cell.wall_kind):
            return tr('这里没有可以趁虚的墙。')
        if int(cell.integrity) >= int(wall_def(cell.wall_kind).integrity):
            return tr('这面墙还完好，趁不了虚。')
    elif requirement == 'unaware_target':
        enemy = _condition_subject(slot, sentence)
        if enemy is None or getattr(enemy, 'alert_state', '') != '未察觉':
            return tr('它已经察觉了，趁不上这一手。')
    return ''


def condition_blocked_reason(state: Any, condition_id: str, slot: WorldSlot,
                             sentence: WorldSentence | None = None,
                             *, word_id: str | None = None) -> str:
    """条件不可用的玩家可读原因；空串 = 可用。"""
    if condition_id not in CONDITION_DEFS:
        return tr('没有这个条件。')
    if word_id is not None and not condition_allowed(condition_id, word_id, slot, sentence):
        return tr('这个条件用不到这个字词上。')
    return condition_requirement_reason(state, condition_id, slot, sentence)


def condition_cost(condition_id: str, word_id: str | None = None,
                   slot: WorldSlot | None = None) -> tuple[int, int]:
    """条件对代价的增量（想象力, 混乱度）；无此条件返回 (0, 0)。"""
    definition = CONDITION_DEFS.get(condition_id)
    if definition is None:
        return 0, 0
    if condition_id in DEGREE_IDS and word_id in DEGREE_VARIANTS:
        original = WORD_DEFS[word_id]
        variant = WORD_DEFS[resolved_word_id(word_id, (condition_id,))]
        return (int(variant['imagination']) - int(original['imagination']),
                int(variant['chaos']) - int(original['chaos']))
    return int(definition['imagination_delta']), int(definition['chaos_delta'])


def word_cost_with_condition(state: Any, word_id: str, slot: WorldSlot,
                             condition_id: str | None = None) -> tuple[int, int]:
    """字词基础代价 + 单个条件增量（向后兼容的旧入口）。"""
    combo = (condition_id,) if condition_id else ()
    return word_cost_with_conditions(state, word_id, slot, combo)


#: 互斥条件：静音的「以想代声」与要求全体听见的「强诱引」不能同时成立。
CONDITION_CONFLICTS: frozenset[frozenset[str]] = frozenset({
    frozenset(DEGREE_IDS),
    frozenset({'pay_with_thought', 'force_lure'}),
})


def _conditions_conflict(first: str, second: str) -> bool:
    return frozenset({first, second}) in CONDITION_CONFLICTS


def _normalize_conditions(condition_id: str | None = None,
                          condition_ids: tuple[str, ...] | None = None) -> tuple[str, ...]:
    """把新旧两种调用统一成有序条件元组（去重、按 CONDITION_ORDER 排序）。"""
    raw: tuple[str, ...] = tuple(condition_ids or ())
    if condition_id:
        raw = (condition_id, *raw)
    ordered = {condition_id_: index for index, condition_id_ in enumerate(CONDITION_ORDER)}
    unique = tuple(dict.fromkeys(raw))
    return tuple(sorted(unique, key=lambda cid: ordered.get(cid, len(ordered))))


def condition_combinations(word_id: str, slot: WorldSlot,
                           sentence: WorldSentence | None = None, *,
                           include_degree: bool = True) -> tuple[tuple[str, ...], ...]:
    """当前字词＋槽允许的条件组合：无、单条件，以及最多 3 个的无冲突组合。

    顺序稳定：先「无」，再按 CONDITION_ORDER 的单条件，再按组合长度与
    CONDITION_ORDER 顺序枚举的无冲突多条件；面板与提交共用这一份列表。
    """
    from itertools import combinations
    from ..data.tamper_world import MAX_CONDITIONS_PER_COMMIT

    singles = tuple(condition_id for condition_id in CONDITION_ORDER
                    if (include_degree or condition_id not in DEGREE_IDS)
                    if condition_allowed(condition_id, word_id, slot, sentence))
    combos: list[tuple[str, ...]] = [()]
    for size in range(1, min(MAX_CONDITIONS_PER_COMMIT + int(include_degree), len(singles)) + 1):
        for group in combinations(singles, size):
            if (sum(cid not in DEGREE_IDS for cid in group) <= MAX_CONDITIONS_PER_COMMIT
                    and all(not _conditions_conflict(first, second)
                   for index, first in enumerate(group) for second in group[index + 1:])):
                combos.append(group)
    return tuple(combos)


def condition_combo_allowed(combo: tuple[str, ...], word_id: str, slot: WorldSlot,
                            sentence: WorldSentence | None = None) -> bool:
    """整组条件在结构上是否合法（逐项适用且两两不冲突）。"""
    from ..data.tamper_world import MAX_CONDITIONS_PER_COMMIT
    if (len(set(combo)) != len(combo)
            or sum(cid not in DEGREE_IDS for cid in combo) > MAX_CONDITIONS_PER_COMMIT):
        return False
    return all(condition_allowed(condition_id, word_id, slot, sentence)
               for condition_id in combo) and all(
        not _conditions_conflict(first, second)
        for index, first in enumerate(combo) for second in combo[index + 1:])


def condition_combo_blocked_reason(state: Any, combo: tuple[str, ...], slot: WorldSlot,
                                   sentence: WorldSentence | None = None,
                                   *, word_id: str | None = None) -> str:
    """条件组合不可用的第一条原因；空串 = 可用。"""
    if word_id is not None and not condition_combo_allowed(combo, word_id, slot, sentence):
        return tr('这个条件组合用不到这个字词上。')
    for condition_id in combo:
        reason = condition_blocked_reason(state, condition_id, slot, sentence,
                                          word_id=word_id)
        if reason:
            return reason
    return ''


def condition_combo_cost(combo: tuple[str, ...], word_id: str | None = None,
                         slot: WorldSlot | None = None) -> tuple[int, int]:
    """整组条件的代价增量之和。"""
    imagination = chaos = 0
    for condition_id in combo:
        delta_imagination, delta_chaos = condition_cost(condition_id, word_id, slot)
        imagination += delta_imagination
        chaos += delta_chaos
    return imagination, chaos


def condition_combo_notes(combo: tuple[str, ...], word_id: str) -> str:
    """整组条件的玩家可读效果说明（用「；」连接）。"""
    return '；'.join(condition_note(condition_id, word_id) for condition_id in combo)


def word_cost_with_conditions(state: Any, word_id: str, slot: WorldSlot,
                              combo: tuple[str, ...] = ()) -> tuple[int, int]:
    """字词基础代价 + 整组条件增量，想象力下限 0。"""
    imagination, chaos = word_cost(state, word_id, slot)
    if combo:
        delta_imagination, delta_chaos = condition_combo_cost(combo, word_id, slot)
        imagination = max(0, imagination + delta_imagination)
        chaos += delta_chaos
    if state is not None:
        quoted = pipeline.quote_cost(state, pipeline.TamperCost(imagination, chaos))
        return quoted.imagination, quoted.chaos_delta
    return imagination, chaos


def _deletes_this_layer(state: Any) -> int:
    return int(state.world_tamper_deletes.get(state.layer_key(), 0))


def word_blocked_reason(state: Any, word_id: str, slot: WorldSlot,
                        sentence: WorldSentence | None = None) -> str:
    """字词不可用的玩家可读原因；空串 = 可用。"""
    # 关键任务对象保护矩阵先于字词自身规则：任务交付物、绑定目标、机关与
    # 设施布局格上的固体不能被永久抹除（docs §二）。返回的是中文原文键，
    # 调用方统一经 tr() 呈现。
    from .tamper_protection import item_reason, slot_reason, terrain_reason
    protected = slot_reason(state, slot, word_id)
    # 保护矩阵先于材料字词规则（docs §二）：保护表的字词集合是旧的抹除类，
    # 点燃／浸透／脆裂同样可能永久减少任务对象（烧毁、软化机关墙、震碎机关），
    # 必须一并拦下。
    if not protected and word_id in ('ignite', 'soak', 'brittle'):
        if slot.category == 'terrain':
            protected = terrain_reason(state, slot.x, slot.y)
        elif slot.category == 'object':
            entry = next((entry for entry in state.world_items
                          if (entry.x, entry.y) == (slot.x, slot.y)), None)
            protected = item_reason(entry.item.definition_id) if entry is not None else ''
    if protected:
        return tr(protected)
    if word_id == 'ignite':
        return _ignite_requirement_reason(state, slot)
    if word_id == 'soak':
        return _soak_requirement_reason(state, slot)
    if word_id == 'brittle':
        return _brittle_requirement_reason(state, slot)
    if word_id in ('spill', 'scatter'):
        return _spread_requirement_reason(state, slot, word_id)
    if word_id == 'uproot':
        return _uproot_requirement_reason(state, slot)
    if word_id == 'gather_liquid':
        protected = _gather_protected_reason(state, slot)
        if protected:
            return tr(protected)
        return _gather_requirement_reason(state, slot, word_id)
    if word_id == 'gather_gas':
        return _gather_requirement_reason(state, slot, word_id)
    if word_id == 'grow':
        return _grow_requirement_reason(state, slot)
    if word_id == 'wither':
        return _wither_requirement_reason(state, slot)
    if word_id == 'evaporate':
        protected = _liquid_protected_reason(state, slot)
        if protected:
            return tr(protected)
        return _evaporate_requirement_reason(state, slot)
    if word_id == 'solidify':
        protected = _liquid_protected_reason(state, slot)
        if protected:
            return tr(protected)
        return _solidify_requirement_reason(state, slot)
    if word_id == 'settle':
        return _settle_requirement_reason(state, slot)
    if word_id=='lure_to':
        if sentence is None:
            return tr('这句话里没有可以招引的异象。')
        actor=next((s.enemy for s in sentence.slots if s.category=='anomaly'),None)
        if actor is None:
            return tr('这句话里没有可以招引的异象。')
        if actor.alert_state=='追踪':
            return tr('它正在紧追你，不会分心调查别处。')
        if actor.portents.get('spooked'):
            return tr('它还在惊散中，无法循线调查。')
        if state.cell(slot.x,slot.y).solid or (slot.x,slot.y)==(state.player.x,state.player.y):
            return tr('那个位置无法作为调查落点。')
        if (actor.x,actor.y)==(slot.x,slot.y):
            return tr('它已经站在那儿了。')
        if state.entity_at(slot.x,slot.y) is not None:
            return tr('那个位置已经被占据。')
        if not state.path_to(slot.x,slot.y,start=(actor.x,actor.y),portents=actor.portents):
            return tr('它走不到那个位置。')
    if word_id == 'delete' and slot.category == 'object':
        from .tamper_protection import slot_reason
        protected_reason = slot_reason(state, slot, word_id)
        if protected_reason:
            return tr(protected_reason)
    if word_id in ('call','clamor'):
        if slot.enemy is not None and slot.enemy.alert_state == "追踪":
            return tr("它已经在追你了。")
    if word_id == 'whisper' and slot.enemy is not None and slot.enemy.alert_state != '未察觉':
        return tr('它已经察觉了动静，低声招引不起作用。')
    if word_id == "dispel" and slot.enemy is not None and slot.enemy.relation == "稳定意识":
        return tr("稳定意识不吃这一套。")
    if word_id == "delete":
        if slot.category == "anomaly" and slot.enemy is not None:
            if slot.enemy.anomaly_kind in ("核心执念", "强烈异象"):
                return tr("这段文字太深，删不动。")
        # 2026-10-22 平衡修复：墙体／物件删除与异象共用每层额度，不再无限次。
        if _delete_uses_quota(state, slot) and _deletes_this_layer(state) >= MAX_DELETES_PER_LAYER:
            return tr("这一层的删除额度用完了（{n} 次）。", n=MAX_DELETES_PER_LAYER)
    return ""


from ..equipment.root_facts import root_action


@root_action
def commit_world_tamper(state: Any, sentence: WorldSentence, word_id: str,
                        slot_index: int,
                        condition_id: str | None = None,
                        *, condition_ids: tuple[str, ...] | None = None) -> ActionResult:
    """一次地图篡改提交：验证 → 条件验证 → 扣费 → 混乱 → 风险 → 推进回合 → 效果。

    条件（单个或组合）先于任何扣费验证：要求不满足、组合冲突或与字词不配时整单
    拒绝，零副作用（不扣想象力／混乱度／时间、不改地图、不推进回合）。效果仍在
    扣费前执行，执行失败同样整单拒绝；合并代价一次扣除（docs §四/§十）。
    """
    from .entities import ActionResult as _AR  # 局部别名，避免与类型注解冲突

    if slot_index < 0 or slot_index >= len(sentence.slots):
        return _AR(False, tr("没有这个名字。"))
    if sentence.consumed:
        return _AR(False, sentence.result_message, {'replayed': True})
    if state.run_over or not _preview_current(state, sentence, slot_index):
        return _AR(False, tr("眼前的情形已经改变，请重新选择。"))
    slot = sentence.slots[slot_index]
    definition = WORD_DEFS.get(word_id)
    if definition is None or not word_allowed(word_id, slot,sentence):
        return _AR(False, tr("这个字词用不到这个名字上。"))
    # 保护矩阵先于字词与条件规则：受保护对象在这里直接拒绝。
    reason = word_blocked_reason(state, word_id, slot,sentence)
    if reason:
        return _AR(False, reason)
    combo = _normalize_conditions(condition_id, condition_ids)
    if combo:
        if any(condition_id_ not in CONDITION_DEFS for condition_id_ in combo):
            return _AR(False, tr("没有这个条件。"))
        condition_reason = condition_combo_blocked_reason(
            state, combo, slot, sentence, word_id=word_id)
        if condition_reason:
            return _AR(False, condition_reason)
    imagination, chaos_delta = word_cost_with_conditions(
        state, word_id, slot, combo)
    if int(state.imagination) < imagination:
        return _AR(False, tr("想象力不够（需要 {n}）。", n=imagination))

    # 删除额度必须在效果落地**之前**判定：抹掉墙后格子已不是墙，
    # _delete_uses_quota 会读不到目标类别（2026-10-22 平衡修复）。
    uses_delete_quota = word_id == "delete" and _delete_uses_quota(state, slot)

    # 效果先执行失败即整单拒绝（代价不动）。
    effect_note, effect_error = _apply_word(
        state, word_id, slot, sentence=sentence, condition_ids=combo)
    if effect_error:
        return _AR(False, effect_error)
    if 'pay_with_noise' in combo:
        # 以声代想：效果结算后，玩家格发出基础半径 8 的**普通**脉冲
        # （by_player=True 让既有距离梯度与洞察修正参与，不使用 full_alert）。
        state._sound_pulse(state.player.x, state.player.y, 8, by_player=True)

    # 共享提交管线（docs §四）：序号、扣费/混乱、风险、时间与对话侧同一套实现。
    sequence = pipeline.next_sequence(state)
    # 风险判定复用对话篡改的事件池：伪 request 只喂稳定种子与归属。
    request = TamperRequest(
        TamperTarget("event", "world_tamper", f"world:{slot.x}:{slot.y}"),
        "world_tamper", word_id, 0,
        f"world|{word_id}|{slot.x}:{slot.y}|{sequence}",
    )
    chaos_after, outcome = pipeline.settle(
        state, request, pipeline.TamperCost(imagination, chaos_delta),
        sequence=sequence, reason=f"world_tamper:{word_id}",
        source_uid=f"world:{slot.x}:{slot.y}")
    sentence.consumed = True
    # 2026-10-22 平衡修复：异象、墙体、物件都计入每层删除额度。
    if uses_delete_quota:
        deletes = dict(getattr(state, "world_tamper_deletes", {}))
        deletes[state.layer_key()] = _deletes_this_layer(state) + 1
        state.world_tamper_deletes = deletes

    parts = [effect_note]
    if combo:
        parts.append(tr('（条件：{name}）',
                        name='＋'.join(tr(CONDITION_DEFS[condition_id_]['name'])
                                      for condition_id_ in combo)))
    parts.append(tr("（想象力 −{n}，混乱度 {chaos}／{tier}）",
                    n=imagination, chaos=chaos_after, tier=tr(chaos_risk_tier(chaos_after))))
    pipeline.advance_time(state)
    feedback = pipeline.apply_risk(
        state, outcome, source_uid=f"world:{slot.x}:{slot.y}")
    if feedback:
        parts.append(feedback)
    message = "".join(parts)
    sentence.result_message = message
    state.messages.append(message)
    return _AR(True, message, {"world_tamper": word_id, "chaos": chaos_after})


def _apply_word(state: Any, word_id: str, slot: WorldSlot, *,
                sentence: WorldSentence | None = None,
                condition_id: str | None = None,
                condition_ids: tuple[str, ...] | None = None) -> tuple[str, str]:
    """执行字词效果；返回 (玩家可见结果, 错误原因)。错误时代价不动。

    ``condition_ids`` 只改变真实结算（伤害/时长/静音/诱引强度），不改变合法性
    判定——条件验证在 :func:`commit_world_tamper` 的扣费之前完成。
    """
    combo = _normalize_conditions(condition_id, condition_ids)
    # 程度词解析后才是真正执行的档位（旧 ID 与基础词都走这里），
    # 预览/费用/结算共用同一个解析入口（docs 四系统重构 §1）。
    definition = WORD_DEFS[resolved_word_id(word_id, combo)]
    verb = definition.get('verb', word_id)
    if verb == 'ignite':
        return _ignite_word(state, slot)
    if verb == 'soak':
        return _soak_word(state, slot)
    if verb == 'brittle':
        return _break_slot(state, slot, _brittle_damage(state, slot))
    if verb == 'spread':
        return _spread_word(state, slot, word_id)
    if verb == 'uproot':
        return _uproot_word(state, slot)
    if verb == 'gather':
        return _gather_word(state, slot, word_id)
    if verb == 'grow':
        return _grow_word(state, slot)
    if verb == 'wither':
        return _wither_word(state, slot)
    if verb == 'evaporate':
        return _evaporate_word(state, slot)
    if verb == 'solidify':
        return _solidify_word(state, slot)
    if verb == 'settle':
        return _settle_word(state, slot)
    if verb == 'lure_to':
        actor=next(s.enemy for s in sentence.slots if s.category=='anomaly')
        if 'catch_unaware' in combo:
            # 条件与关系词的组合（docs §七）：趁它未察觉把它引开时，
            # 它仍停在「未察觉」——悄悄调查，不会先起疑惊动别处。
            actor.alert_state='未察觉'
        else:
            actor.alert_state='怀疑'
        actor.last_seen_x,actor.last_seen_y=slot.x,slot.y
        actor.lost_sight_turns=0
        state._plan_chase(actor,slot.x,slot.y)
        if 'catch_unaware' in combo:
            return tr('〔{actor}〕循着这句改写，悄悄前往〔{destination}〕调查。',
                      actor=tr(actor.label),destination=slot.label),''
        return tr('〔{actor}〕开始向〔{destination}〕调查。',actor=tr(actor.label),destination=slot.label),''
    if verb == 'echo_here':
        if 'force_lure' in combo:
            state._sound_pulse(slot.x,slot.y,6,by_player=True,full_alert=True)
            return tr('强诱引的声音从〔{name}〕所在的位置响起，听见的都在径直赶来。',
                      name=slot.label),''
        state._sound_pulse(slot.x,slot.y,6,by_player=True)
        return tr('声音从〔{name}〕所在的位置响起。',name=slot.label),''
    if verb == 'whisper':
        enemy=slot.enemy
        if enemy.alert_state != '未察觉':
            return '', tr('它已经察觉了动静，低声招引不起作用。')
        enemy.alert_state='怀疑'
        enemy.last_seen_x,enemy.last_seen_y=state.player.x,state.player.y
        enemy.wandering=False
        state._plan_chase(enemy,state.player.x,state.player.y)
        return tr('它循着低语前来调查。'), ''
    if verb in ('call','clamor'):
        enemy = slot.enemy
        enemy.alert_state = "追踪"
        enemy.last_seen_x, enemy.last_seen_y = state.player.x, state.player.y
        enemy.wandering = False
        state._plan_chase(enemy, state.player.x, state.player.y)
        if verb == 'clamor' and 'pay_with_thought' not in combo:
            # 强诱引：同一半径，但所有听众不再按距离梯度只起疑，而是径直追踪。
            state._sound_pulse(state.player.x,state.player.y,8,by_player=True,
                               full_alert='force_lure' in combo)
        state.messages.append(tr("你的呼唤被 {enemy} 听见了。", enemy=tr(enemy.label)))
        if verb == 'clamor' and 'pay_with_thought' in combo:
            # 以想代声：这一声真的不传出去（不是只把提示改掉）。
            return tr("{enemy}循声向你走来，可这一声没能传出去。",
                      enemy=tr(enemy.label)), ""
        return tr("{enemy}循声向你走来。", enemy=tr(enemy.label)), ""

    if verb == "dispel":
        enemy = slot.enemy
        if not state._apply_direct_portent(
                enemy, "spooked", _word_effect_amount(word_id, combo), mode="set"):
            return "", tr("它没有理会这段文字。")
        enemy.alert_state = "未察觉"
        enemy.path_plan=[]
        enemy.plan_index=0
        enemy.lost_sight_turns = 999.0
        enemy.wandering = True
        state.messages.append(tr("{enemy}被这段文字惊散了。", enemy=tr(enemy.label)))
        return tr("{enemy}转身离开，一时不会再主动找你。", enemy=tr(enemy.label)), ""

    if verb == "break":
        return _break_slot(state, slot, _word_effect_amount(word_id, combo))
    if verb == 'thin':
        # 区域按成员逐格作用：整片区域各自减半，不能只拿锚点单格数量当整片。
        attribute = 'gas' if slot.category == 'gas' else 'liquid'
        members = slot.region_members or ((slot.x, slot.y),)
        divisor = _word_effect_amount(word_id, combo)
        from .tamper_protection import liquid_reason
        removed = 0.0
        for mx, my in members:
            cell = state.cell(mx, my)
            amount = getattr(cell, attribute)
            if amount <= 0:
                continue
            if attribute == 'liquid':
                protected = liquid_reason(str(cell.liquid_kind or ""))
                if protected:
                    if len(members) == 1:
                        return '', tr(protected)
                    return '', tr("区域里有受保护的部分，不能一起抹淡。")
            after = amount // divisor
            removed += amount - after
            setattr(cell, attribute, after)
            if not getattr(cell, attribute):
                setattr(cell, attribute + '_kind', '')
        if removed <= 0:
            return '', tr('这里已经没有可以稀释的东西。')
        state._material_index_ready = False
        return tr('你让「{name}」淡了下去。', name=slot.display_name()), ''

    if word_id == "delete":
        if slot.category == "anomaly":
            from .tamper_protection import threat_reason
            protected = threat_reason(state, slot.enemy)
            if protected:
                return "", tr(protected)
            enemy = slot.enemy
            enemy.integrity = 0
            state._resolve_enemy(enemy,half_reward=True)
            state.enemies = [e for e in state.enemies if e is not enemy]
            return tr("你把「{name}」从眼前抹去了。", name=slot.label), ""
        return _delete_cell(state, slot)

    return "", tr("这个字词还没有学会。")


def _ignite_word(state: Any, slot: WorldSlot) -> tuple[str, str]:
    """点燃：真实调用统一点燃入口；点不着即失败，代价不动。"""
    from .content import item_is_flammable

    cell = state.cell(slot.x, slot.y)
    flammable = state._cell_is_flammable(cell) or any(
        (entry.x, entry.y) == (slot.x, slot.y) and item_is_flammable(entry.item)
        for entry in state.world_items)
    if not flammable:
        return '', tr('这里没有可以点燃的东西。')
    if not state._ignite_cell(slot.x, slot.y, 3, by_player=True):
        return '', tr('这段文字没能点着这里。')
    return tr('「{name}」烧了起来。', name=slot.label), ''


def _soak_word(state: Any, slot: WorldSlot) -> tuple[str, str]:
    """浸透：吸水/纤维材质灌水；若目标本身是墙体再扣 10 点完整度（不低于 1）。"""
    cell = state.cell(slot.x, slot.y)
    if _soak_requirement_reason(state, slot):
        return '', _soak_requirement_reason(state, slot)
    state._add_liquid(cell, '水', 30)
    if cell.wall_kind:
        cell.integrity = max(1, int(cell.integrity) - 10)
    state._material_index_ready = False
    return tr('水渗进了「{name}」。', name=slot.label), ''


def _break_slot(state: Any, slot: WorldSlot, damage: int) -> tuple[str, str]:
    if slot.category == "anomaly":
        enemy = slot.enemy
        enemy.integrity = max(0, int(enemy.integrity) - damage)
        if enemy.integrity <= 0:
            state._resolve_enemy(enemy)
            state.enemies = [e for e in state.enemies if e is not enemy]
            return tr("你把「{name}」磨进了尘埃。", name=slot.label), ""
        return tr("「{name}」被损坏了。", name=slot.label), ""
    if slot.category in ("liquid", "gas"):
        return "", tr("流动的东西写不住「破坏」。")
    cell = state.cell(slot.x, slot.y)
    if not cell.solid or not cell.wall_kind:
        return "", tr("这里没有可以损坏的东西。")
    if state._protected_wall(cell.wall_kind):
        return "", tr("这段文字太深，改不动。")
    if state.puzzle_projectile_blocked(slot.x,slot.y):
        return '',tr('这段文字太深，改不动。')
    from .tamper_protection import terrain_reason
    protected = terrain_reason(state, slot.x, slot.y)
    if protected:
        return '', tr(protected)
    remaining=max(0,int(cell.integrity)-damage)
    if remaining <= 0:
        if not state.destroy_wall(slot.x,slot.y,cause='world_tamper'):
            return '',tr('这段文字太深，改不动。')
        state._material_index_ready = False
        return tr("「{name}」塌了。", name=slot.label), ""
    cell.integrity=remaining
    state._material_index_ready = False
    return tr("「{name}」出现了裂痕。", name=slot.label), ""


def _delete_cell(state: Any, slot: WorldSlot) -> tuple[str, str]:
    from .tamper_protection import item_reason, liquid_reason, terrain_reason

    cell = state.cell(slot.x, slot.y)
    if cell.solid and cell.wall_kind:
        if state._protected_wall(cell.wall_kind):
            return "", tr("这段文字太深，删不动。")
        if state.puzzle_projectile_blocked(slot.x,slot.y):
            return '',tr('这段文字太深，删不动。')
        protected = terrain_reason(state, slot.x, slot.y)
        if protected:
            return '', tr(protected)
        if not state.destroy_wall(slot.x,slot.y,cause='world_tamper'):
            return '',tr('这段文字太深，删不动。')
        state._material_index_ready = False
        return tr("「{name}」从地图上消失了。", name=slot.label), ""
    if slot.category == "liquid":
        protected = liquid_reason(str(cell.liquid_kind or ""))
        if protected:
            return '', tr(protected)
        cell.liquid = 0
        cell.liquid_kind = ""
        state._material_index_ready=False
        return tr("「{name}」被抹干了。", name=slot.label), ""
    if slot.category == "gas":
        cell.gas = 0
        cell.gas_kind = ""
        state._material_index_ready=False
        return tr("「{name}」被抹散了。", name=slot.label), ""
    if slot.category == "object":
        for entry in list(state.world_items):
            if (entry.x, entry.y) == (slot.x, slot.y):
                protected = item_reason(entry.item.definition_id)
                if protected:
                    return '', tr(protected)
                state.world_items.remove(entry)
                return tr("「{name}」被收走了。", name=slot.label), ""
    if slot.category == 'terrain' and cell.plant:
        cell.plant=0
        cell.plant_fuel=0
        state._material_index_ready=False
        return tr('「{name}」从地图上消失了。',name=slot.label),''
    return "", tr("这里没有可以删除的东西。")
