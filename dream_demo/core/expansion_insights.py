"""扩展包目录洞察的结算门面（2026-10-25）。

洞察的效果是**读出已经在世界里的信息**，不是另造一套数值：每条规则只读既有记账
（听觉线索、真实光照），产出要么是一条事件记录，要么是一次地形记忆。目录行的
``effect.runtime[0].kind`` 指名规则，宿主是等待（凝听本身就是调查动作）；只读世界
变化的那几条挂在每回合末尾的观测上（见 ``observe``），等待与推进世界的两头都跑得到。

已实装的 ``kind``：

- ``tail_sound_classify``     同地点两声之间分辨移动声／固定节律声（分辨尾音）
- ``external_light_snapshot`` 记下外部灯真正照到的地形轮廓（借亮确认）
- ``gap_in_chorus``           两处来处的声抵达有先后时分别报两条方向（合唱的间隙）
- ``remembered_reflection``   记下亲见反射面的方向，材料换了把旧记录标作废（记住反折面）
- ``light_source_read``       分清一格亮是自己发光还是就近某盏确认过的灯（认光源而非亮斑）
- ``cut_impact_read``         已见过的线路断开后落在哪些确认过的接收端（先断哪根）
- ``gas_front_advance``       这一回合气在眼前真实推进／退散的落点（蒸气的出口）
- ``lamp_order_note``         两次亲见的熄灭之间排出先后，看不见控制端就标未知（留意熄灯顺序）
- ``lit_risk_note``           亮区里先前确认过的视觉型异象此刻看不看得见你（亮处未必安全）
- ``same_tick_pairing``       两只自己按得动的端口会不会同一回合落到同一接收端（同拍才接）
- ``siphon_backflow_note``    架着的导流管里哪个已见出口的读数在倒着走（看见回流）
- ``frontier_exit_bearing``   看得见的出口相对于我确认过的地形边界在哪一向（边界还在更深处）
- ``wall_cavity_echo``        敲过的墙只报回声长短档，不揭示墙后内容与走法（墙后的空腔）
- ``gas_exit_hint``           倒料前指出已知会产气的最近开放格，不替未知通路担保（反应留下出口）
- ``drug_debt_prepay``        在医院等待时提前结一格真实药债，总债不变、不提前恢复（药效不等于痊愈）
- ``empty_magazine_note``     自己打空的那一仓记一笔，下一回换弹的第一步略快（数清空响）
- ``dim_edge_wait``           停在明暗交界留一手，下一步进暗处时异象看你的视距 −1（光圈的边缘）
- ``settled_grab_read``       刚相变完的那一格第一次取液不吃表面附着，伤害照旧（先让它沉下去）
- ``pour_drop_read``          站在看得见的高低边上时，报液体先往哪几格走（先看落差）
- ``live_wire_check``         视野里有线路、身上又有积电时报还剩几层，验电只泄一层（不把亮灯当通电）
- ``pipe_relay_note``         转发来的那一声只注明传声筒入口，不替玩家追没见过的另一头（一声两种来处）
- ``surface_take_note``       贴着陷阱石台时说明「多站一回合」能怎么拿（桌面不是地面）
- ``reload_gap_read``         换弹只剩几步时报下一步的声音传多远（听出填装间隙）
- ``cut_route_note``          身边已见通路只剩一格宽时提醒堵上就断了（留下最后一条路）
- ``cover_edge_read``         面朝已确认掩体时报身侧能出手的空格（先看掩体边）
- ``dump_keep_read``          报膛里还剩几发、退壳会打掉几发留几发（不白退一发）
- ``fake_reload_bait``        空仓被已见异象看着时等一手假装填，用诱引脉冲引它来查（空仓不是失手）
- ``reaction_product_read``   身边那一格在走亲眼见过的液气反应时报出产物，没见过的组合不反演（留意产物）
- ``overload_smell_read``     脚下压电地板只差一层就放电时先报一声，墙后不测（熔断前的气味）
- ``sign_before_read``        对话开着时先把每个选项会抽走什么念一遍（看完再签）
- ``page_age_read``           书库里报脚下这一页地形记录有多旧（页码没有走动）
- ``pending_field_rotation``  还没结算的取向构想（裁光扇区／镜面法线）顺时针转九十度一次（落笔之前）

认不出 kind 的行不会注册（见 ``growth_runtime.insight_rows``），这里也就不该有分支。
"""
from __future__ import annotations

from typing import Any, Callable

from ..i18n import tr
from ..data.insights import EXPANSION_INSIGHTS


def _clue_place(clue: dict[str, Any]):
    """「同一处声响」的分组键：认得出的 emitter 用来源＋类别，认不出退回方位＋远近档。"""
    source = str(clue.get("source") or "")
    if source:
        return ("source", source, str(clue.get("category") or ""))
    return ("bearing", str(clue.get("sector") or ""), str(clue.get("band") or ""))


def _tail_sound_classify(state, name: str, effect: dict[str, Any]) -> int:
    """分辨尾音：同地点、间隔足够久的两声，比的是方位与远近有没有变。"""
    gap = max(1, int(effect.get("min_gap_turns", 1) or 1))
    retention = state._clue_retention()
    fresh = [clue for clue in state.heard_sound_clues
             if state.time - int(clue.get("time", 0)) < retention
             and not clue.get("tail_judged")]
    groups: dict[Any, list[dict[str, Any]]] = {}
    for clue in fresh:
        groups.setdefault(_clue_place(clue), []).append(clue)
    notes = 0
    for place, clues in groups.items():
        times = sorted({int(clue.get("time", 0)) for clue in clues})
        if len(times) < 2 or times[-1] - times[0] < gap:
            continue
        bearings = {(str(c.get("sector") or ""), str(c.get("band") or "")) for c in clues}
        cells = {(int(c.get("x", -1)), int(c.get("y", -1))) for c in clues if c.get("known")}
        moved = len(bearings) > 1 or len(cells) > 1
        where = tr("那个方向") if place[0] == "bearing" else tr("那处声响")
        state.messages.append(tr(
            "{where}的尾音分辨出来了：{verdict}。",
            where=where,
            verdict=tr("声音的方位或远近在两声之间变了，那是移动中的东西") if moved
            else tr("两声的方位与远近都一样，那是固定节律的声响，不是走过来的脚步")))
        for clue in clues:
            # 一次聆听只判一回：反复等待不该把同一条线索重新播报。
            clue["tail_judged"] = True
        notes += 1
    return notes


def _external_light_snapshot(state, name: str, effect: dict[str, Any]) -> int:
    """借亮确认：外部灯实际照到哪一格，就记下那一格的地形轮廓。

    信息权限来自**光本身**（光源确实照到），不要求那格此刻还在正常视野里——
    这正是它比肉眼多出来的部分；依旧只写地形，不揭示生物、物品、液气。
    """
    from .vision import glow
    from .vision.knowledge import record_terrain_cells
    reach = max(1, int(effect.get("reach", 8) or 8))
    px, py = state.player.x, state.player.y
    sources = [source for source in glow.sources_in_window(state, (px, py), reach)
               if (source[0], source[1]) != (px, py)]
    if not sources:
        return 0
    cells = sorted(glow.lit_cells(state))
    if not cells:
        return 0
    learned = record_terrain_cells(state, cells)
    if learned:
        state.messages.append(tr(
            "借外部灯的亮光，{n} 格地形轮廓记进了记忆。", n=learned))
    return learned


def _clue_line(clue: dict[str, Any]) -> str:
    """按听界面板同一口径写一条线索：方位、距离档、类别、可知的位置。"""
    from .enemies import sound_category_name
    where = (f"({clue['x']},{clue['y']})" if clue.get("known")
             else tr("方向与距离可知，位置未知"))
    return tr("{sector} · {band} · {category} · {where}",
              sector=tr(clue.get("fine_sector") or clue.get("sector") or ""),
              band=tr(clue.get("band") or ""),
              category=tr(sound_category_name(str(clue.get("category") or ""))),
              where=where)


def _gap_in_chorus(state, name: str, effect: dict[str, Any]) -> int:
    """合唱的间隙：两处真实来处的声抵达有先后，就分别报两条方向线索。

    只报两条各自的方向，不做交汇推算——合成精确定位是这条洞察明确不给的。
    """
    window = max(1, int(effect.get("max_gap_turns", 3) or 3))
    retention = state._clue_retention()
    fresh = [clue for clue in state.heard_sound_clues
             if state.time - int(clue.get("time", 0)) < retention
             and not clue.get("chorus_judged")]
    earliest: dict[Any, dict[str, Any]] = {}
    for clue in sorted(fresh, key=lambda item: int(item.get("time", 0))):
        earliest.setdefault(_clue_place(clue), clue)
    ordered = sorted(earliest.values(), key=lambda item: int(item.get("time", 0)))
    notes = 0
    for earlier, later in zip(ordered, ordered[1:]):
        gap = int(later.get("time", 0)) - int(earlier.get("time", 0))
        if not 1 <= gap <= window:
            continue
        state.messages.append(tr(
            "合唱里有一条 {gap} 回合的间隙：先 {a}，后 {b}。两条声线分开记着，不并成一处。",
            gap=gap, a=_clue_line(earlier), b=_clue_line(later)))
        # 一对只播报一次；同一段聆听里剩下的线索交给下一次等待。
        for clue in (earlier, later):
            clue["chorus_judged"] = True
        notes += 1
    return notes


REFLECTOR_KINDS = ("expansion.deflector", "expansion.double_mirror")


def _remembered_reflection(state, name: str, effect: dict[str, Any]) -> int:
    """记住反折面：把亲眼见到的反射面连同它脚下的材料一起记下。

    材料换了就说明那块面不再是当初记下的那块，旧记录标成作废；视野外的面
    一律不重新核对，也不替它编新的。
    """
    from .construct_environments import active
    kinds = tuple(effect.get("surfaces") or REFLECTOR_KINDS)
    memo = state.realm_features.setdefault("growth_observations", {})
    stored = memo.setdefault("reflectors", {})
    surfaces: dict[str, dict[str, Any]] = {}
    for field in active(state):
        if field.get("kind") not in kinds:
            continue
        x, y = (int(value) for value in field["position"][:2])
        if not state.is_visible(x, y):
            continue
        surfaces[f"{x},{y}"] = {
            "direction": [int(value) for value in field["direction"][:2]],
            "material": str(state.cell(x, y).floor.value),
            "time": int(state.time)}
    notes = 0
    for key, record in surfaces.items():
        old = stored.get(key)
        if old is None:
            notes += 1
        elif old.get("material") != record["material"]:
            # 脚下的材料换了，先前记下的反射方向不再属于这片面；这一眼看的是
            # 当下的面，所以旧记录作废、新记录当场重写。
            x, y = (int(value) for value in key.split(","))
            state.messages.append(tr(
                "记住的反折面：({x}, {y}) 脚下的材料换了，那条反射记录作废。", x=x, y=y))
            notes += 1
        elif old.get("direction") != record["direction"]:
            notes += 1
        stored[key] = record
    if notes:
        state.messages.append(tr("记住的反折面：本回合核对了 {n} 处亲眼所见的反射面。", n=notes))
    for key in [key for key in stored if key not in surfaces and not stored[key].get("stale")]:
        # 面已经不在了（收回、到期）——记忆留着没有意义，也不据此播报。
        del stored[key]
    return notes


def _light_source_read(state, name: str, effect: dict[str, Any]) -> int:
    """认光源而非亮斑：把亲眼所见的每一格亮，归到「自己发光」或「某盏确认过的灯」。

    口径是**读出已有的光照**，不是另算一套可见性：直射＝那格本身就是光源；
    间接＝就近有一盏自己也在眼前的灯照得到它。两者都说不清时只报「来处未确认」，
    绝不反过来推断墙后藏了灯（目录写明「不倒查隐藏灯源」）。看不见的格子不更新，
    但最近一次确认的来处仍然留着——那是这条洞察里「间接光」的那半句。
    """
    from .vision import glow
    reach = max(1, int(effect.get("reach", 10) or 10))
    px, py = state.player.x, state.player.y
    memo = state.realm_features.setdefault("growth_observations", {})
    stored = memo.setdefault("light_read", {})
    layer = str(state.layer_key())
    window = glow.sources_in_window(state, (px, py), reach)
    seen = [source for source in window if state.is_visible(source[0], source[1])]
    # 先收集「眼前哪些格子真的亮着」以及它离照它的那盏源有多远：目录只允许
    # 查看已见亮格，所以暗格一条都不该被播报。距离 0 就是那格自己发光。
    lit: dict[tuple[int, int], int] = {}
    for sx, sy, sr in window:
        for y in range(max(0, sy - sr), min(state.height, sy + sr + 1)):
            for x in range(max(0, sx - sr), min(state.width, sx + sr + 1)):
                if not state.is_visible(x, y):
                    continue
                step = max(abs(x - sx), abs(y - sy))
                if step and not state._has_line_of_sight(sx, sy, x, y):
                    continue
                if step > lit.get((x, y), step + 1):
                    continue
                lit[(x, y)] = step
    changes: dict[str, list[tuple[int, int, int, int]]] = {
        "direct": [], "indirect": [], "moved": [], "unknown": [], "remembered": []}
    for (x, y), step in sorted(lit.items()):
        key = f"{x},{y}"
        if step == 0:
            record = {"layer": layer, "kind": "direct", "source": None,
                      "radius": int(glow.source_radius(state.cell(x, y))),
                      "time": int(state.time)}
        else:
            owner = min(((max(abs(x - sx), abs(y - sy)), sx, sy)
                         for sx, sy, sr in seen
                         if max(abs(x - sx), abs(y - sy)) <= sr
                         and state._has_line_of_sight(sx, sy, x, y)),
                        default=None)
            if owner is None:
                # 亮着，但眼前没有一盏看得见的灯解释得了它：只说「说不清」，
                # 不说那盏看不见的灯在哪——那是这条洞察明确不给的信息。
                record = {"layer": layer, "kind": "unknown", "source": None,
                          "radius": 0, "time": int(state.time)}
            else:
                _dist, sx, sy = owner
                record = {"layer": layer, "kind": "indirect", "source": [sx, sy],
                          "radius": 0, "time": int(state.time)}
        old = stored.get(key)
        if (record["kind"] == "unknown" and old is not None
                and old.get("layer") == layer and old.get("source")):
            # 看不出来处不等于先前的确认作废：那一次确认仍然作数，所以「说不清」
            # 只在沉默刚开始时报一次，之后每回合重复同一条只是噪声。
            if not old.get("dimmed"):
                changes["remembered"].append(
                    (x, y, int(old["source"][0]), int(old["source"][1])))
            stored[key] = {**old, "dimmed": int(state.time)}
            continue
        if (old is None or old.get("layer") != layer
                or old.get("kind") != record["kind"]
                or old.get("source") != record["source"]):
            if record["kind"] == "direct":
                changes["direct"].append((x, y, record["radius"], 0))
            elif record["kind"] == "indirect":
                sx, sy = record["source"]
                moved = (old is not None and old.get("kind") == "indirect"
                         and old.get("source"))
                changes["moved" if moved else "indirect"].append((x, y, sx, sy))
            else:
                changes["unknown"].append((x, y, 0, 0))
        stored[key] = record
    # 一条消息一类读数：一盏灯点亮的十几格若各报一条，凝听就被这一条洞察占满，
    # 玩家反而看不清「哪儿变了」。坐标本身不是词，所以拼接不进 tr()。
    state.messages.extend(_report_light_read(changes))
    return sum(len(rows) for rows in changes.values())


