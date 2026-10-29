"""UI-only limits for existing animations; never suppress real world markers."""
import colorsys
from dataclasses import replace
from functools import lru_cache

from ..data.visual_catalog import RECIPES, stage_index
from .visual_frame import GlyphLayer, VisualFrame
from .visual_semantics import (palette_for_visual, palette_layer_color,
                               visual_family)

QUALITY_BUDGET = {"high": (2, 32), "low": (1, 32), "off": (0, 0)}
DETAIL_LIMIT = {"high": 2, "low": 1, "off": 0}
ACTIVE_LIMIT = {"high": 20, "low": 16, "off": 0}
ROUTINE_SECONDS = 0.35
_ROUND_GLYPHS = frozenset(".·,oO0○◦")
ROUTINE_CELLS = {"high": 2, "low": 1, "off": 0}


def allows_event_trigger(event, recipe):
    """Only meaningful changes start optional playback; live warnings stay intact."""
    if any(layer.clock_mode == "turn" for layer in recipe.layers):
        return True
    kind = str(getattr(event, "kind", ""))
    if kind in ("plant.absorb", "plant.flow", "plant.purify", "environment.move",
                "environment.safe", "environment.dud"):
        return False
    if kind not in ("plant.periodic", "environment.trigger"):
        return True
    facts = dict(getattr(event, "facts", ()) or ())
    if kind == "plant.periodic":
        spent = facts.get("spent", 0)
        return (facts.get("left") == 0 and isinstance(spent, (int, float)) and spent > 0)
    return facts.get("result") != "empty"


def limit_routine_footprint(frame, recipe, event, stage, quality, *, tier=None):
    """Keep frequent feedback local; do not crop charge or true turn markers."""
    if frame.is_empty or stage == "entry" or not is_routine(recipe, tier):
        return frame
    limit = ROUTINE_CELLS.get(quality, 1)
    per_cell = 2 if quality == "high" else 1
    glyphs, optional = {}, {}
    for cell, layers in frame.glyph_layers.items():
        for layer in layers:
            if layer.clock_mode == "turn":
                glyphs.setdefault(cell, []).append(layer)
            else:
                optional.setdefault(cell, []).append(layer)
    targets = getattr(event, "targets", ()) or getattr(event, "affected_cells", ())
    paths = getattr(event, "paths", ()) or ()
    endpoints = [path[-1] for path in paths if len(path) > 1]
    focus = endpoints[0] if endpoints else (targets[0] if targets else getattr(event, "center", None) or getattr(event, "source", None) or (0, 0))
    cells = sorted(optional, key=lambda cell: (max(abs(cell[0]-focus[0]), abs(cell[1]-focus[1])), cell))
    for cell in cells[:limit]:
        layers = sorted(optional[cell], key=lambda layer: (-layer.z, -layer.alpha))
        glyphs.setdefault(cell, []).extend(layers[:per_cell])
    return VisualFrame({cell: tuple(layers) for cell, layers in glyphs.items()}, dict(frame.backgrounds))


def is_routine(recipe, tier=None):
    # Extensions/custom test catalogs retain their contract. High-frequency
    # system feedback is compact even when its old recipe claimed V2.
    key = recipe.visual_key
    if key.startswith(("plant.", "circuit.", "equipment.", "environment.")):
        return True
    return (key in RECIPES or key.startswith("profile.")) and (
        recipe.tier if tier is None else tier) <= 1


def playback_recipe(recipe, tier=None, kind=""):
    tier = recipe.tier if tier is None else tier
    if kind.startswith(("plant.", "circuit.", "equipment.", "environment.")):
        tier = min(1, tier)  # Procs may reuse a Boss recipe; they are still routine.
    duration = recipe.duration
    if is_routine(recipe, tier) and not any(l.clock_mode == "turn" for l in recipe.layers):
        duration = min(duration, ROUTINE_SECONDS)
    return replace(recipe, tier=tier, duration=duration)


def playback_layers(recipe, stage, *, tier=None, minimal=False):
    layers = recipe.layers_at(stage)
    if not minimal and not is_routine(recipe, tier):
        return layers
    turns = tuple(l for l in layers if l.clock_mode == "turn")
    candidates = [l for l in layers if l.clock_mode != "turn" and l.role != "ambient"
                  and l.clock_mode != "decorative"]
    if stage != "entry":
        candidates = [l for l in candidates if l.requires_stage != "entry"] or [
            l for l in candidates if not l.requires_stage]
    if not candidates:
        return turns
    layer = max(candidates, key=lambda candidate: stage_index(candidate.requires_stage or "release"))
    if minimal or stage == "entry" or layer.primitive in (
            "orbit_ring", "inward_spiral", "implosion_burst", "shock_front"):
        # Routine radial effects are a short mark on settled result cells;
        # shrinking their particle radius would hide every spark under source.
        return turns + (replace(layer, primitive="steady_glyph", params=(("life", 1.0),)),)
    params = dict(layer.params)
    params.update(count=min(4, int(params.get("count", 4))),
                  radius=min(1.0, float(params.get("radius", 1.0))),
                  double=False, double_front=False, front=False, compact=True)
    if layer.primitive == "growth_reaction":
        params.update(shoots=1, spores=False)
    if layer.primitive == "arc_chain":
        params.update(trail_cells=2, head_count=1)
    layer = replace(layer, params=tuple(params.items()))
    return turns + (layer,)


