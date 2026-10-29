"""记忆碎片的「缓冲」通道（2026-10-25 扩展包接入）。

扩展包目录里多数记忆写作「某件事第一次发生时少受一点」。那既不是常驻属性
（``stat``），也不是一路挡住（``resistance``），而是**用掉就没了的一次性缓冲**。
这里提供唯一入口：结算方报出自己的通道名，框架按当前槽里的碎片决定这次吸收
多少，并登记消耗——作用域决定它什么时候重新装满。

通道命名与结算点一一对应，结算方不要再另开分支：

- ``noise:<category>``    自身声音的实际声径（``enemies._sound_radius_breakdown``）
- ``portent:<portent_id>`` 沾染某征兆时的时长（``portents._apply_direct_portent``）
- ``<resource>:<reason>``  资源负向结算（``settlement.settle_delta``）

条目形状（写在 ``MEMORY_FRAGMENT_EFFECTS`` 里，复合碎片可含多条）::

    {"kind": "buffer", "channel": "portent:shocked", "amount": 1,
     "scope": "per_layer", "trigger": {"quiet_turns": 2},
     "short": ..., "detail": ...}

``scope`` ∈ run / layer / encounter / cooldown:N；``encounter`` 需要结算方传
``token``（同一异象、同一武器实例…）。``trigger`` 只是「这次能不能用」的前提，
不满足时缓冲不消耗，留给下一次。
"""

from __future__ import annotations

from typing import Any, Iterator

from ..data.items import ITEM_DEFINITIONS
from ..data.memory import MEMORY_FRAGMENT_EFFECTS
from ..i18n import tr


def _entries(effect: dict[str, Any]) -> tuple[dict[str, Any], ...]:
    if effect.get("kind") == "compound":
        return tuple(effect.get("effects") or ())
    return (effect,)


def _candidates(state: Any, channel: str) -> Iterator[tuple[str, dict[str, Any], str]]:
    for fragment_id in state.memory_fragments:
        definition = ITEM_DEFINITIONS.get(fragment_id, {})
        effect_name = definition.get("memory_effect")
        effect = MEMORY_FRAGMENT_EFFECTS.get(effect_name or "")
        if not effect:
            continue
        for entry in _entries(effect):
            if entry.get("kind") == "buffer" and entry.get("channel") == channel:
                yield fragment_id, entry, str(
                    entry.get("short") or effect.get("short") or definition.get("name") or "")


def _scope_key(state: Any, entry: dict[str, Any], token: Any) -> "str | None":
    scope = str(entry.get("scope") or "layer")
    if scope == "run":
        return "R"
    if scope == "encounter":
        return None if token is None else f"E{token}"
    if scope.startswith("cooldown"):
        turns = max(1, int(scope.split(":", 1)[1]) if ":" in scope
                    else int(entry.get("recovery_turns") or 1))
        return f"C{int(getattr(state, 'time', 0)) // turns}"
    return f"L{int(getattr(state, 'depth', 0))}"


def _trigger_met(state: Any, trigger: dict[str, Any] | None) -> bool:
    if not trigger:
        return True
    player = getattr(state, "player", None)
    held = set(getattr(player, "portents", {}) or {})
    wanted = trigger.get("portent")
    if wanted is not None:
        wanted = set(wanted if isinstance(wanted, (list, tuple, set)) else (wanted,))
        if not held & wanted:
            return False
    blocked = trigger.get("no_portent")
    if blocked is not None:
        blocked = set(blocked if isinstance(blocked, (list, tuple, set)) else (blocked,))
        if held & blocked:
            return False
    if "depth_min" in trigger and int(getattr(state, "depth", 0)) < int(trigger["depth_min"]):
        return False
    if trigger.get("waited"):
        # 「正常等待后」才装得满：listen_until 由 wait 覆盖当次与随后一个真实回合。
        # 0 是「从没等过」的初值而非「等到第 0 回合」，所以必须为正。
        if int(getattr(state, "listen_until", 0)) <= 0 or int(
                getattr(state, "listen_until", 0)) < int(getattr(state, "time", 0)):
            return False
    window = trigger.get("quiet_turns")
    heard = trigger.get("heard")
    if window is not None or heard is not None:
        since = int(getattr(state, "time", 0)) - int(
            window if window is not None else trigger.get("within", 3))
        own_events = [event for event in (getattr(state, "_ambient_noise_events", None) or ())
                      if len(event) >= 8 and int(event[0]) >= since and event[6]]
        if window is not None and any(int(event[5]) > 1 for event in own_events):
            return False
        if heard is not None and not any(str(event[7]) == str(heard) for event in own_events):
            return False
    return True


