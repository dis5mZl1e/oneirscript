"""只读声响预览（docs §16.3 验收 2/3，2026-10-17）。

设计口径：
- **唯一半径来源**：每个预览只调用一次 ``state._pulse_radius_breakdown``，
  与真实 :meth:`_sound_pulse` 的结算共用同一行修正栈；本模块不复制任何
  回声雾/瓷墙/洞察/静默/铁幕/吸声地板的修正规则。
- **只读**：不改世界状态、不触发脉冲、不消耗全局随机数；只读取半径与来源。
- **只描述真实发声入口**：踩踏空鼓地板、构想「回响」、物品「汽笛」、
  投掷「蜂鸣诱饵」落地、装备发射载荷 ``spec['pulse']``。普通近战没有统一
  脉冲入口，因此这里不提供「近战半径」；普通投掷物落地也不发声，预览返回
  静音而不是虚报半径。
"""

from __future__ import annotations

from typing import Any

# 真实发声入口的基础半径（与 core/actions、core/throwing 的实参一一对应）。
ECHO_PULSE_BASE = 10
ECHO_PULSE_FREEZE_NEAR = 0
THROW_LURE_BASE = 8
WHISTLE_DEFAULT_BASE = 8
WHISTLE_FREEZE_NEAR = 1

# 投掷落点效果类别：只列会真正产生落地行为的类别；其余一律「普通落地」。
# 声音仍是独立维度：只有 effect == 'sound_lure' 的蜂鸣诱饵在落点发声。
THROW_LANDING_EFFECTS = {
    "explosion": "爆炸",
    "fireburst": "引火",
    "tar_burst": "引火",
    "ignite_burst": "火星",
    "spark_rays": "火星",
    "smoke_cloud": "浓烟",
    "sound_lure": "响声",
}
PLAIN_LANDING = "普通落地"


def _origin_xy(origin: Any) -> tuple[int, int]:
    """接受 ``Entity``/``WorldItem`` 一类带 x/y 的对象或 (x, y) 元组。"""
    if hasattr(origin, "x") and hasattr(origin, "y"):
        return int(origin.x), int(origin.y)
    return int(origin[0]), int(origin[1])


def pulse_preview(
    state: Any,
    origin: Any,
    base: int,
    *,
    by_player: bool = True,
    full_alert: bool = False,
    note_key: str = "",
    freeze_near: int = 0,
    category: str = "generic",
) -> dict[str, Any]:
    """一次脉冲的读只预览：半径与实际 ``_sound_pulse`` 完全同口径。

    返回 dict 含 ``base``、``origin``、``radius``（实际生效值，静音为 0）、
    ``sources``（逐条修正来源）、``silent``、``full_alert``、``by_player``、
    ``freeze_near`` 与 ``note_key``（发声入口标识，供界面取词）。
    """
    x, y = _origin_xy(origin)
    base = int(base)
    # 唯一一次半径计算：下一行与 _sound_pulse 内部完全相同，不另算一套。
    radius, sources = state._pulse_radius_breakdown(x, y, base, by_player=by_player,
                                                    category=category)
    radius = max(0, int(radius))
    return {
        "base": base,
        "origin": (x, y),
        "radius": radius,
        "sources": list(sources),
        "silent": radius <= 0,
        "full_alert": bool(full_alert),
        "by_player": bool(by_player),
        "freeze_near": int(freeze_near),
        "note_key": note_key,
    }


# ---------------------------------------------------------------------------
# 实际发声入口的语义包装
# ---------------------------------------------------------------------------


def footstep_preview(state: Any, origin: Any = None) -> dict[str, Any]:
    """踩踏声响：地板足音与液面接触声取较大值；安静落脚面为 0。"""
    from ..i18n import tr
    from ..materials import floor_effect_for

    if origin is None:
        origin = (state.player.x, state.player.y)
    x, y = _origin_xy(origin)
    base, step_sources = state._step_noise_breakdown(
        x, y, expose_kind=bool(state.is_visible(x, y)))
    floor = floor_effect_for(state.cell(x, y))
    quiet = state._step_noise_reduction_for(x, y)
    preview = pulse_preview(state, (x, y), max(1, base - quiet) if base else 0,
                            by_player=True, note_key="踩踏声响", category="step")
    preview['base'] = base
    preview['sources'][:0] = step_sources
    if base:
        preview['sources'].insert(0, tr('{name}落脚 {n}',
                                        name=tr(floor.variant), n=floor.footstep))
    if quiet and base:
        preview['sources'].insert(0, tr('脚步准备 −{n}', n=quiet))
    return preview


