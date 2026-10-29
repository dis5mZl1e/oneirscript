"""原生地图图像层的只读场景准备与世界坐标采样。"""
from __future__ import annotations


class _PlaneMotion:
    def __init__(self):
        self._key = None
        self._source = self._target = ((0., 0.), (0., 0.))
        self._started = self._duration = 0.

    def update(self, layer, player, camera, cell_px, now, duration, animate):
        key = (layer, tuple(cell_px))
        target = (tuple(map(float, player)), tuple(map(float, camera)))
        previous = self.sample(now)
        if key == self._key and target == self._target and animate:
            return
        adjacent = all(max(abs(a-b) for a, b in zip(new, old)) <= 1
                       for new, old in zip(target, self._target))
        self._source = previous if key == self._key and adjacent and animate else target
        self._target = target
        self._started = now
        self._duration = max(0., duration) if self._source != target else 0.
        self._key = key

    def sample(self, now):
        fraction = min(1., max(0., (now-self._started)/self._duration)) if self._duration else 1.
        return tuple(tuple(a+(b-a)*fraction for a, b in zip(source, target))
                     for source, target in zip(self._source, self._target))

    def active(self, now):
        return self._duration > 0 and now < self._started+self._duration


def _compose_frame(canvas, origin, sprite, cell_px, player, camera, size):
    left, top = (round((camera[i]-origin[i])*cell_px[i]) for i in range(2))
    box = (left, top, left+size[0], top+size[1])
    if min(left, top) < 0 or box[2] > canvas.width or box[3] > canvas.height:
        raise ValueError('native camera outside permission-filtered guard canvas')
    image = canvas.crop(box)
    position = tuple(round((player[i]-camera[i])*cell_px[i]) for i in range(2))
    image.paste(sprite, position, sprite)
    return image


