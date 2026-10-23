
"""Read-only scene data shared by character and future image map renderers.

docs §13.3: both outputs must consume one permission-filtered snapshot instead of
walking the real world independently. This module never changes world state and
never reveals information the normal vision/knowledge rules would hide:
- visible/developed: live terrain + liquid/gas/objects/actors/flame/danger;
- terrain_known: only terrain, no ordinary liquid/gas/actors (enhancement scope);
- always_visible: only the always-visible category (edge/developer liquid);
- memory: terrain snapshot only; liquid/gas/actors/moving things are not stored;
- unknown: nothing but the cell position/status.
"""
from __future__ import annotations

from dataclasses import dataclass, field, fields, replace
from types import MappingProxyType
from typing import Any

from .constants import Material
from .vision.knowledge import cell_knowledge
from ..materials import CONTAINER_KINDS, DEFAULT_WALL, plant_def_for

SCENE_VERSION = 1

# 热循环常量（2026-10-22 批次3）：Material 成员的显示名只解析一次；液体/气体
# 危险名单用元组常量，避免逐格重建临时容器。值本身与旧代码逐字相同。
_FLOOR_NAMES = {member: str(member.value) for member in Material}
_GAS_HAZARD_KINDS = ('催眠雾', '毒气', '灼热蒸汽')

# 分层观察（docs §13.2）：综合 / 地形 / 液体 / 气体；§15.4 再加地势；
# §16.7 加「声音线索」：综合画面 + 显式声源标记，不额外照亮地形。
# 图像与字符后端都可消费同一份过滤结果，避免各自实现一套"这一层显示什么"。
SPATIAL_LAYERS = ('floor', 'low', 'middle', 'high')
OBSERVE_LAYERS = ('composite', *SPATIAL_LAYERS, 'liquid', 'gas', 'elevation', 'terrain',
                  'sound')


@dataclass(frozen=True)
class SceneTerrain:
    floor: str
    solid: bool
    wall_kind: str
    aggregate_variant: str
    height: int | None = None


@dataclass(frozen=True)
class SceneOccupant:
    """Public physical occupancy, never inferred by a renderer from a name."""
    kind: str
    name: str
    icon: str
    color: str
    layers: tuple[str, ...]
    identity: str = ''
    notes: tuple[str, ...] = ()


@dataclass(frozen=True)
class SceneActor:
    x: int
    y: int
    display_name: str
    icon_key: str
    relation: str = ""
    alert: str = ""
    always_visible: bool = False
    identity: str = ''


@dataclass(frozen=True)
class SceneCell:
    x: int
    y: int
    status: str
    terrain: SceneTerrain | None = None
    liquid: tuple[str, int] | None = None
    gas: tuple[str, int] | None = None
    plant: int = 0
    flame: int = 0
    actors: tuple[SceneActor, ...] = ()
    items: tuple[str, ...] = ()
    events: tuple[str, ...] = ()
    site: str = ""
    danger: bool = False
    telegraph: str = ""
    # 已授权的地势档位（整数档）；None = 未知、恒显类别或旧档「地势未记录」。
    elevation: int | None = None
    # 知识层给出的信息来源（sight / developed / terrain_known / memory / …），
    # 右栏要按来源说明这一格的地势是现在看见的还是上次观察留下的。
    sources: tuple[str, ...] = ()
    occupants: tuple[SceneOccupant, ...] = ()
    hazards: tuple[str, ...] = ()


@dataclass(frozen=True)
class SceneSnapshot:
    version: int
    layer_key: str
    realm_id: str
    revision: tuple
    viewport: tuple[int, int, int, int]
    cell_w: int
    cell_h: int
    cells: dict[tuple[int, int], SceneCell] = field(default_factory=dict)

    visuals: dict = field(default_factory=lambda: MappingProxyType({}))
    # 这一份快照被 observe_scene 过滤成了哪个观察层（'' = 未过滤的综合图）。
    # 渲染端据此切换到该层专用画法，不必各自猜自己正在画什么。
    observe_layer: str = ""

    def __post_init__(self):
        if not isinstance(self.cells, MappingProxyType):
            object.__setattr__(self,'cells',MappingProxyType(dict(self.cells)))
        if not isinstance(self.visuals, MappingProxyType):
            object.__setattr__(self,'visuals',MappingProxyType(dict(self.visuals)))

    def cell(self, x: int, y: int) -> SceneCell | None:
        return self.cells.get((int(x), int(y)))


