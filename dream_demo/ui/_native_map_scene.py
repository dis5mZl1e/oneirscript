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


class _ScaledFrameCache:
    """One exact Pillow result, reusable only for versioned immutable assets."""

    def __init__(self):
        self._key = self._image = None

    def compose(self, packet, player, camera, size):
        from PIL import Image
        versions = packet.get('_asset_versions')
        viewport = tuple(packet['viewport_size'])
        crop = tuple(round((camera[i] - packet['origin'][i]) * packet['cell_px'][i])
                     for i in range(2))
        position = tuple(round((player[i] - camera[i]) * packet['cell_px'][i])
                         for i in range(2))
        key = ((tuple(sorted(versions.items())), viewport, tuple(size), crop, position)
               if versions else None)
        if key is not None and key == self._key:
            return self._image
        image = _compose_frame(packet['canvas'], packet['origin'], packet['sprite'],
                               packet['cell_px'], player, camera, viewport)
        if image.size != size:
            image = image.resize(size, Image.Resampling.BILINEAR)
        overlay = packet.get('text_overlay')
        if overlay is not None:
            if overlay.size != size:
                overlay = overlay.resize(size, Image.Resampling.BILINEAR)
            image = image.convert('RGBA')
            image.alpha_composite(overlay)
        self._key, self._image = key, image
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


def _cached_player_sprite(view, visual, cell_px, scale, token):
    # Keep one unmasked glyph template. Packet-specific difference masks must
    # never mutate this template or carry another cell's background into alpha.
    key = (token, visual.text, visual.color, tuple(cell_px), scale)
    cached = getattr(view, '_native_player_sprite', None)
    if cached is None or cached[0] != key:
        cached = view._native_player_sprite = (key, _player_sprite(visual, cell_px, scale))
    return cached[1].copy()


class _GuardRasterCache:
    """One permitted edge raster; compare complete rendered inputs."""

    def __init__(self, *, owned=False):
        self._key = self._image = None
        self._cache = None
        if owned:
            from .map_image import SceneImageCache
            from ._native_producer_raster import _OwnedRaster
            self._cache = SceneImageCache(image_factory=_OwnedRaster)

    def render(self, scene, cell_px, token, *, backgrounds=None, effect_glyphs=None,
               fog_backgrounds=None, glyph_layers=None, protected_cells=frozenset()):
        from .map_image import _cell_token, render_scene_image
        backgrounds = backgrounds or {}
        fog = fog_backgrounds or {}
        effects = effect_glyphs or {}
        layers = glyph_layers or {}
        protected = protected_cells or ()
        cells = tuple((pos, _cell_token(cell, scene.visuals.get(pos), backgrounds.get(pos),
                                       fog.get(pos), effects.get(pos), layers.get(pos), pos in protected))
                      for pos, cell in scene.cells.items())
        key = (token, tuple(cell_px), scene.viewport, scene.realm_id, scene.observe_layer, cells)
        if key != self._key:
            if self._cache is not None and self._key is not None and self._key[0] != token:
                from .map_image import SceneImageCache
                from ._native_producer_raster import _OwnedRaster
                self._cache = SceneImageCache(image_factory=_OwnedRaster)
            self._image = render_scene_image(scene, cell_px=cell_px, backgrounds=backgrounds,
                                            effect_glyphs=effects, fog_backgrounds=fog,
                                            glyph_layers=layers, protected_cells=protected,
                                            cache=self._cache)
            self._key = key
        return self._image


def _guard_rasters_for(view, guard_key, count):
    """Reuse edge caches across scene wrappers only while their geometry matches."""
    scenes = getattr(view, '_native_guard_scenes', None)
    rasters = getattr(view, '_native_guard_rasters', None)
    if scenes is not None and scenes[1] == guard_key and len(rasters or ()) == count:
        return rasters
    return [_GuardRasterCache(owned=type(view) is _OwnedNativeView) for _ in range(count)]


