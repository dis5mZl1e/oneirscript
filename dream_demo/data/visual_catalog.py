"""分镜/等级/字符 recipe 登记（2026-10-26，ASCII 动画扩展 Task 4）。

每个 visual_key 登记一组 LayerRecipe：原语、clock_mode、阶段门槛、层级、
字符集与配色。配方只决定演出，不反写技能时长或玩法数据；默认时长/角色
复用 data/anomaly_skills.py 的 FX_PROFILES。
"""
from __future__ import annotations

from dataclasses import dataclass, field

TIERS = ("V0", "V1", "V2", "V3")
STAGE_ORDER = ("entry", "release", "impact", "tail")


def stage_index(stage: str) -> int:
    try:
        return STAGE_ORDER.index(stage)
    except ValueError:
        return len(STAGE_ORDER)
CLOCK_MODES = ("turn", "settled", "decorative")


@dataclass(frozen=True)
class LayerRecipe:
    primitive: str
    clock_mode: str = "settled"
    requires_stage: str = ""
    z: int = 0
    role: str = "fx"
    color_role: str = "primary"
    charset: str = ""
    alpha: float = 1.0
    scale: float = 1.0
    params: tuple = ()
    until_stage: str = ""

    def __post_init__(self):
        if self.clock_mode not in CLOCK_MODES:
            raise ValueError(f"未知 clock_mode: {self.clock_mode!r}")
        if self.requires_stage and self.requires_stage not in ("entry", "release", "impact", "tail"):
            raise ValueError(f"未知 requires_stage: {self.requires_stage!r}")
        if self.until_stage and self.until_stage not in STAGE_ORDER:
            raise ValueError(f"未知 until_stage: {self.until_stage!r}")
        if (self.requires_stage and self.until_stage
                and stage_index(self.until_stage) < stage_index(self.requires_stage)):
            raise ValueError("until_stage 不能早于 requires_stage")

    def visible_at(self, stage: str) -> bool:
        if self.until_stage and stage_index(stage) > stage_index(self.until_stage):
            return False
        if not self.requires_stage:
            return True
        return stage_index(stage) >= stage_index(self.requires_stage)


@dataclass(frozen=True)
class VisualRecipe:
    visual_key: str
    tier: int
    duration: float
    theme: str = ""
    charset: str = ".-:+*x/\\|<>()[]{}"
    colors: tuple = ("#f2dca0", "#8a6f3f")
    layers: tuple = ()
    library_components: tuple = ()
    fallback: str = "glyph"

    def layers_at(self, stage: str) -> tuple:
        return tuple(layer for layer in self.layers if layer.visible_at(stage))

    def stage_durations(self) -> tuple:
        return ("entry", "release", "impact", "tail")


def _layer(primitive, **kwargs) -> LayerRecipe:
    return LayerRecipe(primitive, **kwargs)