def _player_sprite(visual, cell_px, scale=.82):
    from PIL import Image
    from .map_presentation import glyph_mask_compatible, glyph_source, _ink_rgb
    value, mask = glyph_mask_compatible(visual.text, *cell_px, scale=scale)
    sprite = Image.new('RGBA', cell_px)
    if mask is None:
        return sprite
    if glyph_source(value)[1]:
        ink = mask.copy()
    else:
        ink = Image.new('RGBA', mask.size, _ink_rgb(visual.color))
        ink.putalpha(mask.getchannel('A'))
    sprite.alpha_composite(ink, ((cell_px[0]-ink.width)//2, (cell_px[1]-ink.height)//2))
    return sprite


def _build_native_packet(view, image):
    """仅为普通世界移动准备一格保护边；其它交互原样显示整张最终图。"""
    app, scene, state = view.app, view.shared_scene, view.state
    live = getattr(app, '_world_view_live', None)
    if live is None:  # 轻量假 App（单元测试）沿用旧的 world 判定
        live = lambda: getattr(app, 'panel_mode', 'world') == 'world'
    if (scene is None or state is None or not live()
            or app.aiming or app.observe_mode or app.layer_observation is not None
            or getattr(app, '_floor_transition', None) is not None
            # 右栏面板不再否决保护画布（2026-10-28）：~ 锁定页下方向键移动仍是
            # 世界移动，原生层若退回整幅 present 会丢掉相机/玩家插值、移动变跳。
            # 但左浮层/篡改编辑器会在地图上叠画，仍整幅 present，避免保护边露边。
            or getattr(app, '_left_panel_open', lambda: False)()
            or getattr(app, 'world_tamper_editor', None) is not None
            or not app.config.get('smooth_movement') or app.config.get('fx_reduce_motion')):
        return None
    player = next((pos for pos, cell in scene.cells.items()
                   if any(actor.relation == 'player' for actor in cell.actors)), None)
    visual = scene.visuals.get(player)
    if player is None or visual is None or not visual.text:
        return None
    if (player == view.observe_cursor or player in (view.assist_cells or ())
            or any(player in (getattr(view, name, None) or {}) for name in
                   ('preview_tints', 'preview_marks', 'intent_marks', 'tamper_highlights'))
            or player in view._image_effects[1]):
        return None
    from PIL import Image, ImageChops
    from dataclasses import replace
    from ..core.map_scene import build_scene
    from .render import render_map
    from .map_presentation import present_scene
    from .map_image import render_scene_image, _tile, _glyph_scale
    from .styles import MOVE_REPEAT_MIN_SECONDS
    left, top, width, height = scene.viewport
    if image.width % width or image.height % height:
        return None
    cell_px = (image.width//width, image.height//height)
    cell = scene.cells[player]
    # 保留演员对材质角标/堆叠徽记的影响，只移除玩家字形，不能把特殊地板
    # 改成无演员时的大地板图标，否则最终静态帧也会与原图不同。
    tile = _tile(cell, replace(visual, text=''), scene.realm_id, cell_px, False,
                 view._image_effects[0].get(player), view._image_fog_backgrounds.get(player),
                 None, scene.observe_layer, None,
                 view._image_glyph_layers.get(player),
                 player in view._image_protected_cells)
    sprite = _player_sprite(visual, cell_px, _glyph_scale(cell, *cell_px, False, False))
    tile_box = ((player[0]-left)*cell_px[0], (player[1]-top)*cell_px[1],
                (player[0]-left+1)*cell_px[0], (player[1]-top+1)*cell_px[1])
    difference = ImageChops.difference(image.crop(tile_box).convert('RGB'), tile.convert('RGB'))
    red, green, blue = difference.split()
    mask = ImageChops.lighter(ImageChops.lighter(red, green), blue).point(lambda p: 255 if p else 0)
    sprite.putalpha(ImageChops.multiply(sprite.getchannel('A'), mask))
    previous_viewport = getattr(view, '_native_guard_viewport', None)
    if previous_viewport == scene.viewport:
        gl, gt, gr, gb = view._native_guard_extent
    else:
        dx = left-previous_viewport[0] if previous_viewport else 0
        dy = top-previous_viewport[1] if previous_viewport else 0
        adjacent = (previous_viewport is not None and previous_viewport[2:] == scene.viewport[2:]
                    and max(abs(dx), abs(dy)) <= 1)
        gl = max(0, left-int(adjacent and dx > 0))
        gt = max(0, top-int(adjacent and dy > 0))
        gr = min(state.width, left+width+int(adjacent and dx < 0))
        gb = min(state.height, top+height+int(adjacent and dy < 0))
        view._native_guard_viewport = scene.viewport
        view._native_guard_extent = (gl, gt, gr, gb)
    canvas = Image.new('RGB', ((gr-gl)*cell_px[0], (gb-gt)*cell_px[1]))
    canvas.paste(image, ((left-gl)*cell_px[0], (top-gt)*cell_px[1]))
    canvas.paste(tile, ((player[0]-gl)*cell_px[0], (player[1]-gt)*cell_px[1]))
    guard_key = (view.symbol_mode, bool(view.animated_combat), (gl, gt, gr, gb))
    cached = getattr(view, '_native_guard_scenes', None)
    if cached is None or cached[0] is not scene or cached[1] != guard_key:
        scenes = []
        visible = state.visible_cells()
        for edge in ((gl, top, left-gl, height), (left+width, top, gr-left-width, height),
                     (gl, gt, gr-gl, top-gt), (gl, top+height, gr-gl, gb-top-height)):
            ex, ey, ew, eh = edge
            if ew <= 0 or eh <= 0:
                continue
            visuals = {}
            rendered = render_map(
                state, viewport_width=ew, viewport_height=eh, origin=(ex, ey),
                symbol_mode=view.symbol_mode, cell_w=max(2, view.cell_w), cell_h=view.cell_h,
                tutorial_cells=view.tutorial_cells,
                explosion_cells=None if view.animated_combat else getattr(state, 'explosion_cells', None),
                explosion_blasts=getattr(state, 'explosion_blasts', None),
                explosion_age=getattr(state, 'explosion_age', 0),
                markers=view.sound_markers or None, visuals=visuals, visible=visible)
            edge_scene = build_scene(state, viewport=edge, cell_w=view.cell_w, cell_h=view.cell_h,
                                     legacy_terrain=not bool(getattr(state, 'map_memory_enabled', False)),
                                     visible=visible)
            scenes.append(present_scene(edge_scene, rendered, visuals=visuals,
                                        priority=set(view.sound_markers) | set(view.tutorial_cells or ())))
        view._native_guard_scenes = (scene, guard_key, scenes)
    for edge_scene in view._native_guard_scenes[2]:
        edge_image = render_scene_image(edge_scene, cell_px=cell_px,
                                        backgrounds=view._image_effects[0],
                                        effect_glyphs=view._image_effects[1],
                                        fog_backgrounds=view._image_fog_backgrounds,
                                        glyph_layers=view._image_glyph_layers,
                                        protected_cells=view._image_protected_cells)
        ex, ey = edge_scene.viewport[:2]
        canvas.paste(edge_image, ((ex-gl)*cell_px[0], (ey-gt)*cell_px[1]))
    return {'canvas': canvas, 'origin': (gl, gt), 'sprite': sprite,
            'player': player, 'camera': (left, top), 'cell_px': cell_px,
            'layer': (state.layer_key(), image.size), 'duration': MOVE_REPEAT_MIN_SECONDS, 'animate': True}