def _report_light_read(changes: dict[str, list[tuple[int, int, int, int]]]) -> list[str]:
    """一条消息一类读数。

    模板必须是**字面量**写在 `tr()` 里：英文覆盖率闸门（``test_i18n_coverage``）只认
    字面量调用，把模板塞进循环变量就等于对闸门隐身。
    """
    lines = []

    def spots(rows):
        return ", ".join(f"({x}, {y})" for x, y, _a, _b in rows[:3])

    rows = sorted(changes["direct"])
    if rows:
        lines.append(tr(
            "认光源而非亮斑：{n} 格是它自己在发光——{cells}，半径 {r}。",
            n=len(rows), cells=spots(rows), r=rows[0][2]))
    rows = sorted(changes["indirect"])
    if rows:
        lines.append(tr(
            "认光源而非亮斑：{n} 格的亮借自眼前确认过的灯——{cells} 归 ({sx}, {sy})。",
            n=len(rows), cells=spots(rows), sx=rows[0][2], sy=rows[0][3]))
    rows = sorted(changes["moved"])
    if rows:
        lines.append(tr(
            "认光源而非亮斑：{n} 格的亮换了来处——{cells} 现在归 ({sx}, {sy}) 那盏灯。",
            n=len(rows), cells=spots(rows), sx=rows[0][2], sy=rows[0][3]))
    rows = sorted(changes["unknown"])
    if rows:
        lines.append(tr(
            "认光源而非亮斑：{n} 格亮着，可眼前没有一盏确认过的灯解释得了它们——{cells}；"
            "不据此猜灯在哪。", n=len(rows), cells=spots(rows)))
    rows = sorted(changes["remembered"])
    if rows:
        lines.append(tr(
            "认光源而非亮斑：{n} 格此刻说不清来处，最近一次确认的仍是 ({sx}, {sy}) 那盏灯。",
            n=len(rows), sx=rows[0][2], sy=rows[0][3]))
    return lines


def _wire_downstream(nodes: dict[str, Any], start: str) -> list[str]:
    """从 `start` 往下游走一遍，列出所有接收端口（含它自己）。

    走的是**接线表**（`node["inputs"]` 的反向），不是电流仿真：这条洞察报的是
    「这根线连着谁」，不替世界重算一遍门的开关——重算属于结算层，两处各算一份
    迟早对不上。交叉的线彼此绝缘（见 `core/circuits.py` 的模块口径），所以这里
    按 net 逐条走，共用一格的另一根线不会被算进落点。
    """
    feeds: dict[str, list[str]] = {}
    for key, node in nodes.items():
        for ref in node.get("inputs", []):
            feeds.setdefault(ref, []).append(key)
    seen: set[str] = set()
    stack = [start]
    receivers: list[str] = []
    while stack:
        current = stack.pop()
        if current in seen:
            continue
        seen.add(current)
        if nodes[current]["op"] == "output":
            receivers.append(current)
        stack.extend(feeds.get(current, []))
    return sorted(receivers)


def _cut_impact_read(state, name: str, effect: dict[str, Any]) -> int:
    """先断哪根：把亲眼见过的每一根线读成「断了会落到哪些确认过的接收端」。

    只读已看见的线段：整条 `path` 一段都没进过眼的线不分析，也不据端点名猜路线。
    落点分两半——格子在眼前的接收端按名字报，看不见的只报有几个，绝不给坐标；
    当下不带电的线照旧报它的落点，但说清断它不改变什么。
    """
    max_lines = max(1, int(effect.get("max_report_lines", 3) or 3))
    memo = state.realm_features.setdefault("growth_observations", {})
    stored = memo.setdefault("wire_cuts", {})
    layer = str(state.layer_key())
    analysed: dict[str, dict[str, Any]] = {}
    for index, board in enumerate(state.circuit_boards):
        nodes = board["nodes"]
        values = board["state"].get("values", {})
        for net in board["nets"]:
            path = [tuple(int(value) for value in point[:2]) for point in net["path"]]
            if not any(state.is_visible(x, y) for x, y in path):
                continue
            to_key = net["to"]
            if to_key not in nodes or net["from"] not in nodes:
                continue
            confirmed: list[str] = []
            hidden = 0
            for key in _wire_downstream(nodes, to_key):
                ox, oy = (int(value) for value in nodes[key]["pos"][:2])
                if state.is_visible(ox, oy):
                    confirmed.append(str(nodes[key]["label"]))
                else:
                    hidden += 1
            analysed[f"{index}:{net['from']}->{to_key}"] = {
                "layer": layer,
                "line": (f"{nodes[net['from']]['label']}"
                         f" \u2192 {nodes[to_key]['label']}"),
                "confirmed": sorted(confirmed),
                "hidden": hidden,
                "live": bool(values.get(net["from"], False)),
                "time": int(state.time),
            }
    news: list[dict[str, Any]] = []
    changed: list[dict[str, Any]] = []
    for key, record in sorted(analysed.items()):
        old = stored.get(key)
        stored[key] = record
        if old is None or old.get("layer") != layer:
            news.append(record)
        elif (old.get("confirmed") != record["confirmed"]
             or old.get("hidden") != record["hidden"]):
            changed.append(record)
    for key in [key for key in stored if key not in analysed
               and stored[key].get("layer") == layer]:
        # 板子拆了／线没了：记忆留着只会报一根不存在的线。
        del stored[key]
    state.messages.extend(_report_cut_impact(news, changed, max_lines))
    return len(news) + len(changed)


def _report_cut_impact(news: list[dict[str, Any]], changed: list[dict[str, Any]],
                       max_lines: int) -> list[str]:
    """一根线一条落点读数；模板照旧写成 `tr()` 字面量，理由见 `_report_light_read`。"""
    lines = []

    def receivers(record):
        return ", ".join(record["confirmed"][:3])

    for record in news[:max_lines]:
        if not record["confirmed"]:
            # 落点里一个确认端都没有：要么全没看清（交给下面那条「未明连线」汇总），
            # 要么这根线谁也不牵。两种都不该编出一份接收端名单。
            if not record["hidden"]:
                lines.append(tr("先断哪根：断「{line}」落不到任何接收端——那根线不牵着机关。",
                                line=tr(record["line"])))
            continue
        if record["live"]:
            lines.append(tr("先断哪根：断「{line}」会落到 {receivers}。",
                            line=tr(record["line"]), receivers=receivers(record)))
        else:
            lines.append(tr("先断哪根：「{line}」眼下不带电，断了不改变什么——它牵着 {receivers}。",
                            line=tr(record["line"]), receivers=receivers(record)))
    if len(news) > max_lines:
        lines.append(tr("先断哪根：另有 {n} 根已见线路的落点一并记下。",
                        n=len(news) - max_lines))
    for record in changed[:max_lines]:
        if record["confirmed"]:
            lines.append(tr("先断哪根：「{line}」的落点和上次确认不一样了——现在牵着 {receivers}。",
                            line=tr(record["line"]), receivers=receivers(record)))
    hidden = [record for record in news + changed if record["hidden"]]
    if hidden:
        lines.append(tr("先断哪根：{n} 根线牵着没看清的接收端——只说可能有未明连线，不给坐标。",
                        n=len(hidden)))
    return lines


GAS_EDGE_STEPS = ((0, 0), (1, 0), (-1, 0), (0, 1), (0, -1))


def _observe_gas_front(state, memo: dict[str, Any]) -> None:
    """蒸气的出口：本回合气在眼前推进到了哪、又从哪退了——报的是已经发生的事。

    这里**不重演扩散规则**：``GAS_MIN_FLOW``、邻格轮转、``max_diffusion`` 都住在
    ``materials_sim`` 自己的活动格索引里，本函数只做两次亲见之间的差分，所以它既不
    预测也不改世界。目录写明「不显示墙后气体」，于是视野外的格子一条都不进快照，
    来向也只认上一回合亲眼见过带气的那一格。要能说「这格是这一回合才起气的」，得
    上一回合看见过它是空的——``blank`` 记的就是眼前没气的那些格。凭空起的气（新开
    的漏口）因此有两条口径：追得到邻格就报来向，追不到就只说起了气、不猜方向。上一
    回合没盯过的格子（刚进视野的）一律不算本回合的推进，免得把旧气报成新事。
    """
    gas: set[str] = set()
    blank: set[str] = set()
    for x, y in state.visible_cells():
        cell = state.cell(x, y)
        (gas if cell.gas > 0 and cell.gas_kind else blank).add(f"{x},{y}")
    layer = str(state.layer_key())
    stored = memo.get("gas_front") or {}
    same_layer = stored.get("layer") == layer
    previous = set(stored.get("gas", ())) if same_layer else set()
    empty_last = set(stored.get("blank", ())) if same_layer else set()
    advances: list[tuple[int, int, int, int]] = []
    unexplained: list[tuple[int, int]] = []
    retreats: list[tuple[int, int]] = []
    px, py = state.player.x, state.player.y
    # 「在已见气体边缘」是目录给的触发口径：站在气旁边看它动，才谈得上出口在哪。
    if any(f"{px + dx},{py + dy}" in gas for dx, dy in GAS_EDGE_STEPS):
        for key in sorted(gas - previous):
            if key not in empty_last:
                continue
            x, y = (int(value) for value in key.split(","))
            origin = next(((x + dx, y + dy) for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))
                           if f"{x + dx},{y + dy}" in previous), None)
            if origin is None:
                unexplained.append((x, y))
            else:
                advances.append((x, y, origin[0], origin[1]))
        for key in sorted(previous - gas):
            if key not in blank:
                continue  # 这回合它不在眼里：是气退了还是只是看不见了，分不出来
            x, y = (int(value) for value in key.split(","))
            retreats.append((x, y))
    memo["gas_front"] = {"layer": layer, "time": int(state.time),
                         "gas": sorted(gas), "blank": sorted(blank)}
    state.messages.extend(_report_gas_front(advances, unexplained, retreats))


def _report_gas_front(advances: list[tuple[int, int, int, int]],
                      unexplained: list[tuple[int, int]],
                      retreats: list[tuple[int, int]]) -> list[str]:
    """一条消息一类读数；模板必须是 `tr()` 字面量，理由见 `_report_light_read`。"""
    lines = []
    if advances:
        lines.append(tr(
            "蒸气的出口：本回合 {n} 格新起了气——{cells}，自 ({sx}, {sy}) 推进。",
            n=len(advances),
            cells=", ".join(f"({x}, {y})" for x, y, _a, _b in advances[:3]),
            sx=advances[0][2], sy=advances[0][3]))
        if len(advances) > 3:
            lines.append(tr("蒸气的出口：另有 {n} 格新推进的落点一并记下。",
                            n=len(advances) - 3))
    if unexplained:
        lines.append(tr(
            "蒸气的出口：本回合 {n} 格起了气，可上一回合没看见挨着它的气——{cells}；不猜来向。",
            n=len(unexplained),
            cells=", ".join(f"({x}, {y})" for x, y in unexplained[:3])))
    if retreats:
        lines.append(tr(
            "蒸气的出口：本回合 {n} 格的气退了——{cells}。",
            n=len(retreats),
            cells=", ".join(f"({x}, {y})" for x, y in retreats[:3])))
    return lines


LAMP_REACH = 10      # 与「认光源而非亮斑」同一档读数窗口
LAMP_LINK_GAP = 2    # 隔在几回合以内的两次亲见，还算同一次联动
LAMP_REPORT_LINES = 3


def _visible_lamps(state, reach: int) -> dict[str, int]:
    """眼前真发光的格（``"x,y"`` → 光源半径）。

    「连续亲见」是目录给的口径：没进过视线的灯不算亮过，也就不算熄灭；正在熄灭的
    那一格如果这一回合已经看不见了，同样不报——分不清是灯灭了还是它出了视野。
    """
    from .vision import glow
    px, py = state.player.x, state.player.y
    return {f"{x},{y}": int(radius)
            for x, y, radius in glow.sources_in_window(state, (px, py), reach)
            if radius and state.is_visible(x, y)}


def _lamp_switch(state, key: str):
    """这格灯上游那个**亲眼见过**的输入端；看不见、没接线就返回 ``None``。

    反查走接线表（``node["inputs"]`` 往上游），与 `先断哪根` 同一份口径，不重跑
    电流仿真。目录写明「未知控制端仍标未知」，所以看不见的开关连名字都不报。
    """
    from ..circuit_schema import INPUTS
    x, y = (int(value) for value in key.split(","))
    for board in state.circuit_boards:
        nodes = board["nodes"]
        for node_key, node in nodes.items():
            if node.get("op") != "output" or list(node["pos"][:2]) != [x, y]:
                continue
            stack = [node_key]
            seen = {node_key}
            while stack:
                current = stack.pop()
                for ref in nodes.get(current, {}).get("inputs", []):
                    if ref in seen or ref not in nodes:
                        continue
                    seen.add(ref)
                    stack.append(ref)
                    source = nodes[ref]
                    if source["op"] not in INPUTS:
                        continue
                    sx, sy = (int(value) for value in source["pos"][:2])
                    if state.is_visible(sx, sy):
                        return (str(source["label"]), sx, sy)
    return None


