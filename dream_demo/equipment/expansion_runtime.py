"""Runtime helpers for the targeted practical equipment revisions.

Only catalog entries explicitly marked ``runtime`` are exposed here. The board
compiler remains the authority: an effect is live only when its completed
equipment sentence produced an active compiled Ability.
"""
from __future__ import annotations

from typing import Any

NON_DAMAGING_CONSTRUCTS = frozenset({
    "combat.backdraft_screen", "farsight", "smoke_veil", "wide_develop",
    "develop", "listen_realm", "mirror_stance", "blur", "rewire",
    "resonance", "nightmare_fuel", "condense_dew", "sow_green", "wax_seal",
    "draw_liquid", "ice_bridge", "transpire", "dissolve_wall", "raise_terrain",
    "sink_terrain", "conjure_wall", "rewrite_corner", "blink", "deep_breath",
    "calm_incense", "purge_wind", "pixel_surge", "mute_protocol",
})


def active_effects(state: Any, effect: str) -> tuple[Any, ...]:
    equipment = getattr(state, "equipment", None)
    if equipment is None:
        return ()
    return tuple(ability for ability in equipment.compiled().abilities
                 if ability.effect == effect)


def params(ability: Any) -> dict[str, Any]:
    return dict(getattr(ability, "profile", ()) or ())


def ready(state: Any, ability: Any, key: str = "") -> bool:
    instance_id = str(getattr(ability, "instance_id", ""))
    timer = f"expansion:{instance_id}:{key or ability.effect}"
    return int(getattr(state, "board_cooldowns", {}).get(timer, 0)) <= int(state.time)


def claim(state: Any, ability: Any, cooldown: int, key: str = "") -> None:
    instance_id = str(getattr(ability, "instance_id", ""))
    timer = f"expansion:{instance_id}:{key or ability.effect}"
    state.board_cooldowns[timer] = int(state.time) + max(0, int(cooldown))


def target_turn_claim(state: Any, ability: Any, target: str, *, key: str = "turn") -> bool:
    """Claim an effect once per target in the current world turn."""
    instance_id = str(getattr(ability, "instance_id", ""))
    ledger_key = f"expansion_claim:{instance_id}:{key}"
    marks = state.equipment_marks.setdefault(ledger_key, {})
    turn = int(state.time)
    target = str(target)
    if marks.get(target) == turn:
        return False
    marks[target] = turn
    # Keep save data bounded when the same item is used over a long run.
    if len(marks) > 128:
        for old_target, old_turn in tuple(marks.items()):
            if int(old_turn) < turn - 2:
                marks.pop(old_target, None)
    return True


def imagination_cost(state: Any, cost: int, effects: tuple[str, ...], *,
                     extra: int = 0) -> int:
    base = max(0, int(cost)) + max(0, int(extra))
    if base <= 0:
        return 0
    reduction = 0
    for effect in effects:
        for ability in active_effects(state, effect):
            reduction += int(params(ability).get("imagination_reduction", 0) or 0)
    # The catalog contract caps combined cost reduction at two native points.
    return max(1, base - min(2, reduction))


def adjust_tamper_chaos(state: Any, chaos: int) -> int:
    return tamper_chaos_quote(state, chaos)[0]


def tamper_chaos_quote(state: Any, chaos: int) -> tuple[int, tuple[str, ...]]:
    value = max(0, int(chaos))
    claimed = []
    for ability in active_effects(state, "tamper_chaos"):
        if not ready(state, ability):
            continue
        reduction = int(params(ability).get("chaos_reduction", 0) or 0)
        if value > int(params(ability).get("minimum_gain", 0) or 0) and reduction > 0:
            value = max(int(params(ability).get("minimum_gain", 0) or 0), value - reduction)
            claimed.append(str(ability.instance_id))
        break
    return value, tuple(claimed)


def claim_tamper_feedback(state: Any, instance_ids: tuple[str, ...] = ()) -> None:
    for ability in active_effects(state, "tamper_chaos"):
        if ability.instance_id in instance_ids and ready(state, ability):
            claim(state, ability, int(params(ability).get("cooldown_turns", 0) or 0))


