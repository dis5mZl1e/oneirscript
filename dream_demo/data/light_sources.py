"""§12 light-source catalog: the single reviewed list of decorative sources."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LightSourceSpec:
    source_id: str
    kind: str                 # plant / wall / liquid
    key: str                  # material code or display key used by the world
    color: str
    note: str = ""
    # ---- §12 A：独立表现参数（2026-10-20）----
    # radius / brightness 只影响**装饰彩光**的表现，不等于机械照明：
    # 机械资格与半径仍由 core/vision/glow.py 的 source_radius() 决定，
    # 补光不扩大视距、射程或显影资格（docs §12.1、§12.7）。
    # brightness 与 effects.TORCH_BRIGHTNESS 同量纲（0.75 = 玩家主光），
    # 换算成相对强度即 brightness / 0.75。
    radius: float = 2.5
    brightness: float = 0.56
    mechanical: bool = False  # True = 该来源同时具备真实机械照明
    # 专门强光（黄铜阅读灯、日光壁）：照亮目标时视距 +4；普通机械光 +3。
    # 多个来源取最高、不求和（docs 261022 §4.1）。
    strong: bool = False
    # 存量门槛（§12.4.3）：液体看存量、气体看浓度，未达到就不形成光晕，
    # 只保留材料自身外观。0 = 不设门槛。
    min_amount: int = 0
    min_gas: int = 0
    # 开关资格（§12.5 生成报告要列「开关状态」）：True = 这条来源的亮灭
    # 跟随真实状态（灯段开关、终端屏幕、断电）。False = 常驻弱光。
    switchable: bool = False


# Keep in sync with materials.plants.PLANT_CODE_* (3/8/16/21 as of 2026-10-20).
_LICHEN = 3
_NIGHT_QUEEN = 8
_GLASS_SHROOM = 16
_WAX_BLOOM = 21


SOURCES: tuple[LightSourceSpec, ...] = (
    LightSourceSpec("plant.lichen", "plant", str(_LICHEN), "#d6e36a",
                    "发光地衣：黄绿低亮，1—2 格；机械照明仍走 glow.source_radius",
                    radius=2.0, brightness=0.42, mechanical=True),
    LightSourceSpec("plant.night_queen", "plant", str(_NIGHT_QUEEN), "#b47ae0",
                    "夜皇后：紫色灯；单株与小片区分",
                    radius=2.5, brightness=0.50, mechanical=True),
    LightSourceSpec("plant.glass_shroom", "plant", str(_GLASS_SHROOM), "#e070d0",
                    "彩玻菌：粉紫灯；不把普通玻璃自动当光源",
                    radius=2.2, brightness=0.46, mechanical=True),
    LightSourceSpec("plant.wax_bloom", "plant", str(_WAX_BLOOM), "#f0d890",
                    "融蜡花：蜡黄灯；真实燃烧才接入火焰光",
                    radius=2.0, brightness=0.44, mechanical=True),
    LightSourceSpec("wall.brass_reading_lamp", "wall", "黄铜阅读灯", "#ffd28a",
                    "暖金主光，表现半径 3—4 格；机械照明走既有规则",
                    radius=3.0, brightness=0.56, mechanical=True, strong=True,
                    switchable=True),
    LightSourceSpec("wall.daylight_wall", "wall", "日光壁", "#dcefff",
                    "青白稳定光，短灯段呈面状；关闭本地灯段需更新",
                    radius=2.8, brightness=0.52, mechanical=True, strong=True,
                    switchable=True),
    LightSourceSpec("liquid.silver_salt", "liquid", "银盐悬液", "#cfd8ff",
                    "银蓝弱光，按现有量阈值与机械半径；流动时局部更新",
                    radius=1.8, brightness=0.34, mechanical=True),
    # ---- §12 D：已有环境补接（2026-10-20）----
    # §13.3：原先只装饰的 7 条在这里升为真实机械照明（半径见材料定义），
    # 呜咽晶柱保留纯装饰。机械资格只影响「目标被照亮时的视距延长」，
    # 不扩大探图、射程或显影；亮灭仍随真实开关/存量/浓度状态。
    LightSourceSpec("wall.lightbox", "wall", "灯箱墙", "#f4e3c0",
                    "乳白偏暖，开启时 2 格；关闭/毁坏即灭，不是所有彩砖都发光",
                    radius=2.5, brightness=0.42, mechanical=True, switchable=True),
    LightSourceSpec("wall.bsod_terminal", "wall", "蓝屏终端", "#5aa8e8",
                    "稳定低亮青蓝 1 格；跟随真实屏幕状态，不给普通事件套蓝光",
                    radius=1.6, brightness=0.28, mechanical=True, switchable=True),
    LightSourceSpec("wall.dream_crystal", "wall", "梦晶簇", "#c9b8ff",
                    "冷紫白约 1 格；完整晶簇才是来源，破坏即撤销",
                    radius=2.0, brightness=0.28, mechanical=True),
    LightSourceSpec("wall.wailing_pillar", "wall", "呜咽晶柱", "#9fd8e8",
                    "低亮青蓝 1—2 格；按既有深度与生成渠道出现；纯装饰，不照路",
                    radius=1.8, brightness=0.22),
    LightSourceSpec("wall.unconscious_crystal", "wall", "无意识结晶", "#b7a8c8",
                    "灰紫 1 格；稳定微光，不虚构激活状态",
                    radius=1.8, brightness=0.22, mechanical=True),
    LightSourceSpec("liquid.molten_thought", "liquid", "熔念金属", "#c86a2e",
                    "暗铜橙；存量 ≥12 才成 2 格机械光，小量只留自身亮点",
                    radius=2.4, brightness=0.36, mechanical=True, min_amount=12),
    LightSourceSpec("liquid.starlight_dew", "liquid", "星辉露", "#f0e8b8",
                    "暖银金；存量 ≥8 有 1 格机械光，流动与消耗即更新",
                    radius=1.8, brightness=0.24, mechanical=True, min_amount=8),
    LightSourceSpec("gas.plasma_fog", "gas", "电浆雾", "#7ee8c0",
                    "低亮青绿；浓度 ≥6 有 1 格机械光，随气团消散变化",
                    radius=1.8, brightness=0.26, mechanical=True, min_gas=6),
    # ---- §12 F：三种新增环境设施（2026-10-20）----
    # 与 D 批「只表现不照路」的墙类来源不同，这三条**有真实的机械照明**
    # （投放时写入 cell.light_radius），因此 mechanical=True；但亮灭一律跟随
    # 各自的真实状态，不允许「登记了就恒亮」：
    #   · 嵌壁梦灯 —— 玩家开关（sight.toggle_light），关掉即暗；
    #   · 弧光灯架 —— 绑定电路通电（core/fixtures.sync_light_fixtures），断电即灭；
    #   · 余烬灯盏 —— 只有 cell.flame>0 才发光，烧尽/被浇水熄灭即暗。
    LightSourceSpec("wall.dream_niche_lamp", "wall", "嵌壁梦灯", "#f2e3bd",
                    "暖米色小灯 2 格；站邻格可开关，打碎即灭，不冒充永久火把",
                    radius=2.0, brightness=0.44, mechanical=True, switchable=True),
    LightSourceSpec("wall.arc_lamp_rig", "wall", "弧光灯架", "#cfe4f2",
                    "冷白略青 2—3 格；只跟真实通电状态，断电即灭、不额外供能",
                    radius=2.2, brightness=0.48, mechanical=True, switchable=True),
    LightSourceSpec("wall.ember_lamp", "wall", "余烬灯盏", "#d8a15e",
                    "橙暖 2 格；只在真实燃烧时发光，复用既有燃料/点燃/灭火",
                    radius=2.0, brightness=0.42, mechanical=True),
)

@dataclass(frozen=True)
class LightFlashSpec:
    """§12.4.3 末行：激活类环境的**一次短光**（不是常驻来源）。

    与 :class:`LightSourceSpec` 分开登记，因为两者的生命周期不同：

    * 常驻来源由 ``light_spec_for_cell`` 逐格判定，只要材料/开关状态成立就一直在；
    * 短光只在「既有激活动作真的发生」的那一瞬存在，之后按 ``life`` 秒衰完。

    显影方尖的「永久显影」是**地图知识**，不是照明；符文墙每次感知后有冷却
    （``logic.RUNE_SENSOR_COOLDOWN``）。所以二者都不能登记成常亮灯——把
    「永久显影」当永久强灯会把一方尖变成免费火把（docs §4.3 最后一行）。
    """

    flash_id: str
    kind: str          # develop / rune：激活动作的稳定标识
    wall_kind: str     # 触发它的墙体种类（说明用，渲染不查它）
    color: str
    radius: float      # 表现半径（格）；不参与机械照明
    brightness: float  # 与 effects.TORCH_BRIGHTNESS 同量纲
    life: float        # 短光总时长（秒，墙钟）
    note: str = ""


FLASHES: tuple[LightFlashSpec, ...] = (
    LightFlashSpec("wall.develop_obelisk.flash", "develop", "显影方尖", "#dfe9ff",
                   radius=3.0, brightness=0.46, life=0.9,
                   note="点亮瞬间的一次冷白短光；永久显影属于地图知识，不是常亮灯"),
    LightFlashSpec("wall.rune_sensor.flash", "rune", "感应符文墙", "#9fe0ff",
                   radius=2.0, brightness=0.34, life=0.55,
                   note="感知触发的一次青白短光；冷却内不重复，没有感知就完全不亮"),
)

_BY_FLASH_KIND = {spec.kind: spec for spec in FLASHES}
_BY_KIND_KEY = {(spec.kind, spec.key): spec for spec in SOURCES}


def source_spec(kind: str, key: str) -> LightSourceSpec | None:
    return _BY_KIND_KEY.get((kind, str(key)))


def plant_light_color(code: int) -> str | None:
    spec = source_spec("plant", code)
    return spec.color if spec else None


def wall_light_color(wall_kind: str) -> str | None:
    spec = source_spec("wall", wall_kind)
    return spec.color if spec else None


def liquid_light_color(liquid_kind: str) -> str | None:
    spec = source_spec("liquid", liquid_kind)
    return spec.color if spec else None


def gas_light_color(gas_kind: str) -> str | None:
    spec = source_spec("gas", gas_kind)
    return spec.color if spec else None


def light_spec_for_cell(cell) -> "LightSourceSpec | None":
    """一格上「该由哪个登记来源发光」（植物 → 液体 → 气体 → 墙体）。

    渲染与生成报告共用这一份判定，避免两处口径不同：未登记不发光、
    液体看存量门槛、气体看浓度门槛（§12.4.1、§12.4.3）。

    墙类来源统一要求 ``cell.light_on``（关闭的灯箱、断电的灯架、熄灭的灯盏
    都不算来源）；余烬灯盏这种「按火发光」的设施还额外要求 ``cell.flame>0``——
    火焰才是它的燃料状态，开关对火没有意义（§12 F）。
    """
    if getattr(cell, "plant", 0):
        spec = source_spec("plant", int(cell.plant))
        if spec is not None:
            return spec
    liquid = getattr(cell, "liquid", 0)
    if getattr(cell, "liquid_kind", "") and liquid > 0:
        spec = source_spec("liquid", cell.liquid_kind)
        if spec is not None and liquid >= spec.min_amount:
            return spec
    gas = getattr(cell, "gas", 0)
    if getattr(cell, "gas_kind", "") and gas > 0:
        spec = source_spec("gas", cell.gas_kind)
        if spec is not None and gas >= spec.min_gas:
            return spec
    if getattr(cell, "solid", False) and getattr(cell, "wall_kind", ""):
        spec = source_spec("wall", cell.wall_kind)
        if spec is None or not getattr(cell, "light_on", True):
            return None
        from ..materials import FLAME_FIXTURE_KINDS
        if cell.wall_kind in FLAME_FIXTURE_KINDS and getattr(cell, "flame", 0) <= 0:
            return None
        return spec
    return None


def switchable_ids() -> tuple[str, ...]:
    """亮灭跟随真实状态的来源（生成报告列「开关状态」用，不是运行时上限）。"""
    return tuple(spec.source_id for spec in SOURCES if spec.switchable)


def flash_spec(kind: str) -> LightFlashSpec | None:
    """激活短光登记（develop / rune）；未登记 = 不播任何短光。"""
    return _BY_FLASH_KIND.get(str(kind))


def flash_ids() -> tuple[str, ...]:
    return tuple(spec.flash_id for spec in FLASHES)


def style(kind: str, key) -> tuple[str, float, float] | None:
    """(光色, 表现半径, 光池亮度)；未登记来源返回 None。

    调用方不得在 None 时改用材质色补齐——「有材料名」不等于「已经接入光照」
    （docs §12.4.1）。渲染侧只消费本函数，材料表不再是隐式光源登记表。
    """
    spec = source_spec(kind, key)
    if spec is None:
        return None
    return spec.color, spec.radius, spec.brightness


def source_id(kind: str, key) -> str:
    """稳定身份：同格多来源只按它去重，不按位置去重。"""
    spec = source_spec(kind, key)
    return spec.source_id if spec else f"{kind}.{key}"