def budget_frame(frame, quality, *, visible=None):
    """Fair main feedback first, then decoration; true turn markers stay intact.

    Turn layers are state information, not optional particles. They must not
    disappear because many settled effects fired during the same action.
    """
    per_cell, total = QUALITY_BUDGET.get(quality, QUALITY_BUDGET["low"])
    if not total:
        return VisualFrame()
    if visible is not None:
        visible = visible if isinstance(visible, (set, frozenset)) else frozenset(visible)
        frame = VisualFrame({cell: layers for cell, layers in frame.glyph_layers.items()
                             if cell in visible},
                            {cell: color for cell, color in frame.backgrounds.items()
                             if cell in visible})
    glyphs, groups = {}, {}
    for cell, layers in frame.glyph_layers.items():
        for layer in layers:
            if layer.clock_mode == "turn":
                glyphs.setdefault(cell, []).append(layer)
            else:
                groups.setdefault(layer.event_id, []).append((cell, layer))
    for group in groups.values():
        group.sort(key=lambda item: (item[1].role == "ambient", item[1].z < 10,
                                     -item[1].alpha, item[0], item[1].z))
    # One glyph for each root/event before allocating extra particles.
    used, counts = 0, {}
    for index in range(max((len(g) for g in groups.values()), default=0)):
        for group in groups.values():
            if index >= len(group):
                continue
            cell, layer = group[index]
            if counts.get(cell, 0) >= per_cell:
                continue
            glyphs.setdefault(cell, []).append(layer)
            counts[cell] = counts.get(cell, 0) + 1
            used += 1
            if used >= total:
                return _pack_frame(VisualFrame(
                    {c: tuple(ls) for c, ls in glyphs.items()}, dict(frame.backgrounds)), quality)
    return _pack_frame(VisualFrame(
        {c: tuple(ls) for c, ls in glyphs.items()}, dict(frame.backgrounds)), quality)


def _pack_frame(frame, quality):
    """Keep at most 1/2 marks per tile and separate paired image glyphs."""
    limit = 2 if quality == "high" else 1
    glyphs = {}
    for cell, layers in frame.glyph_layers.items():
        if len(layers) <= 1:
            glyphs[cell] = layers
            continue
        if (limit == 2 and len(layers) == 2
                and {round(layer.offset[0], 2) for layer in layers} == {-.28, .28}
                and all(layer.scale <= .44 for layer in layers)):
            glyphs[cell] = layers
            continue
        # Keep actual state first, then primary/high-z foreground marks.
        ordered = sorted(enumerate(layers), key=lambda item: (
            item[1].clock_mode != "turn", item[1].role == "ambient",
            -item[1].z, item[0]))
        kept = [layer for _index, layer in ordered[:limit]]
        if len(kept) == 2:
            kept = [replace(layer, offset=(-.28, layer.offset[1]),
                            scale=min(layer.scale, .44)) for layer in kept[:1]] + [
                    replace(kept[1], offset=(.28, kept[1].offset[1]),
                            scale=min(kept[1].scale, .44))]
        if kept:
            glyphs[cell] = tuple(kept)
    return VisualFrame(glyphs, dict(frame.backgrounds))


def static_feedback(recipe, event, stage, progress):
    """Existing steady-glyph fallback, one actual result cell, zero particles."""
    layers = recipe.layers_at(stage)
    if any(l.clock_mode == "turn" for l in layers):
        return None  # The normal sampler must retain every true turn layer.
    layers = [l for l in layers if l.clock_mode == "settled" and l.role != "ambient"
              and (stage == "entry" or l.requires_stage != "entry")]
    if not layers:
        return VisualFrame()
    targets = getattr(event, "targets", ()) or getattr(event, "affected_cells", ())
    cell = targets[0] if targets else getattr(event, "source", None)
    if cell is None:
        return VisualFrame()
    layer = layers[0]
    glyph = next((c for c in (layer.charset or recipe.charset) if 32 < ord(c) < 127), "+")
    return VisualFrame({tuple(cell): (GlyphLayer(
        glyph, color=recipe.colors[0], alpha=max(.08, 1-.85*progress), z=layer.z,
        role=layer.role, event_id=str(getattr(event, "event_id", "")),
        clock_mode=layer.clock_mode),)})