def tamper_damage(state: Any, *, enemy: bool, terrain: bool) -> int:
    amount = 0
    for ability in active_effects(state, "tamper_damage"):
        profile = params(ability)
        amount += int(profile.get("enemy_trauma_bonus", 0) or 0) if enemy else 0
        amount += int(profile.get("terrain_damage_bonus", 0) or 0) if terrain else 0
    return amount


def tamper_target_slow(state: Any, target: Any) -> bool:
    for ability in active_effects(state, "tamper_slow"):
        if not ready(state, ability):
            continue
        duration = int(params(ability).get("duration_turns", 1) or 1)
        if state._apply_direct_portent(target, "slow_turns", duration, mode="max"):
            claim(state, ability, int(params(ability).get("cooldown_turns", 0) or 0))
            return True
    return False


def tamper_noise_radius(state: Any, radius: int) -> int:
    value = max(0, int(radius))
    for ability in active_effects(state, "tamper_noise"):
        profile = params(ability)
        value = max(int(profile.get("minimum_radius", 0) or 0),
                    value - int(profile.get("ordinary_noise_radius_reduction", 0) or 0))
    return value


def nearest_tamper_radius(state: Any, base: int) -> int:
    bonus = sum(int(params(ability).get("range_bonus_cells", 0) or 0)
                for ability in active_effects(state, "tamper_range"))
    return max(0, int(base)) + min(2, bonus)


def _current_cast(state) -> dict[str, Any] | None:
    cast = getattr(state, "_expansion_construct_cast", None)
    return cast if isinstance(cast, dict) else None


def begin_construct(state: Any, ability_id: str, target=None) -> None:
    previous = getattr(state, "_expansion_construct_cast", None)
    if hasattr(target, "x") and hasattr(target, "y"):
        target = (int(target.x), int(target.y))
    elif isinstance(target, (list, tuple)) and len(target) >= 2:
        target = (int(target[0]), int(target[1]))
    else:
        target = None
    state._expansion_construct_cast = {
        "ability_id": str(ability_id), "target": target,
        "origin": (int(state.player.x), int(state.player.y)),
        "imagination_at_start": int(state.imagination),
        "claims": set(), "hits": 0, "damage_applied": False,
        "_previous": previous,
    }


def end_construct(state: Any) -> None:
    cast = getattr(state, "_expansion_construct_cast", None)
    if not isinstance(cast, dict):
        return
    previous = cast.get("_previous")
    if previous is None:
        delattr(state, "_expansion_construct_cast")
    else:
        state._expansion_construct_cast = previous


def construct_range_bonus(state: Any) -> int:
    for ability in active_effects(state, "two_step_construct_range"):
        mark = state.equipment_marks.get(f"expansion_move_charge:{ability.instance_id}", {})
        if int(mark.get("until", 0) or 0) >= int(state.time):
            return int(params(ability).get("range_bonus_cells", 0) or 0)
    return 0


def relocate_construct_sound(state: Any, x: int, y: int) -> tuple[int, int]:
    """Move only the construct's ordinary origin sound to its confirmed target."""
    cast = _current_cast(state)
    if cast is None or cast.get("sound_relocated"):
        return int(x), int(y)
    origin = cast.get("origin")
    target = cast.get("target")
    if origin != (int(x), int(y)) or target is None:
        return int(x), int(y)
    if not active_effects(state, "relocate_cast_sound"):
        return int(x), int(y)
    cast["sound_relocated"] = True
    return int(target[0]), int(target[1])


def consume_construct_range(state: Any) -> None:
    for ability in active_effects(state, "two_step_construct_range"):
        state.equipment_marks.pop(f"expansion_move_charge:{ability.instance_id}", None)