# --- 原语样板（Task 4 验收用；系统接入按同一 key 扩展） ---------------------
RECIPES = {
    "fx.spark": VisualRecipe(
        "fx.spark", 0, 0.35, charset="-+*", colors=("#ffce80", "#b27b42"),
        layers=(_layer("directional_dash", requires_stage="impact", z=10, charset="-+*"),),
        library_components=("asciimatics.particles.Particle",),
    ),
    "fx.impact": VisualRecipe(
        "fx.impact", 0, 0.25, charset="x+", colors=("#e6ecf2", "#596a82"),
        layers=(_layer("shock_front", requires_stage="impact", z=20, charset="x+",
                       params=(("radius", 1.0),)),),
        library_components=("asciimatics.particles.Particle",),
    ),
    "fx.explosion": VisualRecipe(
        "fx.explosion", 1, 0.7, theme="blast", charset="x/+", colors=("#ff3b38", "#75172c"),
        layers=(
            _layer("radial_spokes", z=10, charset="x/+"),
            _layer("shock_front", requires_stage="tail", z=15, charset="-:",
                   alpha=0.45, params=(("radius", 2.0), ("front", True))),
        ),
        library_components=("asciimatics.particles.Particle", "asciimatics.screen.TemporaryCanvas"),
    ),
    "fx.memory": VisualRecipe(
        "fx.memory", 1, 0.8, charset="+*.:", colors=("#dbc4ff", "#8763ad"),
        layers=(_layer("inward_spiral", z=10, charset="+*.", params=(("count", 20), ("radius", 4.0))),),
        library_components=("asciimatics.particles.Particle",),
    ),
    "cast.flame_nova": VisualRecipe(
        "cast.flame_nova", 2, 0.9, theme="flame", charset="^*+:.",
        colors=("#ffb066", "#a23a2a"),
        layers=(
            _layer("flame_rise", requires_stage="entry", z=5, charset="^/\\*"),
            _layer("radial_spokes", requires_stage="impact", z=10, charset="x/+"),
        ),
        library_components=("asciimatics.particles.Particle", "asciimatics.screen.TemporaryCanvas"),
    ),
    "cast.rewrite_corner": VisualRecipe(
        "cast.rewrite_corner", 3, 1.3, theme="paper", charset="/\\[]{}<>",
        colors=("#e8e2d0", "#4a5f8e"),
        layers=(
            _layer("aperture_fold", requires_stage="entry", until_stage="entry", z=5, charset="/\\[]",
                   params=(("corners", True),)),
            _layer("fracture_rebuild", requires_stage="release", z=10, charset="/\\[]{}",
                   params=(("rebuild", True),)),
        ),
        library_components=("asciimatics.particles.Particle", "asciimatics.screen.TemporaryCanvas"),
    ),
    "cast.fault_ring": VisualRecipe(
        "cast.fault_ring", 2, 0.95, theme="earth", charset="/\\|-_",
        colors=("#d9a066", "#5a4632"),
        layers=(
            _layer("aperture_fold", requires_stage="entry", until_stage="entry", z=5, charset="/\\[]",
                   params=(("corners", True),)),
            _layer("shock_front", requires_stage="release", z=10, charset="/\\|-_",
                   params=(("radius", 3.0), ("square", True), ("front", True))),
            _layer("slash_fan", requires_stage="impact", z=15, charset="/\\|",
                   params=(("count", 6),)),
        ),
        library_components=("asciimatics.particles.Particle", "asciimatics.screen.TemporaryCanvas"),
    ),
    "boss.core_cry": VisualRecipe(
        "boss.core_cry", 3, 1.25, theme="sound", charset=")~:.",
        colors=("#8fd8d8", "#3a4a58"),
        layers=(
            _layer("steady_glyph", requires_stage="entry", until_stage="entry", z=5,
                   charset=":~", params=(("life", 1.0),)),
            _layer("resonance_arcs", requires_stage="release", z=10, charset=")~",
                   params=()),
            _layer("resonance_arcs", requires_stage="tail", z=25,
                   role="ambient", charset="~", alpha=.35, params=(("echo", True),)),
        ),
        library_components=("asciimatics.particles.Particle", "asciimatics.screen.TemporaryCanvas"),
    ),
    "tamper.rewrite": VisualRecipe(
        "tamper.rewrite", 1, 0.6, theme="paper", charset="[]{}<>/\\",
        colors=("#e8e2d0", "#8a6f3f"),
        layers=(
            _layer("text_rewrite", requires_stage="entry", z=5, charset="[]{}<>",
                   params=(("old_glyphs", "旧字"), ("new_glyphs", "新字"))),
            _layer("fracture_rebuild", requires_stage="release", z=10, charset="[]{}/\\"),
        ),
        library_components=("asciimatics.particles.Particle",),
    ),
    "fold.travel": VisualRecipe(
        "fold.travel", 1, 0.6, theme="fold", charset="[[ ]] <>",
        colors=("#a6e1dc", "#4a5f8e"),
        layers=(
            _layer("aperture_fold", requires_stage="entry", z=5, charset="[]<>",
                   params=(("layout", "fold"),)),
            _layer("directional_dash", requires_stage="release", z=10, charset="->="),
        ),
        library_components=("asciimatics.particles.Particle",),
    ),
    "plant.growth": VisualRecipe(
        "plant.growth", 1, 0.55, theme="plant", charset="v^/\\,.",
        colors=("#a9cc84", "#3c5a35"),
        layers=(
            _layer("growth_reaction", requires_stage="impact", z=10, charset="v^/\\,."),
        ),
        library_components=("asciimatics.particles.Particle",),
    ),
    # ---- 植物被破坏时的释出反应（docs 2026-10-26 §11）-------------------
    # 全部按 settled 登记：释出在同一次结算里已经定稿，按视觉时钟一次播完，
    # 展示有效格恒等于真实结算值。这里不登记 turn 层——跨回合才变化的燃烧、
    # 电场、气液扩散由各自既有的通道逐真实回合显示，重复登记会补演未发生的
    # 传播。七个键按通道分开，是为了「关掉特效也要认得出是哪一种」。
    "plant.release.gas": VisualRecipe(
        "plant.release.gas", 1, 0.6, theme="plant", charset="~oO.:",
        colors=("#b7d98a", "#3c5a35"),
        layers=(
            _layer("falling_veil", z=10, charset=",;:"),
        ),
        library_components=("asciimatics.particles.Particle",),
    ),
    "plant.release.liquid": VisualRecipe(
        "plant.release.liquid", 1, 0.55, theme="plant", charset=",;:~.",
        colors=("#8fc7e8", "#31556b"),
        layers=(
            _layer("directional_dash", z=10, charset=",;~"),
        ),
        library_components=("asciimatics.particles.Particle",),
    ),
    "plant.release.fire": VisualRecipe(
        "plant.release.fire", 2, 0.75, theme="fire", charset="*^v/\\",
        colors=("#ffb066", "#8a3b1e"),
        layers=(
            _layer("flame_rise", z=10, charset="^/\\*"),
        ),
        library_components=("asciimatics.particles.Particle",),
    ),
    "plant.release.electric": VisualRecipe(
        "plant.release.electric", 2, 0.5, theme="electric", charset="/\\|-+~",
        colors=("#91e7ef", "#2d5a6e"),
        layers=(
            _layer("arc_chain", z=10, charset="/\\|-+~"),
        ),
        library_components=("asciimatics.particles.Particle",),
    ),
    "plant.release.integrity": VisualRecipe(
        "plant.release.integrity", 1, 0.55, theme="stone", charset="\\/x#",
        colors=("#c9c2b4", "#5d5648"),
        layers=(
            _layer("fracture_rebuild", z=10, charset="\\/x#"),
        ),
        library_components=("asciimatics.particles.Particle",),
    ),
    "plant.release.snare": VisualRecipe(
        "plant.release.snare", 1, 0.7, theme="plant", charset="()<>=+",
        # 收紧的括线：被缚是可移动受限，不是减速——所以用闭合而非乱跳。
        colors=("#d7b6ea", "#4c3468"),
        layers=(
            _layer("aperture_fold", z=20, charset="()<>=+",
                   params=(("radius", 1.0), ("layout", "bind"))),
        ),
        library_components=("asciimatics.particles.Particle",),
    ),
    "plant.release.push": VisualRecipe(
        "plant.release.push", 1, 0.5, theme="plant", charset="->=~.",
        colors=("#a6e1dc", "#2f5f5b"),
        layers=(
            _layer("directional_dash", z=10, charset="->=~"),
        ),
        library_components=("asciimatics.particles.Particle",),
    ),
    # 2026-10-26 用户实测：踏入时的「减声括号／慢行缠线」提示动画观感差、
    # 又只是把格子详情里已有的数字再演一遍，已整体下线（连同装饰层轻摆）。
    # 减声与加时本身照旧结算，只是不再有这层字——不要把它们加回来。
    "plant.absorb": VisualRecipe(
        # 常驻吸收：只对**真实被扣掉 1 单位的源格**画一次收束，不铺满 R1。
        "plant.absorb", 0, 0.4, theme="plant", charset=".,'`",
        colors=("#cfe3b1", "#41592f"),
        layers=(
            _layer("inward_spiral", z=10, charset=".,'`",
                   params=(("count", 4), ("radius", 1.0))),
        ),
        library_components=("asciimatics.particles.Particle",),
    ),
    "plant.flow": VisualRecipe(
        # 搬气：源格到目标格的一条流线，挡住的格在这里根本不出现。
        "plant.flow", 0, 0.35, theme="plant", charset="->=.",
        colors=("#a6e1dc", "#2f5f5b"),
        layers=(
            _layer("shock_front", z=10, charset="->=.", params=(("radius", 1.0),)),
        ),
        library_components=("asciimatics.particles.Particle",),
    ),
    "plant.purify": VisualRecipe(
        # 净化达标：目标身上的一次「+」收束印记。没有可洗目标时不发事件。
        "plant.purify", 0, 0.5, theme="plant", charset="+.",
        colors=("#e8f0c9", "#5a6a3c"),
        layers=(
            _layer("steady_glyph", z=20, charset="+",
                   params=(("life", 0.5),)),
            _layer("inward_spiral", z=15, charset=".+",
                   params=(("count", 5), ("radius", 1.0))),
        ),
        library_components=("asciimatics.particles.Particle",),
    ),
    "circuit.arc": VisualRecipe(
        "circuit.arc", 1, 0.5, theme="electric", charset="/\\|-+~",
        colors=("#91e7ef", "#2d5a6e"),
        layers=(
            _layer("arc_chain", requires_stage="impact", z=10, charset="/\\|-+~"),
        ),
        library_components=("asciimatics.particles.Particle",),
    ),
    "boss.core_beacon": VisualRecipe(
        "boss.core_beacon", 3, 1.3, theme="light", charset="|/\\+",
        colors=("#fffef2", "#bbcbe0"),
        layers=(
            _layer("steady_glyph", requires_stage="entry", until_stage="entry", z=5,
                   charset=":+", params=(("life", 1.0),)),
            _layer("beacon_signal", requires_stage="release", z=10, charset="|/\\+"),
        ),
        library_components=("asciimatics.particles.Particle", "asciimatics.screen.TemporaryCanvas"),
    ),
    "boss.scribe_stroke": VisualRecipe(
        "boss.scribe_stroke", 3, 1.2, theme="ink", charset="/\\|-_<>",
        colors=("#e8e2d0", "#2e3a66"),
        layers=(
            _layer("steady_glyph", requires_stage="entry", until_stage="entry", z=5,
                   charset="_:", params=(("life", 1.0),)),
            _layer("slash_fan", requires_stage="release", until_stage="impact", z=10, charset="/\\|-",
                   params=(("count", 3), ("cross", True))),
            _layer("text_rewrite", requires_stage="tail", z=30,
                   role="ambient", charset="_-", alpha=.3),
        ),
        library_components=("asciimatics.particles.Particle", "asciimatics.screen.TemporaryCanvas"),
    ),
    "boss.scribe_erase": VisualRecipe(
        "boss.scribe_erase", 2, 1.0, theme="ink", charset="_-[ ]",
        colors=("#b8a888", "#10131f"),
        layers=(
            _layer("aperture_fold", requires_stage="entry", until_stage="entry", z=5, charset="[]",
                   params=(("layout", "bind"),)),
            _layer("fracture_rebuild", requires_stage="release", z=10, charset="_-",
                   params=(("rebuild", False),)),
        ),
        library_components=("asciimatics.particles.Particle",),
    ),
    "library.last_page": VisualRecipe(
        "library.last_page", 3, 1.35, theme="library", charset="/\\|<>[]",
        colors=("#d5c294", "#2e3a66"),
        layers=(
            _layer("aperture_fold", requires_stage="entry", until_stage="entry", z=5, charset="[]<>",
                   params=(("layout", "fold"),)),
            _layer("text_rewrite", requires_stage="release", until_stage="impact", z=10,
                   charset="/|\\", params=(("mode", "page"),)),
            _layer("text_rewrite", requires_stage="tail", z=30,
                   role="ambient", charset="/|\\", alpha=.3, params=(("mode", "page"),)),
        ),
        library_components=("asciimatics.particles.Particle", "asciimatics.screen.TemporaryCanvas"),
    ),
    "hospital.core_infusion": VisualRecipe(
        "hospital.core_infusion", 2, 0.95, theme="hospital", charset="|~:.",
        colors=("#a6e1dc", "#2d5a6e"),
        layers=(
            _layer("inward_spiral", requires_stage="entry", until_stage="entry", z=5, charset=".o+",
                   alpha=0.8, params=(("count", 10), ("radius", 2.5))),
            _layer("falling_veil", requires_stage="release", z=10, charset="|:.",
                   params=(("drip", True),)),
        ),
        library_components=("asciimatics.particles.Particle",),
    ),
    "cast.pixel_surge": VisualRecipe(
        "cast.pixel_surge", 1, 0.7, theme="pixel", charset="[]{}<>/\\#",
        colors=("#c8a86a", "#8763ad"),
        layers=(
            _layer("fracture_rebuild", requires_stage="release", z=10, charset="[]{}<>",
                   params=(("rebuild", True),)),
            _layer("implosion_burst", requires_stage="impact", z=15, charset="#*+",
                   params=(("count", 12), ("radius", 2.0))),
        ),
        library_components=("asciimatics.particles.Particle",),
    ),
    # ---- 环境机关：用机关本身的动作轮廓，避免继续借用植物/爆炸通用动画。----
    "environment.bolt_trap": VisualRecipe(
        "environment.bolt_trap", 1, 0.42, theme="mechanism", charset="->=|",
        colors=("#f4d48a", "#745637"),
        layers=(
            _layer("directional_dash", z=15, charset="->=", params=(("trail_cells", 2),)),
            _layer("steady_glyph", requires_stage="impact", z=20, charset="x+",
                   params=(("life", 0.28),)),
        ),
        library_components=("asciimatics.particles.Particle",),
    ),
    "environment.gas_vent": VisualRecipe(
        "environment.gas_vent", 1, 0.48, theme="gas", charset="~:;.",
        colors=("#b9d27d", "#405b36"),
        layers=(
            _layer("falling_veil", z=10, charset="~;:", params=(("radius", 1.5),)),
            _layer("shock_front", requires_stage="impact", z=15, charset=".:~",
                   params=(("radius", 1.5), ("front", True))),
        ),
        library_components=("asciimatics.particles.Particle",),
    ),
    "environment.cage_lock": VisualRecipe(
        "environment.cage_lock", 1, 0.5, theme="mechanism", charset="[]|=+",
        colors=("#d8c99b", "#59636e"),
        layers=(
            _layer("aperture_fold", z=15, charset="[]|=", params=(("layout", "bind"),)),
            _layer("steady_glyph", requires_stage="impact", z=20, charset="+",
                   params=(("life", 0.3),)),
        ),
        library_components=("asciimatics.particles.Particle",),
    ),
    "environment.stone_lock": VisualRecipe(
        "environment.stone_lock", 2, 0.65, theme="stone", charset="/\\|_#",
        colors=("#d0c3a8", "#574e43"),
        layers=(
            _layer("fracture_rebuild", z=10, charset="/\\|_",
                   params=(("rebuild", True),)),
            _layer("shock_front", requires_stage="impact", z=15, charset="_#",
                   params=(("radius", 1.5), ("square", True))),
        ),
        library_components=("asciimatics.particles.Particle",),
    ),
    "environment.reveal_scan": VisualRecipe(
        "environment.reveal_scan", 1, 0.55, theme="signal", charset=".-|:",
        colors=("#8fd8d8", "#304b59"),
        layers=(
            _layer("resonance_arcs", z=10, charset=".-|", params=(("radius", 2.0),)),
        ),
        library_components=("asciimatics.particles.Particle",),
    ),
    "environment.summon_seam": VisualRecipe(
        "environment.summon_seam", 1, 0.58, theme="void", charset="<>[]/\\",
        colors=("#c9b8e8", "#43365d"),
        layers=(
            _layer("aperture_fold", z=10, charset="<>[]", params=(("open_close", True),)),
            _layer("inward_spiral", requires_stage="impact", z=15, charset="./\\",
                   params=(("count", 6), ("radius", 1.5))),
        ),
        library_components=("asciimatics.particles.Particle",),
    ),
    "default": VisualRecipe(
        "default", 1, 0.5, charset=".-:+*",
        colors=("#f2dca0", "#8a6f3f"),
        layers=(
            _layer("shock_front", z=10, charset=".-:+*", params=(("radius", 2.0),)),
        ),
        library_components=("asciimatics.particles.Particle",),
    ),
}