def peek(state: Any, channel: str, *, token: Any = None) -> int:
    """这次能吸收多少（只读，供浮层与数值来源展示，绝不消耗）。"""
    for _fragment_id, entry, _short in _available(state, channel, token=token):
        return max(0, int(entry.get("amount", 0)))
    return 0


def available(state: Any, channel: str, *, token: Any = None
              ) -> tuple[tuple[str, int, str], ...]:
    """当前可触发的缓冲（碎片 id、额度、一句效果）——只读，供面板报价。"""
    return tuple((fragment_id, max(0, int(entry.get("amount", 0))), short)
                 for fragment_id, entry, short in _available(state, channel, token=token))


def spend_entry(state: Any, channel: str, *, token: Any = None
                ) -> "tuple[int, dict[str, Any]] | None":
    """消费一次缓冲并登记，返回（额度, 条目）；没有可用缓冲时返回 None。

    每次触发只由一条碎片付款：槽里同通道有多条时按装槽顺序取第一条，与
    ``memory_stat_bonus`` 的「同类取最高」一样，避免同一次触发叠两层减免。
    """
    for fragment_id, entry, short in _available(state, channel, token=token):
        absorbed = max(0, int(entry.get("amount", 0)))
        if not absorbed:
            continue
        _ledger(state)[fragment_id] = _scope_key(state, entry, token) or ""
        if short:
            state.messages.append(tr("缓冲生效：{name}。", name=tr(short)))
        return absorbed, entry
    return None


def spend(state: Any, channel: str, *, token: Any = None) -> int:
    """按额度消费一次缓冲（时长／资源这类「数量就是数值」的通道）。"""
    paid = spend_entry(state, channel, token=token)
    return 0 if paid is None else paid[0]


def reduce_noise(state: Any, category: str, radius: int) -> int:
    """自身声音的缓冲：``absorb`` 整声吞掉，否则声径 −额度（最低 1）。

    「少响一点」与「这一声没有」是两种承诺，条目里自己声明；声径类
    永远保留 1 格，缓冲不该把脚步变成隐身。
    """
    paid = spend_entry(state, f"noise:{category}")
    if paid is None:
        return radius
    absorbed, entry = paid
    if entry.get("absorb"):
        return 0
    return max(1, int(radius) - absorbed)


def _available(state: Any, channel: str, *, token: Any = None
               ) -> Iterator[tuple[str, dict[str, Any], str]]:
    spent = _ledger(state)
    for fragment_id, entry, short in _candidates(state, channel):
        if not _trigger_met(state, entry.get("trigger")):
            continue
        key = _scope_key(state, entry, token)
        if key is None or spent.get(fragment_id) == key:
            continue
        yield fragment_id, entry, short


def _ledger(state: Any) -> dict[str, str]:
    ledger = getattr(state, "memory_buffers", None)
    if ledger is None:
        ledger = {}
        state.memory_buffers = ledger
    return ledger


def forget(state: Any, fragment_id: str) -> None:
    """碎片出槽时清掉它的消耗登记——重新装回来应当是满的。"""
    _ledger(state).pop(fragment_id, None)