def _guard_canvas_for(view, extent, cell_px):
    """Reuse the packet canvas only while its world and pixel geometry match."""
    from PIL import Image
    key = (tuple(extent), tuple(cell_px))
    cached = getattr(view, '_native_guard_canvas', None)
    if cached is None or cached[0] != key:
        gl, gt, gr, gb = extent
        factory = Image.new
        if type(view) is _OwnedNativeView:
            from ._native_producer_raster import _OwnedRaster
            factory = _OwnedRaster
        cached = (key, factory('RGB', ((gr-gl)*cell_px[0], (gb-gt)*cell_px[1])))
        view._native_guard_canvas = cached
    return cached[1]


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
    from .map_image import _tile, _glyph_scale, _cell_token
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
    from ..realm_glyphs import presentation_token
    raster_token = presentation_token()
    sprite = _cached_player_sprite(view, visual, cell_px,
                                    _glyph_scale(cell, *cell_px, False, False), raster_token)
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
    canvas = _guard_canvas_for(view, (gl, gt, gr, gb), cell_px)
    position = ((left-gl)*cell_px[0], (top-gt)*cell_px[1])
    tile_position = ((player[0]-gl)*cell_px[0], (player[1]-gt)*cell_px[1])
    owned = type(view) is _OwnedNativeView
    if owned:
        changed_rows = canvas.paste_owned(image, position, 'viewport')
        recipe = (raster_token, player, scene.realm_id, scene.observe_layer, cell_px,
                  _cell_token(cell, visual, view._image_effects[0].get(player),
                              view._image_fog_backgrounds.get(player), None,
                              view._image_glyph_layers.get(player),
                              player in view._image_protected_cells))
        previous_tile = getattr(view, '_native_removed_player', None)
        if (previous_tile != (canvas, recipe)
                or any(tile_position[1] <= row < tile_position[1]+tile.height for row in changed_rows)):
            canvas.paste(tile, tile_position)
            view._native_removed_player = (canvas, recipe)
        cached_sprite = getattr(view, '_native_owned_sprite', None)
        if cached_sprite is None or cached_sprite[0] != recipe:
            from ._native_producer_raster import _OwnedRaster
            sprite_owner = _OwnedRaster('RGBA', sprite.size)
            sprite_owner.paste(sprite, (0, 0))
            cached_sprite = (recipe, sprite_owner.snapshot())
            view._native_owned_sprite = cached_sprite
        sprite = cached_sprite[1]
    else:
        canvas.paste(image, position)
        canvas.paste(tile, tile_position)
    guard_key = (raster_token, view.symbol_mode, bool(view.animated_combat),
                 getattr(view, 'explosion_cells', frozenset()),
                 getattr(view, 'explosion_blasts', ()), getattr(view, 'explosion_age', 0),
                 (gl, gt, gr, gb))
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
                explosion_cells=None if view.animated_combat else getattr(view, 'explosion_cells', None),
                explosion_blasts=getattr(view, 'explosion_blasts', None),
                explosion_age=getattr(view, 'explosion_age', 0),
                markers=view.sound_markers or None, visuals=visuals, visible=visible)
            edge_scene = build_scene(state, viewport=edge, cell_w=view.cell_w, cell_h=view.cell_h,
                                     legacy_terrain=not bool(getattr(state, 'map_memory_enabled', False)),
                                     visible=visible)
            scenes.append(present_scene(edge_scene, rendered, visuals=visuals,
                                        priority=set(view.sound_markers) | set(view.tutorial_cells or ())))
        rasters = _guard_rasters_for(view, guard_key, len(scenes))
        view._native_guard_scenes = (scene, guard_key, scenes)
        view._native_guard_rasters = rasters
    for edge_scene, raster in zip(view._native_guard_scenes[2], view._native_guard_rasters):
        edge_image = raster.render(edge_scene, cell_px, raster_token,
                                        backgrounds=view._image_effects[0],
                                        effect_glyphs=view._image_effects[1],
                                        fog_backgrounds=view._image_fog_backgrounds,
                                        glyph_layers=view._image_glyph_layers,
                                        protected_cells=view._image_protected_cells)
        ex, ey = edge_scene.viewport[:2]
        position = ((ex-gl)*cell_px[0], (ey-gt)*cell_px[1])
        if owned:
            canvas.paste_owned(edge_image, position, ('edge', ex, ey))
        else:
            canvas.paste(edge_image, position)
    if owned:
        canvas = canvas.snapshot()
    return {'canvas': canvas, 'origin': (gl, gt), 'sprite': sprite,
            'player': player, 'camera': (left, top), 'cell_px': cell_px,
            'layer': (state.layer_key(), image.size), 'duration': MOVE_REPEAT_MIN_SECONDS,
            'animate': True}