# Select authored animation only for its known content/profile/motion tuple.
# A mod or extension changing the motion keeps its own profile choreography.
CAST_RECIPES = {
    ("skill:core_cry", "sound", "wave"): "boss.core_cry",
    ("skill:core_beacon", "needle", "line"): "boss.core_beacon",
    ("skill:scribe_stroke", "needle", "line"): "boss.scribe_stroke",
    ("skill:scribe_erase", "terrain", "terrain"): "boss.scribe_erase",
    ("skill:library.last_page", "needle", "page"): "library.last_page",
    ("skill:hospital.core_infusion", "field", "drip"): "hospital.core_infusion",
    ("ability:flame_nova", "blast", "blast"): "cast.flame_nova",
    ("ability:rewrite_corner", "terrain", "terrain"): "cast.rewrite_corner",
    ("ability:combat.fault_ring", "blast", "blast"): "cast.fault_ring",
    ("ability:pixel_surge", "terrain", "terrain"): "cast.pixel_surge",
}

CAST_RECIPE_ALIASES = {"skill:library.last_page:second": "skill:library.last_page"}


# cast.motion -> primitive 的默认分层；供旧 cast_fx 适配与新视觉事件共享。
MOTION_PRIMITIVES = {
    "line": "directional_dash", "needle": "directional_dash",
    "projectile": "directional_dash", "push": "directional_dash",
    "arc": "arc_chain", "electric": "arc_chain", "chain": "arc_chain",
    "cut": "slash_fan", "slash": "slash_fan",
    "wave": "resonance_arcs", "blast": "radial_spokes", "fire": "flame_rise",
    "frost": "frost_facets", "mist": "falling_veil", "poison": "falling_veil",
    "spread": "shock_front", "wash": "shock_front",
    "pull": "inward_spiral", "gather": "inward_spiral", "summon": "aperture_fold",
    "fold": "aperture_fold", "teleport": "aperture_fold",
    "terrain": "fracture_rebuild", "erase": "fracture_rebuild", "ink": "text_rewrite",
    "grow": "growth_reaction", "drip": "falling_veil", "spore": "growth_reaction",
    "page": "text_rewrite", "scan": "directional_dash", "shift": "aperture_fold",
}