def cast_tier(event):
    """Use already wired cast IDs; profile duration is not content importance."""
    from ..data.visual_catalog import CAST_RECIPE_ALIASES
    cast_id = str(event.get("cast_id") or "")
    cast_id = CAST_RECIPE_ALIASES.get(cast_id, cast_id)
    kind, _, content_id = cast_id.partition(":")
    if kind == "skill":
        from ..data.visual_tiers import tier_for_skill
        return tier_for_skill(content_id)
    if kind == "ability":
        from ..data.visual_tiers import tier_for_ability
        return tier_for_ability(content_id)
    return 1


def cast_recipe(event):
    theme = str(event.get("theme") or "")
    # 区域物品往往复用通用恢复/投掷 effect，旧数据因而没有 theme；cast_id
    # 保留了真实物品定义 id，可安全补回美术主题而不猜测玩法结果。
    if not theme:
        cast_id = str(event.get("cast_id") or "")
        kind, _, content_id = cast_id.partition(":")
        if kind == "item" and "." in content_id:
            family = content_id.partition(".")[0]
            if family in ("hospital", "library"):
                theme = family
    return _cast_recipe(str(event.get("profile") or ""), str(event.get("motion") or ""),
                        theme, cast_tier(event), str(event.get("cast_id") or ""))


@lru_cache(maxsize=256)
def _cast_recipe(profile, motion, theme, tier, cast_id=""):
    from ..data.visual_catalog import CAST_RECIPES, CAST_RECIPE_ALIASES, profile_recipe
    cast_id = CAST_RECIPE_ALIASES.get(cast_id, cast_id)
    key = CAST_RECIPES.get((cast_id, profile, motion))
    recipe = RECIPES[key] if key else profile_recipe(profile, motion, theme)
    return playback_recipe(recipe, tier)


@lru_cache(maxsize=256)
def _muted_color(body, shade, amount=.28):
    """Use actual muted RGB as character terminals do not blend alpha."""
    channels = [round(int(body[i:i+2], 16) * (1-amount)
                      + int(shade[i:i+2], 16) * amount) for i in (1, 3, 5)]
    return "#%02x%02x%02x" % tuple(channels)


@lru_cache(maxsize=128)
def _lift_theme_color(color, amount=.38):
    """Lighten dark theme inks in HLS so their authored hue stays visible."""
    rgb = tuple(int(color[i:i+2], 16) / 255 for i in (1, 3, 5))
    hue, lightness, saturation = colorsys.rgb_to_hls(*rgb)
    target = lightness + (0.72 - lightness) * min(1.0, max(0.0, amount) * 2)
    red, green, blue = colorsys.hls_to_rgb(hue, target, max(0.5, saturation))
    channels = [round(channel * 255) for channel in (red, green, blue)]
    return "#%02x%02x%02x" % tuple(channels)


def style_frame(frame, recipe, color_role="primary"):
    """Shared small-character styling; live state and warnings retain fidelity.

    Profile palettes historically put the bright peak first. Its authored body
    is the second color; ordinary recipes put their thematic body first.
    Bright color is reserved for explicitly authored accents, never alpha.
    """
    if frame is None or frame.is_empty:
        return VisualFrame()
    colors = recipe.colors or ("#9aa6b2", "#59636e")
    palette = palette_for_visual(recipe.visual_key, recipe.theme, colors=colors)
    family = visual_family(recipe.visual_key, recipe.theme)
    peak = palette[0]
    shade = palette[1] if len(palette) > 1 else palette[0]
    # Keep the authored theme hue: blending a cream peak into a blue ink shade
    # made signature animations neutral grey. Lift the actual body color instead.
    glyphs = {}
    for cell, layers in frame.glyph_layers.items():
        styled = []
        for index, layer in enumerate(layers):
            if layer.clock_mode == "turn" or layer.role in ("danger", "warning") or color_role == "danger":
                styled.append(layer)
                continue
            ambient = layer.role == "ambient"
            accent = color_role in ("accent", "bright") and recipe.tier >= 2
            color = palette_layer_color(palette, layer, cell, index,
                                        blast=family in ("blast", "fire"))
            if accent and layer.alpha >= .9:
                color = _lift_theme_color(peak, .08)
            elif (ambient or layer.alpha < .4) and family != "blast":
                color = _muted_color(color, shade, .35)
            body_alpha = .78 if recipe.tier >= 2 else .6
            styled.append(replace(layer, color=color,
                alpha=min(layer.alpha * (.4 if ambient else body_alpha), .22 if ambient else .6),
                scale=min(layer.scale, .6 if ambient else
                          .42 if layer.glyph in _ROUND_GLYPHS else .72)))
        glyphs[cell] = tuple(styled)
    return VisualFrame(glyphs, dict(frame.backgrounds))
