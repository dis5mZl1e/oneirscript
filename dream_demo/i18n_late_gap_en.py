"""English text for late gaps found by the i18n coverage gate (2026-10-17).

内容来源都是已有系统但此前没有英文的字符串，集中在这里避免再散进巨型文件：
- 异象「惊散」征兆名与效果（地图篡改「退散」引入）；
- 被打醒的异象反馈；
- 普通遭遇样板里「走廊改写」的全部提示。

只补翻译，不改任何结算或文案口径。
"""

EN_LATE_GAP = {
    # ---- 惊散征兆（materials/portents.py）----
    "惊散": "Spooked",
    "被突兀的文字惊散了：不再寻找你、不发起攻击，并主动与你拉开距离；挨一下打就会惊醒。":
        "Spooked by abrupt words: it stops hunting you, holds its attacks, and "
        "pulls away from you; a single hit wakes it.",
    # ---- 被打醒的异象（core/enemies.py）----
    "{enemy}被这一下惊醒了！": "{enemy} is jolted awake by the blow!",
    # ---- 普通遭遇样板·走廊改写（core/tactical_layouts.py）----
    "走廊的纸纹正在合拢：{n} 个客观回合后，中央通道会变成纸墙。两端仍可退到外圈。":
        "The corridor's paper grain is closing: in {n} world rounds the central "
        "passage becomes a paper wall. Both ends still lead back to the outer ring.",
    "纸纹改写还剩 {n} 个客观回合；可以从任一端退到外圈。":
        "Paper-grain rewrite in {n} world rounds; you can fall back to the outer "
        "ring from either end.",
    "中央通道尚有占位或流动材料，纸纹暂缓合拢；移开后才会继续。":
        "Something stands in or flows through the central passage, so the paper "
        "grain holds back; it resumes once the way is clear.",
    "中央通道已改写；两侧仍可各自退到外圈，也可以破开纸墙。":
        "The central passage has been rewritten; both sides still lead back to "
        "the outer ring, and the paper wall can be broken.",
    "积液通向深处的显化物；一盏灯照着那里，另一侧留着一条干路。":
        "The pooled liquid leads to the manifestation deeper in; a lamp lights it, "
        "and a dry path remains on the other side.",
    "中央通道将在 {n} 个客观回合后改写；两端通向外圈，纸墙可提前破开。":
        "The central passage will be rewritten in {n} world rounds; both ends lead "
        "to the outer ring, and the paper wall can be broken early.",
    "中央通道已经改写。两端仍通向外圈；破开纸墙可另留退路。":
        "The central passage has been rewritten. Both ends still lead to the "
        "outer ring; breaking the paper wall leaves another way out.",
    "纸面写着：两侧各有一件用途不同的物品；看清走廊后，中央纸纹会开始合拢。两端通向外圈。":
        "The paper reads: one item of a different use on each side. Once the "
        "corridor is seen clearly, the central paper grain begins to close. Both "
        "ends lead to the outer ring.",
    # ---- 多解门禁（第三处普通遭遇样板）----
    "纸墙挡住近路：可以点着、用弹体打穿，或直接改写它；外圈仍有一条干路可绕。":
        "A paper wall blocks the shortcut: set it alight, shoot through it, or "
        "rewrite it outright; the outer ring still offers a dry detour.",
}
