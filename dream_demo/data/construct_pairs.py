"""构件的配合提示（方案 P3「同质物战术分工」的尾巴：构件类配方提示）。

六件「构筑桥接组件」单独看只是一句效果，玩家真正需要知道的是**它跟哪套
打法配起来才成立**——E5 报告里「构件类 0 使用」正是因为这个：东西在包里，
但没有任何地方告诉玩家「先有水枪，盐渍线圈才有意义」。

这里只登记**机制**，不登记具体物品 ID：机制名是稳定的，物品池会随 P4／P5
扩表调整；写成 `salt_soaked_coil → water_gun` 这种硬绑定，一旦水枪的位置
被新件挤掉，提示就成了错话。
"""

from __future__ import annotations

# 构件 id -> (配合的机制名, 为什么)
CONSTRUCT_PAIRS: dict[str, tuple[str, str]] = {
    "prism_pendant": ("跳弹", "弹体要真的改向过，折射印记才刻得上"),
    "salt_soaked_coil": ("放电", "水枪／导电液态记忆把目标打湿，多传的那一次才有人接"),
    "ember_boots": ("火源", "每层第一次由你亲手点燃才触发，得有能点火的东西"),
    "hunting_lanyard": ("材料附着", "对手身上挂着附着，这一档创伤才加得上去"),
    "split_tuning_fork": ("声波引诱", "要把意识真的引走，脉冲武装才会成立"),
    "blank_half_page": ("留白", "想象归零时才用得上；与洞察「留白」共享同一次额度"),
}

# 机制名 -> 英文由 i18n_surface_en 统一登记（键就是上面的中文机制名）。


def pair_for(definition_id: str) -> "tuple[str, str] | None":
    """这件构件的配合机制与理由；不是构件返回 None。"""
    return CONSTRUCT_PAIRS.get(str(definition_id or ""))


def pair_hint(definition_id: str) -> str:
    """一行提示：「配合：跳弹（弹体要真的改向过…）」；非构件返回空串。"""
    pair = pair_for(definition_id)
    if not pair:
        return ""
    mechanic, why = pair
    from ..i18n import tr

    return tr("配合：{mechanic}——{why}。", mechanic=tr(mechanic), why=tr(why))


def construct_ids() -> tuple[str, ...]:
    """全部构件的定义 id（供图鉴／测试枚举，别在别处再抄一份）。"""
    return tuple(CONSTRUCT_PAIRS)
