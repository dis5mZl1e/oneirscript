"""承载面归属与领取费用的英文译文（见 core/surface_terms.py）。"""

from __future__ import annotations

EN_SURFACE = {
    "台面归{owner}；每取一件付 {amount} 点{resource}。":
        "This surface belongs to {owner}; taking one item costs {amount} {resource}.",
    "台面归{owner}：领取要先付 {amount} 点{resource}，你只剩 {have}。":
        "This surface belongs to {owner}: taking it costs {amount} {resource}, and you have only {have}.",
    "取走{owner}台面上的东西：{resource} −{amount}。":
        "Took an item from {owner}'s surface: {resource} −{amount}.",
    # ---- 构件的配合提示（data/construct_pairs.py）----
    "配合：{mechanic}——{why}。": "Pairs with: {mechanic} — {why}.",
    "跳弹": "ricochet",
    "放电": "electric discharge",
    "火源": "a fire source",
    "材料附着": "material attachment",
    "声波引诱": "sound luring",
    "留白": "the Blank insight",
    "弹体要真的改向过，折射印记才刻得上":
        "the shot must actually have been deflected before the mark can be carved",
    "水枪／导电液态记忆把目标打湿，多传的那一次才有人接":
        "the water gun or conductive liquid memory wets the target, so the extra hop has someone to reach",
    "每层第一次由你亲手点燃才触发，得有能点火的东西":
        "it only fires on the first thing you ignite each floor, so you need a way to start a fire",
    "对手身上挂着附着，这一档创伤才加得上去":
        "the target must still carry an attachment for the extra trauma to land",
    "要把意识真的引走，脉冲武装才会成立":
        "something must actually follow the sound before the pulse is armed",
    "想象归零时才用得上；与洞察「留白」共享同一次额度":
        "it only matters once imagination hits zero, and it shares one charge with the Blank insight",
    # ---- 搜刮柜：一次只带走一件（§5.1 P1「柜内二选一」）----
    "取走：{name}": "Take: {name}",
    "先不拿": "Take nothing",
    "柜里有几样东西，你只拿得走一样。":
        "There are a few things in the cabinet, and you can only take one.",
    "抽屉拉开了一半。里面的东西各有各的位置。":
        "The drawer is half open. Each thing inside has its own place.",
    "你把{name}收进行囊。": "You put {name} into your satchel.",
    "柜里还剩 {count} 件，没拿的仍留在原处。":
        "{count} things are still in the cabinet; whatever you didn't take stays where it was.",
    "柜子还在远处。": "The cabinet is still out of reach.",
    "柜里已经空了。": "The cabinet is empty.",
    "行囊装不下了，东西仍留在柜里。":
        "Your satchel is full; the things stay in the cabinet.",
}