def echo_ability_preview(state: Any, origin: Any = None) -> dict[str, Any]:
    """The moving echo's next real pulse, including its predicted source."""
    if origin is None:
        from .construct_environments import active, echo_step
        echoes = [field for field in active(state) if field['kind'] == 'echo_pulse']
        position = echoes[-1]['position'] if echoes else (state.player.x, state.player.y)
        direction = echoes[-1]['direction'] if echoes else state.facing
        origin, _ = echo_step(state, position, direction)
    return pulse_preview(
        state,
        origin,
        ECHO_PULSE_BASE,
        by_player=True,
        freeze_near=ECHO_PULSE_FREEZE_NEAR,
        note_key="回声脉冲（构想）",
        category="lure",
    )


def throw_landing_effect(item: Any) -> str:
    """投掷落点的效果类别（界面取词键）；非发声类也可能有爆炸/引火等效果。"""
    return THROW_LANDING_EFFECTS.get(getattr(item, "effect", None), PLAIN_LANDING)


def throw_landing_preview(state: Any, item: Any, landing: Any) -> dict[str, Any]:
    """投掷落地：只有蜂鸣诱饵（``sound_lure``）在落点发半径 8 的强诱引。"""
    base = THROW_LURE_BASE if getattr(item, "effect", None) == "sound_lure" else 0
    preview = pulse_preview(
        state,
        landing,
        base,
        by_player=True,
        full_alert=bool(base),
        note_key="投掷落点",
        category="lure",
    )
    preview["landing_effect"] = throw_landing_effect(item)
    preview["emits_on_landing"] = bool(base)
    return preview


def item_use_preview(state: Any, item: Any) -> dict[str, Any]:
    """物品使用：只有汽笛（``blast_lure``）在玩家格发基础 ``power`` 的强诱引。"""
    origin = (state.player.x, state.player.y)
    if getattr(item, "effect", None) == "blast_lure":
        base = int(getattr(item, "power", 0) or WHISTLE_DEFAULT_BASE)
        preview = pulse_preview(
            state,
            origin,
            base,
            by_player=True,
            full_alert=True,
            freeze_near=WHISTLE_FREEZE_NEAR,
            note_key="汽笛长鸣",
            category="lure",
        )
        preview["emits_on_use"] = True
        return preview
    preview = pulse_preview(state, origin, 0, by_player=True, note_key="物品使用")
    preview["emits_on_use"] = False
    return preview


def equipment_pulse_preview(state: Any, target: Any, spec: Any) -> dict[str, Any]:
    """装备发射载荷 ``spec['pulse']``：命中时在目标格发声。"""
    payload = spec or {}
    base = int(payload.get("pulse") or 0)
    return pulse_preview(state, target, base, by_player=True, note_key="发射载荷响声",
                         category="projectile")


def equipment_pulse_base(item: Any) -> int:
    """从物品定义读取发射载荷半径（无 ``fire.pulse`` 的物品为 0）。"""
    from .content import ITEM_DEFINITIONS

    definition = ITEM_DEFINITIONS.get(getattr(item, "definition_id", ""), {})
    fire = definition.get("fire") or {}
    try:
        return int(fire.get("pulse") or 0)
    except (TypeError, ValueError):
        return 0


def item_sound_previews(state: Any, item: Any) -> list[dict[str, Any]]:
    """物品详情用：只返回**真实发声物品**的预览，不发声物品返回空列表。

    - 汽笛：使用时的发声点就是玩家所在格，可给出实际半径（含环境修正）。
    - 蜂鸣诱饵：发声点在落点，详情只给基础半径（实际值按落点环境修正）。
    - 带 ``fire.pulse`` 的装备（音爆哨）：发声点在命中格，详情只给基础半径。
    """
    effect = getattr(item, "effect", None)
    if effect == "blast_lure":
        preview = item_use_preview(state, item)
        preview["origin_kind"] = "player"
        return [preview]
    if effect == "sound_lure":
        return [
            {
                "base": THROW_LURE_BASE,
                "origin": None,
                "radius": None,
                "sources": [],
                "silent": False,
                "full_alert": True,
                "by_player": True,
                "freeze_near": 0,
                "note_key": "蜂鸣诱饵落地",
                "origin_kind": "landing",
            }
        ]
    pulse = equipment_pulse_base(item)
    if pulse > 0:
        return [
            {
                "base": pulse,
                "origin": None,
                "radius": None,
                "sources": [],
                "silent": False,
                "full_alert": False,
                "by_player": True,
                "freeze_near": 0,
                "note_key": "装备载荷命中",
                "origin_kind": "target",
            }
        ]
    return []


# 语义化短名：与任务里列举的动作名一一对应（长的 *_preview 名保持权威实现）。
footstep = footstep_preview
echo_ability = echo_ability_preview
throw_landing = throw_landing_preview
item_use = item_use_preview
equipment_pulse = equipment_pulse_preview
