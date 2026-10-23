"""Deterministic, persistent entrances for the two authored five-floor realms."""
from __future__ import annotations

from collections import deque
import random

from .entities import WorldEvent


ENTRY_RULES = {
    "library_palace": (16, 22, 1.0, 0x4C494247, "无名藏书门厅", "#e8d7a7"),
    "white_sanatorium": (21, 26, 0.70, 0x484F5350, "未填写的入院单", "#dcdcdf"),
}


def plan_entries(state):
    for realm, (lo, hi, chance, salt, name, color) in ENTRY_RULES.items():
        if realm not in state.realm_entry_state:
            rng = random.Random(state.seed ^ salt)
            state.realm_entry_state[realm] = {
                "exists": rng.random() < chance, "layer": rng.randint(lo, hi),
                "uid": f"{state.seed}:realm-entry:{realm}", "version": 1,
            }


def _reachable(state):
    from ..materials import DOOR_KINDS
    blocked = {(e.x, e.y) for e in state.enemies if e.integrity > 0}
    seen = {(state.player.x, state.player.y)}
    queue = deque(seen)
    while queue:
        x, y = queue.popleft()
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                p = x+dx, y+dy
                if p in seen or not (0 < p[0] < state.width-1 and 0 < p[1] < state.height-1):
                    continue
                cell = state.cell(*p)
                if p in blocked:
                    continue
                if "enlarged" in state.portents and state._cell_too_narrow_for_enlarged(*p):
                    continue
                if not cell.solid or cell.wall_kind in DOOR_KINDS:
                    seen.add(p)
                    queue.append(p)
    return seen


def spawn_entries(state):
    from ..data.dreams import realm_def
    if state.realm_id:
        return
    plan_entries(state)
    reachable = None
    for realm, rule in ENTRY_RULES.items():
        record = state.realm_entry_state[realm]
        if (not record["exists"] or record["layer"] != state.depth
                or realm in state.closed_realms or realm_def(realm) is None):
            continue
        event_id = f"realm_gate.{realm}"
        if any(e.event_id == event_id for e in state.events):
            continue
        if reachable is None:
            reachable = _reachable(state)
        occupied = {(e.x, e.y) for e in state.enemies if e.integrity > 0}
        occupied |= {(e.x, e.y) for e in state.events}
        occupied |= {(i.x, i.y) for i in state.world_items}
        occupied |= {(state.player.x, state.player.y)}
        candidates = sorted(p for p in reachable if p not in occupied
                            and not state.cell(*p).solid)
        rng = random.Random(state.seed ^ rule[3] ^ state.depth*3571)
        rng.shuffle(candidates)
        full = None
        for x, y in candidates:
            if not (3 <= x < state.width-3 and 3 <= y < state.height-3):
                continue
            region = [(x+dx, y+dy) for dx in range(-2, 3) for dy in range(-2, 3)]
            if all(p not in occupied and not state.cell(*p).solid
                   and not state.cell(*p).liquid and not state.cell(*p).gas
                   and not state.cell(*p).flame and not state.cell(*p).wire
                   for p in region):
                if not state.path_to(x, y, respect_map_knowledge=False):
                    continue
                full = (x, y)
                break
        # Very narrow layer forms keep a reachable directory without blocking
        # their only passage. The full vestibule is preferred whenever it fits.
        anchor = full or next((p for p in candidates
                               if not state.cell(*p).flame
                               and not state.cell(*p).liquid
                               and not state.cell(*p).gas
                               and state.path_to(*p, respect_map_knowledge=False)), None)
        if anchor is None:
            anchor = state.player.x, state.player.y
        x, y = anchor
        record["anchor"] = [x, y]
        record["layout"] = "vestibule" if full else "compact_directory"
        radius = 2 if full else 0
        color = rule[5]
        state.realm_bg_zones.append({"rect": (x-radius, y-radius, x+radius, y+radius), "color": color})
        if full:
            for sx, sy in ((x-2, y-1), (x+2, y-1)):
                state.configure_wall(state.cell(sx, sy), "木桌子")
        name = rule[4]
        if realm == "library_palace":
            description = "淡黄地板与整齐书架间，一张空白目录台等待着借阅者。"
            dialogue = ("借条上的日期尚未到来。签名处已经有你的笔迹。",)
            label = "借阅尚未发生的书"
        else:
            description = "一张空白入院单放在洁白而明亮的台面上。"
            dialogue = ("灯亮起来时，白瓷上的影子都无处藏身。", "入院单还在等一个名字。")
            label = "填写一个尚未存在的名字"
        state.events.append(WorldEvent(event_id=event_id, catalog_id=event_id, name=name,
                                       x=x, y=y, description=description, kind="compound",
                                       dialogue=dialogue,
                                       options=({"label": label, "enter_realm": realm},
                                                {"label": "暂不进入", "leave": True}),
                                       bound=True, dissolution_reward=0))
        from ..i18n import tr
        state.messages.append(tr("地图上出现了一扇「{name}」。", name=tr(name)))