def _observe_lamp_order(state, memo: dict[str, Any]) -> None:
    """留意熄灯顺序：只在亲见的熄灭之间排先后，两次一致才敢说顺序。

    每回合把眼前的灯抄一份快照，与上一份做差，得到的只是**已经发生**的熄灭——
    既不预测谁下一个灭，也不替世界改任何一盏灯。一次联动是两个熄灭之间相隔
    ≤ ``LAMP_LINK_GAP`` 回合；同一回合熄灭的两盏只算「同时」，永远不排先后。
    只有同一对先后关系被亲见**两次**，这条洞察才报出顺序（目录那句「连续亲见
    两盏灯联动后」）；反过来的先后也出现过，就把这条推演当众作废。读过的对子
    按层存进 ``realm_features['growth_observations']['lamp_order']``，报过一次的
    不再重复开口；换了层，全部读数清零。
    """
    lamps = _visible_lamps(state, LAMP_REACH)
    layer = str(state.layer_key())
    stored = memo.get("lamp_order") or {}
    same_layer = stored.get("layer") == layer
    previous = dict(stored.get("lamps", {})) if same_layer else {}
    darkened_at: dict[str, int] = dict(stored.get("dark", {})) if same_layer else {}
    pairs: dict[str, dict[str, Any]] = dict(stored.get("pairs", {})) if same_layer else {}
    turn = int(state.time)

    just_dark: list[str] = []
    for key in sorted(previous):
        if key in lamps:
            continue
        x, y = (int(value) for value in key.split(","))
        if not state.is_visible(x, y):
            continue  # 这一眼看不见它：是灭是留分不出来，不记
        just_dark.append(key)
    for key in lamps:
        # 又亮了：这一轮的联动到此为止，不跟以后的熄灭配对。攒下的先后记录留着——
        # 「连续亲见两盏灯联动」说的就是两轮，删了它这条洞察永远确认不了顺序。
        darkened_at.pop(key, None)
    for key in just_dark:
        darkened_at[key] = turn

    ties: list[str] = []
    for second in just_dark:
        for first, at in darkened_at.items():
            if first == second:
                continue
            gap = turn - at
            if gap < 0 or gap > LAMP_LINK_GAP:
                continue
            if gap == 0:
                ties.append("|".join(sorted((first, second))))
                continue
            pid = f"{first}|{second}"
            row = pairs.setdefault(pid, {"lags": [], "reported": False, "void": False})
            row["lags"].append(gap)
            if f"{second}|{first}" in pairs:
                row["void"] = True
                pairs[f"{second}|{first}"]["void"] = True
    for key in [key for key, at in darkened_at.items() if turn - at > LAMP_LINK_GAP]:
        del darkened_at[key]

    confirmed: list[dict[str, Any]] = []
    void: list[dict[str, Any]] = []
    known_ties = set(stored.get("ties", ())) if same_layer else set()
    # 同一对灯在一回合里会正反各撞上一次，先去掉重复，再说「几对」。
    new_ties = [tie for tie in dict.fromkeys(ties) if tie not in known_ties]
    for pid, row in sorted(pairs.items()):
        if row.get("void"):
            first, second = pid.split("|")
            twin = f"{second}|{first}"
            row["voided"] = True
            pairs.get(twin, {})["voided"] = True
            # 一对灯的先后相反只有一句话可说，不因为正反两条记录各报一遍。
            if not row.get("void_said") and pid <= twin:
                row["void_said"] = True
                pairs.get(twin, {})["void_said"] = True
                void.append({"first": first, "second": second})
            continue
        if len(row["lags"]) >= 2 and not row.get("reported"):
            first, second = pid.split("|")
            row["reported"] = True
            row["control"] = _shared_switch(state, first, second)
            confirmed.append({"first": first, "second": second,
                              "lags": list(row["lags"][:2]),
                              "control": row["control"]})

    memo["lamp_order"] = {"layer": layer, "time": turn, "lamps": dict(lamps),
                          "dark": darkened_at, "pairs": pairs,
                          "ties": sorted(known_ties | set(new_ties))}
    state.messages.extend(_report_lamp_order(confirmed, void, sorted(new_ties)))


def _shared_switch(state, first: str, second: str):
    """两盏灯共用的、看得见的控制端；各接各的或都看不见就返回 ``None``。"""
    left = _lamp_switch(state, first)
    right = _lamp_switch(state, second)
    if left is not None and left == right:
        return left
    return None


def _report_lamp_order(confirmed: list[dict[str, Any]], void: list[dict[str, Any]],
                       ties: list[str]) -> list[str]:
    """一类读数一条消息；模板必须是 `tr()` 字面量，理由见 `_report_light_read`。"""
    lines: list[str] = []
    for row in confirmed[:LAMP_REPORT_LINES]:
        ax, ay = (int(value) for value in row["first"].split(","))
        bx, by = (int(value) for value in row["second"].split(","))
        lines.append(tr(
            "留意熄灯顺序：({ax}, {ay}) 先于 ({bx}, {by}) 熄灭，两次亲见分别隔 {g1}、{g2} 回合。",
            ax=ax, ay=ay, bx=bx, by=by,
            g1=int(row["lags"][0]), g2=int(row["lags"][1])))
        control = row.get("control")
        if control:
            label, sx, sy = control
            lines.append(tr(
                "留意熄灯顺序：这一对的上游是亲眼见过的「{label}」 ({x}, {y})。",
                label=label, x=sx, y=sy))
        else:
            lines.append(tr("留意熄灯顺序：这一对的控制端两次都没看见，按未知记下。"))
    if len(confirmed) > LAMP_REPORT_LINES:
        lines.append(tr("留意熄灯顺序：另有 {n} 对已确认的先后一并记下。",
                        n=len(confirmed) - LAMP_REPORT_LINES))
    for row in void[:LAMP_REPORT_LINES]:
        ax, ay = (int(value) for value in row["first"].split(","))
        bx, by = (int(value) for value in row["second"].split(","))
        lines.append(tr(
            "留意熄灯顺序：({ax}, {ay}) 与 ({bx}, {by}) 两次的先后相反，这条推演作废。",
            ax=ax, ay=ay, bx=bx, by=by))
    if ties:
        lines.append(tr(
            "留意熄灯顺序：{n} 对灯在同一回合熄灭，分不出先后——{pairs}。",
            n=len(ties),
            pairs=", ".join(
                f"({ax}, {ay})、({bx}, {by})"
                for ax, ay, bx, by in (_tie_spots(tie) for tie in ties[:3]))))
    return lines


def _tie_spots(tie: str) -> tuple[int, int, int, int]:
    a, b = tie.split("|")
    ax, ay = (int(value) for value in a.split(","))
    bx, by = (int(value) for value in b.split(","))
    return ax, ay, bx, by


LIT_RISK_REACH = 12        # 读数窗口：与异象听觉上限同一档，超过这一圈不作提示
LIT_RISK_REPORT_LINES = 3


def _lit_risk_read(state, name: str, effect: dict[str, Any]) -> int:
    """亮处未必安全：只报亮区里那些「先前亲眼确认过、而且是审核过的视觉型」的异象。

    目录给的两条信息权限都收在这一个函数里。一是**不泄露暗处敌人**：异象脚下那一格
    必须此刻真被光源照到（``glow.lit``，与被「裁光」挡在扇区外的口径同一张表），
    暗处的异象连数量都不报——这一条读数只说亮处有几个。二是**提示自己可能进入其
    视线**：只有它此刻真看得见玩家，或玩家已经落在它当前视距之内，才开口；站得够远
    就一个字不说，不制造不存在的危险。既不预测走位，也不替世界改动任何一格光。

    「视觉型」认的是 ``data/perception`` 里审核过的视距：没有审核过视听的种类
    （``anomaly.unknown`` 一类）与不靠视听的迁徙楼梯／空白裂隙都不在提示之列——
    说不清它靠不靠眼睛，就不替它下这个结论。位置也必须是**先前确认过的**（
    ``catalog_observed``）：这条洞察读的是「已知的那只走到了亮处」，不是隔墙定位。

    同一只异象的同一档读数只报一次，反复凝听不该把同一句危险说两遍；读数换档
    （「够得着」↔「正看着你」）才算新消息。换了层，全部读数清零。
    """
    from ..data.perception import perception_profile
    from .vision import glow
    reach = max(1, int(effect.get("reach", LIT_RISK_REACH) or LIT_RISK_REACH))
    px, py = state.player.x, state.player.y
    memo = state.realm_features.setdefault("growth_observations", {})
    layer = str(state.layer_key())
    stored = memo.get("lit_risk") or {}
    marks: dict[str, str] = dict(stored.get("marks", {})) if stored.get("layer") == layer else {}
    news: list[dict[str, Any]] = []
    for enemy in state.enemies:
        if enemy.integrity <= 0 or not enemy.catalog_observed:
            continue
        if abs(enemy.x - px) + abs(enemy.y - py) > reach:
            continue
        if not glow.lit(state, enemy.x, enemy.y):
            continue
        profile = perception_profile(getattr(enemy, "catalog_id", ""))
        if profile is None or profile.vision is None or profile.vision <= 0:
            continue
        vision = state._effective_vision(enemy)
        distance = abs(enemy.x - px) + abs(enemy.y - py)
        if state.can_see(enemy, px, py):
            risk = "sees"
        elif distance <= vision:
            risk = "near"
        else:
            continue
        key = str(enemy.id)
        if marks.get(key) == risk:
            continue
        marks[key] = risk
        news.append({"x": int(enemy.x), "y": int(enemy.y), "risk": risk, "vision": int(vision),
                     "label": state.observed_entity_label(enemy)})
    memo["lit_risk"] = {"layer": layer, "marks": marks}
    state.messages.extend(_report_lit_risk(news))
    return len(news)


def _report_lit_risk(rows: list[dict[str, Any]]) -> list[str]:
    """一只异象一行读数，「正看着你」排在「够得着」前面。

    模板必须是**字面量**写在 `tr()` 里，理由见 `_report_light_read`：英文覆盖率闸门
    只认字面量调用。
    """
    if not rows:
        return []
    ordered = sorted(rows, key=lambda row: (row["risk"] != "sees", row["y"], row["x"]))
    lines: list[str] = []
    for row in ordered[:LIT_RISK_REPORT_LINES]:
        if row["risk"] == "sees":
            lines.append(tr(
                "亮处未必安全：({x}, {y}) 的「{label}」站在亮区里，它此刻正看得见你（视距 {v}）。",
                x=row["x"], y=row["y"], label=row["label"], v=row["vision"]))
        else:
            lines.append(tr(
                "亮处未必安全：({x}, {y}) 的「{label}」站在亮区里，眼下隔着遮挡，"
                "但你已经在它视距 {v} 之内。",
                x=row["x"], y=row["y"], label=row["label"], v=row["vision"]))
    if len(rows) > LIT_RISK_REPORT_LINES:
        lines.append(tr(
            "亮处未必安全：另有 {n} 个亮区里已确认的视觉型异象一并记下。",
            n=len(rows) - LIT_RISK_REPORT_LINES))
    return lines


PAIR_SUBMITTABLE_OPS = ("toggle", "pulse", "step")
PAIR_MEMORY_OPS = ("toggle", "pulse", "sequence", "timer")
PAIR_MAX_ROUTES = 24      # 单只端口的下游路线上限：读不完就标未知，不替它作保
PAIR_MAX_CHAIN = 12       # 单条路线最长走到第几只件：超过这一样也算读不完
PAIR_REPORT_LINES = 3


def _pair_cell(nodes: dict[str, Any], key: str) -> tuple[int, int]:
    return tuple(int(value) for value in nodes[key]["pos"][:2])


def _pair_feeds(nodes: dict[str, Any]) -> dict[str, list[str]]:
    """`node["inputs"]` 的反向邻接：这一只往下牵给谁。"""
    feeds: dict[str, list[str]] = {}
    for key, node in nodes.items():
        for ref in node.get("inputs", []):
            feeds.setdefault(ref, []).append(key)
    return feeds


def _pair_routes(nodes: dict[str, Any], feeds: dict[str, list[str]], start: str,
                 *, max_routes: int = PAIR_MAX_ROUTES,
                 max_chain: int = PAIR_MAX_CHAIN) -> tuple[list[tuple[str, ...]], bool]:
    """从端口一路往下走到接收端，把每条路线（含两端）列出来。

    走的是**接线表**，不重跑 `core/circuits.py::_settle_circuit`：这条洞察报的是
    「这一拍接不接得上」，替世界合闸属于结算层，两处各算一份迟早对不上。分叉全收，
    同一只件不在一条路线里走两遍（防环）。走得太长或铺得太多就不下结论——
    第二个返回值是「这一眼读不完」。
    """
    routes: list[tuple[str, ...]] = []
    unread = False
    stack: list[tuple[str, ...]] = [(start,)]
    while stack:
        chain = stack.pop()
        current = chain[-1]
        nxt = [key for key in feeds.get(current, []) if key not in chain]
        if not nxt:
            if nodes[current]["op"] == "output" and len(chain) > 1:
                routes.append(chain)
            continue
        for key in nxt:
            if len(chain) + 1 > max_chain:
                unread = True
                continue
            stack.append(chain + (key,))
    if len(routes) > max_routes:
        unread = True
    return routes[:max_routes], unread


def _pair_verdict(state, board: dict[str, Any], nodes: dict[str, Any],
                  feeds: dict[str, list[str]], left: str, right: str,
                  *, max_routes: int = PAIR_MAX_ROUTES,
                  max_chain: int = PAIR_MAX_CHAIN):
    """两只端口现在各提交一次信号，会不会**同一回合**落到同一个接收端。

    `core/circuits.py` 的模块口径：组合门在一个客观回合里按拓扑序一次落定，只有
    开关／脉冲／音序／节拍与自锁输出记得住上一回合。所以「同拍」的判据是**会师的
    每一条路线都只过不带记忆的件**：
      * 有一条会师路线上某个中途件（或接收端自锁）是那种记得住上一回合的件＝不同拍，
        当场点名那只件——它就在眼前的格子上，看得见才敢报名字；
      * 有一条会师路线上有一格没看清，或整片下级这一眼读不完＝未明延迟，标未知；
      * 两只端口根本不会师＝没什么可说（返回 None，不编一条「不同拍」出来）。
    """
    left_routes, left_unread = _pair_routes(nodes, feeds, left,
                                            max_routes=max_routes, max_chain=max_chain)
    right_routes, right_unread = _pair_routes(nodes, feeds, right,
                                              max_routes=max_routes, max_chain=max_chain)
    if left_unread or right_unread:
        return "unknown", "unread"
    met = [(a, b) for a in left_routes for b in right_routes if a[-1] == b[-1]]
    if not met:
        return None
    forced = board["state"].get("forced_until", {})
    now = int(state.time)
    for a, b in met:
        if not all(state.is_visible(*_pair_cell(nodes, key))
                   for key in set(a) | set(b)):
            return "unknown", "unseen"
        for key in list(a[1:-1]) + list(b[1:-1]):
            node = nodes[key]
            if node["op"] in PAIR_MEMORY_OPS or int(forced.get(key, -1)) > now:
                return "held", str(node["label"])
        receiver = nodes[a[-1]]
        if receiver.get("latch") or int(forced.get(a[-1], -1)) > now:
            return "held", str(receiver["label"])
    return "same", str(nodes[met[0][0][-1]]["label"])