def note_player_move(state: Any, origin: tuple[int, int], destination: tuple[int, int]) -> None:
    for ability in active_effects(state, "two_step_construct_range"):
        key = f"expansion_move_path:{ability.instance_id}"
        path = state.equipment_marks.get(key, {})
        if int(path.get("until", 0) or 0) < int(state.time):
            path = {"moves": 0, "cells": [], "until": int(state.time) + 3}
        cells = list(path.get("cells", ()))
        if not cells:
            cells.append([int(origin[0]), int(origin[1])])
        cells.append([int(destination[0]), int(destination[1])])
        path["moves"] = int(path.get("moves", 0)) + 1
        path["cells"] = cells[-4:]
        path["until"] = int(state.time) + 3
        state.equipment_marks[key] = path
        distinct = {tuple(cell) for cell in path["cells"]}
        required_moves = int(params(ability).get("required_moves", 2) or 2)
        if (path["moves"] >= required_moves
                and len(distinct) >= int(params(ability).get("distinct_cells", 3))):
            state.equipment_marks[f"expansion_move_charge:{ability.instance_id}"] = {
                "until": int(state.time) + int(params(ability).get("charge_duration_turns", 3))
            }
            state.equipment_marks.pop(key, None)


def adjust_construct_cost(state: Any, ability_id: str, cost: int) -> int:
    radius_effect = ("construct_radius" in {
        ability.effect for ability in active_effects(state, "construct_radius")
    } and ability_id == "combat.fault_ring")
    extra = 0
    if radius_effect:
        for ability in active_effects(state, "construct_radius"):
            extra = max(extra, int(params(ability).get("extra_imagination", 0) or 0))
    effects = ("construct_cost",)
    if not radius_effect:
        effects += ("focused_construct_cost",)
    return imagination_cost(state, cost, effects, extra=extra)


def construct_cooldown(state: Any, ability_id: str, cooldown: int, *,
                       non_damaging: bool = False) -> int:
    value = max(1, int(cooldown))
    if not non_damaging:
        return value
    for ability in active_effects(state, "utility_construct_cooldown"):
        if ready(state, ability):
            reduced = max(int(params(ability).get("minimum_cooldown", 1) or 1),
                          value - int(params(ability).get("cooldown_reduction_turns", 0) or 0))
            if reduced < value:
                value = reduced
                claim(state, ability, int(params(ability).get("cooldown_turns", 0) or 0))
            break
    return value


def note_world_action(state: Any, *, kind=None) -> None:
    """Build the external-light charge only from a real fixed mechanical source."""
    if kind is not None:
        from ..core.constants import ActionKind
        if kind != ActionKind.MOVE:
            for key in tuple(state.equipment_marks):
                if key.startswith("expansion_move_path:"):
                    state.equipment_marks.pop(key, None)
    abilities = active_effects(state, "external_light_construct_damage")
    if not abilities:
        return
    from ..core.vision.glow import _lit_cells
    from ..data.light_sources import light_spec_for_cell

    lit_by_external_source = False
    for cell in _lit_cells(state, state.player.x, state.player.y):
        spec = light_spec_for_cell(cell)
        if spec is not None and spec.mechanical:
            lit_by_external_source = True
            break
    for ability in abilities:
        key = f"expansion_light_charge:{ability.instance_id}"
        mark = state.equipment_marks.get(key, {})
        if not lit_by_external_source:
            state.equipment_marks.pop(key, None)
            continue
        if not mark:
            state.equipment_marks[key] = {"since": int(state.time)}
            continue
        if int(state.time) - int(mark.get("since", state.time)) >= int(
                params(ability).get("charge_time_turns", 1)):
            mark["until"] = int(state.time) + int(
                params(ability).get("charge_duration_turns", 4))
            state.equipment_marks[key] = mark


