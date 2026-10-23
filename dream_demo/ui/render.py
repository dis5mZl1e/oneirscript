"""地图渲染：多图层前景/背景、显影地形、伪装与残影直觉。"""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from rich.text import Text
from rich.cells import set_cell_size

from ..core import Entity, GameState, Material
from ..core.realm_surface import cached_surface_color, display_zones, normalize_bg_zones, surface_color
from ..materials import CONTAINER_KINDS, DEFAULT_WALL, gas_def, liquid_def, plant_def_for, wall_def
from ..symbols import (NARROW_BY_GLYPH as _NARROW_BY_GLYPH, drop_glyph, entity_glyph,
                       event_site_glyph, map_symbol, symbol)
from ..symbols import CONTINUOUS_WALL_KEYS
from . import glyphs
from .glyphs import (
    compact_tile_glyph,
    darken,
    gas_depth_key,
    liquid_depth_key,
    normalize_tile_glyph,
    viewport_origin,
    with_background,
    layered_background,
)
from ..materials import floor_def
from ..core.vision.knowledge import always_visible_category
from .styles import (AGGREGATE_STYLES, CATEGORY_STYLES, RELATION_STYLES,
                     item_display_color, realm_relation_style)


def _realm_zone_color(zones, x: int, y: int) -> str | None:
    """梦中梦的格级地表底色带。

    命中矩形的**最后一条**生效（生成器后画的覆盖先画的）；不命中返回 None
    （维持默认背景）。zone 数 ≤6，逐格线性查表只在脏帧发生。
    """
    color = None
    for zone in zones:
        x0, y0, x1, y1 = zone["rect"]
        if x0 <= x <= x1 and y0 <= y <= y1:
            color = zone["color"]
    return color


@lru_cache(maxsize=64)
def _dim_zone_color(color: str) -> str:
    """视野外未显影格的压暗地表底色：原色 × 0.55。

    全图生效：未显影视野外铺压暗版，墙体字形仍叠在底色上；视野内地形保持
    原色，视野边界再由灰度字形与底色亮度差标出。色值有限，缓存兜住热路径。
    """
    return darken(color, 0.55)


# ---- 三层信息渲染常量（2026-10-18 docs 第 1 节第二批）----
# 记忆层压暗、全图地形增强层稍亮；黑色未知区不读取任何真实地形。
# 视野外记忆色：docs §7.6 第三批复核「暗色造成第二次损失」。grey27 在常见
# 终端背景上对比度过低，提到 grey35；全图地形层再用 grey42 保持「记忆 < 已知」
# 的层级差异，仍明显暗于当前视野。
_MEMORY_STYLE = "grey35"
_TERRAIN_KNOWN_STYLE = "grey42"


def _terrain_layer(cell, tile_symbol, mode):
    """当前地形（墙/地板）的符号与稳定键；不含液体/气体/植物/对象。"""
    if cell.solid:
        # 全图地形增强只给「有实体挡路」，不点名隐藏容器的种类：
        # 容器仍显示为普通聚合墙，避免增强从侧面拆掉容器保密机制。
        wall_name = DEFAULT_WALL if cell.wall_kind in CONTAINER_KINDS else cell.wall_kind
        definition = wall_def(wall_name)
        key = definition.symbol_key
        return tile_symbol(key, mode), key, True
    if cell.floor is Material.PLAIN_AGGREGATE:
        definition = floor_def(cell.aggregate_variant)
        return tile_symbol(definition.symbol_key, mode), definition.symbol_key, False
    return symbol("floor", mode), "floor", False


def _memory_layer(memory, tile_symbol, mode):
    """地形记忆快照的符号与稳定键；未知墙体回落普通地面。"""
    if memory.solid:
        definition = wall_def(memory.wall_kind)
        key = definition.symbol_key
        return tile_symbol(key, mode), key, True
    variant = memory.aggregate_variant
    if variant:
        definition = floor_def(variant)
        return tile_symbol(definition.symbol_key, mode), definition.symbol_key, False
    return symbol("floor", mode), "floor", False


def _fog_background(realm_zones, x: int, y: int) -> str | None:
    """黑幕/记忆格的地表底色：只取位面格级底色带，不读取液体/气体实时颜色。"""
    zone = _realm_zone_color(realm_zones, x, y)
    return _dim_zone_color(zone) if zone else None