# Motion-first cast choreography. Entries specify authored silhouette and glyph
# vocabulary; there is deliberately no default ring or generic particle tail.
_MOTION_LAYERS = {
    "line": (("directional_dash", "release", "->=", ()),),
    "needle": (("directional_dash", "release", "->=", ()),),
    "projectile": (("directional_dash", "release", "->=", ()),),
    "push": (("directional_dash", "release", ">-=", ()),),
    "pull": (("inward_spiral", "release", ".+", (("count", 8), ("radius", 2.0))),),
    "gather": (("inward_spiral", "release", ".+*", (("count", 8), ("radius", 2.0))),),
    "wave": (("resonance_arcs", "release", ")~", ()),),
    "sound": (("resonance_arcs", "release", ")~", ()),),
    "scan": (("directional_dash", "release", ".-|", ()),),
    "fire": (("flame_rise", "release", "^/\\*", ()),),
    "blast": (("radial_spokes", "release", "x/+", ()),),
    "electric": (("arc_chain", "release", "/\\~", (("head", True),)),),
    "arc": (("arc_chain", "release", "/\\~", (("head", True),)),),
    "chain": (("arc_chain", "release", "/\\~", (("head", True),)),),
    "frost": (("frost_facets", "release", "<>/\\", ()),),
    "mist": (("falling_veil", "release", ",;:", ()),),
    "poison": (("falling_veil", "release", ",;:", ()),),
    "spread": (("shock_front", "release", "-:=", (("front", True),)),),
    "wash": (("shock_front", "release", "~.:", (("front", True),)),),
    "cut": (("slash_fan", "release", "/\\", (("count", 3),)),),
    "slash": (("slash_fan", "release", "/\\", (("count", 3),)),),
    "bind": (("aperture_fold", "release", "()<>", (("layout", "bind"),)),),
    "hex": (("aperture_fold", "release", "[]<>/\\", (("layout", "bind"),)),),
    "fold": (("aperture_fold", "release", "[]<>", (("layout", "fold"),)),),
    "teleport": (("aperture_fold", "release", "[]<>", (("layout", "fold"),)),),
    "summon": (("aperture_fold", "release", "[]{}", (("layout", "seam"),)),),
    "shift": (("aperture_fold", "release", "[]<>", (("layout", "fold"),)),),
    "terrain": (("fracture_rebuild", "release", "/\\|_", (("rebuild", True),)),),
    "grow": (("growth_reaction", "release", "v^/\\", (("shoots", 2), ("spores", False))),),
    "drip": (("falling_veil", "release", "|:.", ()),),
    "ink": (("text_rewrite", "release", "[]{}<>/\\", ()),),
    "erase": (("fracture_rebuild", "release", "_-", (("rebuild", False),)),),
    "page": (("text_rewrite", "release", "[]<>/", (("mode", "page"),)),),
    "reveal": (("frost_facets", "release", ".-|", ()),),
    "terrain_scan": (("resonance_arcs", "release", ".-|", ()),),
}