def _same_tick_pairing(state, name: str, effect: dict[str, Any]) -> int:
    """同拍才接：把同一块板上「自己按得动的两只端口」读成会不会同一回合落到一处。

    只对**此刻两只都看得见**的可提交端口开口：看不见的那只现在按不按得到都不知道，
    更不说它牵了什么。读数按层存进
    `realm_features['growth_observations']['same_tick']`，同一对同样结论不重复播报，
    结论变了才再开口，换层清零。
    """
    max_lines = max(1, int(effect.get("max_report_lines", PAIR_REPORT_LINES)
                            or PAIR_REPORT_LINES))
    max_routes = max(1, int(effect.get("max_routes", PAIR_MAX_ROUTES) or PAIR_MAX_ROUTES))
    max_chain = max(2, int(effect.get("max_chain", PAIR_MAX_CHAIN) or PAIR_MAX_CHAIN))
    memo = state.realm_features.setdefault("growth_observations", {})
    layer = str(state.layer_key())
    stored = memo.get("same_tick") or {}
    pairs: dict[str, dict[str, Any]] = (dict(stored.get("pairs", {}))
                                        if stored.get("layer") == layer else {})
    analysed: dict[str, dict[str, Any]] = {}
    for index, board in enumerate(state.circuit_boards):
        nodes = board["nodes"]
        feeds = _pair_feeds(nodes)
        ports = sorted(key for key, node in nodes.items()
                       if node["op"] in PAIR_SUBMITTABLE_OPS
                       and state.is_visible(*_pair_cell(nodes, key)))
        for position, left in enumerate(ports):
            for right in ports[position + 1:]:
                verdict = _pair_verdict(state, board, nodes, feeds, left, right,
                                        max_routes=max_routes, max_chain=max_chain)
                if verdict is None:
                    continue
                kind, detail = verdict
                analysed[f"{index}:{left}|{right}"] = {
                    "layer": layer, "verdict": kind, "detail": detail,
                    "left": str(nodes[left]["label"]),
                    "right": str(nodes[right]["label"]),
                }
    fresh: list[dict[str, Any]] = []
    changed: list[dict[str, Any]] = []
    for key, record in sorted(analysed.items()):
        old = pairs.get(key)
        if old is None or old.get("layer") != layer:
            fresh.append(record)
        elif old.get("verdict") != record["verdict"] or old.get("detail") != record["detail"]:
            changed.append(record)
        pairs[key] = record
    for key in [key for key in pairs if key not in analysed]:
        # 板子拆了／端口挪了：留着旧读数就会报一对已经不存在的接线。
        del pairs[key]
    memo["same_tick"] = {"layer": layer, "pairs": pairs}
    state.messages.extend(_report_same_tick(fresh, changed, max_lines))
    return len(fresh) + len(changed)


def _report_same_tick(fresh: list[dict[str, Any]], changed: list[dict[str, Any]],
                      max_lines: int) -> list[str]:
    """一对端口一行读数；模板必须写成 `tr()` 字面量，理由见 `_report_light_read`。"""
    if not fresh and not changed:
        return []
    lines: list[str] = []
    for record in fresh[:max_lines]:
        lines.append(_same_tick_line(record))
    if len(fresh) > max_lines:
        lines.append(tr("同拍才接：另有 {n} 对可提交端口一并记下。",
                        n=len(fresh) - max_lines))
    for record in changed[:max_lines]:
        lines.append(_same_tick_line(record))
    if len(changed) > max_lines:
        lines.append(tr("同拍才接：另有 {n} 对读数改口一并记下。",
                        n=len(changed) - max_lines))
    return lines


def _same_tick_line(record: dict[str, Any]) -> str:
    if record["verdict"] == "same":
        return tr("同拍才接：「{left}」与「{right}」只过不带记忆的接线，"
                  "落在「{recv}」时同一回合到。", left=record["left"],
                  right=record["right"], recv=record["detail"])
    if record["verdict"] == "held":
        return tr("同拍才接：「{left}」与「{right}」眼下不同拍——"
                  "中间那只「{el}」记得住上一回合。", left=record["left"],
                  right=record["right"], el=record["detail"])
    if record["detail"] == "unread":
        return tr("同拍才接：「{left}」与「{right}」的下级接得太密，这一眼读不完——"
                  "未明的延迟标未知。", left=record["left"], right=record["right"])
    return tr("同拍才接：「{left}」与「{right}」之间有一截接线没看清——"
              "未明的延迟标未知，不猜第几回合到。",
              left=record["left"], right=record["right"])


BACKFLOW_REPORT_LINES = 3


def _backflow_tubes(state) -> dict[str, dict[str, Any]]:
    """本层还架着的导流管：把「谁往谁那边搬」读成一张以出口为名的网络。

    只认 `core/item_devices.py` 那一张逐层装置表——`deploy_siphon` 登记什么形状，
    这里就读什么形状，不另存一份管子台账（两处各记迟早对不上）。键用**源与出口的
    坐标对**，不用列表下标：同一层再架一根，旧的读数不该跟着挪位。
    """
    from .item_devices import devices
    tubes: dict[str, dict[str, Any]] = {}
    for record in devices(state):
        if str(record.get("kind")) != "siphon":
            continue
        data = record.get("data") or {}
        source = [int(value) for value in data.get("source", ())[:2]]
        outlet = [int(value) for value in data.get("exit", ())[:2]]
        if len(source) != 2 or len(outlet) != 2:
            continue
        tubes[f"{source[0]},{source[1]}>{outlet[0]},{outlet[1]}"] = {
            "source": source, "outlet": outlet, "mode": str(data.get("mode", "liquid"))}
    return tubes


def _backflow_medium(mode: str) -> str:
    return tr("气体") if mode == "gas" else tr("液体")


def _backflow_levels(state, tube: dict[str, Any]) -> tuple[int, int]:
    attribute = "gas" if tube["mode"] == "gas" else "liquid"
    sx, sy = tube["source"]
    ox, oy = tube["outlet"]
    return (int(getattr(state.cell(sx, sy), attribute)),
            int(getattr(state.cell(ox, oy), attribute)))


def _siphon_backflow_note(state, name: str, effect: dict[str, Any]) -> int:
    """看见回流：只在**两头都盯在眼里**的两次读数之间比差额，出口退了就报那个出口。

    目录给这条的信息权限收在三点上。一是**只比已见的两头**：源与出口某一眼没被看见，
    这一眼就不比差额，并把底重新起——中间那一段没看着，不能拿它当逆流。二是**只报
    哪一格变了，不报为什么变**：源被别的东西灌回、出口被蒸干或被人泼走，世界这一回合
    干的事这条洞察不猜，每一行末尾都留一句「原因还得自己再看一眼」；重新看过一次也
    只报新读数，不因为多看了一眼就把原因说出来。三是**管子撤了就不提**：装置表里没有
    的那根，台账跟着删，不留一根已经不存在的管子继续记账。

    同一根管子同一档读数只报一次；报过之后要等出口再出现一次**新的**读数才算重新看过，
    否则只进「还没重新看到」那一笔账，而且那笔账只在名单变化时开口一次。换了层清零。
    """
    max_lines = max(1, int(effect.get("max_report_lines", BACKFLOW_REPORT_LINES)
                            or BACKFLOW_REPORT_LINES))
    memo = state.realm_features.setdefault("growth_observations", {})
    layer = str(state.layer_key())
    stored = memo.get("backflow") or {}
    watched: dict[str, dict[str, Any]] = (dict(stored.get("tubes", {}))
                                          if stored.get("layer") == layer else {})
    tubes = _backflow_tubes(state)
    news: list[dict[str, Any]] = []
    rewatched: list[dict[str, Any]] = []
    for key, tube in sorted(tubes.items()):
        sx, sy = tube["source"]
        ox, oy = tube["outlet"]
        old = watched.get(key)
        if not (state.is_visible(sx, sy) and state.is_visible(ox, oy)):
            watched.pop(key, None)
            continue
        source_now, outlet_now = _backflow_levels(state, tube)
        current = {"layer": layer, "mode": tube["mode"], "key": key, "x": ox, "y": oy,
                   "sx": sx, "sy": sy, "source_amount": source_now,
                   "outlet_amount": outlet_now}
        if old is None:
            watched[key] = current
            continue
        outlet_loss = int(old["outlet_amount"]) - outlet_now
        source_gain = source_now - int(old["source_amount"])
        pending = old.get("pending")
        if outlet_loss > 0 or source_gain > 0:
            current["pending"] = {"outlet_amount": outlet_now}
            watched[key] = current
            news.append({**current, "outlet_loss": max(0, outlet_loss),
                         "source_gain": max(0, source_gain)})
        elif isinstance(pending, dict) and int(pending.get("outlet_amount",
                                                           outlet_now)) != outlet_now:
            watched[key] = current
            rewatched.append({**current, "was": int(pending["outlet_amount"])})
        else:
            if isinstance(pending, dict):
                current["pending"] = pending
            watched[key] = current
    for key in [key for key in watched if key not in tubes]:
        # 管子灌满撤了：留着旧读数就会给一根已经不存在的管子记账。
        del watched[key]
    reported = {item["key"] for item in news}
    carried = sorted(key for key, record in watched.items()
                     if isinstance(record.get("pending"), dict) and key not in reported)
    notified = sorted(stored.get("notified", [])) if stored.get("layer") == layer else []
    memo["backflow"] = {"layer": layer, "tubes": watched, "notified": carried}
    unnoticed = [key for key in carried if key not in set(notified)]
    state.messages.extend(_report_backflow(news, rewatched, carried, unnoticed, max_lines))
    return len(news) + len(rewatched)


def _report_backflow(news: list[dict[str, Any]], rewatched: list[dict[str, Any]],
                    carried: list[str], unnoticed: list[str],
                    max_lines: int) -> list[str]:
    """一根管子一行读数；模板必须写成 `tr()` 字面量，理由见 `_report_light_read`。"""
    if not news and not rewatched and not unnoticed:
        return []
    lines: list[str] = []
    for record in news[:max_lines]:
        lines.append(_backflow_line(record))
    if len(news) > max_lines:
        lines.append(tr("看见回流：另有 {n} 处已见出口的逆流一并记下。",
                        n=len(news) - max_lines))
    for record in rewatched[:max_lines]:
        lines.append(tr(
            "看见回流：重新看到 ({x}, {y}) 的出口——读数从 {was} 变成 {now}。"
            "这一眼仍只报数，不替它说原因。",
            x=record["x"], y=record["y"], was=record["was"], now=record["outlet_amount"]))
    if len(rewatched) > max_lines:
        lines.append(tr("看见回流：另有 {n} 处重新看到的出口读数一并记下。",
                        n=len(rewatched) - max_lines))
    if unnoticed:
        lines.append(tr(
            "看见回流：{n} 处报过的逆流还没重新看到出口的新读数——不替它们猜原因。",
            n=len(carried)))
    return lines


def _backflow_line(record: dict[str, Any]) -> str:
    medium = _backflow_medium(record["mode"])
    if record["outlet_loss"] and record["source_gain"]:
        return tr(
            "看见回流：({x}, {y}) 的出口退了 {o} 单位{medium}，({sx}, {sy}) 的源反倒多回 "
            "{s} 单位——两头都在倒着走。原因还得自己再看一眼。",
            x=record["x"], y=record["y"], o=record["outlet_loss"], s=record["source_gain"],
            medium=medium, sx=record["sx"], sy=record["sy"])
    if record["outlet_loss"]:
        return tr(
            "看见回流：({x}, {y}) 的出口在退——这一格少了 {n} 单位{medium}，"
            "不像是管子往它那边送的样子。原因还得自己再看一眼。",
            x=record["x"], y=record["y"], n=record["outlet_loss"], medium=medium)
    return tr(
        "看见回流：({x}, {y}) 的出口没退，倒是 ({sx}, {sy}) 的源多回来 {n} 单位{medium}"
        "——这一眼只报方向反了。原因还得自己再看一眼。",
        x=record["x"], y=record["y"], sx=record["sx"], sy=record["sy"],
        n=record["source_gain"], medium=medium)


FRONTIER_REPORT_LINES = 3
EXIT_OPTION_KEYS = ("enter_realm", "exit_realm")


def _frontier_exits(state) -> list[dict[str, Any]]:
    """眼下还在场上、还回应得了、出口那一格此刻也在眼里的「走得出去的地方」。

    出口只认事件选项里真的写着换层／换位面动作的那几条；已 resolved 的地点不再指路。
    """
    found: list[dict[str, Any]] = []
    for event in getattr(state, "events", ()):
        if bool(getattr(event, "resolved", False)):
            continue
        options = getattr(event, "options", ()) or ()
        if not any(isinstance(option, dict)
                   and any(option.get(key) for key in EXIT_OPTION_KEYS)
                   for option in options):
            continue
        x, y = int(event.x), int(event.y)
        if not state.is_visible(x, y):
            continue
        found.append({"x": x, "y": y})
    return sorted(found, key=lambda item: (item["y"], item["x"]))


def _frontier_walk(state, x: int, y: int) -> tuple[int, int, int]:
    """沿「我 → 那一格」这条直线走，看确认过的地形能撑到第几格。

    返回（最远连续确认格的距离、第一个没确认过的格的距离、出口自身的距离）；
    整条线都确认过则第二个是 −1。只走这一条直线，不铺路径、不替玩家找下一步。
    """
    from .vision.knowledge import remembered_terrain

    px, py = int(state.player.x), int(state.player.y)
    steps = max(abs(x - px), abs(y - py))
    if steps <= 0:
        return (1, -1, 0) if remembered_terrain(state, x, y) is not None else (0, 1, 0)
    confirmed = 0
    gap = -1
    for step in range(1, steps + 1):
        cx = px + round((x - px) * step / steps)
        cy = py + round((y - py) * step / steps)
        if remembered_terrain(state, cx, cy) is None:
            gap = step
            break
        confirmed = step
    return confirmed, gap, steps