def _fog_cell_layer(state, cell, fog_state: str, tile_symbol, mode, memory,
                    realm_zones, x: int, y: int):
    """三层信息下的非当前视野图层；已发现地点标记优先于地形快照显示。"""
    glyph, style, wall_face, background = _fog_cell_layer_base(
        state, cell, fog_state, tile_symbol, mode, memory, realm_zones, x, y)
    if memory is not None and memory.site:
        # 地点标记与「内容是否可见」分开：知道这里有什么地点，但不显示当前内容。
        return tile_symbol("site", mode), "bold #e5c780", None, background
    return glyph, style, wall_face, background


def _fog_cell_layer_base(state, cell, fog_state: str, tile_symbol, mode, memory,
                         realm_zones, x: int, y: int):
    """三层信息下的非当前视野图层，返回 (glyph, style, wall_face, background)。

    - unknown：黑色空白，不读取真实地形/物品；
    - memory：只按正常视野确认过的快照画暗色地形；
    - terrain_known：只按当前真实地形画压暗地形（全图地形增强的显示权限）；
    - always_visible：只画授权类别本身（意识边界/显影液），不公开同格其它内容。
    """
    if fog_state == "unknown":
        return "  ", "black", None, None
    if fog_state == "always_visible":
        category = always_visible_category(cell)
        if category == "显影液" and cell.liquid > 0:
            key = liquid_depth_key(cell.liquid)
            return symbol(key, mode), "grey35", None, None
        if category == "意识边界" and cell.solid:
            definition = wall_def(cell.wall_kind)
            glyph = tile_symbol(definition.symbol_key, mode)
            wall_face = glyph if definition.symbol_key in CONTINUOUS_WALL_KEYS else None
            return glyph, "grey35", wall_face, None
        return "  ", "black", None, None
    background = _fog_background(realm_zones, x, y)
    if fog_state == "memory":
        if memory is None:
            return "  ", "black", None, None
        glyph, key, is_wall = _memory_layer(memory, tile_symbol, mode)
        wall_face = glyph if is_wall and key in CONTINUOUS_WALL_KEYS else None
        return glyph, _MEMORY_STYLE, wall_face, background
    # terrain_known：地形类型可知，但样式仍与当前视野区分。
    glyph, key, is_wall = _terrain_layer(cell, tile_symbol, mode)
    wall_face = glyph if is_wall and key in CONTINUOUS_WALL_KEYS else None
    return glyph, _TERRAIN_KNOWN_STYLE, wall_face, background


def _frame_normalized_glyph(
    glyph: str,
    mode: str,
    cell_w: int,
    continuous: bool,
    normalize_memo: dict[tuple[str, bool], str],
    compact_memo: dict[str, str],
) -> str:
    """C4（2026-10-22）：帧内字形归一化记忆。

    render_map 一次调用里 effective_mode/cell_w/cell_h 固定，同一原始字形
    的归一化（或紧凑档压缩）结果必然逐字节相同；一帧 1000+ 格里真正不同
    的字形只有十几种，记忆后每个键只走一次 set_cell_size。记忆表由
    render_map 本次调用独占，**跨调用不缓存**，所以模式或缩放档切换时
    不存在需要失效的旧值。compact/normalize 是两个分支，分表存放。
    """
    if cell_w == 1:
        try:
            return compact_memo[glyph]
        except KeyError:
            value = compact_tile_glyph(glyph, mode)
            compact_memo[glyph] = value
            return value
    key = (glyph, continuous)
    try:
        return normalize_memo[key]
    except KeyError:
        value = normalize_tile_glyph(glyph, mode, continuous=continuous)
        normalize_memo[key] = value
        return value