def construct_damage_bonus(state: Any, target: Any) -> int:
    cast = _current_cast(state)
    if cast is None or target is None:
        return 0
    amount = 0
    for ability in active_effects(state, "external_light_construct_damage"):
        key = f"expansion_light_charge:{ability.instance_id}"
        mark = state.equipment_marks.get(key, {})
        claim_key = f"light:{ability.instance_id}"
        if (ready(state, ability, "light_recharge")
                and int(mark.get("until", 0) or 0) >= int(state.time)
                and claim_key not in cast["claims"]):
            amount += int(params(ability).get("trauma_bonus", 0) or 0)
            cast["claims"].add(claim_key)
            state.equipment_marks.pop(key, None)
            claim(state, ability, int(params(ability).get("recharge_cooldown_turns", 0) or 0),
                  "light_recharge")

    target_key = str(getattr(target, "id", ""))
    is_melee_construct = cast["ability_id"] in {
        "combat.beat_cut", "combat.cross_step", "combat.arc_slash"}
    for ability in active_effects(state, "construct_melee_mark"):
        if not is_melee_construct:
            continue
        key = f"expansion_melee_mark:{ability.instance_id}"
        mark = state.equipment_marks.get(key, {})
        if mark and int(mark.get("until", 0) or 0) < int(state.time):
            state.equipment_marks.pop(key, None)
            mark = {}
        if mark.get("target") == target_key and int(mark.get("until", 0) or 0) >= int(state.time):
            amount += int(params(ability).get("melee_trauma_bonus", 0) or 0)
            state.equipment_marks.pop(key, None)

    for feedback in active_effects(state, "consume_mark_for_cooldown"):
        if not is_melee_construct or not ready(state, feedback):
            continue
        key = f"expansion_melee_mark:{feedback.instance_id}"
        mark = state.equipment_marks.get(key, {})
        if (mark.get("target") != target_key
                or int(mark.get("until", 0) or 0) < int(state.time)):
            continue
        marked_construct = str(mark.get("ability_id") or "")
        remaining = int(state.ability_cooldowns.get(marked_construct, 0) or 0)
        if remaining <= 0:
            continue
        profile = params(feedback)
        state.ability_cooldowns[marked_construct] = max(
            int(profile.get("minimum_remaining_cooldown", 1) or 1),
            remaining - int(profile.get("cooldown_reduction_turns", 0) or 0))
        claim(state, feedback, 4)
        state.equipment_marks.pop(key, None)
        cast["claims"].add(f"mark:{feedback.instance_id}")

    for ability in active_effects(state, "consume_flame_for_construct_damage"):
        claim_key = f"consume-flame:{ability.instance_id}"
        if "consume-flame-checked" in cast["claims"]:
            continue
        cast["claims"].add("consume-flame-checked")
        cell = state.cell(target.x, target.y)
        flame_cost = int(params(ability).get("flame_strength_cost", 1) or 1)
        if cell.flame >= flame_cost and claim_key not in cast["claims"]:
            state._set_flame(target.x, target.y, max(0, int(cell.flame) - flame_cost))
            amount += int(params(ability).get("trauma_bonus", 0) or 0)
            cast["claims"].add(claim_key)
    return amount


def on_construct_hit(state: Any, target: Any, *, killed: bool) -> None:
    cast = _current_cast(state)
    if cast is None or target is None:
        return
    cast["hits"] += 1
    cast["damage_applied"] = True
    target_key = str(getattr(target, "id", ""))
    cast.setdefault("first_target_id", target_key)
    cast["last_target_id"] = target_key

    for ability in active_effects(state, "construct_melee_mark"):
        claim_key = f"mark:{ability.instance_id}"
        key = f"expansion_melee_mark:{ability.instance_id}"
        if claim_key not in cast["claims"]:
            cast["claims"].add(claim_key)
            if not killed and key not in state.equipment_marks:
                state.equipment_marks[key] = {
                    "target": target_key,
                    "ability_id": str(cast["ability_id"]),
                    "until": int(state.time) + int(params(ability).get("mark_duration_turns", 2)),
                }


    if killed:
        for ability in active_effects(state, "construct_kill_refund"):
            claim_key = f"refund:{ability.instance_id}"
            if claim_key in cast["claims"] or not ready(state, ability):
                continue
            profile = params(ability)
            paid = max(0, int(cast.get("imagination_at_start", state.imagination))
                       - int(state.imagination))
            maximum_refund = max(0, paid - int(profile.get("minimum_net_cost", 1) or 1))
            amount = min(int(profile.get("imagination_refund", 0) or 0), maximum_refund)
            if amount:
                state.restore_resource("imagination", amount)
                claim(state, ability, int(params(ability).get("cooldown_turns", 0) or 0))
                cast["claims"].add(claim_key)
            break
        for ability in active_effects(state, "construct_kill_afterblast"):
            claim_key = f"afterblast:{ability.instance_id}"
            if claim_key in cast["claims"] or not ready(state, ability):
                continue
            profile = params(ability)
            extra = int(profile.get("extra_imagination", 0) or 0)
            if int(state.imagination) < extra:
                continue
            if extra:
                state._pay_ability_cost(extra)
            claim(state, ability, int(profile.get("cooldown_turns", 0) or 0))
            cast["claims"].add(claim_key)
            state._explode(target.x, target.y,
                           int(profile.get("radius_cells", 1) or 1),
                           int(profile.get("power", 1) or 1), from_player=True)
            break