def _frontier_exit_bearing(state, name: str, effect: dict[str, Any]) -> int:
    """「边界还在更深处」：把看得见的出口对着**我自己确认过的地形边界**报一次相对方向。

    三条信息权限：①只报此刻在眼里的出口，看不见的一条不报、也不给个数；
    ②边界只由 `terrain_memory` 里我亲自记下的格撑起，线上一格没记到就停下来说
    「说不清」，绝不拿真实地图冒充我的确认；③只给方位与格数，不给路径、不猜那边有什么。
    """
    from .tamper_compass import direction_of

    max_lines = max(1, int(effect.get("max_report_lines",
                                      FRONTIER_REPORT_LINES) or FRONTIER_REPORT_LINES))
    memo = state.realm_features.setdefault("growth_observations", {})
    layer = str(state.layer_key())
    stored = memo.get("frontier") or {}
    seen: dict[str, dict[str, Any]] = (dict(stored.get("exits", {}))
                                       if stored.get("layer") == layer else {})
    exits = _frontier_exits(state)
    news: list[dict[str, Any]] = []
    changed: list[dict[str, Any]] = []
    current: dict[str, dict[str, Any]] = {}
    for cell in exits:
        x, y = cell["x"], cell["y"]
        confirmed, gap, distance = _frontier_walk(state, x, y)
        verdict = ("unseen" if confirmed <= 0 and gap > 0
                   else "inside" if gap < 0 else "beyond")
        record = {"x": x, "y": y, "distance": distance,
                  "bearing": str(direction_of(state, x, y)),
                  "confirmed": confirmed, "verdict": verdict}
        key = f"{x},{y}"
        current[key] = record
        old = seen.get(key)
        if old is None:
            news.append(record)
        elif (old.get("verdict") != record["verdict"]
                or old.get("bearing") != record["bearing"]
                or old.get("distance") != record["distance"]
                or old.get("confirmed") != record["confirmed"]):
            changed.append(record)
        seen[key] = record
    for key in [key for key in seen if key not in current]:
        # 出口拆了／挪出眼了：留着旧读数就会给一个已经不在这儿的方向记账。
        del seen[key]
    memo["frontier"] = {"layer": layer, "exits": seen}
    state.messages.extend(_report_frontier(news, changed, max_lines))
    return len(news) + len(changed)


def _report_frontier(news: list[dict[str, Any]], changed: list[dict[str, Any]],
                     max_lines: int) -> list[str]:
    """一处出口一行；模板必须写成 `tr()` 字面量，理由见 `_report_light_read`。"""
    if not news and not changed:
        return []
    lines: list[str] = []
    for record in news[:max_lines]:
        lines.append(_frontier_line(record))
    if len(news) > max_lines:
        lines.append(tr("边界更深：另有 {n} 处看得见的出口一并记下。",
                        n=len(news) - max_lines))
    for record in changed[:max_lines]:
        lines.append(tr("边界更深：重新对上 ({x}, {y}) 的出口——现在在{bearing}、"
                        "约 {distance} 格外，{tail}",
                        x=record["x"], y=record["y"], bearing=record["bearing"],
                        distance=record["distance"],
                        tail=_frontier_tail(record["verdict"], record["confirmed"])))
    if len(changed) > max_lines:
        lines.append(tr("边界更深：另有 {n} 处出口改了读数一并记下。",
                        n=len(changed) - max_lines))
    return lines


def _frontier_tail(verdict: str, confirmed: int) -> str:
    if verdict == "unseen":
        return tr("这一向我连一格确认过的地形都没有，边界在哪说不清。")
    if verdict == "inside":
        return tr("出口还在已确认的地形里，走得过去。")
    return tr("沿这一向我确认过的地形只到 {n} 格，再往外是没亲自走过的地方。"
              "它不报边界之外有什么。", n=confirmed)


def _frontier_line(record: dict[str, Any]) -> str:
    return tr("边界更深：({x}, {y}) 的出口在{bearing}、约 {distance} 格外——{tail}",
              x=record["x"], y=record["y"], bearing=record["bearing"],
              distance=record["distance"],
              tail=_frontier_tail(record["verdict"], record["confirmed"]))


RHYTHM_REACH = 12          # 耳程：与异象听觉上限同档，超出这一圈的蓄势声不进我的账
RHYTHM_REPORT_LINES = 3


def _rhythm_skill_name(skill_id: str) -> str:
    from ..data.anomaly_skills import SKILL_DEFINITIONS

    skill = SKILL_DEFINITIONS.get(skill_id)
    return tr(skill.name_zh) if skill is not None else skill_id


def _void_stale_rhythm(last_skill: str, skill_id: str, gaps: dict[str, int],
                       label: str, voided: list[dict[str, Any]]) -> None:
    """换招那一刻作废旧节拍：只作废**报过节拍**的那一招，光起过底的没什么可作废。"""
    if last_skill and skill_id != last_skill and last_skill in gaps:
        voided.append({"label": label, "skill": _rhythm_skill_name(last_skill)})
        gaps.pop(last_skill, None)


def _charge_rhythm_read(state, name: str, effect: dict[str, Any]) -> int:
    """留给对方一拍：同一只已见异象连听两回同一招的蓄势，只报两次起手之间隔了几回合。

    读的是世界自己记下的起手时刻（`core/enemy_skills.py::_skill_begin_cast` 每次蓄势起手都
    写 `active_skill_state['skill_last_used'][skill_id]`），不重演冷却计时、不复制
    `global_gap_rounds`、也不预测下一回收在哪里。三条信息权限：①只数**亲眼确认过身份**
    （`catalog_observed`）且还站着的异象；②曼哈顿 `RHYTHM_REACH` 之外听不见，这一整只当场
    从账上摘掉，重新进耳只起底、不拿听不见的那一段比差额；③目录那句「技能变化后旧提示失效」
    落在换招上——先前那招已经报过节拍的，在它第一次听见另一招蓄势的那一刻作废并说一句，
    它的时间戳仍留着当底，免得把同一段历史重新数一遍。

    第一次进耳只起底（它此前起过几次手我没听见，不替世界补历史）；同一招的同一档间隔只说
    一次，间隔变了才算新读数；换层、死亡、离场一律清零。
    """
    reach = max(1, int(effect.get("reach", RHYTHM_REACH) or RHYTHM_REACH))
    max_lines = max(1, int(effect.get("max_report_lines",
                                      RHYTHM_REPORT_LINES) or RHYTHM_REPORT_LINES))
    px, py = int(state.player.x), int(state.player.y)
    memo = state.realm_features.setdefault("growth_observations", {})
    layer = str(state.layer_key())
    stored = memo.get("charge_rhythm") or {}
    marks: dict[str, dict[str, Any]] = (dict(stored.get("marks", {}))
                                        if stored.get("layer") == layer else {})
    news: list[dict[str, Any]] = []
    voided: list[dict[str, Any]] = []
    present: set[str] = set()
    for enemy in state.enemies:
        if enemy.integrity <= 0 or not enemy.catalog_observed:
            continue
        if abs(enemy.x - px) + abs(enemy.y - py) > reach:
            continue
        book = getattr(enemy, "active_skill_state", None)
        used = book.get("skill_last_used") if isinstance(book, dict) else None
        if not isinstance(used, dict) or not used:
            continue
        key = str(enemy.id)
        present.add(key)
        mark = marks.get(key) or {}
        seen = {str(skill): int(when) for skill, when in (mark.get("seen") or {}).items()}
        gaps = {str(skill): int(gap) for skill, gap in (mark.get("gaps") or {}).items()}
        last_skill = str(mark.get("last_skill", ""))
        label = state.observed_entity_label(enemy)
        charges = sorted(((str(skill), int(when)) for skill, when in used.items()),
                         key=lambda item: (item[1], item[0]))
        for skill_id, start in charges:
            previous = seen.get(skill_id)
            if previous is not None and start <= previous:
                continue
            seen[skill_id] = start
            _void_stale_rhythm(last_skill, skill_id, gaps, label, voided)
            last_skill = skill_id
            if previous is None:
                continue
            gap = start - previous
            if gaps.get(skill_id) == gap:
                continue
            gaps[skill_id] = gap
            news.append({"x": int(enemy.x), "y": int(enemy.y), "label": label,
                         "skill": _rhythm_skill_name(skill_id), "gap": gap})
        marks[key] = {"seen": seen, "gaps": gaps, "last_skill": last_skill}
    for key in [key for key in marks if key not in present]:
        # 死了／散了／走出耳程：留着旧底就会把听不见的那一段当成节拍。
        del marks[key]
    memo["charge_rhythm"] = {"layer": layer, "marks": marks}
    state.messages.extend(_report_charge_rhythm(news, voided, max_lines))
    return len(news) + len(voided)


def _report_charge_rhythm(news: list[dict[str, Any]], voided: list[dict[str, Any]],
                          max_lines: int) -> list[str]:
    """一条读数一行；模板必须写成 `tr()` 字面量，理由见 `_report_light_read`。"""
    if not news and not voided:
        return []
    lines: list[str] = []
    for record in news[:max_lines]:
        lines.append(tr("留给对方一拍：({x}, {y}) 的「{label}」这一招「{skill}」连听两回蓄势，"
                        "两次起手之间隔了 {gap} 回合。它不预测下一回收在哪里。",
                        x=record["x"], y=record["y"], label=record["label"],
                        skill=record["skill"], gap=record["gap"]))
    if len(news) > max_lines:
        lines.append(tr("留给对方一拍：另有 {n} 条节拍读数一并记下。",
                        n=len(news) - max_lines))
    for record in voided[:max_lines]:
        lines.append(tr("留给对方一拍：「{label}」换了要蓄势的那一招——"
                        "先前「{skill}」那条节拍不作数了。",
                        label=record["label"], skill=record["skill"]))
    if len(voided) > max_lines:
        lines.append(tr("留给对方一拍：另有 {n} 条作废一并记下。",
                        n=len(voided) - max_lines))
    return lines


# ---- 墙后的空腔（expansion.sound.i03，2026-10-25 洞察 A 批）----
#
# 「回声长短」在本作只对应一件事：墙后连通空处的大小。所以读数只有档位，
# 而且**绝不**顺手把墙后的地形记进知识——描述里写死了「不揭示空腔内容和可达路线」。
_CAVITY_BANDS: tuple[tuple[int, str, str], ...] = (
    (0, "很短", "墙后立刻又是实的"),
    (2, "偏短", "墙后只有一线空处"),
    (6, "偏长", "墙后是一片不大的空处"),
    (99, "很长", "墙后连着更大的空处"),
)


def _wall_face(px: int, py: int, x: int, y: int) -> tuple[int, int]:
    """玩家→墙格的主轴方向；只有一根轴有位移时才算敲出了「墙后」。"""
    dx = (x > px) - (x < px)
    dy = (y > py) - (y < py)
    if dx and dy:
        return 0, 0
    return dx, dy


def _cavity_open_cells(state, x: int, y: int, dx: int, dy: int, limit: int) -> int:
    """从墙后那一格数出去：只数**空格数**，不看里面有什么，也不写任何知识。"""
    start = (x + dx, y + dy)
    if not (0 <= start[0] < state.width and 0 <= start[1] < state.height):
        return 0
    if state.cell(*start).solid:
        return 0
    seen = {start}
    queue = [start]
    count = 0
    while queue and count < limit:
        cx, cy = queue.pop()
        count += 1
        for nx, ny in ((cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)):
            if (nx, ny) in seen or not (0 <= nx < state.width and 0 <= ny < state.height):
                continue
            if state.cell(nx, ny).solid:
                continue
            seen.add((nx, ny))
            queue.append((nx, ny))
    return count


def _cavity_band(count: int) -> tuple[str, str]:
    """空格数 → 回声档位；档位与形状分开给，模板里各插一处。"""
    for edge, band, shape in _CAVITY_BANDS:
        if count <= edge:
            return band, shape
    return _CAVITY_BANDS[-1][1], _CAVITY_BANDS[-1][2]


def _wall_cavity_echo(state, name: str, effect: dict[str, Any]) -> int:
    """墙后的空腔：敲过的墙只报回声长短档，档位不变就不再重复播报。"""
    limit = max(1, int(effect.get("probe_limit", 14) or 14))
    px, py = state.player.x, state.player.y
    memo = (state.realm_features.setdefault("growth_observations", {})
            .setdefault("wall_cavity", {}))
    layer = state.layer_key()
    notes = 0
    for entry in list(getattr(state, "delayed_sounds", ()) or ()):
        if not entry.get("wall"):
            continue
        x, y = int(entry.get("x", 0) or 0), int(entry.get("y", 0) or 0)
        if not (0 <= x < state.width and 0 <= y < state.height):
            continue
        if not state.cell(x, y).solid:
            continue
        dx, dy = _wall_face(px, py, x, y)
        if not dx and not dy:
            continue
        count = _cavity_open_cells(state, x, y, dx, dy, limit)
        band, shape = _cavity_band(count)
        key = f"{layer}:{x},{y}"
        if memo.get(key) == band:
            continue
        memo[key] = band
        state.messages.append(tr(
            "墙后的空腔：({x}, {y}) 后面的回声{band}——{shape}。"
            "里面有什么、怎么进去，这一手听不出来。",
            x=x, y=y, band=tr(band), shape=tr(shape)))
        notes += 1
    return notes


# ---- 反应留下出口（expansion.circuit.i06，2026-10-25 洞察 A 批）----

def _carried_liquids(state) -> list[str]:
    """身上容器里真有存量的液体：倒得出去的才算原料。"""
    kinds: set[str] = set()
    for item in getattr(state, "inventory", ()) or ():
        contents = getattr(item, "contents", None)
        if not isinstance(contents, dict):
            continue
        for kind, amount in contents.items():
            if kind and int(amount or 0) > 0:
                kinds.add(str(kind))
    return sorted(kinds)