LAYER_RETENTION_ORDER = (
    "观察/瞄准", "任务关键标记", "主体", "液气", "特殊地板", "普通地板",
)


def cell_layer_names(cell: "SceneCell") -> tuple[str, ...]:
    """Known on-cell layers ordered by the §4.2 retention priority.

    Observation/aim highlights live in the compositor; task markers, actors,
    materials and terrain follow in that order. The right panel lists every
    layer, not just the currently selected observation layer.
    """
    tasks: list[str] = []
    bodies: list[str] = []
    materials: list[str] = []
    ground: list[str] = []
    if cell.events:
        tasks.append(f"事件×{len(cell.events)}" if len(cell.events) > 1 else "事件")
    if cell.site:
        tasks.append("地点")
    if cell.telegraph:
        tasks.append("预警")
    if cell.danger:
        tasks.append("危险")
    if cell.actors:
        bodies.append(f"生物×{len(cell.actors)}" if len(cell.actors) > 1 else "生物")
    if cell.items:
        bodies.append(f"物品×{len(cell.items)}" if len(cell.items) > 1 else "物品")
    if cell.flame:
        bodies.append("火焰")
    if cell.plant:
        bodies.append("植物")
    if cell.gas:
        materials.append(cell.gas[0])
    if cell.liquid:
        materials.append(cell.liquid[0])
    if cell.terrain is not None:
        terrain = (cell.terrain.wall_kind or cell.terrain.aggregate_variant
                   or cell.terrain.floor)
        if terrain:
            ground.append(terrain)
    return tuple(tasks + bodies + materials + ground)


# SceneCell 的字段顺序（与 dataclass 生成的 __init__ 完全一致）；快速构造路径
# 用它把值直接填进 __dict__，省掉 frozen dataclass 逐字段 object.__setattr__。
# 字段清单由 tests/test_scene_build_fast_261022.py 的全字段等价测试守护。
_SCENE_CELL_FIELDS = tuple(f.name for f in fields(SceneCell))


def _fast_scene_cell(*values) -> SceneCell:
    """构造 SceneCell 的快速路径：结果与 SceneCell(*values) 逐字段相等。

    frozen dataclass 生成的 __init__ 对 18 个字段逐个 object.__setattr__，
    一帧 1020 格实测约 1.4 us/格；直接填 __dict__ 约 0.6 us/格。字段顺序
    与 __init__ 相同，外部仍然无法赋值（__setattr__ 仍被 frozen 拦截）；
    __eq__/__hash__/__repr__/dataclasses.replace 都按字段读取，行为不变。
    """
    cell = object.__new__(SceneCell)
    cell.__dict__.update(zip(_SCENE_CELL_FIELDS, values))
    return cell


def _terrain(knowledge, cell) -> SceneTerrain | None:
    if knowledge.status == "unknown" or (knowledge.status == "always_visible" and "显影液" in knowledge.sources):
        return None
    if knowledge.status == 'always_visible':
        # The public boundary identity grants no knowledge of its substrate.
        return _intern_terrain('', True, str(knowledge.wall_kind or ''), '', None)
    return _intern_terrain(
        str(knowledge.floor or ""),
        bool(knowledge.solid),
        str(knowledge.wall_kind or ""),
        str(knowledge.aggregate_variant or ""),
        getattr(knowledge, 'height', None),
    )