def consume_melee_mark(state: Any, target: Any) -> int:
    """The next real melee hit consumes L-E14, including ordinary attacks."""
    amount = 0
    for ability in active_effects(state, "construct_melee_mark"):
        key = f"expansion_melee_mark:{ability.instance_id}"
        mark = state.equipment_marks.get(key, {})
        if int(mark.get("until", -1)) < int(state.time):
            state.equipment_marks.pop(key, None)
        elif mark.get("target") == str(target.id):
            amount += int(params(ability).get("melee_trauma_bonus", 0) or 0)
            state.equipment_marks.pop(key, None)
    return amount


def after_construct(state: Any, result: Any) -> None:
    cast = _current_cast(state)
    if cast is None or not getattr(result, "changed", False):
        return
    ability_id = str(cast.get("ability_id") or "")
    if ability_id in NON_DAMAGING_CONSTRUCTS:
        current = int(state.ability_cooldowns.get(ability_id, 1) or 1)
        state.ability_cooldowns[ability_id] = construct_cooldown(
            state, ability_id, current, non_damaging=True)
    for ability in active_effects(state, "cast_lucidity_guard"):
        if ready(state, ability):
            state.equipment_marks[f"expansion_lucidity_guard:{ability.instance_id}"] = {
                "charges": int(params(ability).get("max_charges", 1) or 1),
                "until": int(state.time) + int(params(ability).get("duration_turns", 2) or 2),
            }
            claim(state, ability, int(params(ability).get("cooldown_turns", 0) or 0))
            break

    if cast["hits"]:
        for ability in active_effects(state, "construct_blind"):
            if ready(state, ability):
                data = getattr(result, "data", {}) or {}
                target_id = str(cast.get("first_target_id") or data.get("hit") or "")
                target = next((enemy for enemy in state.enemies if enemy.id == target_id), None)
                if target is not None and target.integrity > 0:
                    if state._apply_direct_portent(target, "blinded",
                            int(params(ability).get("duration_turns", 1) or 1), mode="max"):
                        claim(state, ability, int(params(ability).get("cooldown_turns", 0) or 0))
                break
        for ability in active_effects(state, "construct_fresh_target_slow"):
            if not ready(state, ability):
                continue
            target_id = str(cast.get("first_target_id") or "")
            target = next((enemy for enemy in state.enemies if enemy.id == target_id
                           and enemy.integrity > 0 and enemy.slow_turns <= 0), None)
            if target is not None and state._apply_direct_portent(
                    target, "slow_turns",
                    int(params(ability).get("duration_turns", 1) or 1), mode="max"):
                claim(state, ability, int(params(ability).get("cooldown_turns", 0) or 0))
            break

    point = cast.get("target")
    if point is not None:
        try:
            x, y = int(point[0]), int(point[1])
        except (TypeError, ValueError, IndexError):
            x = y = -1
        for ability in active_effects(state, "construct_ignite"):
            claim_key = f"ignite:{ability.instance_id}"
            profile = params(ability)
            from ..core.content import item_is_flammable
            from ..materials import floor_fireproof
            cell = state.cell(x, y) if state.inside_board(x, y) else None
            can_burn = (cell is not None and not floor_fireproof(cell)
                        and (not cell.wall_kind or state._wall_can_burn(x, y)))
            has_fuel = can_burn and (
                state._cell_is_flammable(cell)
                or any((entry.x, entry.y) == (x, y)
                       and item_is_flammable(entry.item) for entry in state.world_items))
            if (claim_key in cast["claims"] or not state.inside_board(x, y)
                    or not has_fuel
                    or not ready(state, ability)):
                continue
            extra = int(profile.get("extra_imagination", 0) or 0)
            if int(state.imagination) < extra:
                continue
            if extra:
                state._pay_ability_cost(extra)
            if state._ignite_cell(x, y, int(profile.get("flame_strength", 2) or 2),
                                  by_player=True):
                claim(state, ability, int(profile.get("cooldown_turns", 0) or 0))
                cast["claims"].add(claim_key)
            break