def _gas_exit_hint(state, name: str, effect: dict[str, Any]) -> int:
    """反应留下出口：倒料前指出**已知**会产气的最近开放格，不替未知路径担保。"""
    from ..materials.reactions import LIQUID_GAS_RECIPES

    carried = _carried_liquids(state)
    if not carried:
        return 0
    px, py = state.player.x, state.player.y
    found: list[tuple[int, int, int, str, str]] = []
    for x, y in state.visible_cells():
        cell = state.cell(x, y)
        if cell.solid or int(cell.gas or 0) <= 0 or not cell.gas_kind:
            continue
        for kind in carried:
            recipe = LIQUID_GAS_RECIPES.get(frozenset((kind, cell.gas_kind)))
            if recipe is None or recipe.product_type != "气体":
                continue
            found.append((abs(x - px) + abs(y - py), x, y, kind, recipe.product))
    if not found:
        return 0
    found.sort()
    limit = max(1, int(effect.get("max_lines", 1) or 1))
    memo = (state.realm_features.setdefault("growth_observations", {})
            .setdefault("gas_exit", {}))
    layer = state.layer_key()
    notes = 0
    for _, x, y, kind, product in found:
        if notes >= limit:
            break
        key = f"{layer}:{x},{y}:{kind}"
        if memo.get(key) == product:
            continue
        memo[key] = product
        state.messages.append(tr(
            "反应留下出口：把{item}倒进 ({x}, {y}) 会生成{product}——"
            "这是已知会产气的最近一格；没见过的通路不能当安全。",
            item=tr(kind), x=x, y=y, product=tr(product)))
        notes += 1
    return notes


# ---- 药效不等于痊愈（expansion.realm.i03，2026-10-25 洞察 A 批）----

# 只认医院这一处安全设施：描述写的就是「在安全设施等待」，图书馆不算。
_SAFE_FACILITY_REALMS: tuple[str, ...] = ("white_sanatorium",)


def _drug_debt_prepay(state, name: str, effect: dict[str, Any]) -> int:
    """医院里等着的时候，把一格真实药物债务提前结掉：总债不变、不提前恢复。"""
    from . import drug_debts

    if str(getattr(state, "realm_id", "") or "") not in _SAFE_FACILITY_REALMS:
        return 0
    result = drug_debts.prepay_one(state)
    if not result:
        return 0
    resource, source, remaining = result
    state.messages.append(tr(
        "药效不等于痊愈：你把「{item}」的一格账提前结了——{resource} −1，还剩 {n} 格；"
        "总债没有变少，也没有提前恢复什么。",
        item=tr(source),
        resource=tr("心智" if resource == "mind" else "清醒度"),
        n=remaining))
    return 1


# ---- 数清空响（expansion.projectile.i01，2026-10-25 洞察 B 批）----
#
# 真正的减免在 ``actions/combat.py::reload_weapon_step``（第一步多走一格进度）；
# 这里只做「这一枪把仓打空了，我数清了」这一次提醒，顺带把同实例的旧账收掉。

def _weapon_label(state, instance_id: str) -> str:
    from .firing_sources import LEGACY_BASIC_ID, LEGACY_BASIC_NAME

    if instance_id == LEGACY_BASIC_ID:
        return LEGACY_BASIC_NAME
    for item in getattr(state, "inventory", ()) or ():
        if str(getattr(item, "instance_id", "")) == instance_id:
            return str(getattr(item, "name", instance_id))
    return instance_id


def _empty_magazine_note(state, name: str, effect: dict[str, Any]) -> int:
    """数清空响：自己打空的那一仓记一笔，下一回换弹的第一步会快一点。"""
    features = getattr(state, "realm_features", None)
    if not isinstance(features, dict):
        return 0
    marks = features.get("emptied_by_fire")
    if not isinstance(marks, dict) or not marks:
        return 0
    memo = features.setdefault("growth_observations", {}).setdefault("empty_magazine", {})
    notes = 0
    for instance_id, moment in list(marks.items()):
        key = f"{instance_id}:{int(moment)}"
        if memo.get(key):
            continue
        memo[key] = True
        state.messages.append(tr(
            "数清空响：{name} 这一仓是你自己打空的——下一次换弹的第一步会快一点，"
            "该付的费用一分不少。",
            name=tr(_weapon_label(state, str(instance_id)))))
        notes += 1
    return notes


# ---- 光圈的边缘（expansion.light.i04，2026-10-25 洞察 B 批）----
#
# 减免挂在 ``vision/sight.can_see`` 里「异象看你」那条分支：视距 −1，不改它看别的
# 东西的视距。开窗只有两回合（等待 + 下一步），且踏进任何真实光源就作废。

def _cell_emits_light(state, x: int, y: int) -> bool:
    from .vision import glow

    return int(glow.source_radius(state.cell(x, y)) or 0) > 0


def _dim_edge_armed(state) -> bool:
    features = getattr(state, "realm_features", None)
    if not isinstance(features, dict):
        return False
    memo = features.get("dim_edge")
    if not isinstance(memo, dict):
        return False
    return int(getattr(state, "time", 0) or 0) <= int(memo.get("until", -1))


def dim_edge_shadow(state) -> int:
    """异象看你时这一手留的余量：暗处 −1；站在真实光源里就是 0（作废）。"""
    if not _dim_edge_armed(state):
        return 0
    from .vision import glow

    px, py = state.player.x, state.player.y
    if _cell_emits_light(state, px, py):
        return 0
    if int(glow.sight_bonus(state, px, py) or 0) > 0:
        return 0
    return -1


def dim_edge_spend(state) -> None:
    """正是这一格遮住了这次露光——用掉即失效（所谓「减少**一次**视觉暴露」）。"""
    features = getattr(state, "realm_features", None)
    if isinstance(features, dict):
        features.pop("dim_edge", None)


def _dim_edge_wait(state, name: str, effect: dict[str, Any]) -> int:
    """光圈的边缘：停在已见的明暗交界上一手，下一步跨进暗侧时少露一格光。"""
    px, py = state.player.x, state.player.y
    if _cell_emits_light(state, px, py):
        return 0        # 自己就站在光源格上，没有「边缘」可停
    lit = False
    from .vision import glow

    for nx, ny in ((px + 1, py), (px - 1, py), (px, py + 1), (px, py - 1)):
        if not (0 <= nx < state.width and 0 <= ny < state.height):
            continue
        if not _cell_emits_light(state, nx, ny):
            continue
        # 灯多半长在墙上（黄铜阅读灯／日光壁都是实心墙种）：这里**不能**再按
        # 通行性筛一遍，否则「看得见的明暗交界」永远判不出来。
        if not state.is_visible(nx, ny):
            continue
        lit = True
        break
    # 只在「看得见的明暗交界」上才成立：边界那一侧必须真有一盏灯，且它照得到我这一格。
    if not lit or int(glow.sight_bonus(state, px, py) or 0) <= 0:
        return 0
    features = state.realm_features
    memo = features.get("dim_edge") if isinstance(features, dict) else None
    if isinstance(memo, dict) and int(memo.get("until", -1)) > int(state.time):
        return 0        # 已经留过一手，别叠
    features["dim_edge"] = {"until": int(state.time) + 2, "from": [px, py]}
    state.messages.append(tr(
        "光圈的边缘：你在明暗交界停了一手——下一步跨进暗处，露光少一格；"
        "踏进别的真实光源就作废。"))
    return 1


# ---- 先让它沉下去（expansion.terrain.i06，2026-10-25 洞察 C 批）----
#
# 减免落在 ``portents._grant_material_portents``（附着层削成 0，征兆照给），
# 登记落在 ``actions/social.container_fill``。这里只负责"看得见"那一半。

def _settled_grab_read(state, name: str, effect: dict[str, Any]) -> int:
    """先让它沉下去：站在刚相变完、又还有液体的格子上时，提醒这一手可以取。"""
    from . import phase_changes

    px, py = state.player.x, state.player.y
    cell = state.cell(px, py)
    if int(getattr(cell, "liquid", 0) or 0) <= 0:
        return 0
    if not phase_changes.settled(state, cell):
        return 0
    memo = (state.realm_features.setdefault("growth_observations", {})
            .setdefault("settled", {}))
    key = (f"{state.layer_key()}:{px},{py}:"
           f"{int(cell.material_clocks.get(phase_changes.CLOCK, 0) or 0)}")
    if memo.get(key):
        return 0
    memo[key] = True
    state.messages.append(tr(
        "先让它沉下去：({x}, {y}) 刚相变完，这时候取液沾不上表面附着——"
        "身上的东西该发作还是发作。", x=px, y=py))
    return 1


# ---- 落笔之前（expansion.realm.i02，2026-10-25 洞察 D 批）----
#
# 目录这句是一条**行动**承诺（「可花行动转向九十度一次」），不是读数，所以这一条
# 真的改世界状态，而且只改 ``direction`` 一个键。场上只有四处会读场记录的
# ``direction``：裁光的扇区（``construct_environments.py:583-587``）、三面镜的法线
# （同文件 :754-766），以及回响的行进轨迹（:690-692）。轨迹那一处排除——转它等于
# 改落点，而目录明文要求「落点、范围和触发时刻不变」。其余 kind 的 ``direction``
# 从来没人读（光幕只读 cells、逆风幕按玩家方位搬气、上坡液／钉液传的是 (0,0)），
# 报一次世界根本不认的转向就是撒谎，所以也不碰。

ORIENTED_FIELD_KINDS = frozenset({
    "expansion.narrow_light", "mirror_stance",
    "expansion.deflector", "expansion.double_mirror",
})


def _unit_axis(direction) -> tuple[int, int] | None:
    """四轴向的单位朝向才谈得上「转九十度」；斜向与零向量一律不碰。"""
    dx, dy = int(direction[0]), int(direction[1])
    if abs(dx) + abs(dy) != 1 or (dx and dy):
        return None
    return dx, dy


def _pending_field_rotation(state, name: str, effect: dict[str, Any]) -> int:
    """落笔之前：把自己布下、还在倒计时里、朝向是平面／扇区的构想顺时针转九十度。"""
    from .construct_environments import active
    from .enemies import sound_sector

    for field in active(state):        # active 已经筛过「同层 + remaining > 0」
        if field.get("kind") not in ORIENTED_FIELD_KINDS:
            continue
        if field.get("persistent") or int(field.get("pause_ticks", 0) or 0) > 0:
            continue                    # 长驻的、被按住的没有「还没落笔」这一说
        if field.get("rotated_once"):
            continue                    # 一发只转一次；记号与 paused_once 同一套路
        direction = _unit_axis(field.get("direction") or (0, 0))
        if direction is None:
            continue
        # 与 _sound_fold 的 side = (-normal[1], normal[0]) 同一算法：北→东→南→西。
        side = (-direction[1], direction[0])
        field["direction"] = list(side)
        field["rotated_once"] = True
        state._narrow_light_cache = None    # 裁光表按（回合, 场数）缓存，转完必须清
        state.invalidate_sight_radius()
        state.messages.append(tr(
            "落笔之前：你把 ({x}, {y}) 那发朝向{old}的构想转到{new}——"
            "落点、范围与剩下的 {n} 回合一个数都不动。",
            x=int(field["position"][0]), y=int(field["position"][1]),
            old=tr(sound_sector(*direction)), new=tr(sound_sector(*side)),
            n=int(field["remaining"])))
        return 1                        # 一次等待只换一发的朝向，不是一轮广播
    return 0


# ---- 先看落差（expansion.terrain.i01，2026-10-25 洞察 E 批）----
#
# 效果落在既有核心动作 ``actions/social.container_pour``：看得见相邻更低的一格时，
# 一次倾倒只走一半，剩下的留在容器里等下一次确认。这里只提供三个纯读取，不新增数值。

POUR_STAGE_FLOOR = 1


def _known_tier(cell) -> int | None:
    """这一格玩家有权知道的地势档位（与 ``ui/elevation.known_elevation`` 同口径）。

    ``dream_demo.core`` 不 import ``ui``，所以这里只重写那几行判据，不复制色阶。
    🔴 参数必须是**已经筛过可视性**的格子：真实 ``Cell`` 上没有 ``status`` 字段
    （那是 ``CellKnowledge`` 的），拿未看过的格子来问就会偷读到真实地势。
    """
    if cell is None or getattr(cell, "status", "") == "unknown":
        return None
    tier = getattr(cell, "elevation", None)
    return None if tier is None else int(tier)


def _lower_neighbours(state) -> list[tuple[int, int, int]]:
    """看得见的四邻里，地势比脚下更低的那几格（坐标 + 对方档位）。"""
    px, py = int(state.player.x), int(state.player.y)
    here = _known_tier(state.cell(px, py))
    if here is None:
        return []
    lower: list[tuple[int, int, int]] = []
    for nx, ny in ((px + 1, py), (px - 1, py), (px, py + 1), (px, py - 1)):
        if not (0 <= nx < state.width and 0 <= ny < state.height):
            continue
        if not state.is_visible(nx, ny):
            continue
        there = _known_tier(state.cell(nx, ny))
        if there is not None and there < here:
            lower.append((nx, ny, there))
    return lower


def pour_drop_seen(state) -> bool:
    """脚下与**已见**四邻之间有没有真落差（相邻更低一档）。"""
    return bool(_lower_neighbours(state))