# 地形值池（2026-10-21 任务3）：一帧 1000+ 格里真正不同的地形只有十几种，
# 以前每格都新造一个 SceneTerrain（≈1.1µs/个 → 一帧 1.2ms 全花在重复对象上）。
# SceneTerrain 是 frozen 且按值比较，共享同一个实例对调用方完全不可见；
# 上限存在是为了「地图被脚本改得很碎」时不会无限长。
_TERRAIN_POOL: dict[tuple, SceneTerrain] = {}
_TERRAIN_POOL_LIMIT = 4096


def _intern_terrain(floor: str, solid: bool, wall_kind: str,
                    aggregate_variant: str, height: int | None) -> SceneTerrain:
    key = (floor, solid, wall_kind, aggregate_variant, height)
    cached = _TERRAIN_POOL.get(key)
    if cached is not None:
        return cached
    value = SceneTerrain(floor, solid, wall_kind, aggregate_variant, height)
    if len(_TERRAIN_POOL) >= _TERRAIN_POOL_LIMIT:
        _TERRAIN_POOL.clear()
    _TERRAIN_POOL[key] = value
    return value


def actor_display(state, enemy) -> tuple[str, str]:
    """显示名与图标键：伪装在未察觉且无残影直觉时仍使用显化物表现。"""
    if (enemy.trait == "disguise" and enemy.alert_state == "未察觉"
            and not state.insight_active("残影直觉")
            and not enemy.portents.get("hospital_diagnosed", 0)
            and not enemy.portents.get("hospital_silver", 0)):
        return "显化物", "manifestation"
    return enemy.label, enemy.catalog_id


def observe_scene(scene: SceneSnapshot, layer: str) -> SceneSnapshot:
    """按观察层只保留允许显示的信息；unknown/memory 的地形规则不变。"""
    if layer not in OBSERVE_LAYERS or layer in ("composite", "sound"):
        # 声音线索层只叠加显式声源标记（渲染端负责），画面内容与综合层一致。
        return scene
    if layer in SPATIAL_LAYERS:
        band = {'low': 1, 'middle': 2, 'high': 3}.get(layer, 0)
        cells = {}
        for pos, cell in scene.cells.items():
            terrain = cell.terrain
            if (terrain is not None and terrain.wall_kind != '意识边界'
                    and (not band or terrain.height is None or terrain.height < band)):
                terrain = replace(terrain, solid=False, wall_kind='')
            occupants = tuple(o for o in cell.occupants if layer in o.layers)
            public_ids = {a.identity for a in cell.actors if a.always_visible}
            occupants += tuple(replace(o, kind='marker', layers=()) for o in cell.occupants
                               if o.kind == 'actor' and o.identity in public_ids and o not in occupants)
            actor_ids = {o.identity for o in occupants if o.kind == 'actor'}
            items = tuple(o.name for o in occupants if o.kind == 'item')
            actors = tuple(a for a in cell.actors if a.always_visible or
                           any(o.kind == 'actor' and o.identity == a.identity and o.identity in actor_ids
                               and o.name == a.display_name for o in occupants))
            # Explicitly constructed scenes retain their pre-existing low objects.
            if layer == 'low' and not cell.occupants:
                items, actors = cell.items, cell.actors
            cells[pos] = replace(cell, terrain=terrain,
                liquid=cell.liquid if layer == 'low' else None,
                gas=cell.gas if layer == 'high' else None,
                plant=cell.plant if any(o.kind == 'plant' for o in occupants)
                      or (layer == 'low' and not cell.occupants) else 0,
                flame=cell.flame if layer == 'low' else 0,
                actors=actors, items=items, occupants=occupants,
                danger=cell.danger)
        return replace(scene, cells=cells, visuals=MappingProxyType({}), observe_layer=layer)
    if layer == "elevation":
        # 地势视图只画高低（同屏只有一种地图），但右栏的局部查看仍要读到同格
        # 允许查看的液体、气体与危险（docs §15.4），所以这里不清空内容，只把
        # 主体收敛成玩家自己——切层不会消除视线遮挡，也不会看见隐藏生物。
        cells = {pos: replace(cell, actors=tuple(
                     actor for actor in cell.actors if actor.relation == 'player' or actor.always_visible))
                 for pos, cell in scene.cells.items()}
        return replace(scene, cells=MappingProxyType(cells),
                       visuals=MappingProxyType({}), observe_layer=layer)
    cells: dict[tuple[int, int], SceneCell] = {}
    for pos, cell in scene.cells.items():
        live = cell.status in ("visible", "developed")
        cells[pos] = SceneCell(
            x=cell.x, y=cell.y, status=cell.status, terrain=cell.terrain,
            elevation=cell.elevation, sources=cell.sources,
            liquid=cell.liquid if (layer == "liquid" and (live or cell.status == "always_visible")) else None,
            gas=cell.gas if (layer == "gas" and live) else None,
            plant=cell.plant if layer == "terrain" and live else 0,
            flame=0, actors=tuple(a for a in cell.actors if a.always_visible), items=(), events=(),
            site=cell.site, danger=cell.danger if live else False,
            telegraph=cell.telegraph if live else '',
            hazards=cell.hazards if live else (),
        )
    return replace(scene, cells=MappingProxyType(cells),
                   visuals=MappingProxyType({}), observe_layer=layer)


