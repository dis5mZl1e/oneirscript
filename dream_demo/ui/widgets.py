"""界面控件：地图视图、右侧面板容器、原生按钮、本局时长标题栏。"""

from __future__ import annotations

import time

from rich.text import Text
from textual.containers import Vertical
from textual.app import ComposeResult
from textual.widgets import Button, Header, Static
from textual.events import MouseDown, MouseMove, MouseScrollDown, MouseScrollUp
from textual.widgets._header import HeaderClockSpace, HeaderIcon, HeaderTitle

from ..core import GameState
from .styles import MAP_DEFAULT_ZOOM, MAP_ZOOM_LEVELS, highlighted_message
from ..i18n import tr
from ._native import _trace_native
from .glyphs import viewport_origin
from .render import render_map
from .frame_geometry import cell_ranges, compose_fx
from .ornament_frame import OrnamentBorderMixin


class MapView(Static):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.can_focus = True
        self.state: GameState | None = None
        self.symbol_mode = "themed"
        self.zoom = MAP_DEFAULT_ZOOM
        self.viewport = (0, 0, 1, 1)
        self._last_render: tuple[str, tuple] | None = None
        self._frame_key: tuple | None = None
        # 目标辅助路径格集合：render_map 据此黄底高亮（app 每帧同步）。
        self.assist_cells: set[tuple[int, int]] | None = None
        # 教程目标格：{格子: 叠加字形}——青金底色脉动 + 引导标记（app 每帧同步）。
        self.tutorial_cells: dict[tuple[int, int], str] | None = None
        # 篡改草稿中需要编号区分的对象标记（docs §8 第二批），由 update_state
        # 从当前 world_tamper_editor 的固定引用生成。
        self.tamper_markers: dict[tuple[int, int], str] = {}
        # 观察模式的光标格（None = 未在观察）：渲染成一枚白色 ?。
        self.observe_cursor: tuple[int, int] | None = None
        # §15.6 操作预览（app 每帧同步，全部是**地图绝对坐标**）：
        # tints = 实际作用区底色（新档位色阶／拒绝与未知标记色），
        # marks = 只给「改了也读不出」的格子的字形，boundary = 作用区外一格的接触圈。
        self.preview_tints: dict[tuple[int, int], str] | None = None
        self.preview_marks: dict[tuple[int, int], tuple[str, str]] | None = None
        self.preview_boundary: tuple[tuple[int, int], ...] = ()
        # 异象意图角标：(x,y) -> (kind, glyph, color, alpha)；图像后端画在右上角。
        self.intent_marks: dict[tuple[int, int], tuple[str, str, str, float]] = {}
        # 最近一帧 render_map 的输出（FX 画布叠加的基准帧）。
        self.last_base_text = None
        self.cell_ranges = {}
        self.animated_combat = False
        self._scene_text = None
        self._scene_ranges = {}
        # 🔴 基帧覆盖标志（2026-10-10 性能 P1）：update_state 原生重画基帧时
        # 会把 widget 直接覆盖成无光照纯帧——此时 app._fx_frame_digest 即使
        # 相同也不能跳过补画（「摘要相同」≠「widget 上还是叠加帧」）。
        # fx_paint 写回叠加层后置回 False。
        self.fx_base_overwritten = False
        self._interaction_key = None
        self.shared_scene = None
        self.display_mode = "character"
        self._image_cache = None
        self._image_effects = ({}, {})
        # 视野外线索底色（声波）：图像后端必须允许它压过迷雾，不能套用
        # 「只给可见格上底色」的常规叠加层门槛。
        self._image_fog_backgrounds = {}
        self._image_effects_key = None
        self._image_effects_at = 0.0
        from .map_image import SceneImageCache
        self._raster_cache = SceneImageCache()
        # C7（2026-10-22）：当前合成图是否来自 SceneImageCache，以及叠加层逐格
        # 指纹。live_map 只在基础栅格未变、仅少量叠加格变化时发脏格补丁；
        # 默认关闭（ONEIRSCRIPT_IMAGE_PATCHES=0），这里只提供判定数据。
        self._image_base_cached = False
        self._image_overlay_sig: dict[tuple[int, int], tuple] = {}

    def _frame_signature(self, state: GameState, width: int, height: int) -> tuple:
        """渲染指纹：地图可能依赖的字段中所有“会变”的部分。

        回合制游戏里地图变化都发生在推进时间的动作（移动/攻击/物品/材料模拟）中，
        time 与玩家位置、实体数量共同覆盖了渲染依赖；指纹相同则直接复用上一帧。
        光标与辅助路径不影响基帧指纹，另从当前完整光照帧叠加。
        """
        return (
            id(state),
            state.time,
            state.depth,
            state.developed_total,
            bool(getattr(state,"map_memory_enabled",False)), bool(getattr(state,"terrain_known",False)),
            getattr(state,"map_knowledge_version",0),
            state.reveals_anomalies,  # 诅咒灵视：开关一变就要重绘视野外的显形
            state.player.x,
            state.player.y,
            len(state.enemies),
            len(state.world_items),
            len(state.events),
            width,
            height,
            self.symbol_mode,
            self.zoom,
            tuple(sorted(state.electric_field_cells())),
        )

    def viewport_for(self, state: GameState) -> tuple[int, int, int, int]:
        """按给定 state 算出视口 (left, top, width, height)——不渲染、不写缓存。

        任何「换了 state 还要知道视口在哪」的地方都必须走这里：可见格数被
        **地图实际尺寸**钳制，而层型会改写地图长宽（长廊/迷宫），沿用上一层
        的视口去读新层格子会越界。
        """
        # zoom 是视野比例，物理实现为每格终端尺寸：
        # 放大时格子与图标同步扩大；缩小时保留图标的原始两列宽度，
        # 通过扩大可见视口实现缩小，避免宽 Unicode 图标被压成 ASCII 或互相覆盖。
        # 可见格数 = 物理容量 / 每格尺寸，受地图实际尺寸钳制。
        zoom = self.zoom if self.zoom in MAP_ZOOM_LEVELS else MAP_DEFAULT_ZOOM
        # 0.5 档是全图概览：每格压缩到一列。此前 max(2, ...) 把它
        # 强行钳成两列，导致 Ctrl+↓ 的 zoom 数值变了、可视范围却不变。
        cell_w = max(1, round(2 * zoom))
        cell_h = max(1, round(zoom))
        physical_cols = max(1, self.content_size.width - 1)
        width = max(1, min(physical_cols // cell_w, state.width))
        height = max(1, min(self.content_size.height // cell_h, state.height))
        self.cell_w, self.cell_h = cell_w, cell_h
        previous = self.viewport if self.viewport[2:] == (width, height) else None
        left, top = viewport_origin(state, width, height, previous[:2] if previous else None)
        layer = getattr(self.app, 'layer_observation', None)
        if layer is not None:
            left, top = self.viewport[:2]
            cx, cy = layer.cursor
            left = max(0,min(state.width-width, min(left,cx) if cx < left else max(left,cx-width+1)))
            top = max(0,min(state.height-height, min(top,cy) if cy < top else max(top,cy-height+1)))
        return (left, top, width, height)

    def _tamper_markers(self) -> dict[tuple[int, int], str]:
        """只给「同方位同距离、必须编号」的槽画地图标记；普通单体目标不加噪。"""
        editor = getattr(self.app, "world_tamper_editor", None)
        sentence = getattr(editor, "sentence", None)
        if sentence is None:
            return {}
        numbers = "①②③④⑤⑥⑦⑧⑨⑩"
        markers: dict[tuple[int, int], str] = {}
        for slot in getattr(sentence, "slots", ()) or ():
            number = int(getattr(slot, "number", 0) or 0)
            if 1 <= number <= len(numbers):
                markers[(slot.x, slot.y)] = numbers[number - 1]
        # 区域聚流的明确落点：地图上临时标「落」。
        destination = getattr(editor, "gather_destination", None)
        if destination is not None:
            word_id = getattr(editor, "word_id", "")
            if word_id in ('gather_liquid', 'gather_gas'):
                markers[tuple(destination)] = '落'
        return markers

    def update_state(self, state: GameState) -> None:
        self.state = state
        viewport = self.viewport_for(state)
        left, top, width, height = viewport
        self.tamper_markers = self._tamper_markers()
        from ..core.sound_markers import sound_markers
        self.sound_markers = sound_markers(
            state, getattr(self.app, '_signal_clue_index', None))
        layer = getattr(self.app, 'layer_observation', None)
        display_mode = self.app.resolved_map_display()[0]
        frame_key = self._frame_signature(state, width, height) + (
            viewport, display_mode, layer.layer if layer else None,
            len(getattr(state, "explosion_cells", ()) or ()), getattr(state, "explosion_age", 0), self.animated_combat,
            tuple(sorted((self.tutorial_cells or {}).items())), state.time % 2,
            tuple(sorted(self.tamper_markers.items())),
            tuple(sorted(self.sound_markers.items())),
        )
        if frame_key == self._frame_key and self._last_render is not None:
            # 状态未变：跳过整张地图的重建，直接复用上一帧。
            self.viewport = viewport
            self.update_interaction()
            return
        glyph_cell_w = max(2,self.cell_w) if display_mode == "image" else self.cell_w
        rendered = render_map(
            state,
            viewport_width=width,
            viewport_height=height,
            origin=(left, top),
            symbol_mode=self.symbol_mode,
            cell_w=glyph_cell_w,
            cell_h=self.cell_h,
            tutorial_cells=self.tutorial_cells,
            explosion_cells=None if self.animated_combat else getattr(state, "explosion_cells", None),
        explosion_blasts=getattr(state, "explosion_blasts", None),
            explosion_age=getattr(state, "explosion_age", 0),
            markers={**self.sound_markers, **self.tamper_markers} or None,
        )
        from ..core.map_scene import build_scene, observe_scene
        from .map_presentation import present_scene, render_observation
        scene = build_scene(state, viewport=viewport, cell_w=self.cell_w, cell_h=self.cell_h,
                            legacy_terrain=not bool(getattr(state,"map_memory_enabled",False)))
        # 同一帧的切片表只算一次（2026-10-21 任务3）：present_scene 与控件本身以前
        # 各算一遍，而它是这一帧里仅次于 render_map 的开销。
        ranges_cell_w = glyph_cell_w
        ranges = cell_ranges(rendered, width, height, ranges_cell_w, self.cell_h)
        self.shared_scene = present_scene(scene, rendered,
            priority=set(self.tamper_markers) | set(self.sound_markers) | set(self.tutorial_cells or ()),
            source_cell_w=glyph_cell_w, ranges=ranges)
        if layer is not None and layer.layer != 'composite':
            # 图像后端也消费同一份过滤结果：观察帧重新采成 visuals，切层时同屏
            # 只有一种地图，而不是图像继续画综合层。
            observed = observe_scene(scene, layer.layer)
            rendered = render_observation(observed, layer.layer, self.symbol_mode,
                                          markers=self.sound_markers or None)
            # 观察帧按 scene.cell_w 重新排版（present_scene 的默认口径）。
            ranges_cell_w = self.cell_w
            ranges = cell_ranges(rendered, width, height, ranges_cell_w, self.cell_h)
            self.shared_scene = present_scene(observed, rendered,
                priority=set(self.tamper_markers) | set(self.sound_markers) | set(self.tutorial_cells or ()),
                ranges=ranges)
        extent = (width*self.cell_w,height*self.cell_h)
        if (self.display_mode != display_mode or (display_mode == "image"
                and extent != getattr(self,"_image_extent",None))):
            # Textual's previous blank placeholder cannot describe image pixels;
            # a full layout repaint clears them, including still-blank fog cells.
            self.screen.refresh(layout=True)
        self._image_extent = extent if display_mode == "image" else None
        self.display_mode = display_mode
        if self.app.config.get('fx_quality') == 'off':
            self._image_effects = ({},{})
            self._image_fog_backgrounds = {}
            self._image_effects_key = None
        self._image_cache = None
        signature = (rendered.plain, tuple(rendered._spans))
        changed = signature != self._last_render or viewport != self.viewport
        self._last_render = signature
        # 最近一帧基准文本：FX 特效画布（#map-fx）在其上做叠加着色，
        # 不重复调用 render_map（渲染特效计划 §4 数据流）。
        self.last_base_text = rendered
        self.cell_ranges = (ranges if ranges_cell_w == self.cell_w
                            else cell_ranges(rendered, width, height, self.cell_w, self.cell_h))
        self._frame_key = frame_key
        self.viewport = viewport
        # 气泡跟随（2026-10-11）：玩家移动后地图帧必然重算，这里让气泡栈
        # 复查角落（右上 1/4 避让 → 右下）。place() 自带指纹去抖，重复调用
        # 零写回；主页/无地图时 query 失败静默跳过。
        try:
            self.app.query_one("#map-hints").place()
        except Exception:
            pass
        if changed or self._scene_text is None:
            self.fx_base_overwritten = True
            self.update_scene(rendered)
        else:
            self.update_interaction()

    def update_scene(self, rendered: Text) -> None:
        """Store the complete lighting/FX frame, before cursor overlays."""
        if self.display_mode == 'image' or getattr(self.app, 'layer_observation', None) is not None:
            rendered = self.last_base_text if self.last_base_text is not None else rendered
        self._scene_text = rendered
        _, _, width, height = self.viewport
        self._scene_ranges = (self.cell_ranges if self.last_base_text is not None
                              and rendered.plain == self.last_base_text.plain else None)
        if self.display_mode != "image":
            self._interaction_key = None
        self.update_interaction()

    def update_interaction(self) -> None:
        """Only replace cursor/path pixels; leave the cached lighting unchanged."""
        if self._scene_text is None:
            return
        from .terrain_preview import BOUNDARY_COLOR
        key = (self.viewport, self.observe_cursor, frozenset(self.assist_cells or ()),
               frozenset((self.preview_tints or {}).items()),
               frozenset((self.preview_marks or {}).items()),
               frozenset(self.preview_boundary or ()),
               id(self.shared_scene) if self.display_mode == "image" else None)
        if key == self._interaction_key:
            return
        self._interaction_key = key
        if self.display_mode == 'image':
            _, _, width, height = self.viewport
            self.update(Text((' '* (width*self.cell_w)+'\n')*(height*self.cell_h-1)
                             +' '*(width*self.cell_w), style='on #07070b'))
            return
        left, top, width, height = self.viewport
        def local(cell):
            x, y = cell[0] - left, cell[1] - top
            return (x, y) if 0 <= x < width and 0 <= y < height else None
        styles = {pos: "#4a4020" for cell in self.assist_cells or ()
                  if (pos := local(cell)) is not None}
        # 预览压在最外层：玩家正在决定的这一发，比它脚下的路径高亮更要紧；
        # 但观察光标的白色 ? 永远最后写——它标的是「我在看哪一格」。
        styles.update({pos: BOUNDARY_COLOR for cell in self.preview_boundary or ()
                       if (pos := local(cell)) is not None})
        styles.update({pos: color for cell, color in (self.preview_tints or {}).items()
                       if (pos := local(cell)) is not None})
        glyphs = {pos: mark for cell, mark in (self.preview_marks or {}).items()
                  if (pos := local(cell)) is not None}
        if self.observe_cursor is not None and (pos := local(self.observe_cursor)) is not None:
            glyphs[pos] = ("?", "bold white")
        if not styles and not glyphs:
            self.update(self._scene_text)
            return
        if self._scene_ranges is None:
            self._scene_ranges = cell_ranges(self._scene_text, width, height, self.cell_w, self.cell_h)
        self.update(compose_fx(self._scene_text, self._scene_ranges, styles, glyphs,
                               self.cell_w, self.cell_h))

    def set_intent_marks(self, marks) -> None:
        """Anomaly intent badges live in the image cell, so a change repaints it."""
        marks = dict(marks or {})
        if marks == self.intent_marks:
            return
        self.intent_marks = marks
        self._image_cache = None
        if self.display_mode == 'image':
            self.refresh()

    def update_image_effects(self, styles, glyphs, force=False, fog_styles=None):
        from rich.style import Style
        from .effects import overlay_style
        from .map_presentation import foreground
        now = time.monotonic()
        fog_styles = fog_styles or {}
        if not force and now-self._image_effects_at < .125:
            return
        key = (self.viewport, frozenset(styles.items()),frozenset(glyphs.items()),
               frozenset(fog_styles.items()))
        if key == self._image_effects_key:
            return
        left,top,_,_ = self.viewport
        backgrounds = {}
        for (x,y),value in styles.items():
            color = Style.parse(overlay_style(value)).bgcolor
            if color:
                backgrounds[(left+x,top+y)] = '#{:02x}{:02x}{:02x}'.format(*color.get_truecolor())
        fog_backgrounds = {}
        for (x,y),value in fog_styles.items():
            color = Style.parse(overlay_style(value)).bgcolor
            if color:
                fog_backgrounds[(left+x,top+y)] = '#{:02x}{:02x}{:02x}'.format(*color.get_truecolor())
        foregrounds = {(left+x,top+y):(glyph,foreground(color) or '#ffffff')
                       for (x,y),(glyph,color) in glyphs.items()}
        self._image_effects = backgrounds,foregrounds
        self._image_fog_backgrounds = fog_backgrounds
        self._image_effects_key = key
        self._image_effects_at = now
        self._image_cache = None
        self.refresh()

    def image_frame(self):
        from .map_image import render_scene_image
        transition = getattr(self.app,'_floor_transition',None)
        if transition is not None and transition.get('image_frame') is not None:
            return transition['image_frame']
        from PIL import ImageDraw
        # Resize.pixel_size when supplied by the terminal gives actual DPI geometry.
        pixels = getattr(self.app, '_map_terminal_pixels', None)
        size = self.app.size
        px = (max(1,round(pixels.width/max(1,size.width))) if pixels else 12)
        py = (max(1,round(pixels.height/max(1,size.height))) if pixels else 24)
        pitch = getattr(self.app,"_map_terminal_cell_pixels",None)
        if pitch is not None:
            px,py=max(1,round(pitch[0])),max(1,round(pitch[1]))
        cell_px = (px*self.cell_w,py*self.cell_h)
        preview = self.preview_tints or {}
        marks = self.preview_marks or {}
        key = (id(self.shared_scene),cell_px,self.observe_cursor,frozenset(self.assist_cells or ()),self._image_effects_key,
               frozenset(preview.items()),frozenset(marks.items()),frozenset(self.intent_marks.items()))
        if self._image_cache and self._image_cache[0] == key:
            return self._image_cache[1]
        base = render_scene_image(self.shared_scene, cell_px=cell_px,
                                  backgrounds=self._image_effects[0],effect_glyphs=self._image_effects[1],
                                  fog_backgrounds=self._image_fog_backgrounds,
                                  cache=self._raster_cache)
        # C7：仅当基础栅格确实来自 SceneImageCache 时，逐格脏格补丁才有像素
        # 语义；光照/过渡等逐格渲染路径保持整包重发。
        self._image_base_cached = base is self._raster_cache.image
        image = base.copy()
        draw = ImageDraw.Draw(image)
        left,top,width,height = self.viewport
        overlay_sig = {}
        for pos in set(self.assist_cells or ()) | ({self.observe_cursor} if self.observe_cursor else set()):
            if left <= pos[0] < left+width and top <= pos[1] < top+height:
                x,y = (pos[0]-left)*cell_px[0],(pos[1]-top)*cell_px[1]
                outline = 'white' if pos == self.observe_cursor else '#c6a446'
                draw.rectangle((x,y,x+cell_px[0]-1,y+cell_px[1]-1),
                               outline=outline,width=1)
                overlay_sig[pos] = ('outline', outline)
        # §15.6：图像后端的预览只画**朝向区外**的那条边（等高线在这一层本来就是线），
        # 相邻两格都在作用区里时不画内线，整片区域读起来是一个轮廓而不是格子网。
        from .map_presentation import draw_glyph
        cw, ch = cell_px
        for pos, color in preview.items():
            if not (left <= pos[0] < left+width and top <= pos[1] < top+height):
                continue
            x, y = (pos[0]-left)*cw, (pos[1]-top)*ch
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                if (pos[0]+dx, pos[1]+dy) in preview:
                    continue
                if dx:
                    edge = x + (cw - 1 if dx > 0 else 0)
                    draw.line((edge, y, edge, y + ch - 1), fill=color, width=2)
                else:
                    edge = y + (ch - 1 if dy > 0 else 0)
                    draw.line((x, edge, x + cw - 1, edge), fill=color, width=2)
            mark = marks.get(pos)
            if mark:
                draw_glyph(image, mark[0], mark[1], (x, y, cw, ch), scale=.62)
            overlay_sig[pos] = overlay_sig.get(pos, ()) + (
                ('tint', color) + (('mark', mark[0], mark[1]) if mark else ()))
        # 异象意图角标（2026-10-21）：同格右上角，初值约占格宽 40%（设计 §4.1），
        # 淡出只按不透明度分档，始终裁切在本格。
        for pos, (_kind, glyph, color, alpha) in (self.intent_marks or {}).items():
            if alpha <= 0.0 or not (left <= pos[0] < left+width and top <= pos[1] < top+height):
                continue
            x, y = (pos[0]-left)*cw, (pos[1]-top)*ch
            badge = max(2, round(cw*0.4))
            draw_glyph(image, glyph, color,
                       (x+cw-badge, y, badge, max(2, round(ch*0.4))),
                       scale=.9, alpha=alpha)
            overlay_sig[pos] = overlay_sig.get(pos, ()) + (
                'intent', glyph, color, alpha)
        self._image_overlay_sig = overlay_sig
        self._image_cache = key,image
        return image

    def image_patch_state(self):
        """C7：脏格补丁判定所需的当前帧信息；None 表示该帧不可增量输出。

        返回 (image, scene, base_revision, overlay_signature)：
        - image/scene 用来确认与上一帧是同一份合成图、同一个场景对象；
        - base_revision 是 SceneImageCache 的重建/平移/贴格计数，任一变化都说明
          基础栅格像素变了（或整张换了），必须整包重发；
        - overlay_signature 是每格叠加参数的指纹；它的差异格就是脏格。旧光标
          格也在差异里，补丁会把新 base 像素发过去完成擦除。

        None 覆盖过渡帧、光照/观察层逐格渲染等不经过 SceneImageCache 的路径，
        这些帧一律走整包重发，不猜。
        """
        cached = self._image_cache
        if not cached or not self._image_base_cached:
            return None
        return (cached[1], self.shared_scene,
                (self._raster_cache.full_rebuilds, self._raster_cache.pan_reuses,
                 self._raster_cache.painted_cells),
                self._image_overlay_sig)

    def on_resize(self, event) -> None:
        if self.state is not None:
            self.update_state(self.state)
            self.app.query_one("#map-hints").place()
            if self.app.tamper_editor is not None or self.app.panel_mode == 'event_dialog':
                self.app.call_after_refresh(self.app.refresh_view)

    def cell_from_offset(self, offset) -> tuple[int, int] | None:
        if not self.state:
            return None
        left, top, width, height = self.viewport
        # MapView itself has no border or padding; offsets are content-relative.
        local_x, local_y = offset.x, offset.y
        if local_x < 0 or local_y < 0:
            return None
        cell_w = getattr(self, "cell_w", 2)
        cell_h = getattr(self, "cell_h", 1)
        x = left + int(local_x // cell_w)
        y = top + int(local_y // cell_h)
        return (x, y) if 0 <= x < left + width and 0 <= y < top + height else None

    def on_mouse_down(self, event: MouseDown) -> None:
        _trace_native(
            f"MapView.on_mouse_down control={type(event.control).__name__} "
            f"offset={event.offset} button={event.button}"
        )
        self.app.handle_map_mouse_down(self, event)

    def on_mouse_move(self, event: MouseMove) -> None:
        self.app.handle_map_mouse_move(self, event)


class EventPanel(OrnamentBorderMixin, Static):
    def on_resize(self, event) -> None:
        self.app.refresh_view()

    def on_mouse_down(self, event: MouseDown) -> None:
        """面板鼠标：左键 = 使用/展开等；右键 = 打开该物品的左侧菜单。"""
        _trace_native(
            f"EventPanel.on_mouse_down control={type(event.control).__name__} "
            f"offset={event.offset} button={event.button}"
        )
        if event.button == 3:
            self.app.handle_panel_right_click(event)
            event.stop()
            return
        if event.button != 1:
            return
        self.app.handle_panel_mouse_down(event, panel=self)
        event.stop()


class DebugListWidget(Static):
    """调试面板的左/右列表：点击行 = 选中（右列点击即确认）。"""

    def on_mouse_down(self, event) -> None:
        side = "left" if self.id == "debug-left" else "right"
        self.app.handle_debug_panel_mouse(side, event)
        event.stop()

    def on_mouse_scroll_up(self, event) -> None:
        # 2026-09-19：滚轮分区——左列滚左列光标，右列滚右列光标。
        side = "left" if self.id == "debug-left" else "right"
        self.app._debug_scroll_side(side, -1)
        event.stop()

    def on_mouse_scroll_down(self, event) -> None:
        side = "left" if self.id == "debug-left" else "right"
        self.app._debug_scroll_side(side, 1)
        event.stop()


class MapOverlayPanel(EventPanel):
    """独立于右侧菜单的地图上层信息面板。

    左键条目与右侧面板完全一致（单条展开，见 handle_panel_mouse_down）；
    滚轮同样冒泡到应用的统一滚动处理，行为与右侧面板一致。
    """


class TamperOverlayPanel(OrnamentBorderMixin, Static):
    """篡改旁侧面板（规格 §4.2）：输入全部交给应用的篡改控制器。

    不复用 :class:`EventPanel` —— 那条路会走到右侧面板的行映射，把篡改面板的
    点击当成物品/操作条目。这里连滚轮与移动都自己吃掉：编辑期间不穿透到地图。
    """

    def on_resize(self, event) -> None:
        self.app.refresh_view()

    def on_mouse_down(self, event: MouseDown) -> None:
        self.app.handle_tamper_mouse("tamper-overlay", event.offset.y - self.styles.gutter.top,
                                     event.offset.x - self.styles.gutter.left,
                                     event_kind="down", button=event.button)
        event.stop()

    def on_mouse_move(self, event: MouseMove) -> None:
        self.app.handle_tamper_mouse("tamper-overlay", event.offset.y - self.styles.gutter.top,
                                     event.offset.x - self.styles.gutter.left,
                                     event_kind="move")
        event.stop()

    def on_mouse_scroll_up(self, event: MouseScrollUp) -> None:
        self.app.scroll_tamper(-1)
        event.stop()

    def on_mouse_scroll_down(self, event: MouseScrollDown) -> None:
        self.app.scroll_tamper(1)
        event.stop()


class CodexListView(OrnamentBorderMixin, Static):
    can_focus = True

    def on_mouse_down(self, event: MouseDown) -> None:
        # offset 含 1 行边框 + 1 行内边距：扣掉才是条目行号（否则点击的
        # 行与 ▶ 选中行错位两行——「图鉴鼠标光标错位」的根源）。
        self.app.select_codex_row(event.offset.y - 2)
        event.stop()

    def on_mouse_scroll_up(self, event: MouseScrollUp) -> None:
        self.app.scroll_codex(-1)
        event.stop()

    def on_mouse_scroll_down(self, event: MouseScrollDown) -> None:
        self.app.scroll_codex(1)
        event.stop()


class HistoryListView(OrnamentBorderMixin, Static):
    """旧梦回忆列表：左键点行 = 打开该局详情；滚轮 = 滚动（列表/详情共用）。"""

    can_focus = True

    def on_resize(self, event) -> None:
        if self.app.panel_mode == 'home_history':
            self.app.call_after_refresh(self.app._refresh_history_after_layout)

    def on_mouse_down(self, event: MouseDown) -> None:
        if event.button != 1 or self.app.history_page['detail'] is not None:
            return
        row = getattr(self.app, '_history_hit_rows', {}).get(event.offset.y - self.styles.gutter.top)
        if row is not None:
            self.app.history_list_click(row)
        event.stop()

    def on_mouse_scroll_up(self, event: MouseScrollUp) -> None:
        self.app.scroll_history(-1)
        event.stop()

    def on_mouse_scroll_down(self, event: MouseScrollDown) -> None:
        self.app.scroll_history(1)
        event.stop()


class SettingRowView(Static):
    def __init__(self, setting_index: int, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setting_index = setting_index

    def on_mouse_down(self, event: MouseDown) -> None:
        self.app.activate_setting(self.setting_index, event.offset.x, self.content_size.width)
        event.stop()


class SettingsListView(OrnamentBorderMixin, Vertical):
    can_focus = True


class PauseOptionView(OrnamentBorderMixin, Static):
    """全屏暂停菜单的单个选项块（2026-09-20 二次修订）。

    每个选项是**独立控件**：左键点击命中哪个控件就触发哪个选项，
    不再做「内容行号 → 选项下标」的换算——整块列表换行、加空行、
    加大间距都不会影响点击语义（真机上按行号换算曾把「图鉴」点成
    相邻项，间接引发误回主页/误开新档）。滚轮与键盘光标见 app 层。
    """

    def __init__(self, option_index: int, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.option_index = option_index

    def on_mouse_down(self, event: MouseDown) -> None:
        self.app.pause_click(self.option_index)
        event.stop()

    def on_mouse_scroll_up(self, event) -> None:
        self.app.pause_move(-1)
        event.stop()

    def on_mouse_scroll_down(self, event) -> None:
        self.app.pause_move(1)
        event.stop()


class NativeButton(OrnamentBorderMixin, Button):
    """Button that remains clickable when Win32 does not synthesize Click."""

    def on_mouse_down(self, event: MouseDown) -> None:
        _trace_native(
            f"NativeButton.on_mouse_down id={self.id} control={type(event.control).__name__} "
            f"offset={event.offset} button={event.button} display={self.display} disabled={self.disabled}"
        )
        native_route = event.button == 1 and event.control is None
        _trace_native(f"NativeButton.native_route id={self.id} enabled={native_route}")
        if not native_route:
            return
        self.suppress_click()
        self.app.call_later(self.app.handle_button_press, self)
        event.stop()


class SidebarTabButton(NativeButton):
    """Use the whole allocated tab width for its symbol and complete title.

    Textual's default Button.render adds two implicit columns even when CSS
    padding is zero. Removing that internal pad only for workspace tabs lets
    all five icons and full titles fit the existing 32-column compact sidebar.
    """

    def render(self):
        label = self.label.copy()
        label.stylize_before(self.rich_style)
        return label


class QolConfirmButton(NativeButton):
    """Require a press begun inside this confirmation, never a prior panel click."""

    def on_mouse_down(self, event: MouseDown) -> None:
        if event.button == 1:
            self._question_pressed = getattr(self.app, 'qol_confirmation', None)
            if event.control is None:
                token = self._question_pressed
                self.suppress_click()
                def press_question():
                    if token is not None and token is getattr(self.app, 'qol_confirmation', None):
                        self.app.handle_button_press(self)
                self.app.call_later(press_question)
                event.prevent_default()
                event.stop()

    async def _on_click(self, event) -> None:
        token = getattr(self, '_question_pressed', None)
        self._question_pressed = None
        if token is None or token is not getattr(self.app, 'qol_confirmation', None):
            # Textual dispatches each handler in the widget's MRO. Stopping
            # bubbling alone still lets Button._on_click call press().
            event.prevent_default()
            event.stop()
            return
        # A valid click proceeds to Button._on_click once via Textual's MRO.


class RunClock(HeaderClockSpace):
    """标题栏右上角显示本局时长（替代默认的现实时钟）。"""

    DEFAULT_CSS = """
    RunClock {
        background: $foreground-darken-1 5%;
        color: $foreground;
        text-opacity: 85%;
        content-align: center middle;
        width: 14;
    }
    """

    def _on_mount(self, _event) -> None:
        self.set_interval(1, callback=self.refresh, name="update run clock")

    def render(self):
        session = getattr(self.app, "session", None)
        if session is None:
            return Text("")
        elapsed = max(0, int(time.monotonic() - session.started))
        hours, rem = divmod(elapsed, 3600)
        minutes, seconds = divmod(rem, 60)
        if hours:
            return Text(f"{tr('本局')} {hours}:{minutes:02d}:{seconds:02d}")
        return Text(f"{tr('本局')} {minutes:02d}:{seconds:02d}")


class HeaderTicker(Static):
    """标题栏事件播报条（2026-09-19）：事件提示在顶部滚动播放 3 秒。

    无事件时隐藏（原 HeaderTitle 照常显示标题）；有事件时替换标题位，
    消息**从左端**开始显示（不再走 HeaderTitle 的居中）。
    更新时做上下滚动字幕式切换（旧行 → 空行 → 新行三帧，约 0.2 秒），
    而不是突然变化；3 秒内再来新消息则立即切入并重新计时；
    时间结束后没有其他事件，还原标题。终端只有整行粒度，
    「滚动」以三帧轮替模拟（老行滚出 → 空行 → 新行滚入）。
    """

    DEFAULT_CSS = """
    HeaderTicker {
        width: 1fr;
        height: 1;
        content-align: left middle;
        color: $foreground;
        text-opacity: 85%;
        display: none;
    }
    """

    ROLL_FRAME_SECONDS = 0.07
    PLAY_SECONDS = 3.0

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._current = ""
        self._playing = False
        self._roll_timers: list = []
        self._hide_timer = None
        self._token = 0

    def push(self, message: str, app) -> None:
        """播放一条消息：滚动切入并重新计时；重复推送同一条只重置 3 秒计时。"""
        self._token += 1
        token = self._token
        for timer in self._roll_timers:
            timer.stop()
        self._roll_timers.clear()
        if self._hide_timer is not None:
            self._hide_timer.stop()
            self._hide_timer = None
        if self._playing and message == self._current:
            # 同一条消息连发（如帧循环与 show_toast 双通道）：只重置计时，不重滚。
            self._hide_timer = self.set_timer(self.PLAY_SECONDS, lambda: self._finish(app, token))
            return
        was_playing = self._playing
        previous = self._current
        self._current = message
        if not self._playing:
            self._playing = True
            self.styles.display = "block"
            try:
                app.query_one(HeaderTitle).styles.display = "none"
            except Exception:
                pass
        # 上下滚动字幕式切换：旧行 → 空行 → 新行（首次播放从空行滚入）。
        # 新消息帧走 highlighted_message：物品名按各自定义色高亮（2026-09-21）。
        frames = (
            [Text(previous), Text(""), highlighted_message(message)]
            if was_playing
            else [Text(""), highlighted_message(message)]
        )
        if not was_playing:
            self.update(frames.pop(0))
        for index, frame in enumerate(frames):
            self._roll_timers.append(
                self.set_timer(
                    self.ROLL_FRAME_SECONDS * (index + 1),
                    lambda f=frame, t=token: self._roll_frame(f, t),
                )
            )
        self._hide_timer = self.set_timer(self.PLAY_SECONDS, lambda: self._finish(app, token))

    def _roll_frame(self, frame: Text, token: int) -> None:
        if token != self._token or not self._playing:
            return
        self.update(frame)

    def _finish(self, app, token: int) -> None:
        if token != self._token:
            return
        # 先滚出成空行，再还原标题（标题回位也有一个过渡帧，不生硬跳变）。
        self.update(Text(""))
        self.set_timer(self.ROLL_FRAME_SECONDS, lambda: self._teardown(app, token))

    def _teardown(self, app, token: int) -> None:
        if token != self._token:
            return
        self._playing = False
        self.styles.display = "none"
        try:
            app.query_one(HeaderTitle).styles.display = "block"
        except Exception:
            pass


class DreamHeader(Header):
    """标准 Header 布局，右侧时钟位换成本局时长；标题位可被事件播报条临时替换。"""

    def compose(self) -> ComposeResult:
        yield HeaderIcon().data_bind(Header.icon)
        yield HeaderTicker(id="header-ticker")
        yield HeaderTitle()
        yield RunClock()