# 同一种 motion 在不同世界主题中不应长得一样。这里保留已有原语和预算，
# 只重编排轮廓：医院是滴注/缝合/扫描，图书馆是页边/墨线/删改。
_THEME_MOTION_LAYERS = {
    ("hospital", "drip"): (
        ("falling_veil", "release", "|:.", (("radius", 1.5),)),
        ("inward_spiral", "impact", ".+", (("count", 6), ("radius", 1.5))),
    ),
    ("hospital", "scan"): (
        ("directional_dash", "release", "-->", (("trail_cells", 2),)),
        ("resonance_arcs", "impact", ".-|", (("radius", 1.5),)),
    ),
    ("hospital", "wash"): (
        ("shock_front", "release", "~.:", (("radius", 2.0), ("front", True))),
        ("frost_facets", "impact", "+<>", (("radius", 1.0),)),
    ),
    ("hospital", "gather"): (
        ("inward_spiral", "release", ".:+", (("count", 6), ("radius", 1.5))),
        ("steady_glyph", "impact", "+", (("life", 0.35),)),
    ),
    ("library", "page"): (
        ("text_rewrite", "release", "[]<>/", (("mode", "page"),)),
        ("slash_fan", "impact", "/\\", (("count", 1), ("radius", 1.5))),
    ),
    ("library", "ink"): (
        ("directional_dash", "release", "-=>", (("trail_cells", 2),)),
        ("text_rewrite", "impact", "{}[]", (("old_glyphs", "."), ("new_glyphs", "#"))),
    ),
    ("library", "erase"): (
        ("aperture_fold", "release", "[]", (("open_close", False),)),
        ("fracture_rebuild", "impact", "_-", (("rebuild", False),)),
    ),
    ("library", "fold"): (
        ("aperture_fold", "release", "[]<>", (("layout", "fold"),)),
        ("directional_dash", "impact", ">>=", (("trail_cells", 1),)),
    ),
}