class _OwnedNativeView:
    """Native-only cache context; no borrowed public image enters this route."""
    def __init__(self, view):
        import weakref
        from .map_image import SceneImageCache
        from ._native_producer_raster import _OwnedRaster
        self._view = weakref.ref(view)
        self._base_cache = SceneImageCache(image_factory=_OwnedRaster)
        self._raster_policy = None

    def __getattr__(self, name):
        if name.startswith('_native_'):
            raise AttributeError(name)
        return getattr(self._view(), name)


class _NativeFrameGeometry:
    """Immutable presentation metadata; carries no publicly borrowed pixels."""
    __slots__ = ('size', 'width', 'height')

    def __init__(self, size):
        self.size = tuple(size)
        self.width, self.height = self.size


def _prepare_native_frame(view, *, overview=False):
    """Actual native producer entry: private facts first, PIL only on fallback."""
    smooth = view._smooth_player_sample()
    if smooth is not None:
        return view._native_image_frame(_prepared_smooth=smooth), None
    packet = None if overview else _build_owned_native_packet(view, view._image_cell_pixels())
    if packet is None:
        return view._native_image_frame(_prepared_smooth=None), None
    context = view._owned_native_context
    identity = (packet['canvas'], packet['sprite'], packet['layer'][1])
    previous = getattr(context, '_frame_geometry', None)
    if (previous is None or previous[0][0] is not identity[0]
            or previous[0][1] is not identity[1] or previous[0][2] != identity[2]):
        previous = (identity, _NativeFrameGeometry(packet['layer'][1]))
        context._frame_geometry = previous
    return previous[1], packet


def _build_owned_native_packet(view, cell_px):
    """Render permission-filtered facts into exclusive rasters, never PIL aliases.

    Post-base image decorations retain their exact existing borrowed fallback
    until their drawing writes have an equivalent ownership contract.
    """
    scene = view.shared_scene
    app = view.app
    live = getattr(app, '_world_view_live', lambda: getattr(app, 'panel_mode', 'world') == 'world')
    if (scene is None or not live() or min(cell_px) < 2
            or app.aiming or app.observe_mode or app.layer_observation is not None
            or getattr(app, '_floor_transition', None) is not None
            or getattr(app, '_left_panel_open', lambda: False)()
            or getattr(app, 'world_tamper_editor', None) is not None
            or not app.config.get('smooth_movement') or app.config.get('fx_reduce_motion')):
        return None
    current = getattr(view, '_image_cache', None)
    if current is not None and view._public_image_was_exposed(current[1]):
        return None
    if (scene is None or scene.observe_layer in ('elevation', 'floor', 'low', 'middle', 'high')
            or view.observe_cursor is not None or view.assist_cells
            or view.preview_tints or view.preview_marks or view.intent_marks
            or view.tamper_highlights or view.tamper_focus or view.tamper_destination is not None):
        return None
    from .map_image import SceneImageCache
    from ._native_producer_raster import _OwnedRaster
    from ..realm_glyphs import presentation_token
    context = getattr(view, '_owned_native_context', None)
    if context is None:
        context = view._owned_native_context = _OwnedNativeView(view)
    policy = presentation_token()
    if context._raster_policy != policy:
        context._base_cache = SceneImageCache(image_factory=_OwnedRaster)
        context._raster_policy = policy
    base = context._base_cache.render(scene, cell_px, False, view._image_effects[0],
                                     view._image_effects[1], view._image_fog_backgrounds,
                                     view._image_glyph_layers, view._image_protected_cells)
    return _build_native_packet(context, base)