def reduce_lucidity_trauma(state: Any, delta: float, *, source: str) -> tuple[float, bool]:
    """Spend one live cast guard on eligible lucidity trauma."""
    if delta >= 0:
        return delta, False
    for key, mark in list(state.equipment_marks.items()):
        if not key.startswith("expansion_lucidity_guard:"):
            continue
        charges = int(mark.get("charges", 0) or 0)
        if charges <= 0 or int(mark.get("until", 0) or 0) < int(state.time):
            state.equipment_marks.pop(key, None)
            continue
        amount = max(1, -int(delta))
        if amount <= 1:
            continue
        mark["charges"] = charges - 1
        if mark["charges"] <= 0:
            state.equipment_marks.pop(key, None)
        return -max(1, amount - 1), True
    return delta, False


def radius_bonus(state: Any, ability_id: str) -> tuple[int, int]:
    if ability_id != "combat.fault_ring":
        return 0, 0
    for ability in active_effects(state, "construct_radius"):
        profile = params(ability)
        return (min(int(profile.get("maximum_total_radius_bonus", 1) or 1),
                    int(profile.get("radius_bonus_cells", 0) or 0)),
                int(profile.get("extra_imagination", 0) or 0))
    return 0, 0


def explosion_damage_bonus(state: Any, from_player: bool) -> tuple[int, int]:
    """Return (enemy bonus, self bonus); feedback guard replaces both bonuses."""
    if not from_player:
        return 0, 0
    guard = active_effects(state, "focused_blast_protection")
    if guard:
        return 0, 0
    enemy = max((int(params(ability).get("enemy_trauma_bonus", 0) or 0)
                 for ability in active_effects(state, "player_explosion_damage")), default=0)
    self_bonus = max((int(params(ability).get("self_lucidity_trauma_bonus", 0) or 0)
                      for ability in active_effects(state, "player_explosion_damage")), default=0)
    return enemy, self_bonus


def blast_guard(state: Any, from_player: bool, trauma: int) -> int:
    if not from_player:
        return max(1, int(trauma))
    return environment_guard(state, "focused_blast_protection", trauma)


def consume_feedback_for_blast_slow(state: Any, target: Any, used: bool) -> bool:
    if used or target is None:
        return used
    for ability in active_effects(state, "blast_slow"):
        if not ready(state, ability):
            continue
        if state._apply_direct_portent(target, "slow_turns",
                int(params(ability).get("duration_turns", 1) or 1), mode="max"):
            claim(state, ability, int(params(ability).get("cooldown_turns", 0) or 0))
            return True
    return used


def owned_environment_bonus(state: Any, effect: str, target: Any) -> int:
    amount = 0
    for ability in active_effects(state, effect):
        if target_turn_claim(state, ability, str(getattr(target, "id", "player")), key=effect):
            profile = params(ability)
            amount += int(profile.get("enemy_trauma_bonus", 0) or 0)
    return amount


def flame_guard(state: Any, trauma: int) -> int:
    return environment_guard(state, "flame_trauma_reduction", trauma)


def environment_guard(state: Any, effect: str, amount: int) -> int:
    value = max(1, int(amount))
    for ability in active_effects(state, effect):
        profile = params(ability)
        reduction = int(profile.get("lucidity_trauma_reduction",
                                   profile.get("self_lucidity_trauma_reduction", 0)) or 0)
        value = max(int(profile.get("minimum_trauma", profile.get("minimum_self_trauma", 1)) or 1),
                    value - reduction)
    return value


