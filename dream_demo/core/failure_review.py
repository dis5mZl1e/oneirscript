"""失败复盘只引用已发生的近期结算，不把缺失记录推断成死因。"""
from __future__ import annotations


def record_descent(state, target, shortage, loss):
    if state.difficulty_revision < 3 or state.realm_id:
        return
    state.run_stats.update(descent_target=target, descent_shortage=shortage,
                           descent_mind_loss=loss, descent_time=state.time)
    state.run_stats["descent_mind_loss_total"] = state.run_stats.get("descent_mind_loss_total", 0) + loss


def build_review(state):
    if not state.run_over or state.victory or state.ending_id not in ("E", "F"):
        return {}
    from .settlement import recent_settlements
    losses = [entry.to_dict() for entry in recent_settlements(state, 50)
              if entry.applied < 0 and 0 <= state.time - entry.world_time <= 8
              and entry.reason != "debug"][-3:]
    tools = ("coiled_spring", "clockwork_half", "clear_glass")
    held = [item.definition_id for item in state.inventory
            if item.definition_id in tools and item.quantity > 0]
    result = {"losses": losses, "held_tools": sorted(set(held))}
    if state.difficulty_revision >= 3:
        from .content import ITEM_DEFINITIONS, ABILITY_DEFINITIONS
        effects = {"restore_mind", "restore_lucidity", "restore_imagination",
                   "restore_split", "warm_restore", "deploy_escape_route",
                   "knockback", "slow_burst", "parry", "blind", "liquid_step"}
        result["tools"] = [{"id": item.definition_id, "count": item.quantity}
                           for item in state.inventory if item.quantity > 0
                           and ITEM_DEFINITIONS.get(item.definition_id, {}).get("effect") in effects]
        result["abilities"] = [{"id": key, "cooldown": state.ability_cooldowns.get(key, 0),
                                "cost": state._ability_imagination_cost(key, ABILITY_DEFINITIONS[key])}
                               for key in state.abilities if key in ABILITY_DEFINITIONS]
        result["imagination"] = state.imagination
        result["descent"] = {key: value for key, value in state.run_stats.items()
                             if key.startswith("descent_")}
    return result


def review_lines(review):
    if not review:
        return []
    from ..i18n import tr
    from .content import ITEM_DEFINITIONS
    resources = {"mind": "心智", "lucidity": "清醒度", "imagination": "想象力"}
    reasons = {"combat": "战斗创伤", "environment": "环境影响",
               "ability_cost": "构想费用", "tamper_cost": "篡改费用",
               "trade_cost": "交易费用", "drug_debt": "药物分期",
               "story": "剧情变化", "max_change": "上限变化"}
    lines = [tr("近期复盘（最近 8 游戏时间，最多 3 条；不等于完整死因）：")]
    losses = review.get("losses", [])
    if not losses:
        lines.append(tr("没有足够的近期结算记录；旧梦痕不会补造记录。"))
    for entry in losses:
        lines.append(tr("{resource} {amount} · {reason} · {source}",
                        resource=tr(resources.get(entry["resource"], entry["resource"])),
                        amount=f'{entry["applied"]:g}',
                        reason=tr(reasons.get(entry["reason"], "资源变化")),
                        source=tr(entry.get("source") or "来源未记录")))
    descent = review.get("descent", {})
    if descent:
        lines.append(tr("下潜折损：上次前往 {depth} 层，清醒缺口 {shortage}，实际心智损失 {loss}；本局累计 {total}。",
                        depth=descent.get("descent_target", 0),
                        shortage=descent.get("descent_shortage", 0),
                        loss=descent.get("descent_mind_loss", 0),
                        total=descent.get("descent_mind_loss_total", 0)))
    for tool in review.get("tools", []):
        definition = ITEM_DEFINITIONS.get(tool["id"], {})
        lines.append(tr("持有工具：{name} ×{count}；需主动使用，效果与使用条件见行囊。",
                        name=tr(definition.get("name", tool["id"])), count=tool["count"]))
    from .content import ABILITY_DEFINITIONS
    for ability in review.get("abilities", []):
        lines.append(tr("构想：{name} · 冷却 {cooldown} · 想象力费用 {cost}（持有 {held}）；仍需满足目标条件。",
                        name=tr(ABILITY_DEFINITIONS.get(ability["id"], {}).get("name", ability["id"])),
                        cooldown=ability["cooldown"], cost=ability["cost"], held=review.get("imagination", 0)))
    held = review.get("held_tools", [])
    if held:
        item_id = held[0]
        definition = ITEM_DEFINITIONS.get(item_id, {})
        lines.append(tr("下次可尝试提前使用随身工具：{name}。{description}",
                        name=tr(definition.get("name", item_id)),
                        description=tr(definition.get("description", ""))))
    elif losses:
        lines.append(tr("第 3、5 层的行前工具台可补充推离、减速或清醒恢复工具；领取后需从行囊主动使用。"))
    return lines