def pour_stage(contents: dict[str, int]) -> dict[str, int]:
    """这一手先倒多少：每类只走一半（至少 1 点），剩下的留在容器里。"""
    stage: dict[str, int] = {}
    for kind, amount in contents.items():
        amount = int(amount)
        if amount <= 0:
            continue
        stage[str(kind)] = max(POUR_STAGE_FLOOR, amount // 2)
    return stage


def _pour_drop_read(state, name: str, effect: dict[str, Any]) -> int:
    """先看落差：站在看得见的高低边上时，报液体先往哪几格走。"""
    lower = _lower_neighbours(state)
    if not lower:
        return 0
    px, py = int(state.player.x), int(state.player.y)
    memo = (state.realm_features.setdefault("growth_observations", {})
            .setdefault("pour_drop", {}))
    key = f"{state.layer_key()}:{px},{py}:{tuple(sorted(lower))}"
    if memo.get(key):
        return 0
    memo[key] = True
    where = "、".join(f"({x}, {y})" for x, y, _tier in lower[:3])
    state.messages.append(tr(
        "先看落差：脚下的地势比 {where} 高——从这里倒液会先往那边走，"
        "这一份可以分两段确认。", where=where))
    return 1


# ---- 不把亮灯当通电（expansion.circuit.i03，2026-10-25 洞察 E 批）----
#
# 效果落在 ``actions/combat.py`` 的接线构想（``rewire``）：近身断线验电后，
# ``materials_sim.shed_piezo_charge`` 泄掉一层压电层数。这里只负责「看得见」。

def _live_wire_read(state, name: str, effect: dict[str, Any]) -> int:
    """不把亮灯当通电：视野里有线路、身上又有积电时，报还剩几层。

    先看身上的积电再看线：`layers <= 0` 是绝大多数回合的情况，那时根本不需要
    扫视野（11×11 逐格 `is_visible` 约 4ms，逐回合白付）。
    """
    stacks = getattr(state, "_piezo_stacks", None)
    layers = int((stacks or {}).get(id(state.player), 0) or 0)
    if layers <= 0:
        return 0
    px, py = int(state.player.x), int(state.player.y)
    node_seen = False
    for ny in range(max(0, py - 5), min(state.height, py + 6)):
        for nx in range(max(0, px - 5), min(state.width, px + 6)):
            if not state.is_visible(nx, ny):
                continue
            if state.circuit_node_at(nx, ny):
                node_seen = True
                break
        if node_seen:
            break
    if not node_seen:
        return 0
    memo = (state.realm_features.setdefault("growth_observations", {})
            .setdefault("live_wire", {}))
    key = f"{state.layer_key()}:{layers}"
    if memo.get(key):
        return 0
    memo[key] = True
    state.messages.append(tr(
        "不把亮灯当通电：附近那条线亮着，不等于通着电——你身上还有 {n} 层积电；"
        "贴着一个端口断开、验过电再接线，能泄掉一层，灯灭不算断电。", n=layers))
    return 1


# ---- 一声两种来处（expansion.sound.i06，2026-10-25 洞察 E 批）----
#
# 凭据落在 ``enemies._record_hearing_clue`` 的 ``relay`` 字段（传声筒入口坐标，
# 只在 ``_sound_pulse`` 的转发链里写）。这里只读：见过那套传声筒才说明白。

def _pipe_relay_note(state, name: str, effect: dict[str, Any]) -> int:
    """一声两种来处：转发来的那一声只注明入口，不替玩家追没见过的另一头。"""
    retention = state._clue_retention()
    notes = 0
    for clue in state.heard_sound_clues:
        if state.time - int(clue.get("time", 0)) >= retention:
            continue
        relay = clue.get("relay")
        if not relay or clue.get("relay_judged"):
            continue
        try:
            rx, ry = int(relay[0]), int(relay[1])
        except (TypeError, ValueError, IndexError):
            clue["relay_judged"] = True
            continue
        # 「已见传声装置」：这套筒子至少有一头亲眼见过，否则谈不上「认出来」。
        if not (state.is_visible(rx, ry) or state.is_visible(int(clue.get("x", -1)),
                                                          int(clue.get("y", -1)))):
            continue
        clue["relay_judged"] = True
        notes += 1
        if state.is_visible(rx, ry):
            state.messages.append(tr(
                "一声两种来处：这一声是经传声筒从 ({x}, {y}) 转过来的——"
                "原声在那一头，不在这边。", x=rx, y=ry))
        else:
            state.messages.append(tr(
                "一声两种来处：这一声是传声筒转过来的，入口 ({x}, {y}) 你没亲眼见过——"
                "另一头不替你追。", x=rx, y=ry))
    return notes


# ---- 听出填装间隙（expansion.projectile.i06，2026-10-25 洞察 F 批）----
#
# 只读既有换弹记账（``Item.reload_steps`` ＋ ``firing_sources.magazine_spec``）与
# ``actions/combat.py`` 里那两个声径常量——不预测别人、不替你算什么时候能开火。

def _reload_gap_read(state, name: str, effect: dict[str, Any]) -> int:
    """换弹只剩几步时，报下一步的声音会传多远（完成那一步更响）。"""
    from .actions import combat
    from .firing_sources import magazine_spec

    memo = (state.realm_features.setdefault("growth_observations", {})
            .setdefault("reload_gap", {}))
    notes = 0
    for item in list(getattr(state, "inventory", ()) or ()):
        steps = int(getattr(item, "reload_steps", 0) or 0)
        if steps <= 0:
            continue
        spec = magazine_spec(getattr(item, "definition_id", ""))
        total = int(getattr(spec, "reload_time", 0) or 0)
        if total <= 0 or steps >= total:
            continue
        left = total - steps
        key = f"{getattr(item, 'instance_id', '')}:{left}"
        if memo.get(key):
            continue
        memo[key] = True
        notes += 1
        state.messages.append(tr(
            "听出填装间隙：{name} 还差 {n} 步装填——这一步的声音大约传到 {step} 格，"
            "最后那一步更响（{done} 格）。",
            name=tr(item.name), n=left,
            step=combat.RELOAD_SOUND_RADIUS_STEP,
            done=combat.RELOAD_SOUND_RADIUS_DONE))
    return notes


# ---- 留下最后一条路（expansion.realm.i06，2026-10-25 洞察 F 批）----
#
# 只走**已知地形**（``cell.status != 'unknown'``）与既有通行判据；未知格一律当作
# 「不知道」，既不进连通块也不当安全——描述里「未知通路不能当已知安全」是结构性的。

def _known_walkable(state) -> set[tuple[int, int]]:
    """一次取齐「已知且通行」的格子：可见格读实时格子，其余读地形记忆。

    只能在 ``core`` 里这么做——``Cell.status`` 是**视图层**（``CellKnowledge``）的
    字段，真实 ``Cell`` 上没有；逐格调 ``cell_knowledge`` 又太贵（一次等待会走上千次）。
    未知格不在这个集合里，所以「未知通路不能当已知安全」是结构性的。
    """
    visible = state.visible_cells()
    layer = (getattr(state, "terrain_memory", None) or {}).get(state.layer_key()) or {}
    walkable: set[tuple[int, int]] = set()
    for x, y in visible:
        if not state.cell(x, y).solid:
            walkable.add((x, y))
    for (x, y), memory in layer.items():
        if (x, y) not in visible and not getattr(memory, "solid", False):
            walkable.add((x, y))
    return walkable


def _known_reachable(state, walkable: set[tuple[int, int]],
                     blocked: tuple[int, int] | None = None) -> set[tuple[int, int]]:
    """从玩家所在格出发、只走已知通行格的连通块；``blocked`` 视为已堵上。"""
    start = (int(state.player.x), int(state.player.y))
    if start not in walkable or blocked == start:
        return set()
    seen = {start}
    queue = [start]
    while queue:
        x, y = queue.pop()
        for neighbour in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if neighbour in seen or neighbour == blocked:
                continue
            if neighbour not in walkable:
                continue
            seen.add(neighbour)
            queue.append(neighbour)
    return seen


def _cut_route_note(state, name: str, effect: dict[str, Any]) -> int:
    """留下最后一条路：身边某个已见通路只剩一格宽时，提醒「堵上这里就断了」。"""
    walkable = _known_walkable(state)
    reach = _known_reachable(state, walkable)
    if len(reach) <= 2:
        return 0            # 站在一条死路尽头，没什么可堵的
    px, py = int(state.player.x), int(state.player.y)
    chokes: list[tuple[int, int]] = []
    for x, y in ((px + 1, py), (px - 1, py), (px, py + 1), (px, py - 1)):
        if (x, y) not in reach:
            continue
        without = _known_reachable(state, walkable, blocked=(x, y))
        if len(without) < len(reach) - 1:
            chokes.append((x, y))
    if not chokes:
        return 0
    memo = (state.realm_features.setdefault("growth_observations", {})
            .setdefault("cut_route", {}))
    key = f"{state.layer_key()}:{px},{py}:{tuple(sorted(chokes))}"
    if memo.get(key):
        return 0
    memo[key] = True
    where = "、".join(f"({x}, {y})" for x, y in chokes[:3])
    state.messages.append(tr(
        "留下最后一条路：{where} 一堵上，你已经知道的那片就断了——"
        "没见过的通路不能当退路。", where=where))
    return 1


# ---- 桌面不是地面（expansion.terrain.i02，2026-10-25 洞察 F 批）----
#
# 效果落在 ``actions/items.take_from``：从**陷阱**石台上取物时多站一回合，
# 这一回合经 ``logic.trigger_platform(safe_note=…)`` 只隔开陷阱那一段——
# 石台照旧发信号、机关石台照旧执行（与绝缘手套同一条口径）。这里只负责「看得见」。

def _surface_take_read(state, name: str, effect: dict[str, Any]) -> int:
    """桌面不是地面：贴着陷阱石台站着时，先说明这一拿能怎么拿。"""
    px, py = int(state.player.x), int(state.player.y)
    traps = []
    for x, y in ((px + 1, py), (px - 1, py), (px, py + 1), (px, py - 1)):
        if not state.is_visible(x, y):
            continue
        if state.cell(x, y).wall_kind == "陷阱石台":
            traps.append((x, y))
    if not traps:
        return 0
    memo = (state.realm_features.setdefault("growth_observations", {})
            .setdefault("surface_take", {}))
    key = f"{state.layer_key()}:{tuple(sorted(traps))}"
    if memo.get(key):
        return 0
    memo[key] = True
    where = "、".join(f"({x}, {y})" for x, y in traps[:3])
    state.messages.append(tr(
        "桌面不是地面：{where} 底下有机关——多站一回合慢慢取，陷阱就不响；"
        "石台照旧发信号，机关石台也照旧触发。", where=where))
    return 1


# ---- 先看掩体边（expansion.projectile.i02，2026-10-25 洞察 G 批）----
#
# 改描述：真正的「开枪源点挪到身侧」要改发射链（谁算弹道起点、谁付暴露），
# 那会牵到所有远程来源。这里只读：面朝已确认掩体时，报哪几个身侧空格真能出手。

def _side_cells(state) -> list[tuple[int, int]]:
    """站在实地上时，垂直于朝向的两格（左手／右手那两格）。"""
    dx, dy = (int(state.facing[0]), int(state.facing[1]))
    px, py = int(state.player.x), int(state.player.y)
    return [(px - dy, py + dx), (px + dy, py - dx)]


def _cover_edge_read(state, name: str, effect: dict[str, Any]) -> int:
    """先看掩体边：面朝的那一格确实是掩体时，报身侧能出手的空格。"""
    dx, dy = (int(state.facing[0]), int(state.facing[1]))
    fx, fy = int(state.player.x) + dx, int(state.player.y) + dy
    if not (0 <= fx < state.width and 0 <= fy < state.height):
        return 0
    if not state.is_visible(fx, fy):
        return 0
    cell = state.cell(fx, fy)
    if not cell.solid or int(getattr(cell, "cover", 0) or 0) <= 0:
        return 0
    legal: list[tuple[int, int]] = []
    for sx, sy in _side_cells(state):
        if not (0 <= sx < state.width and 0 <= sy < state.height):
            continue
        if not state.is_visible(sx, sy) or state.cell(sx, sy).solid:
            continue
        legal.append((sx, sy))
    memo = (state.realm_features.setdefault("growth_observations", {})
            .setdefault("cover_edge", {}))
    key = f"{state.layer_key()}:{state.player.x},{state.player.y}:{dx},{dy}:{tuple(legal)}"
    if memo.get(key):
        return 0
    memo[key] = True
    if not legal:
        state.messages.append(tr(
            "先看掩体边：这面掩体两侧都被堵着——要换个出手的位置，得先挪身。"))
    else:
        where = "、".join(f"({x}, {y})" for x, y in legal[:2])
        state.messages.append(tr(
            "先看掩体边：{where} 能从掩体旁边出手，人不用挪；"
            "越过掩体的弹道还是按老规矩算。", where=where))
    return 1


# ---- 空仓不是失手（expansion.projectile.i05，2026-10-25 洞察 G 批）----
#
# 用既有的诱引脉冲（``_sound_pulse(category='lure')``）当「假装填」：一次等待就是一
# 次有耗时的假动作，响在自己脚下——对方以为你正在装填，会照既有调查逻辑靠过来。
# 「同一异象每次交锋仅一次」用层键记账实现（换层自然清零）。

FAKE_RELOAD_REACH = 4
FAKE_RELOAD_RADIUS = 3
FAKE_RELOAD_MAX_ENEMIES = 3


def _empty_magazine(state) -> bool:
    for item in list(getattr(state, "inventory", ()) or ()):
        magazine = getattr(item, "magazine", None)
        if magazine is None:
            continue
        if int(magazine) <= 0 and int(getattr(item, "magazine_capacity", 0) or 0) > 0:
            return True
    return False


def _fake_reload_bait(state, name: str, effect: dict[str, Any]) -> int:
    """空仓不是失手：空仓被已见异象看着时，等一手做一次假装填引它来查。"""
    if not _empty_magazine(state):
        return 0
    px, py = int(state.player.x), int(state.player.y)
    memo = (state.realm_features.setdefault("growth_observations", {})
            .setdefault("fake_reload", {}))
    layer = str(state.layer_key())
    marked: list = []
    for enemy in state.enemies:
        if getattr(enemy, "integrity", 0) <= 0:
            continue
        if getattr(enemy, "relation", "") != "失控意识":
            continue
        if max(abs(int(enemy.x) - px), abs(int(enemy.y) - py)) > FAKE_RELOAD_REACH:
            continue
        if not state.is_visible(int(enemy.x), int(enemy.y)):
            continue
        key = f"{layer}:{getattr(enemy, 'id', '')}"
        if key in memo:            # 🔴 记的是回合号：第 0 回合写进去的值是 0（falsy）
            continue
        memo[key] = int(state.time)
        marked.append(enemy)
        if len(marked) >= FAKE_RELOAD_MAX_ENEMIES:
            break
    if not marked:
        return 0
    state.messages.append(tr(
        "空仓不是失手：{name} 看见你枪口空着，你就势慢条斯理地做出一次装填——"
        "机括响在自己脚下，看它敢不敢顺着这声音过来。",
        name=tr(state.observed_entity_label(marked[0]))))
    state._sound_pulse(px, py, FAKE_RELOAD_RADIUS, by_player=True, category="lure",
                       source=tr("假装填"), announce=False, triggers_rewards=False)
    return len(marked)


# ---- 不白退一发（expansion.projectile.i03，2026-10-25 洞察 G 批）----
#
# 效果落在 ``core/expansion_abilities._dump_magazine``（退壳构想）：``keep=1`` 让
# ``expansion_consumables.projectile`` 只打掉真实剩下的 n−1 发。这里只报账。

def _dump_keep_read(state, name: str, effect: dict[str, Any]) -> int:
    """不白退一发：报膛里还剩几发，退壳会打掉几发、留下几发。"""
    gun = None
    for item in list(getattr(state, "inventory", ()) or ()):
        magazine = getattr(item, "magazine", None)
        if magazine is None or int(magazine) <= 0:
            continue
        if int(getattr(item, "magazine_capacity", 0) or 0) <= 0:
            continue
        gun = item
        break
    if gun is None:
        return 0
    rounds = int(gun.magazine)
    keep = 1 if rounds >= 2 else 0
    memo = (state.realm_features.setdefault("growth_observations", {})
            .setdefault("dump_keep", {}))
    key = f"{getattr(gun, 'instance_id', '')}:{rounds}"
    if memo.get(key):
        return 0
    memo[key] = True
    if keep:
        state.messages.append(tr(
            "不白退一发：{name} 膛里还有 {n} 发——退壳会打掉 {fired} 发，"
            "最后那一发留在膛里，随时能打出去。",
            name=tr(gun.name), n=rounds, fired=rounds - 1))
    else:
        state.messages.append(tr(
            "不白退一发：{name} 膛里只剩 {n} 发——退壳就真打空了，留不下东西。",
            name=tr(gun.name), n=rounds))
    return 1


# ---- 留意产物（expansion.circuit.i02，2026-10-25 洞察 H 批）----
#
# 账在 ``materials_sim._note_seen_reaction``（只记**看得见**的液气反应，键是
# ``reactions.reaction_key``）。这里只读：脚下或身边那一格正在走哪条**见过**的反应。
# 没见过的一律不报——「不反演未知配方」是结构性的，不是靠措辞。

def _reaction_product_read(state, name: str, effect: dict[str, Any]) -> int:
    """留意产物：身边看得见的液气格在走一条亲眼见过的反应时，报出它会出什么。"""
    from ..materials.reactions import LIQUID_GAS_RECIPES, reaction_key

    features = getattr(state, "realm_features", None)
    ledger = features.get("seen_reactions") if isinstance(features, dict) else None
    if not isinstance(ledger, dict) or not ledger:
        return 0
    px, py = int(state.player.x), int(state.player.y)
    notes = 0
    for x, y in ((px, py), (px + 1, py), (px - 1, py), (px, py + 1), (px, py - 1)):
        if not (0 <= x < state.width and 0 <= y < state.height):
            continue
        if not state.is_visible(x, y):
            continue
        cell = state.cell(x, y)
        kind = str(getattr(cell, "liquid_kind", "") or "")
        gas = str(getattr(cell, "gas_kind", "") or "")
        if not kind or not gas or int(getattr(cell, "liquid", 0) or 0) <= 0:
            continue
        recipe = LIQUID_GAS_RECIPES.get(frozenset((kind, gas)))
        if recipe is None:
            continue
        key = reaction_key(recipe)
        if key not in ledger:
            continue            # 没亲眼见过这条反应：不替你反演
        memo = (features.setdefault("growth_observations", {})
                .setdefault("reaction_product", {}))
        spot = f"{state.layer_key()}:{x},{y}:{key}"
        if memo.get(spot):
            continue
        memo[spot] = True
        notes += 1
        state.messages.append(tr(
            "留意产物：({x}, {y}) 这一格在走你见过的那条反应——{kind}与{gas}出的是{product}，"
            "没见过的组合不替你反演。",
            x=x, y=y, kind=tr(kind), gas=tr(gas), product=tr(recipe.product)))
    return notes


# ---- 熔断前的气味（expansion.circuit.i04，2026-10-25 洞察 H 批）----
#
# 改描述：本作没有熔丝与过载。真有的「快撑不住」是压电地板那本蓄电账——
# 只报**脚下这一格**，墙后线路一律不测（描述里「不能检测墙后线路」是结构性的）。

def _overload_smell_read(state, name: str, effect: dict[str, Any]) -> int:
    """熔断前的气味：脚下压电地板只差一层就放电时，先闻一声。"""
    from ..materials import floor_effect_for

    cell = state.cell(int(state.player.x), int(state.player.y))
    floor = floor_effect_for(cell)
    if not getattr(floor, "piezo", False):
        return 0
    stacks = getattr(state, "_piezo_stacks", None)
    layers = int((stacks or {}).get(id(state.player), 0) or 0)
    threshold = int(getattr(floor, "piezo_threshold", 0) or 0)
    if threshold <= 0 or layers < threshold - 1:
        return 0
    memo = (state.realm_features.setdefault("growth_observations", {})
            .setdefault("overload_smell", {}))
    key = f"{state.layer_key()}:{layers}"
    if memo.get(key):
        return 0
    memo[key] = True
    remaining = max(1, threshold - layers)
    state.messages.append(tr(
        "熔断前的气味：脚下这块压电地板已经蓄了 {n} 层，再有 {left} 层就要放电——"
        "这只报你踩着的那一格，墙后的线路它闻不出来。",
        n=layers, left=remaining))
    return 1


# ---- 看完再签（expansion.realm.i01，2026-10-25 洞察 H 批）----
#
# 改描述：本作没有「封存实物」这一层（行囊就是行囊，没有冻结标记），而且真封存还要
# 与事件交付对接。改成读手上真有的东西：对话里每个选项**会从行囊里抽走什么**。
# 代价照旧在按下那一刻才结算，所以「可取消、不绕过验证」是结构性的。

def _sign_before_read(state, name: str, effect: dict[str, Any]) -> int:
    """看完再签：稳定意识对话开着时，先把每个选项要抽走的东西念一遍。"""
    from .content import ITEM_DEFINITIONS, npc_effective_options

    npc = state.pending_npc()
    if npc is None:
        return 0
    memo = (state.realm_features.setdefault("growth_observations", {})
            .setdefault("sign_before", {}))
    lines: list[str] = []
    for index, option in enumerate(npc_effective_options(state, npc)):
        cost = option.get("cost") or {}
        if not isinstance(cost, dict):
            continue
        if "items" in cost:
            item_id, count = cost["items"]
            owned = sum(entry.quantity for entry in state.inventory
                        if entry.definition_id == item_id)
            name_text = ITEM_DEFINITIONS.get(item_id, {}).get("name", item_id)
            lines.append(tr("{item} ×{n}（行囊里有 {owned}）",
                            item=tr(name_text), n=count, owned=owned))
        elif "consumables" in cost:
            need = int(cost["consumables"])
            owned = sum(entry.quantity for entry in state._consumable_pool())
            lines.append(tr("摄入物/易逝物 ×{n}（行囊里有 {owned}）",
                            n=need, owned=owned))
        elif "random_gear" in cost:
            owned = len([entry for entry in state.inventory if entry.slot])
            lines.append(tr("可支付的携带意象 ×{n}（行囊里有 {owned}）",
                            n=int(cost["random_gear"]), owned=owned))
    if not lines:
        return 0
    key = f"{getattr(npc, 'id', '')}:{'/'.join(lines)}"
    if memo.get(key):
        return 0
    memo[key] = True
    state.messages.append(tr(
        "看完再签：{name} 桌上的这一笔要抽走 {what}——按下之前都还能退，"
        "付不出就不会成交。", name=tr(npc.label), what="；".join(lines)))
    return 1


# ---- 页码没有走动（expansion.realm.i04，2026-10-25 洞察 H 批）----
#
# 改描述：本作没有「位置置换」，也就没有「置换之后复核」这一步。改成读真有的那一页：
# 脚下这一格的地形记忆是几回合前记下的。记忆只在亲眼看过的时刻刷新，「这一页」不动
# 就说明这一段走廊你还没重新看过，别拿旧页当同一段走廊。

def _page_age_read(state, name: str, effect: dict[str, Any]) -> int:
    """页码没有走动：书库里报脚下这一页地形记录有多旧。"""
    from .vision import knowledge

    if getattr(state, "realm_id", "") != "library_palace":
        return 0
    memory = knowledge.remembered_terrain(state, int(state.player.x),
                                          int(state.player.y))
    if memory is None:
        return 0
    age = int(state.time) - int(getattr(memory, "seen_turn", 0) or 0)
    memo = (state.realm_features.setdefault("growth_observations", {})
            .setdefault("page_age", {}))
    bucket = 0 if age <= 0 else (1 if age <= 4 else 2)
    px, py = int(state.player.x), int(state.player.y)
    key = f"{state.layer_key()}:{px},{py}:{bucket}"
    if memo.get(key):
        return 0
    memo[key] = True
    if bucket == 0:
        state.messages.append(tr(
            "页码没有走动：({x}, {y}) 这一页就是这一刻记下的——"
            "它和你眼前看到的是同一段走廊。", x=px, y=py))
    else:
        state.messages.append(tr(
            "页码没有走动：({x}, {y}) 这一页还是 {age} 回合前记下的，"
            "中间没再翻过——旧页当不了同一段走廊的凭据。", x=px, y=py, age=age))
    return 1


RESOLVERS: dict[str, Callable] = {
    "tail_sound_classify": _tail_sound_classify,
    "external_light_snapshot": _external_light_snapshot,
    "gap_in_chorus": _gap_in_chorus,
    "remembered_reflection": _remembered_reflection,
    "light_source_read": _light_source_read,
    "cut_impact_read": _cut_impact_read,
    "lit_risk_note": _lit_risk_read,
    "same_tick_pairing": _same_tick_pairing,
    "siphon_backflow_note": _siphon_backflow_note,
    "frontier_exit_bearing": _frontier_exit_bearing,
    "charge_rhythm_note": _charge_rhythm_read,
    # 洞察 A 批（2026-10-25）：三条只读既有记账的规则。
    "wall_cavity_echo": _wall_cavity_echo,
    "gas_exit_hint": _gas_exit_hint,
    "drug_debt_prepay": _drug_debt_prepay,
    # 洞察 B 批（2026-10-25）：两条挂到既有结算点上的规则。
    "empty_magazine_note": _empty_magazine_note,
    "dim_edge_wait": _dim_edge_wait,
    # 洞察 C 批（2026-10-25）：相变后的第一次取液。
    "settled_grab_read": _settled_grab_read,
    # 洞察 D 批（2026-10-25）：落笔之前——转还没结算的取向构想。
    "pending_field_rotation": _pending_field_rotation,
    # 洞察 E 批（2026-10-25）：分两段倒液、验电泄积电、传声筒转发。
    "pour_drop_read": _pour_drop_read,
    "live_wire_check": _live_wire_read,
    "pipe_relay_note": _pipe_relay_note,
    # 洞察 F 批（2026-10-25）：慢取免踩、填装间隙、最后一条路。
    "surface_take_note": _surface_take_read,
    "reload_gap_read": _reload_gap_read,
    "cut_route_note": _cut_route_note,
    # 洞察 G 批（2026-10-25）：掩体边的出手位、退壳留一发、假装填诱调查。
    "cover_edge_read": _cover_edge_read,
    "dump_keep_read": _dump_keep_read,
    "fake_reload_bait": _fake_reload_bait,
    # 洞察 H 批（2026-10-25）：留意产物、熔断前的气味、看完再签、页码没有走动。
    "reaction_product_read": _reaction_product_read,
    "overload_smell_read": _overload_smell_read,
    "sign_before_read": _sign_before_read,
    "page_age_read": _page_age_read,
}


def on_wait(state) -> None:
    """等待即观察：对每条已习得的扩展包洞察跑它的读取规则。"""
    for insight_name in list(state.insights):
        row = EXPANSION_INSIGHTS.get(insight_name)
        if not row:
            continue
        handler = RESOLVERS.get(row["expansion_effect_kind"])
        if handler is not None:
            handler(state, insight_name, row["expansion_effect"] or {})



def observe(state):
    """Compare only observations made in sight, keeping historical records inert."""
    liquid_on = state.insight_active('积水的年龄')
    shadow_on = state.insight_active('阴影会移动')
    investigation_on = state.insight_active('不追最后一声')
    gas_on = state.insight_active('蒸气的出口')
    order_on = state.insight_active('留意熄灯顺序')
    if not (liquid_on or shadow_on or investigation_on or gas_on or order_on):
        return
    memo = state.realm_features.setdefault('growth_observations', {})
    if gas_on:
        _observe_gas_front(state, memo)
    if order_on:
        _observe_lamp_order(state, memo)
    if liquid_on or shadow_on:
        liquid = memo.setdefault('liquid', {})
        shadows = memo.setdefault('obstructions', {})
        # 只走可见集合：逐格 `state.is_visible` 是 35µs 级的调用，整图扫一遍要 20ms
        # 以上，而这条读数每个回合都跑（五条手写洞察还会各调一次 observe）。
        # 排序保持原来的行优先顺序，播报次序不变。
        for x, y in sorted(state.visible_cells(), key=lambda point: (point[1], point[0])):
            cell = state.cell(x, y)
            key = f'{x},{y}'
            if liquid_on:
                current = dict(kind=cell.liquid_kind, amount=cell.liquid, time=state.time)
                old = liquid.get(key)
                if old and old['kind'] == current['kind'] and old['amount'] != current['amount']:
                    state.messages.append(tr('积水的年龄：({x}, {y}) 的液体正在{change}。',
                       x=x, y=y, change=tr('积聚') if current['amount'] > old['amount'] else tr('消退')))
                liquid[key] = current
            if shadow_on:
                current = [bool(cell.solid), int(cell.height), int(cell.cover)]
                if key in shadows and shadows[key] != current:
                    state.messages.append(tr('阴影会移动：({x}, {y}) 的遮挡轮廓与上次亲见不同。',x=x,y=y))
                shadows[key] = current
    if investigation_on:
        records = memo.setdefault('investigations', {})
        for enemy in state.enemies:
            if enemy.integrity <= 0 or not state.is_visible(enemy.x, enemy.y):
                continue
            if enemy.last_heard_x < 0 or enemy.last_heard_y < 0:
                continue
            # The target is a last-confirmed sound location, never a live hidden entity.
            current = [enemy.last_heard_x, enemy.last_heard_y, enemy.last_heard_time]
            if records.get(enemy.id) != current:
                records[enemy.id] = current
                state.messages.append(tr('不追最后一声：{name}上次确认的调查目标是 ({x}, {y})。',
                    name=state.observed_entity_label(enemy),x=current[0],y=current[1]))



def _observe_rule(state, name, effect):
    """五条手写观测洞察共用的入口（`liquid_age`/`moving_shadows`/…）。

    它们共用同一趟 `observe()`，而 `on_wait` 是**逐条洞察**派发的：五条都学会时
    同一回合会被调五次，等于把整图扫五遍。这里按「回合」去重——观测本来就只在
    每回合取一次快照，多调一次不会多读到任何东西。
    """
    if getattr(state, "_expansion_observe_turn", None) == state.time:
        return 0
    state._expansion_observe_turn = state.time
    observe(state)
    return 0


RESOLVERS.update({'liquid_age':_observe_rule,'moving_shadows':_observe_rule,
                  'investigation_memory':_observe_rule,'gas_front_advance':_observe_rule,
                  'lamp_order_note':_observe_rule})