def build_scene(state: Any, *, viewport: tuple[int, int, int, int] | None = None,
                cell_w: int = 2, cell_h: int = 1, legacy_terrain: bool = False) -> SceneSnapshot:
    """Build the shared permission-filtered map scene (read-only).

    2026-10-22 批次3 微优化：输出与优化前逐字段等价
    （见 tests/test_scene_build_fast_261022.py 的全字段对拍）。只做纯机械优化：
    材质常量/plant_def_for 提到模块级、legacy_terrain 分支不再先算一份随后被丢弃的
    _terrain、hazards 直接构造（不再逐格生成器）、每格坐标元组只建一次、空字典/
    空集合不逐格查、SceneCell 改位置参数构造、occupants 仅在真有内容时建列表。
    信息权限/知识语义（unknown/memory/terrain_known/always_visible/容器伪装/
    developed/显影液/sensed/电场/预警/hazards）逐项未改。
    """
    if viewport is None:
        viewport = (0, 0, state.width, state.height)
    left, top, width, height = (int(v) for v in viewport)
    left = max(0, min(left, state.width - 1))
    top = max(0, min(top, state.height - 1))
    width = max(1, min(width, state.width - left))
    height = max(1, min(height, state.height - top))
    visible = set(state.visible_cells())
    # Resolve the expensive LOS/glow set once, then add only separately public
    # actor cells. is_visible() per viewport cell rescans nearby light sources.
    knowledge_visible = None if (state.debug_full_vision or state.light_turns > 0) else visible
    if knowledge_visible is not None:
        for enemy in state.enemies:
            if enemy.integrity > 0 and (enemy.always_visible or state.reveals_anomalies):
                if state.is_visible(enemy.x, enemy.y):
                    visible.add((enemy.x, enemy.y))
    actors_by_pos: dict[tuple[int, int], list[SceneActor]] = {}
    sensed = set()
    player_x, player_y = state.player.x, state.player.y
    radius = state.effective_sight_radius() if state.insight_active('残影直觉') else -1
    for enemy in state.enemies:
        if enemy.integrity > 0 and (enemy.always_visible or state.reveals_anomalies or
                (radius >= 0 and enemy.trait in ('phantom', 'disguise') and
                 max(abs(enemy.x - player_x), abs(enemy.y - player_y)) <= radius)):
            sensed.add((enemy.x, enemy.y))
    for enemy in state.enemies:
        if enemy.integrity <= 0:
            continue
        pos = (int(enemy.x), int(enemy.y))
        if pos not in visible and pos not in sensed:
            continue
        name, icon = actor_display(state, enemy)
        actors_by_pos.setdefault(pos, []).append(SceneActor(
            pos[0], pos[1], str(name), str(icon), str(enemy.relation),
            str(enemy.alert_state), bool(enemy.always_visible), str(enemy.id)))
    player_pos = (player_x, player_y)
    actors_by_pos.setdefault(player_pos, []).append(
        SceneActor(player_pos[0], player_pos[1], '自身', 'player', 'player', identity='player'))
    item_entries_by_pos: dict[tuple[int, int], list] = {}
    for entry in state.world_items:
        item_entries_by_pos.setdefault((int(entry.x), int(entry.y)), []).append(entry)
    events_by_pos: dict[tuple[int, int], list[str]] = {}
    for entry in state.events:
        if not getattr(entry, "resolved", False):
            events_by_pos.setdefault((int(entry.x), int(entry.y)), []).append(str(entry.name))
    telegraphs = state.skill_telegraphs()
    electric_cells = state.electric_field_cells()
    # 一次渲染事务的共用上下文（2026-10-21 任务3）：层键与显影集合只解析一次。
    # 以前这两样在 cell_knowledge 里逐格解析，1017 格就是 1017 次字符串构造 +
    # 1017 次 setdefault；这里传下去，单格查询路径不变。
    memory_layer = state.terrain_memory.get(state.layer_key()) or {}
    developed_cells = state.developed_for_depth()
    cells: dict[tuple[int, int], SceneCell] = {}
    # 帧内只绑定一次：热循环里省掉逐格的属性解析与闭包/生成器对象。
    knowledge_of = cell_knowledge
    terrain_of = _terrain
    intern_terrain = _intern_terrain
    floor_names = _FLOOR_NAMES
    get_actors = actors_by_pos.get
    get_items = item_entries_by_pos.get
    get_events = events_by_pos.get
    get_telegraph = telegraphs.get
    has_actors = bool(actors_by_pos)
    has_items = bool(item_entries_by_pos)
    has_events = bool(events_by_pos)
    has_telegraphs = bool(telegraphs)
    has_electric = bool(electric_cells)
    has_sensed = bool(sensed)
    gas_hazard_kinds = _GAS_HAZARD_KINDS
    for y in range(top, top + height):
        for x in range(left, left + width):
            pos = (x, y)
            knowledge = knowledge_of(state, x, y, visible=knowledge_visible,
                                     memory_layer=memory_layer, developed=developed_cells)
            cell = state.cell(x, y)
            knowledge_status = knowledge.status
            live_content = knowledge_status in ("visible", "developed")
            if legacy_terrain and not live_content and knowledge_status != 'always_visible':
                # Existing runs with map-memory disabled expose terrain, not live
                # contents. Changing renderer must not silently enable new fog.
                # 此分支会覆盖掉 _terrain 的结果，所以不再先算那一份垃圾。
                floor = cell.floor
                floor_name = floor_names.get(floor)
                if floor_name is None:
                    floor_name = str(getattr(floor, 'value', floor))
                terrain = intern_terrain(floor_name, bool(cell.solid),
                                         str(cell.wall_kind or ''),
                                         str(cell.aggregate_variant or ''),
                                         int(cell.height))
                # 关闭地图记忆时本来就整层公开实时地形；地势档位跟随同一口径，
                # 免得地势视图在旧配置下整片空白（改这条要连同地形口径一起改）。
                status = 'terrain_known'
                sources = ('terrain_known',)
                elevation = int(getattr(cell, 'elevation', 0) or 0)
            else:
                terrain = terrain_of(knowledge, cell)
                status = knowledge_status
                sources = knowledge.sources
                elevation = knowledge.elevation
            if (terrain is not None and status == 'terrain_known'
                    and terrain.wall_kind in CONTAINER_KINDS):
                if legacy_terrain:
                    terrain = intern_terrain(terrain.floor, False, '',
                                             terrain.aggregate_variant, terrain.height)
                else:
                    terrain = intern_terrain(terrain.floor, terrain.solid, DEFAULT_WALL,
                                             terrain.aggregate_variant, terrain.height)
            liquid = gas = None
            plant = flame = 0
            actors: tuple[SceneActor, ...] = ()
            items: tuple[str, ...] = ()
            events: tuple[str, ...] = ()
            item_entries = None
            if live_content:
                if int(cell.liquid) > 0 and cell.liquid_kind:
                    liquid = (str(cell.liquid_kind), int(cell.liquid))
                if int(cell.gas) > 0 and cell.gas_kind:
                    gas = (str(cell.gas_kind), int(cell.gas))
                plant = int(cell.plant)
                flame = int(cell.flame)
                if has_actors:
                    actors = tuple(get_actors(pos) or ())
                if has_items:
                    item_entries = get_items(pos)
                    if item_entries:
                        items = tuple(str(entry.item.name) for entry in item_entries)
                if has_events:
                    events = tuple(get_events(pos) or ())
            elif cell.liquid_kind == '显影液' and cell.liquid > 0:
                liquid = (str(cell.liquid_kind), int(cell.liquid))
            if has_sensed and pos in sensed:
                actors = tuple(get_actors(pos) or ())
            occupants = None
            if live_content:
                if plant:
                    definition = plant_def_for(plant)
                    occupants = [SceneOccupant(
                        'plant', definition.name, definition.key, definition.color,
                        ('low', 'middle', 'high')[:definition.height])]
                if item_entries:
                    if occupants is None:
                        occupants = []
                    support_band = min(3, max(1, int(cell.height) + 1))
                    wall_kind = cell.wall_kind
                    solid = cell.solid
                    for entry in item_entries:
                        surface = entry.surface
                        # 2026-10-22：承载面不再要求 solid——白瓷工作台／胡桃木书架
                        # 是可步行的家具，但「东西搁在上面」跟台子是一回事。
                        support = bool(surface and surface == wall_kind)
                        band = support_band if support else 1
                        item = entry.item
                        occupants.append(SceneOccupant(
                            'item', item.name, item.icon or 'manifestation', item.color,
                            (('low', 'middle', 'high')[band - 1],), item.instance_id,
                            (str(surface),) if support else ()))
            if actors:
                if occupants is None:
                    occupants = []
                for actor in actors:
                    # Existing actors have ground occupancy; flight is not guessed
                    # from flavour text, sprite size or a ghost-like name.
                    occupants.append(SceneOccupant(
                        'actor', actor.display_name, actor.icon_key,
                        '#e8e2d0' if actor.relation == 'player' else '#e59b9b',
                        ('low',), actor.identity, (actor.alert,) if actor.alert else ()))
            gas_kind_hazard = cell.gas_kind in gas_hazard_kinds
            hazards: tuple[str, ...] = ()
            telegraph = ''
            danger = False
            if live_content:
                hazard_names = None
                if has_electric and pos in electric_cells:
                    hazard_names = ['electric']
                if flame:
                    if hazard_names is None:
                        hazard_names = []
                    hazard_names.append('flame')
                if cell.gas and gas_kind_hazard:
                    if hazard_names is None:
                        hazard_names = []
                    hazard_names.append('gas')
                if hazard_names:
                    hazards = tuple(hazard_names)
                if has_telegraphs:
                    telegraph = str(get_telegraph(pos, ''))
                danger = bool(flame or (has_telegraphs and pos in telegraphs)
                              or gas_kind_hazard)
            cells[pos] = _fast_scene_cell(
                x, y, status, terrain, liquid, gas, plant, flame, actors, items,
                events, str(knowledge.site or ""), danger, telegraph, elevation,
                sources, tuple(occupants) if occupants else (), hazards)
    revision = (
        int(getattr(state, "time", 0) or 0), str(state.layer_key()),
        int(getattr(state, "depth", 0) or 0), str(getattr(state, "realm_id", "") or ""),
        int(getattr(state, "map_knowledge_version", 0) or 0),
        int(getattr(state, "plant_revision", 0) or 0),
    )
    return SceneSnapshot(SCENE_VERSION, str(state.layer_key()),
                         str(getattr(state, 'realm_id', '') or ''), revision,
                         (left, top, width, height), int(cell_w), int(cell_h),
                         MappingProxyType(cells))