def render_map(
    state: GameState,
    unicode_mode: bool | None = None,
    viewport_width: int | None = None,
    viewport_height: int | None = None,
    origin: tuple[int, int] | None = None,
    symbol_mode: str = "themed",
    cell_w: int = 2,
    cell_h: int = 1,
    observer: tuple[int, int] | None = None,
    assist_cells: set[tuple[int, int]] | None = None,
    tutorial_cells: dict[tuple[int, int], str] | None = None,
    explosion_cells: set[tuple[int, int]] | None = None,
    explosion_age: int = 0,
    explosion_blasts: list | None = None,
    markers: dict[tuple[int, int], str] | None = None,
) -> Text:
    """把地图渲染为终端文本。

    cell_w/cell_h 是每格占用的终端列/行数（缩放的物理实现）：
    - 2/1：常规，每格一个 2 列符号；
    - >2/>1：放大——格子变大，符号在格子内水平居中，空隙沿用符号
      背景色（格与符号同步“放大”，符号不重复）；
    - 1/1：紧凑概览——每格压缩为 1 列宽的主题 Unicode 符号，
      不切换到 ASCII，物理宽度可容纳更多地图格。

    ``observer`` 是观察模式的光标格：那里画一枚白色 ``?``（盖过玩家自己），
    但它只是目光的落点——该格的地形/物品仍按原来的可见性呈现，不会因此
    变亮，视野也不会重算。
    """
    unicode_supported = glyphs._unicode_mode(unicode_mode)
    effective_mode = symbol_mode if unicode_supported else "ascii"
    # 2026-10-18（docs/261018方案合集.md §7）：两列常规/放大档使用地图专用大轮廓；
    # 单列紧凑档继续用原生小字形，否则大字面压进一列会侵入相邻格（§7.6.4）。
    tile_symbol = map_symbol if cell_w > 1 else symbol
    # 梦中梦格级地表底色带：旧档/主梦空表零开销。
    realm_zones = (
        tuple(display_zones(state))
        if getattr(state, "realm_bg_zones", None) or state.realm_id in ('library_palace','white_sanatorium')
        else ()
    )
    surface_cache: dict[tuple[int, int], str | None] = {}
    viewport_width = max(1, min(viewport_width or state.width, state.width))
    viewport_height = max(1, min(viewport_height or state.height, state.height))
    left, top = origin if origin is not None else viewport_origin(state, viewport_width, viewport_height)
    # 外部传入的 origin 也可能越界（换层时新层比旧层窄/矮，调用方拿的还是旧
    # 视口），这里统一钳回地图内——否则后面 state.cell(x, y) 直接 IndexError。
    left = max(0, min(left, max(0, state.width - viewport_width)))
    top = max(0, min(top, max(0, state.height - viewport_height)))
    visible = state.visible_cells()
    electric_cells = state.electric_field_cells()
    mind_shadow = state.mind_tier >= 2
    # 电工直觉（扩展包 v1）：持有时电线格渲染为沟槽底色+连线符号。
    wire_insight = state.insight_active("电工直觉")
    board_visible = wire_insight or state.realm_id == "toy_memories"
    board_nodes = {tuple(n["pos"]): n for b in state.circuit_boards for n in b["nodes"].values()}
    board_values = {tuple(n["pos"]): b["state"].get("values", {}).get(k, False)
                    for b in state.circuit_boards for k,n in b["nodes"].items()}
    board_traces = {}
    if board_visible:
        for board_index, board in enumerate(state.circuit_boards):
            for net in board["nets"]:
                for p in net["path"]:
                    board_traces.setdefault(tuple(p), set()).add((board_index, net["from"]))
    wire_cells = set()
    if wire_insight:
        for _wy in range(state.height):
            for _wx in range(state.width):
                if state.cells[_wy][_wx].wire:
                    wire_cells.add((_wx, _wy))
    # 显影液淌过的地形：永久显影，但只显地形，不显实体 / 物品 / 事件。
    developed = state.developed_for_depth()
    # 三层信息显示（2026-10-18 docs 第 1 节第二批）：默认关闭，整套配套验收后
    # 才决定切换默认；打开后未知格不再读取真实地形，记忆层读快照，增强项只给地形。
    fog_enabled = bool(getattr(state, "map_memory_enabled", False))
    memory_layer = (state.terrain_memory.get(state.layer_key()) or {}) if fog_enabled else {}
    terrain_known = fog_enabled and bool(getattr(state, "terrain_known", False))
    player_pos = (state.player.x, state.player.y)
    # 预建位置索引，避免渲染每格时对敌人/物品/事件做线性扫描。
    entities_at: dict[tuple[int, int], Entity] = {
        (enemy.x, enemy.y): enemy for enemy in state.enemies if enemy.integrity > 0
    }
    items_at: dict[tuple[int, int], Any] = {
        (entry.x, entry.y): entry for entry in state.world_items
    }
    events_at: dict[tuple[int, int], Any] = {
        (entry.x, entry.y): entry for entry in state.events if not entry.resolved
    }
    from ..core.tactical_layouts import MULTI_SOLUTION_GATE,gate_control
    gate_controls={gate_control(record):record for record in state.world_ledger.facilities.values()
                   if record.layer_key==state.layer_key() and record.definition_id==MULTI_SOLUTION_GATE}
    # 残影直觉：视野半径内的残影/伪装体显形为虚线轮廓（隔墙可见、不被伪装骗到）。
    phantom_echo: set[tuple[int, int]] = set()
    if state.insight_active("残影直觉"):
        radius = state.effective_sight_radius()
        phantom_echo = {
            (enemy.x, enemy.y)
            for enemy in state.enemies
            if enemy.integrity > 0 and enemy.trait in ("phantom", "disguise")
            and max(abs(enemy.x - state.player.x), abs(enemy.y - state.player.y)) <= radius
        }
    # 诅咒灵视：所有失控意识的位置与类型都显形（真实字形 + 阵营色），
    # 代价是它们也看得见你。只取位置集合，是否「照亮格子」另算。
    cursed_seen: set[tuple[int, int]] = set()
    if state.reveals_anomalies:
        cursed_seen = {
            (enemy.x, enemy.y) for enemy in state.enemies if enemy.integrity > 0
        }
    # 核心执念恒显（2026-09-22）：剧情实体的存在性感知——所在格视为在视野中，
    # 地形与实体都按正常视野渲染（不暗化、不标轮廓）。
    core_seen: set[tuple[int, int]] = {
        (enemy.x, enemy.y)
        for enemy in state.enemies
        if enemy.integrity > 0 and enemy.always_visible
    }
    # 异象技能预警（2026-09-22）：范围技能蓄力区 / 炸弹落点杀伤区，
    # 垫警示底色——「有渲染提示范围」：看到的格子就是即将受影响的格子。
    telegraphs = state.skill_telegraphs()
    from ..core.construct_environments import visual_cells
    construct_cells = visual_cells(state)
    cell_w = max(1, int(cell_w))
    cell_h = max(1, int(cell_h))
    # 一次渲染事务内的字形记忆表（2026-10-21 任务3）：一帧 1000+ 格里真正不同的
    # 字形键只有十几种，而每次解析都要走 game_icon → os.environ 读取（实测
    # 一帧 2300+ 次环境变量读取 ≈1.1ms）。mode 与解析器在本次调用内固定，
    # 所以同一个 key 的记忆结果与逐次调用完全等价。
    _glyph_memo: dict[str, str] = {}
    # C4（2026-10-22）：帧内字形记忆表。normalize 的键含 glyph 与 continuous，
    # compact 单独一表；表只由本次 render_map 调用持有，跨调用不缓存——模式/
    # 缩放档切换不需要任何失效逻辑。with_background 的帧内记忆经 A/B 实测收益
    # 不稳定（同帧同色组合太少、dict 查找抵消 f-string），故不做。
    _normalize_memo: dict[tuple[str, bool], str] = {}
    _compact_memo: dict[str, str] = {}

    def _tile_glyph(key: str) -> str:
        try:
            return _glyph_memo[key]
        except KeyError:
            value = _glyph_memo[key] = tile_symbol(key, effective_mode)
            return value

    floor_glyph = symbol("floor", effective_mode)
    lines: list[Text] = []
    grid = state.cells
    for row in range(viewport_height):
        row_text = Text()
        # cell_h=1 时 row_blank 从不进入 lines；不建它，省掉每格一次 append。
        row_blank = Text() if cell_h > 1 else None
        y = top + row
        for col in range(viewport_width):
            x = left + col
            position = (x, y)
            in_sight = (
                position in visible or position in phantom_echo or position in core_seen
            )
            # 诅咒灵视改版：所见异象同样按完整视野渲染（格子亮起，而非暗轮廓）；
            # cursed_reveal 仅保留「视野外」的判定语义。
            if position in cursed_seen and position not in visible:
                in_sight = True
            # 诅咒灵视：视野外的失控意识也完整显形（位置与类型都准确）。但它只
            # 借走「生物信息」，不点亮地形——该格背景仍按视野外处理，玩家一眼
            # 就能看出这是灵视所见、而非亲眼所见。
            cursed_reveal = position in cursed_seen and position not in visible
            cell = grid[y][x]
            # 多图层渲染：前景为该格最高层符号（生物=墙体 > 气体 > 液体 > 地面），
            # 被前景压住的气体/液体颜色经降亮度后作为背景色透出——
            # 上层完全表示、下层以颜色轮廓可见。
            # ⚠️ 顺序别再改：气体**浮在液体之上**（物理如此，且 ░▒▓ 点阵字会透出
            # 液体底色，两种物质一眼都读得到）。2026-09-21 修「液气同格只看得见
            # 液体」时把顺序调回了气体在上的原设计。
            # 前景为气体符号时传 "gas"，让背景透出的是液体而非气体自身。
            # 液体是独立的顶层前景：只以波线符号+颜色完全覆盖地面点，
            # 不把格子底色染色（液体之下只有地板，无更下层可透出）。
            if not in_sight and position not in developed:
                # 未显影视野外：所有梦中梦的地表底色铺压暗版；墙体/实心格也在
                # 这层底色上绘制，保证墙下仍有地板色。无底色带的地图维持黑底。
                zone = cached_surface_color(state,x,y,realm_zones,surface_cache)
                background = _dim_zone_color(zone) if zone else None
            elif cell.liquid > 0 and cell.gas <= 0 and not cell.solid and not (
                entities_at.get(position) or items_at.get(position) or events_at.get(position)
            ) and not (cell.flame or cell.floor is Material.SOLID_AGGREGATE):
                background = None
            elif cell.liquid > 0 and cell.gas > 0 and not cell.solid and not (
                entities_at.get(position) or items_at.get(position) or events_at.get(position)
            ) and not (cell.flame or cell.solid or cell.floor is Material.SOLID_AGGREGATE):
                # 液气共存（2026-09-21 回归）：**气体图层在液体图层之上**——
                # 前景是气体浓度图标（░/▒/▓ 点阵字，天然透出底色），底色是液体色
                # （按液量降亮度），一格同时读出「什么气·多浓」与「什么液·多深」。
                # 中间那版被改成「液体图标 + 气体底色」，气体图标整格消失、只剩
                # 一层看不出种类的暗色，玩家无法再同时观察两种物质。
                background = layered_background(cell, "gas")
            else:
                # 地表色位于地板/墙体下层；液体、气体等有显式底色时继续优先显示。
                background = layered_background(cell) or cached_surface_color(state,x,y,realm_zones,surface_cache)
            if in_sight or position in developed:
                ground = cached_surface_color(state,x,y,realm_zones,surface_cache)
                if ground and (background is None or state.realm_id == 'white_sanatorium'):
                    background = ground
            glyph, style = floor_glyph, "grey15" if not in_sight else "green"
            wall_face = None
            # 显影格即使视野外也完整可见：地形（原 developed 分支） +
            # 物品与生物（本次扩展）。未回应的异常地点仍需真正看见。
            dev_revealed = position in developed and position not in visible
            fog_state = ""
            if fog_enabled:
                if in_sight or dev_revealed:
                    fog_state = "visible_live"
                elif terrain_known:
                    fog_state = "terrain_known"
                elif always_visible_category(cell):
                    fog_state = "always_visible"
                elif position in memory_layer:
                    fog_state = "memory"
                else:
                    fog_state = "unknown"
            if observer is not None and position == observer:
                # 观察模式：白色 ?。它盖过玩家自己（进入瞬间两者同格），
                # 也永远画得出来——你看得见自己的目光落在哪，哪怕那格是黑的。
                glyph, style = symbol("observer", effective_mode), "bold bright_white"
            elif position == player_pos:
                glyph, style = symbol("player", effective_mode), "bold bright_cyan"
            elif in_sight or dev_revealed or cursed_reveal:
                entity = entities_at.get(position)
                if entity and entity.integrity > 0 and mind_shadow and entity.relation == "失控意识":
                    glyph, style = "? ", "bold bright_red"
                elif entity and entity.integrity > 0:
                    if cursed_reveal:
                        # 诅咒灵视：准确给出位置与类型——真实字形 + 阵营色，
                        # 连伪装也看穿（灵视看见的是「它是什么」，不是「它装成什么」）。
                        style = "bold " + realm_relation_style(state.realm_id, entity.relation)
                        known_glyph = _tile_glyph(entity.catalog_id)
                        glyph = known_glyph if known_glyph != "??" else entity_glyph(entity.glyph, effective_mode)
                    elif entity.trait == "disguise" and entity.alert_state == "未察觉" and not state.insight_active("残影直觉") and not entity.portents.get('hospital_diagnosed', 0) and not entity.portents.get('hospital_silver', 0):
                        # 人形衣架伪装：静止（未警戒）时显示为显化物符号（类别色）。
                        glyph, style = symbol("manifestation", effective_mode), CATEGORY_STYLES.get("易逝物", "bright_white")
                    elif position in phantom_echo and position not in visible:
                        # 残影直觉：隔墙显形为灰色虚线轮廓。
                        glyph, style = entity_glyph(entity.glyph, effective_mode), "grey58"
                    else:
                        style = "bold " + realm_relation_style(state.realm_id, entity.relation)
                        known_glyph = _tile_glyph(entity.catalog_id)
                        glyph = known_glyph if known_glyph != "??" else entity_glyph(entity.glyph, effective_mode)
                else:
                    world_item = items_at.get(position)
                    world_event = events_at.get(position)
                    if world_item:
                        # 物品自带图标（书卷 📚 / 残页 📜）优先；否则能装进栏位的
                        # 用 ♕、其余掉落物用 ◆（判据只看 slot 真假，与 category 名解耦）。
                        glyph = drop_glyph(
                            world_item.item, effective_mode, unicode_supported,
                            compact=cell_w == 1,
                        )
                        style = item_display_color(world_item.item)
                    elif world_event and not dev_revealed:
                        # 简单/复合同类内按事件分形；颜色统一亮黄标记「异常地点」。
                        if any(o.get('realm_scavenge') for o in world_event.options) and cell.solid:
                            definition = wall_def(cell.wall_kind)
                            glyph,style=_tile_glyph(definition.symbol_key),definition.color
                        else:
                            glyph, style = event_site_glyph(world_event, effective_mode), "bright_yellow"
                    else:
                        if cell.flame:
                            # 火焰分档渲染（扩展设计 2026-09-22）：按强度三档。
                            if cell.flame >= 6:
                                glyph, style = symbol("flame", effective_mode), "bold #ffd166"
                            elif cell.flame >= 3:
                                glyph, style = symbol("flame", effective_mode), "bold #ff8a3a"
                            else:
                                glyph, style = symbol("flame", effective_mode), "#c96a30"
                        elif position in gate_controls and not cell.solid:
                            from ..data.icon_glyphs import game_icon
                            glyph=('= ' if effective_mode=='ascii' else (game_icon('nav.equipment') or '⚙ '))
                            style='grey50' if gate_controls[position].flags.get('resolved') else 'bright_yellow'
                        elif cell.light_radius>0 and not cell.solid:
                            glyph=('o ' if effective_mode=='ascii' else '☼ ')
                            style='bright_yellow' if cell.light_on else 'grey50'
                        elif cell.plant:
                            # 植物：可穿行的固体地形，绿色（高丛更高更绿）。
                            plant = plant_def_for(cell.plant)
                            glyph, style = _tile_glyph(plant.key), plant.color
                        elif cell.solid or cell.floor is Material.SOLID_AGGREGATE:
                            definition = wall_def(cell.wall_kind)
                            glyph, style = _tile_glyph(definition.symbol_key), definition.color
                            if definition.symbol_key in CONTINUOUS_WALL_KEYS:
                                wall_face = glyph
                        elif cell.gas > 0 or cell.floor is Material.DIFFUSE_IMPRESSION:
                            # 🔴 气体**先判**（2026-09-21 回归）：液气共存时气体是
                            # 上层，画在这里；液体转为该格的底色（见上面 background
                            # 的液气共存分支）。反过来（先判液体）会让气体图标被
                            # 整格盖掉——正是玩家反馈「气体图标和颜色被完全遮盖」。
                            # 气体图标浓度标准化：1-5 ░ / 6-15 ▒ / 16+ ▓，颜色区分种类。
                            definition = gas_def(cell.gas_kind)
                            glyph, style = _tile_glyph(gas_depth_key(cell.gas)), definition.color
                        elif cell.liquid > 0 or cell.floor is Material.LIQUID_MEMORY:
                            definition = liquid_def(cell.liquid_kind)
                            glyph, style = symbol(liquid_depth_key(cell.liquid), effective_mode), definition.color
                        else:
                            variant = cell.aggregate_variant
                            style = AGGREGATE_STYLES.get(variant, "bright_green")
                            if variant == "棋盘格地板":
                                # 黑白格随回合奇偶交替：黑格白格互换，一眼可辨。
                                style = "#f0f0f0" if state.time % 2 == 0 else "#282830"
                            definition = floor_def(variant)
                            glyph, style = _tile_glyph(definition.symbol_key), style
            elif cell.solid and cell.wall_kind not in CONTAINER_KINDS:
                # 视野外只保留墙体记忆。地面容器（记忆/思绪容器）本不属于墙体，
                # 只是在数据上占一个实心格，因此不进入灰色记忆层——与地板同形。
                glyph, style = _tile_glyph(wall_def(cell.wall_kind).symbol_key), "grey19"
                if wall_def(cell.wall_kind).symbol_key in CONTINUOUS_WALL_KEYS:
                    wall_face = glyph
            if fog_enabled and fog_state not in ("visible_live", ""):
                # 未知/记忆/全图地形/始终可见：用知识层覆盖上面的实时地形选择。
                glyph, style, wall_face, background = _fog_cell_layer(
                    state, cell, fog_state, tile_symbol, effective_mode,
                    memory_layer.get(position), realm_zones, x, y)
            # 战术电场在关闭动画时仍有静态标识，不泄露视野外地形。
            if position in electric_cells and position in visible:
                background = "#102c30"
            # 爆炸动画：饱和黄（前 2 帧）→ 橙红（中 2 帧）→ 深红余温，
            # 6 帧后清除（见 app._refresh_game_frame 的老化计时）。
            on_explosion = bool(explosion_cells) and position in explosion_cells
            if on_explosion and (not fog_enabled or fog_state == "visible_live"):
                # 中心→边缘距离渐变（2026-09-22 改版）：白热黄→橙红→深红。
                # 用最近爆心的曼哈顿距离/radius 取色；帧龄只做收尾压暗。
                best_d = 10 ** 9
                best_r = 1
                for bx, by, br in (explosion_blasts or []):
                    d = abs(x - bx) + abs(y - by)
                    if d / max(1, br) < best_d / max(1, best_r):
                        best_d, best_r = d, max(1, br)
                frac = min(1.0, best_d / max(1, best_r))
                if explosion_age < 2:
                    background = "#ffe14d"
                elif frac <= 1 / 3:
                    background = "#ffe14d"
                elif frac <= 2 / 3:
                    background = "#ff7028"
                else:
                    background = "#a01810"
                if explosion_age >= 4:
                    background = "#a01810"  # 收尾压暗
            on_assist = bool(assist_cells) and position in assist_cells
            if on_assist and (not fog_enabled or fog_state != "unknown"):
                # 目标辅助路径：降饱和暗黄垫底（不遮盖上层字形/地形）；
                # 带复杂图形的格子不加粗不提亮，只垫底色以示路径经过。
                if entities_at.get(position) or items_at.get(position) or events_at.get(position):
                    background = "#3a3420"
                else:
                    background = "#4a4020"
            if wire_insight and position in wire_cells and (
                not fog_enabled or fog_state != "unknown"
            ):
                # 电线层（独立于地形层）：暗蓝沟槽底色 + 中心连线点。
                background = "#1a2a4a"
                # Keep the player, components and objects above the wire layer.
            # 褪色雾（扩展包 v1）：吸入「褪色」征兆期间，显影格暂时失效。
            if "褪色" in state.portents and position in developed:
                if position not in visible and position not in (cursed_seen or set()):
                    background = None
            tut_mark = (tutorial_cells or {}).get(position)
            if tut_mark is not None:
                # 教程目标格：青金底色脉动（随回合奇偶呼吸）+ 引导标记字形。
                # 目标是灯塔式的存在——视野外同样可见；空格上叠标记字形。
                background = "#0f3a46" if state.time % 2 == 0 else "#12505f"
                if not (entities_at.get(position) or items_at.get(position) or events_at.get(position)):
                    glyph, style = tut_mark, "bold bright_cyan"
            # 电路层（电路逻辑 v2，独立覆盖图层）：持「电工直觉」时，
            # 电线格染线路沟槽底色、门/接收器与当回合通电格加亮——
            # 地形字形保持不变，电路信息全部走背景/前景覆盖层表达。
            if (cell.wire and state.insight_active("电工直觉")
                    and (not fog_enabled or fog_state != "unknown")):
                from ..materials.logic import LOGIC_KINDS

                background = "#2a3a5a" if cell.wall_kind in LOGIC_KINDS else "#1a2a4a"
                if position in getattr(state, "_logic_energized", set()):
                    style = "bold #7ad0ff"
            if board_visible and position in visible and position in board_traces:
                live = board_values.get(position, position in state._logic_energized)
                background = "#263d43" if live else "#18262f"
                # Components, entities and goals stay above traces.
                if position not in board_nodes and not cell.solid and position not in entities_at and position not in items_at and position not in events_at and position != player_pos:
                    junctions = {1:"│", 2:"─", 3:"└", 4:"│", 5:"│", 6:"┌", 7:"├", 8:"─", 9:"┘", 10:"─", 11:"┴", 12:"┐", 13:"┤", 14:"┬", 15:"┼"}
                    glyph = ("╳" if len(board_traces[position]) > 1 else junctions.get(cell.wire, "·")) + " " if unicode_mode else "+ "
                    style = "bold #d4ba72" if live else "#607d8b"
                if position in board_nodes:
                    node = board_nodes[position]
                    if position != player_pos and position not in entities_at:
                        style = "bold #d4ba72" if live else style
                    if node["op"] == "cube" and cell.wall_kind == "理念立方体":
                        style, background = "bold #87ddb0", "#224036"
                    elif node["op"] in {"cube", "plate", "step"} and position != player_pos and position not in entities_at and position not in items_at and position not in events_at:
                        glyph = "□ " if unicode_mode else "o "
            tele = telegraphs.get(position)
            if tele is not None and position in visible:
                # 预警范围：暗红（范围爆发/主动技能蓄力）/ 暗橙（炸弹落点）
                # / 暗紫（效果场）垫底，随回合奇偶脉动——站在格子里就是站在
                # 即将受影响的范围里。主动技能预警（cast/cast_path/field）
                # 与旧 burst/bomb 样式并存，FX off 也可见。
                if state.time % 2 == 0:
                    backgrounds = {"burst": "#4a1414", "bomb": "#4a2c10", "field": "#3a1a3a"}
                else:
                    backgrounds = {"burst": "#3a1010", "bomb": "#3a240c", "field": "#2e142e"}
                if tele in ("burst", "cast", "cast_path"):
                    background = backgrounds["burst"]
                elif tele == "bomb":
                    background = backgrounds["bomb"]
                else:
                    background = backgrounds["field"]
            construct = construct_cells.get(position)
            if construct and position in visible:
                mark, color, background, remaining = construct
                if position != player_pos and position not in entities_at and position not in items_at and position not in events_at:
                    glyph, style = mark, f'bold {color}'
            if markers and position in markers:
                # 篡改对象的临时编号标记（docs §8.4）：只盖字形、保留格子底色，
                # 不改变可见性/命中/结算；编号由草稿固定，刷新不跳号。
                from ..core.sound_markers import marker_glyph
                mark = marker_glyph(str(markers[position])[:1],
                                    ascii_mode=effective_mode == "ascii")
                glyph = mark + " " if cell_w > 1 else mark
                style = "bold bright_yellow"
            style_with_bg = with_background(style, background)
            continuous = wall_face is not None and glyph == wall_face
            # 紧凑档使用主题字形的单列版本；其它档位保持原始两列图标，
            # 放大时只在图标两侧增加背景间距，避免重复堆叠。同一原始字形的
            # 归一化结果在一帧内必然相同，走帧内记忆（C4）。
            glyph_block = _frame_normalized_glyph(
                glyph, effective_mode, cell_w, continuous,
                _normalize_memo, _compact_memo)
            if continuous:
                # 基础聚合墙铺满整个放大地格，横竖相邻格都保持连续墙面。
                filled = set_cell_size(glyph_block * ((cell_w + 1) // 2), cell_w)
                row_text.append(filled, style=style_with_bg)
                if row_blank is not None:
                    row_blank.append(filled, style=style_with_bg)
                continue
            pad_total = max(0, cell_w - 2)
            left_pad = pad_total // 2
            right_pad = pad_total - left_pad
            if left_pad:
                row_text.append(" " * left_pad, style=style_with_bg)
            row_text.append(glyph_block, style=style_with_bg)
            if right_pad:
                row_text.append(" " * right_pad, style=style_with_bg)
            if row_blank is not None:
                row_blank.append(" " * cell_w, style=style_with_bg)
        for r in range(cell_h):
            lines.append(row_text if r == (cell_h - 1) // 2 else row_blank)
    text = Text()
    for index, line in enumerate(lines):
        if index:
            text.append("\n")
        text.append_text(line)
    return text