_RECIPE_CACHE: dict = {}


def recipe_for(visual_key: str) -> VisualRecipe:
    cached = _RECIPE_CACHE.get(visual_key)
    if cached is not None:
        return cached
    if visual_key in RECIPES:
        recipe = RECIPES[visual_key]
    elif visual_key.startswith("profile."):
        parts = visual_key.split(".")
        recipe = profile_recipe(parts[1], parts[2] if len(parts) > 2 else "")
    else:
        recipe = RECIPES["default"]
    _RECIPE_CACHE[visual_key] = recipe
    return recipe


def tier_from_seconds(seconds: float) -> int:
    if seconds < 0.35:
        return 0
    if seconds < 0.7:
        return 1
    if seconds < 1.05:
        return 2
    return 3


def profile_recipe(profile_id: str, motion: str = "", theme: str = "") -> VisualRecipe:
    """把现有 FxProfile 映射成新 recipe（真实内容覆盖的分母）。"""
    from ..data.anomaly_skills import FX_PROFILES

    profile = FX_PROFILES.get(profile_id)
    if profile is None:
        return RECIPES["default"]
    duration = float(profile.entry_seconds + profile.cast_seconds + profile.tail_seconds)
    choreography = _THEME_MOTION_LAYERS.get((theme or "", motion or ""))
    if choreography is None:
        choreography = _MOTION_LAYERS.get(motion or "")
    charset = profile.particle_char or ".-:+*"
    if choreography is None:
        primitive = MOTION_PRIMITIVES.get(motion or "", "shock_front")
        choreography = ((primitive, "release", charset,
                         (("count", max(4, profile.cast_cells_high)), ("radius", 2.0))),)
    layers = (_layer("steady_glyph", requires_stage="entry", until_stage="entry",
                     z=5, charset=choreography[0][2], params=(("life", 1.0),)),) + tuple(
        _layer(primitive, requires_stage=stage, clock_mode="settled", z=10 + index * 5,
               charset=glyphs or charset, params=params,
               until_stage=(STAGE_ORDER[stage_index(choreography[index+1][1])-1]
                            if index+1 < len(choreography)
                            and stage_index(choreography[index+1][1]) > stage_index(stage) else ""))
        for index, (primitive, stage, glyphs, params) in enumerate(choreography)
    )
    charset = "".join(dict.fromkeys(char for layer in layers for char in layer.charset))
    return VisualRecipe(
        visual_key=f"profile.{profile_id}" + (f".{motion}" if motion else ""),
        tier=tier_from_seconds(duration),
        duration=max(0.2, duration),
        theme=theme or profile.color_role,
        charset=charset,
        colors=(profile.bright_hex, profile.color_hex),
        layers=layers,
        library_components=("asciimatics.particles.Particle",),
    )