def electric_field_damage_bonus(state: Any, target: Any) -> int:
    amount = 0
    for ability in active_effects(state, "owned_field_damage_and_guard"):
        if target_turn_claim(state, ability, str(getattr(target, "id", "player")), key="owned-field"):
            amount += int(params(ability).get("enemy_trauma_bonus", 0) or 0)
    return amount


def electric_field_slow(state: Any, target: Any) -> None:
    for ability in active_effects(state, "field_slow"):
        if not ready(state, ability):
            continue
        if state._apply_direct_portent(target, "slow_turns",
                int(params(ability).get("duration_turns", 1) or 1), mode="max"):
            claim(state, ability, int(params(ability).get("cooldown_turns", 0) or 0))
        break


def owned_field_duration(state: Any) -> int:
    return max((int(params(ability).get("duration_bonus_turns", 0) or 0)
                for ability in active_effects(state, "owned_field_duration")), default=0)


def reactive_field(state: Any, enemy: Any) -> int:
    """Fire C-E07 after a direct ordinary enemy hit, only on real conductors."""
    abilities = active_effects(state, "reactive_conductive_field")
    if not abilities or enemy is None:
        return 0
    origin = (int(state.player.x), int(state.player.y))
    zone = state._conductive_zone(origin)
    if not zone:
        return 0
    cells = sorted(zone, key=lambda pos: (abs(pos[0] - origin[0]) + abs(pos[1] - origin[1]), pos))
    for ability in abilities:
        if not ready(state, ability):
            continue
        profile = params(ability)
        extra = int(profile.get("extra_imagination", 0) or 0)
        if int(state.imagination) < extra:
            continue
        if extra:
            state._pay_ability_cost(extra)
        selected = cells[:max(1, int(profile.get("max_cells", 5) or 5))]
        duration = int(profile.get("duration_turns", 2) or 2)
        state._charge_electric_field(selected, source="expansion_e07",
                                    origin=origin, duration=duration)
        claim(state, ability, int(profile.get("cooldown_turns", 0) or 0))
        state._emit_combat_fx("electric", origin, selected)
        return len(selected)
    return 0


def action_conductive_field(state: Any, action_plan: Any,
                            point: tuple[int, int]) -> int:
    """C-E07 modifier reading: charge a real conductor hit by this action."""
    if action_plan is None or not state.inside_board(*point):
        return 0
    if not state._conductive_cell(state.cell(*point)):
        return 0
    from ..core.content import ITEM_DEFINITIONS
    from ..i18n import tr

    seen: set[str] = set()
    for row in getattr(action_plan, "rows", ()):
        for instance_id, effect, power in getattr(row, "action_modifiers", ()):
            if effect != "reactive_conductive_field" or int(power) <= 0:
                continue
            instance_id = str(instance_id)
            if instance_id in seen:
                continue
            seen.add(instance_id)
            voice = next((voice for voice in getattr(row, "voices", ())
                          if voice.instance_id == instance_id), None)
            definition = ITEM_DEFINITIONS.get(voice.definition_id, {}) if voice else {}
            profile = definition.get("runtime_primary_params") or {}
            timer = f"expansion:{instance_id}:reactive_conductive_field"
            if int(state.board_cooldowns.get(timer, 0) or 0) > int(state.time):
                continue
            extra = int(profile.get("extra_imagination", 0) or 0)
            if int(state.imagination) < extra:
                continue
            component = state._conductive_component(point)
            cells = sorted(component, key=lambda cell: (
                abs(cell[0] - point[0]) + abs(cell[1] - point[1]), cell))
            cells = cells[:max(1, int(profile.get("max_cells", 5) or 5))]
            if not cells:
                continue
            if extra:
                state._pay_ability_cost(extra)
            duration = int(profile.get("duration_turns", 2) or 2)
            state._charge_electric_field(cells, source="expansion_e07",
                                         origin=point, duration=duration)
            state.board_cooldowns[timer] = int(state.time) + max(
                0, int(profile.get("cooldown_turns", 0) or 0))
            state._emit_combat_fx("electric", point, cells)
            state.messages.append(tr(
                "反扣的接地腕带沿导电介质接通了 {n} 格电场。", n=len(cells)))
            return len(cells)
    return 0
