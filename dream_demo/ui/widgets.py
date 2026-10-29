"""界面控件：地图视图、右侧面板容器、原生按钮、本局时长标题栏。"""

from __future__ import annotations

import os
import time

from rich.text import Text
from textual.containers import Vertical
from textual.geometry import Region
from textual.app import ComposeResult
from textual.widgets import Button, Header, Static
from textual.events import MouseDown, MouseMove, MouseScrollDown, MouseScrollUp
from textual.widgets._header import HeaderClockSpace, HeaderTitle
from textual.visual import visualize

from ..core import GameState
from .styles import MAP_DEFAULT_ZOOM, MAP_ZOOM_LEVELS, highlighted_message
from ..i18n import tr
from ._native import _trace_native
from .glyphs import viewport_origin
from .render import render_map
from .frame_geometry import cell_ranges, compose_fx
from .ornament_frame import OrnamentBorderMixin, solid_right_edge
from .glass_button import GlassButtonMixin
from .world_renderer import WorldCanvas


def _dim_hex(color: str, factor: float) -> str:
    """把 #rrggbb 按亮度系数压暗；非六位十六进制原样返回。"""
    value = color.lstrip('#')
    if len(value) != 6:
        return color
    try:
        r, g, b = (int(value[index:index + 2], 16) for index in (0, 2, 4))
    except ValueError:
        return color
    return '#{:02x}{:02x}{:02x}'.format(round(r * factor), round(g * factor), round(b * factor))


VISUALS_ONLY_ENV = 'ONEIRSCRIPT_IMAGE_VISUALS_ONLY'


def _image_visuals_only() -> bool:
    """F3（2026-10-27）：图像模式跳过 render_map 的 Text 组装，默认开。

    present_scene 在把 visuals 交给图像后端时**不读**传入的文本（M2-A 快路径），
    所以 image 模式的这一帧 Text（逐格 append + 样式叠加 + span）没有任何
    消费者。设 ``ONEIRSCRIPT_IMAGE_VISUALS_ONLY=0`` 完整回退到旧行为。
    """
    value = os.environ.get(VISUALS_ONLY_ENV, '1').strip().lower()
    return value not in ('0', 'false', 'off', 'no')


def _image_stable_reuse_enabled() -> bool:
    """F1（2026-10-27）：像素级零脏时复用上一张合成图，默认开。

    栅格本来就是增量的（SceneImageCache 只重画脏格）；当本拍没有任何格被重画、
    覆盖层输入也没变时，重新 copy 一张图并整帧发给原生平面是纯浪费。
    设 ONEIRSCRIPT_IMAGE_STABLE_REUSE=0 回退。
    """
    value = os.environ.get('ONEIRSCRIPT_IMAGE_STABLE_REUSE', '1').strip().lower()
    return value not in ('0', 'false', 'off', 'no')


def _blank_base_text(width: int, height: int, cell_w: int, cell_h: int) -> Text:
    """图像后端的同尺寸空白基准帧。

    visuals_only 帧没有文本，但楼层过渡仍会对 last_base_text 做 cell_segments
    （需要完整的行/列网格，空 Text 会让切表越界）。图像模式的过渡只消费像素，
    这里给一份纯空白、逐行等宽的帧即可——构造是一次字符串拼接，不逐格 append。
    """
    line = ' ' * (max(1, width) * max(1, cell_w))
    return Text('\n'.join([line] * max(1, height * cell_h)), style='on #07070b')


class MapView(WorldCanvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.can_focus = True
        self.state: GameState | None = None
        self.symbol_mode = "themed"
        self.zoom = MAP_DEFAULT_ZOOM
        self.viewport = (0, 0, 1, 1)
        # 上一帧相机属于哪一层；只有同一层才允许跨尺寸沿用 left/top。
        self._camera_layer: str | None = None
        self._last_render: tuple[str, tuple] | None = None
        self._frame_key: tuple | None = None
        # M3 平滑呈现（2026-10-24）：本视图最近一次合成的采样键，以及最近一次
        # 真正写到终端（整包或 mini 事务补丁）的采样键。两者相等时无需再动。
        self._smooth_current_key: tuple | None = None
        self._smooth_emitted_key: tuple | None = None
        # 目标辅助路径格集合：render_map 据此黄底高亮（app 每帧同步）。
        self.assist_cells: set[tuple[int, int]] | None = None
        # 教程目标格：{格子: 叠加字形}——青金底色脉动 + 引导标记（app 每帧同步）。
        self.tutorial_cells: dict[tuple[int, int], str] | None = None
        # 篡改草稿的地图高亮（2026-10-24 用户定稿）：名称槽不再画 ①②/落 之类的
        # 汉字标记，改为类别色高亮——图像后端画朝向区域外的彩色描边（与观察
        # 光标的白色选中框同一套语言），字符后端画同色底色。三个字段由
        # update_state 从当前 world_tamper_editor 派生：
        # highlights = 全部名称槽的格 → 类别色；focus = 当前选中槽的格集合
        # （加粗一档）；destination = 聚流落点（强调色单独框出）。
        self.tamper_highlights: dict[tuple[int, int], str] = {}
        self.tamper_focus: frozenset[tuple[int, int]] = frozenset()
        self.tamper_destination: tuple[int, int] | None = None
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
        # F3（2026-10-27）：上一帧的逐格视觉事实。图像模式跳过 Text 组装后，
        # 「基帧变了」由这份字典的相等性判定（与图像像素等价）。
        self._last_visuals: dict | None = None
        # 未经视口计算的实例（单元测试直接构造 MapView()、或还没法算出内容尺寸）
        # 也要有合法格尺寸：叠加层脏区刷新会用 self.cell_w/cell_h 换算像素矩形。
        _zoom = self.zoom if self.zoom in MAP_ZOOM_LEVELS else MAP_DEFAULT_ZOOM
        self.cell_w, self.cell_h = max(1, round(2 * _zoom)), max(1, round(_zoom))
        self.cell_ranges = {}
        self.animated_combat = False
        self._scene_text = None
        self._scene_ranges = {}
        # 🔴 基帧覆盖标志（2026-10-10 性能 P1）：update_state 原生重画基帧时
        # 会把 widget 直接覆盖成无光照纯帧——此时 app._fx_frame_digest 即使
        # 相同也不能跳过补画（「摘要相同」≠「widget 上还是叠加帧」）。
        # fx_paint 写回叠加层后置回 False。
        self.fx_base_overwritten = False
        # 一次性标志：本帧基帧真的重画过（已经把 widget 标脏，随后的显示事务
        # 一定会整包写出一次）。图像后端里叠加层再走 emit_effect_frame 就是同一
        # 帧的第二次整包 present，所以叠加层写入时消费掉它并跳过那次写出。
        self._base_rerender_pending = False
        self._interaction_key = None
        self.shared_scene = None
        self._pending_shared_scene = None
        self._next_frame_defer = None
        self.display_mode = "character"
        self._image_cache = None
        self._image_effects = ({}, {})
        # 多层字符叠加（2026-10-26 ASCII 动画扩展）：世界格 -> tuple[GlyphLayer,...]。
        # 缺省为空，旧路径渲染结果逐像素不变。
        self._image_glyph_layers = {}
        self._image_protected_cells = frozenset()
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
        # F1（2026-10-27）：上一张合成图与它的覆盖层指纹；两者都没变且
        # _base_changed 为 False 时直接复用同一个对象（上游按 id(image) 去重）。
        self._image_stable_image = None
        self._image_stable_overlay = None
        # F1 的「本拍基帧有没有变」由 update_state 写；但 image_frame() 是公开
        # 入口，可能在第一拍 update_state 之前就被调用（独立挂载的 MapView、
        # 采样/测试宿主、过渡帧）。缺省按「已变」处理，只会多渲染一次，
        # 不会复用旧图；不初始化会在 image_frame 里直接 AttributeError
        # （2026-10-28 平台复测暴露）。
        self._base_changed = True

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
        self.cell_w, self.cell_h = cell_w, cell_h
        if self.content_size.width <= 0 or self.content_size.height <= 0:
            # 地图被整块遮住时（键位表/QoL 确认框把 #map 设成 visibility:hidden，
            # content_size 归零），这里会算出 1×1 的退化视口并把相机钉到玩家脚下，
            # 关掉浮层后地图就跳两格。看不见的那一帧不该改写相机。
            return self.viewport
        physical_cols = max(1, self.content_size.width - 1)
        width = max(1, min(physical_cols // cell_w, state.width))
        height = max(1, min(self.content_size.height // cell_h, state.height))
        # 相机跨尺寸锚定：可视格数一变（面板让宽、缩放、改窗口）原实现就把
        # previous 丢掉重新居中，整幅地图横向推 7 格、纵向推 4 行——玩家看到的是
        # 「切面板时地图跳一下」。同一层内玩家仍在上一帧视口里时改为沿用
        # left/top：变宽只在边缘多显几列，变窄由 viewport_origin 的死区逐格把
        # 玩家拉回中部带。换层、或玩家已经不在旧视口里（传送/被推走）时照旧居中。
        previous = self.viewport
        anchored: tuple[int, int] | None = None
        px, py = state.player.x, state.player.y
        if (self._camera_layer == state.layer_key() and previous[2] and previous[3]
                and previous[0] <= px < previous[0] + previous[2]
                and previous[1] <= py < previous[1] + previous[3]):
            anchored = previous[:2]
        left, top = viewport_origin(state, width, height, anchored)
        self._camera_layer = state.layer_key()
        layer = getattr(self.app, 'layer_observation', None)
        if layer is not None:
            left, top = self.viewport[:2]
            cx, cy = layer.cursor
            left = max(0,min(state.width-width, min(left,cx) if cx < left else max(left,cx-width+1)))
            # 分层观察的上下两条浮在地图上（见 ui/layer_observation.py 的
            # LayerStrip/LayerStatus：position absolute + overlay 层，顶 1 行、底 2 行），
            # 光标必须留在没被盖住的那一带，否则会躲到条子底下看不见。
            band_lo, band_hi = top + 1, top + height - 3
            if band_hi < band_lo:
                top = max(0, min(state.height - height, top))
            elif cy < band_lo:
                top = max(0, min(state.height - height, top - (band_lo - cy)))
            elif cy > band_hi:
                top = max(0, min(state.height - height, top + (cy - band_hi)))
        return (left, top, width, height)

    def _tamper_highlights(self) -> tuple[dict[tuple[int, int], str],
                                          frozenset[tuple[int, int]],
                                          tuple[int, int] | None]:
        """从当前篡改草稿派生地图高亮：(全部槽格→类别色, 选中槽格, 聚流落点)。

        左侧完整面板与右栏简版共用同一个 editor 对象，因此无论在哪一侧选择，
        地图上标的都是当前选中的那处；区域槽把整片成员都框出来。聚流/聚气
        未手动选落点时标出默认落点（与面板显示、提交执行同一入口）。
        """
        editor = getattr(self.app, "world_tamper_editor", None)
        sentence = getattr(editor, "sentence", None)
        if sentence is None:
            return {}, frozenset(), None
        highlights: dict[tuple[int, int], str] = {}
        focus: set[tuple[int, int]] = set()
        slots = tuple(getattr(sentence, "slots", ()) or ())
        selected = int(getattr(editor, "slot_index", 0) or 0) % max(1, len(slots))
        for index, slot in enumerate(slots):
            color = slot.color
            cells = tuple(getattr(slot, "region_members", ()) or ()) or ((slot.x, slot.y),)
            for cell in cells:
                highlights[cell] = color
                if index == selected:
                    focus.add(cell)
        destination = getattr(editor, "gather_destination", None)
        word_id = getattr(editor, "word_id", "")
        slot = getattr(editor, "slot", None)
        if (destination is None and word_id in ('gather_liquid', 'gather_gas')
                and slot is not None and getattr(slot, 'region_members', ())
                and self.state is not None):
            from ..core.tamper_fluid import default_gather_destination
            destination = default_gather_destination(self.state, slot, word_id)
        return highlights, frozenset(focus), destination

    def update_state(self, state: GameState) -> bool:
        defer_scene, defer_shared_scene = self._next_frame_defer or (False, False)
        self._next_frame_defer = None
        self.finish_pending_shared_scene()
        self._base_changed = False
        self.state = state
        viewport = self.viewport_for(state)
        left, top, width, height = viewport
        # 篡改高亮必须在基帧指纹**之前**派生：面板里换词/换槽不改世界，
        # 基帧指纹不变会走下面的复用路径，高亮却必须立刻跟着选中项走。
        self.tamper_highlights, self.tamper_focus, self.tamper_destination = (
            self._tamper_highlights())
        from ..core.sound_markers import KNOWN_GLYPH, sound_markers
        # Keep hearing facts intact; only suppress redundant map decorations
        # where the source itself is already visible. Selection stays explicit.
        self.sound_markers = {
            pos: mark for pos, mark in sound_markers(
                state, getattr(self.app, '_signal_clue_index', None)).items()
            if mark != KNOWN_GLYPH or not state.is_visible(*pos)
        }
        layer = getattr(self.app, 'layer_observation', None)
        display_mode = self.app.resolved_map_display()[0]
        frame_key = self._frame_signature(state, width, height) + (
            viewport, display_mode, layer.layer if layer else None,
            len(getattr(state, "explosion_cells", ()) or ()), getattr(state, "explosion_age", 0), self.animated_combat,
            tuple(sorted((self.tutorial_cells or {}).items())), state.time % 2,
            tuple(sorted(self.sound_markers.items())),
        )
        if frame_key == self._frame_key and self._last_render is not None:
            # 状态未变：跳过整张地图的重建，直接复用上一帧。
            self.viewport = viewport
            self.update_interaction()
            return False
        glyph_cell_w = max(2,self.cell_w) if display_mode == "image" else self.cell_w
        # M2-A（2026-10-24）：同一次界面刷新里 render_map 与 build_scene 共用
        # 一份可见集合（此前各解析一次；视野带缓存，但签名与查表仍要付一次钱）。
        visible = state.visible_cells()
        # 图像后端在渲染同一帧时顺手记下每格视觉事实，省掉 cell_ranges 与文本
        # 反解；字符后端继续走原文本路径（present_scene 无 visuals 时为旧实现）。
        visuals = {} if display_mode == "image" else None
        # F3（2026-10-27）：图像后端只消费 visuals——present_scene 拿到 visuals
        # 后不再读这一帧文本，所以非观察层的 image 帧不需要 Text 组装。
        # render_map(visuals_only=True) 只算逐格事实，返回空帧。
        visuals_only = bool(visuals is not None and layer is None and _image_visuals_only())
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
            markers=self.sound_markers or None,
            visuals=visuals,
            visible=visible,
            visuals_only=visuals_only,
        )
        from ..core.map_scene import build_scene, observe_scene
        from .map_presentation import present_scene, render_observation
        priority = set(self.sound_markers) | set(self.tutorial_cells or ())
        ranges_cell_w = glyph_cell_w
        ranges = None
        if visuals is None:
            # 同一帧的切片表只算一次（2026-10-21 任务3）：present_scene 与控件本身以前
            # 各算一遍，而它是这一帧里仅次于 render_map 的开销。
            ranges = cell_ranges(rendered, width, height, ranges_cell_w, self.cell_h)
        if defer_shared_scene and display_mode == "character" and layer is None:
            # The character frame and its FX don't consume the image scene. It
            # can be built immediately after the early terminal write, while
            # retaining the same scene for subsequent input and other views.
            self._pending_shared_scene = (state, viewport, self.cell_w, self.cell_h,
                                          rendered, priority, glyph_cell_w, ranges, visible)
            scene = None
        else:
            scene = build_scene(state, viewport=viewport, cell_w=self.cell_w, cell_h=self.cell_h,
                                legacy_terrain=not bool(getattr(state,"map_memory_enabled",False)),
                                visible=visible)
            self.shared_scene = present_scene(scene, rendered, priority=priority,
                source_cell_w=glyph_cell_w, ranges=ranges, visuals=visuals)
        # 新场景意味着上一帧采样贴片已不代表终端当前像素：mini 事务去重失效。
        self._smooth_emitted_key = None
        if layer is not None and layer.layer != 'composite':
            # 图像后端也消费同一份过滤结果：观察帧重新采成 visuals，切层时同屏
            # 只有一种地图，而不是图像继续画综合层。
            observed = observe_scene(scene, layer.layer)
            observed_visuals = {} if visuals is not None else None
            rendered = render_observation(observed, layer.layer, self.symbol_mode,
                                          markers=self.sound_markers or None,
                                          visuals=observed_visuals)
            # 观察帧按 scene.cell_w 重新排版（present_scene 的默认口径）。
            ranges_cell_w = self.cell_w
            ranges = (None if observed_visuals is not None else
                      cell_ranges(rendered, width, height, ranges_cell_w, self.cell_h))
            self.shared_scene = present_scene(observed, rendered, priority=priority,
                ranges=ranges, visuals=observed_visuals)
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
            self._image_glyph_layers = {}
            self._image_protected_cells = frozenset()
            self._image_fog_backgrounds = {}
            self._image_effects_key = None
        self._image_cache = None
        if visuals_only:
            # 这一帧没有文本：图像后端的「基帧变了」等价于逐格视觉事实变了。
            # 字典每帧新建、其后不再被修改，直接留存身份即可，不必复制。
            signature = ('visuals-only', ())
            changed = visuals != self._last_visuals or viewport != self.viewport
            self._last_visuals = visuals
        else:
            signature = (rendered.plain, tuple(rendered._spans))
            changed = signature != self._last_render or viewport != self.viewport
            self._last_visuals = None
        self._base_changed = bool(changed)
        self._last_render = signature
        # 最近一帧基准文本：FX 特效画布（#map-fx）在其上做叠加着色，
        # 不重复调用 render_map（渲染特效计划 §4 数据流）。visuals_only 帧没有
        # 文本，垫一份同尺寸空白帧：图像模式读它的楼层过渡只消费像素，但
        # cell_segments 需要完整网格（空 Text 会让切表越界）。
        self.last_base_text = (rendered if not visuals_only
                               else _blank_base_text(width, height, glyph_cell_w, self.cell_h))
        # 图像后端不再需要文本切片表（视觉事实已由 render_map 直接给出）；
        # 字符后端的 compose_fx 与观察光标仍消费它。
        self.cell_ranges = ranges if ranges is not None else {}
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
            self._base_rerender_pending = True
            # The painter's action path will immediately combine this base
            # with FX. Publishing the unlit base first needlessly rebuilds the
            # interaction layer and marks the widget dirty twice.
            if defer_scene and display_mode == "character" and layer is None:
                return True
            self.update_scene(rendered)
        else:
            self.update_interaction()
        return False

    def finish_pending_shared_scene(self) -> None:
        pending = self._pending_shared_scene
        if pending is None:
            return
        self._pending_shared_scene = None
        state, viewport, cell_w, cell_h, rendered, priority, source_w, ranges, visible = pending
        from ..core.map_scene import build_scene
        from .map_presentation import present_scene
        scene = build_scene(state, viewport=viewport, cell_w=cell_w, cell_h=cell_h,
                            legacy_terrain=not bool(getattr(state, "map_memory_enabled", False)),
                            visible=visible)
        self.shared_scene = present_scene(scene, rendered, priority=priority,
                                          source_cell_w=source_w, ranges=ranges)

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
               frozenset(self.tamper_highlights.items()), self.tamper_focus,
               self.tamper_destination,
               (id(self.shared_scene) if self.display_mode == "image" else None))
        if key == self._interaction_key:
            return
        self._interaction_key = key
        if self.display_mode == 'image':
            # 图像后端里这块控件的内容永远是同一张空白占位图（真正的像素由
            # OSC 图像或原生图像层画在上面）。旧实现每个移动帧都重建并 update
            # 一次 ~3600 字符的 Text：interaction key 含 shared_scene 身份，每步
            # 都会变，于是每步都标脏整块地图区域，让 Textual 合成器整屏重排
            # （2026-10-26 实测 profile：_render_chops ~30ms/步，是移动卡顿大头）。
            # 同一几何 + 样式的空白只写一次即可。
            _, _, width, height = self.viewport
            blank_key = (width, height, self.cell_w, self.cell_h)
            if getattr(self, '_image_blank_key', None) == blank_key:
                return
            self._image_blank_key = blank_key
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
        # 篡改草稿的槽位底色（字符后端的高亮边框等价物）：当前选中槽亮一档，
        # 其余名称槽暗一档；白色观察光标 / 预览字形仍画在其上。
        if self.tamper_highlights:
            focus = self.tamper_focus
            styles.update({pos: _dim_hex(color, .8 if cell in focus else .38)
                           for cell, color in self.tamper_highlights.items()
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

    def update_image_effects(self, styles, glyphs, force=False, fog_styles=None,
                             glyph_layers=None, protected_cells=None):
        from rich.style import Style
        from .effects import overlay_style
        from .map_presentation import foreground
        # 顶部就消费，避免下面的叠加层摘要去重提前返回时把标志留到下一帧，
        # 那会让一个纯动画帧误跳过 emitter、画面停在旧叠加层上。
        base_rerendered = self._base_rerender_pending
        self._base_rerender_pending = False
        now = time.monotonic()
        fog_styles = fog_styles or {}
        glyph_layers = dict(glyph_layers or {})
        protected_cells = frozenset(protected_cells or ())
        # The caller already throttles writes. Dropping a changed image state
        # here lets its caller record an unpainted digest, losing static sound
        # overlays (and their removal) until some unrelated effect changes.
        key = (self.viewport, frozenset(styles.items()),frozenset(glyphs.items()),
               frozenset(fog_styles.items()),frozenset(glyph_layers.items()),
               protected_cells)
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
        previous_backgrounds, previous_foregrounds = self._image_effects
        previous_layers = self._image_glyph_layers
        self._image_effects = backgrounds,foregrounds
        self._image_glyph_layers = glyph_layers
        self._image_protected_cells = protected_cells
        self._image_fog_backgrounds = fog_backgrounds
        self._image_effects_key = key
        self._image_effects_at = now
        self._image_cache = None
        if base_rerendered:
            # 叠加层状态已经写进本控件，而这一帧的基帧重画把整块地图标了脏：
            # 随后的显示事务会用这份新叠加层合成并整包写出一次。自己再走
            # emit_effect_frame（原生图像层里它就是一次完整 present）或退到
            # refresh() 都是同一帧的第二遍——真机实测每步 3.1 次地图写出。
            return
        # 图像后端：FX 只改图像叠加层时直接写脏格补丁。若走 refresh()，
        # Textual 会把地图控件的占位文字整片写到终端，覆盖内联图像；随后的
        # 补丁只能恢复变化格，其余地图会变黑。emitter 返回 False（guard 不满足、
        # 需要整包等）时仍回退常规 refresh()。
        # 未挂载的 MapView（单元测试里直接构造）没有 app：Textual 的 self.app
        # 会抛 NoActiveAppError，不能让它把叠加层更新整条打断。
        try:
            app = self.app
        except Exception:
            app = None
        emitter = getattr(app, 'emit_effect_frame', None)
        if self.display_mode == 'image' and emitter is not None:
            try:
                if emitter(self):
                    return
            except Exception:
                pass
        # 回退路径只重画真正变化的叠加格（2026-10-26）：整块 refresh 会让
        # Textual 合成器每个移动帧重排整张地图（无头实测 _render_chops 16–30ms/
        # 步）。叠加层通常只变玩家周围几格，按变化包围盒 refresh 即可；包围盒
        # 超过可见格一半或出现未知坐标时退回整块，避免局部刷新漏画面。
        changed = {pos for pos in set(previous_backgrounds) | set(backgrounds)
                   if previous_backgrounds.get(pos) != backgrounds.get(pos)}
        changed |= {pos for pos in set(previous_foregrounds) | set(foregrounds)
                    if previous_foregrounds.get(pos) != foregrounds.get(pos)}
        changed |= {pos for pos in set(previous_layers) | set(glyph_layers)
                    if previous_layers.get(pos) != glyph_layers.get(pos)}
        region = None
        if changed and self.viewport:
            _, _, width, height = self.viewport
            xs = [pos[0] - left for pos in changed]
            ys = [pos[1] - top for pos in changed]
            if xs and xs and min(xs) >= 0 and min(ys) >= 0 and max(xs) < width and max(ys) < height:
                span_w = max(xs) - min(xs) + 1
                span_h = max(ys) - min(ys) + 1
                if span_w * span_h * 2 <= width * height:
                    region = Region(min(xs) * self.cell_w, min(ys) * self.cell_h,
                                    span_w * self.cell_w, span_h * self.cell_h)
        if region is None:
            self.refresh()
        else:
            dx, dy = self.content_offset
            self.refresh(region.translate((-dx, -dy)))

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
        smooth_player = self._smooth_player_sample()
        smooth_key = None
        if smooth_player is not None:
            player_pos, sample = smooth_player
            smooth_key = (player_pos, round(sample[0] * cell_px[0]),
                          round(sample[1] * cell_px[1]))
        key = (id(self.shared_scene),cell_px,self.observe_cursor,frozenset(self.assist_cells or ()),self._image_effects_key,
               frozenset(preview.items()),frozenset(marks.items()),frozenset(self.intent_marks.items()),
               frozenset(self.tamper_highlights.items()),self.tamper_focus,self.tamper_destination,
               smooth_key)
        self._smooth_current_key = smooth_key
        # F1（2026-10-27）像素级零脏：本拍的逐格视觉事实与上一拍相同（_base_changed
        # 由 update_state 用 visuals 内容判定）、覆盖层输入也没变、且上一张确实
        # 来自 SceneImageCache → 不重渲染、不 copy、返回同一个对象。上游
        # _present_native_map 的 key 含 id(image)，对象不变即整帧不发
        # （实测每帧 3.12MB 共享内存 + worker 合成全部省掉）。
        overlay_key = key[1:]
        if (_image_stable_reuse_enabled()
                and self._image_stable_image is not None
                and not self._base_changed
                and self._image_base_cached
                and self._image_stable_overlay == overlay_key):
            self._image_cache = (key, self._image_stable_image)
            return self._image_stable_image
        if self._image_cache and self._image_cache[0] == key:
            return self._image_cache[1]
        base = render_scene_image(self.shared_scene, cell_px=cell_px,
                                  backgrounds=self._image_effects[0],effect_glyphs=self._image_effects[1],
                                  fog_backgrounds=self._image_fog_backgrounds,
                                  glyph_layers=self._image_glyph_layers,
                                  protected_cells=self._image_protected_cells,
                                  cache=self._raster_cache)
        # C7：仅当基础栅格确实来自 SceneImageCache 时，逐格脏格补丁才有像素
        # 语义；光照/过渡等逐格渲染路径保持整包重发。
        self._image_base_cached = base is self._raster_cache.image
        image = base.copy()
        smooth_cells = ()
        if smooth_player is not None:
            from .map_image import draw_movement_presentation
            _player_pos, sample = smooth_player
            smooth_cells = draw_movement_presentation(
                image, self.shared_scene, sample, cell_px,
                backgrounds=self._image_effects[0],
                fog_backgrounds=self._image_fog_backgrounds)
        draw = ImageDraw.Draw(image)
        left,top,width,height = self.viewport
        overlay_sig = {}
        # 篡改草稿的彩色选中框（2026-10-24）：名称槽按类别色描边——只有朝向
        # 高亮区外的边画线（与 §15.6 预览同一规则），整片区域读成一个轮廓；
        # 当前选中槽加粗一档；聚流落点用强调色单独框出。先于白色观察光标画，
        # 光标所在格的白框永远压在高亮之上。
        if self.tamper_highlights:
            highlight_set = set(self.tamper_highlights)
            focus_set = set(self.tamper_focus)
            tw, th = cell_px
            for pos, color in sorted(self.tamper_highlights.items()):
                if not (left <= pos[0] < left+width and top <= pos[1] < top+height):
                    continue
                x, y = (pos[0]-left)*tw, (pos[1]-top)*th
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    if (pos[0]+dx, pos[1]+dy) in highlight_set:
                        continue
                    if dx:
                        edge = x + (tw - 1 if dx > 0 else 0)
                        draw.line((edge, y, edge, y + th - 1), fill=color, width=1)
                    else:
                        edge = y + (th - 1 if dy > 0 else 0)
                        draw.line((x, edge, x + tw - 1, edge), fill=color, width=1)
                overlay_sig[pos] = overlay_sig.get(pos, ()) + (('tamper', color),)
            for pos in sorted(focus_set):
                if not (left <= pos[0] < left+width and top <= pos[1] < top+height):
                    continue
                color = self.tamper_highlights.get(pos)
                if not color:
                    continue
                x, y = (pos[0]-left)*tw, (pos[1]-top)*th
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    if (pos[0]+dx, pos[1]+dy) in focus_set:
                        continue
                    if dx:
                        edge = x + (tw - 1 if dx > 0 else 0)
                        draw.line((edge, y, edge, y + th - 1), fill=color, width=2)
                    else:
                        edge = y + (th - 1 if dy > 0 else 0)
                        draw.line((x, edge, x + tw - 1, edge), fill=color, width=2)
                overlay_sig[pos] = overlay_sig.get(pos, ()) + (('tamper-focus', color),)
        if self.tamper_destination is not None:
            pos = self.tamper_destination
            if left <= pos[0] < left+width and top <= pos[1] < top+height:
                tw, th = cell_px
                x, y = (pos[0]-left)*tw, (pos[1]-top)*th
                draw.rectangle((x, y, x+tw-1, y+th-1), outline='#7ad0ff', width=2)
                overlay_sig[pos] = overlay_sig.get(pos, ()) + ('tamper-dest',)
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
        if smooth_key is not None:
            for pos in smooth_cells:
                overlay_sig[pos] = overlay_sig.get(pos, ()) + ('smooth-player', smooth_key)
        self._image_overlay_sig = overlay_sig
        self._image_cache = key,image
        self._image_stable_image = image
        self._image_stable_overlay = overlay_key
        return image

    def _smooth_player_sample(self):
        """Return the active image-only player sample, snapping on invalid geometry."""
        plane = getattr(self.app, '_native_image_plane', None)
        if plane is not None and not plane.error:
            return None  # 原生层同时采样玩家与相机；这里保留准确的最终场景。
        movement = getattr(self.app, "_movement_presentation", None)
        if movement is None:
            return None
        config = getattr(self.app, "config", None)
        try:
            setting_enabled = bool(config.get("smooth_movement"))
            reduced = bool(config.get("fx_reduce_motion"))
        except (AttributeError, KeyError, TypeError):
            setting_enabled, reduced = False, True
        now = time.monotonic()
        live = getattr(self.app, "_world_view_live", None)
        if live is None:  # 轻量假 App（单元测试）沿用旧的 world 判定
            live = lambda: getattr(self.app, "panel_mode", "world") == "world"
        enabled = (setting_enabled and not reduced and self.display_mode == "image"
                   and live()
                   and not getattr(self.app, "aiming", False)
                   and not getattr(self.app, "observe_mode", False)
                   and getattr(self.app, "layer_observation", None) is None)
        if not enabled:
            if movement.is_active(now):
                scene = self.shared_scene
                player_pos = next((pos for pos, cell in (scene.cells.items() if scene else ())
                                   if any(actor.relation == "player" for actor in cell.actors)), None)
                if player_pos is not None:
                    movement.reset((player_pos[0] - self.viewport[0],
                                    player_pos[1] - self.viewport[1]))
                    self.app._movement_presentation_needs_final_frame = True
            self.app._movement_presentation_viewport = None
            return None
        scene = self.shared_scene
        if scene is None or scene.observe_layer:
            return None
        player_pos = next((pos for pos, cell in scene.cells.items()
                           if any(actor.relation == "player" for actor in cell.actors)), None)
        if player_pos is None:
            return None
        target = (float(player_pos[0] - self.viewport[0]),
                  float(player_pos[1] - self.viewport[1]))
        if getattr(self.app, "_movement_presentation_viewport", None) != self.viewport:
            movement.reset((int(target[0]), int(target[1])))
            self.app._movement_presentation_viewport = None
            return None
        if not movement.is_active(now) or movement.target != target:
            movement.reset((int(target[0]), int(target[1])))
            self.app._movement_presentation_viewport = None
            return None
        return player_pos, movement.sample(now)

    def try_emit_presentation_frame(self) -> bool:
        """M3：不经过 Textual 重绘，直接把当前采样写成地图补丁（mini 事务）。

        动画中间帧只有角色像素在动：文字、视口、底图 token 全部不变。走整屏
        重绘会被 ~90ms 的合成/排版周期拖死（实测 <12Hz），因此帧回调在本帧
        自行合成采样图，并让 app 用带 2026 同步标记的小事务把脏格补丁写入
        同一个 driver 输出队列（单写者保序，不破坏擦除/覆盖次序）。任何
        guard 不满足都返回 False，调用方退回常规 refresh() 整帧路径。
        """
        if self.display_mode != "image" or self.shared_scene is None:
            return False
        image = self.image_frame()
        key = self._smooth_current_key
        if key is None:
            # 采样已失效（对齐/关闭/遮挡）：交给常规整帧路径。
            return False
        if key == self._smooth_emitted_key:
            return True
        emitted = self.app.emit_presentation_patch(self, image)
        if emitted:
            self._smooth_emitted_key = key
        return emitted

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
        smooth_player = self._smooth_player_sample()
        if smooth_player is not None:
            player_pos, sample = smooth_player
            map_x, map_y = local_x / cell_w, local_y / cell_h
            if (sample[0] <= map_x < sample[0] + 1
                    and sample[1] <= map_y < sample[1] + 1):
                return player_pos
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


class ClickableHoverInfo(Static):
    """右上角「当前地形所在格」读数：点击等于右键自己所在格。

    只负责把点击转成左侧格子详情面板；读数内容仍由 panels._hover_text 生成。
    观察模式/模态窗口的守卫交给 open_cell_detail 与宿主状态判断。
    """

    def update(self, content="") -> None:
        # Terrain descriptions change on each step. With a fixed width, equal
        # wrapped height leaves the sidebar geometry unchanged.
        width = self.content_size.width
        if (self.is_mounted and width > 0 and not self._layout_required
                and not self.styles.is_auto_width and self.styles.is_auto_height
                and self._visual is not None):
            visual = visualize(self, content)
            if visual.get_height(width) == self._visual.get_height(width) == self.content_size.height:
                self._content = content
                self._visual = visual
                self.refresh()
                return
        super().update(content)

    def on_mouse_down(self, event: MouseDown) -> None:
        if event.button != 1:
            return
        app = self.app
        if getattr(app, 'home_mode', False):
            return
        try:
            state = app.session.state
            app.open_cell_detail((state.player.x, state.player.y))
        except Exception:
            return
        event.stop()
        event.prevent_default()


class EventPanel(OrnamentBorderMixin, WorldCanvas):
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
        self.app._select_input_region('overlay')
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

    def render_lines(self, crop):
        # 2026-10-26：图鉴左列表的右边缘就是两栏之间的那条中线。装饰珠链
        # （│·│◇│╰│ 逐行循环）把点、菱形与转角放到这条本该笔直的线上，
        # 恰好紧贴右侧详情 Panel 的实线边框（只隔一列），扫描时就像个别行
        # 错开半格。中线锁成连续竖线；左右上下的其余三边照旧走装饰。
        strips = super().render_lines(crop)
        return solid_right_edge(strips, crop, self.region.width, self.region.height)

    def on_resize(self, event) -> None:
        # 两列布局按列表可用宽裁字：窗口尺寸变了要重算列宽与省略号。
        if getattr(self.app, "panel_mode", "") in ("home_catalog", "pause_codex"):
            self.app.call_after_refresh(
                self.app._refresh_codex_components, self.app._symbol_mode())

    def on_mouse_down(self, event: MouseDown) -> None:
        # offset 含 1 行边框 + 1 行内边距：扣掉才是条目行号（否则点击的
        # 行与 ▶ 选中行错位两行——「图鉴鼠标光标错位」的根源）。
        # 两列布局：右半区按第二列取条目。
        content_width = max(1, self.content_size.width)
        relative_x = max(0, event.offset.x - 2)
        column_width = max(8, (content_width - 2) // 2)
        column = 1 if relative_x >= column_width + 2 else 0
        self.app.select_codex_row(event.offset.y - 2, column)
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


class NativeButton(GlassButtonMixin, OrnamentBorderMixin, Button):
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


class _PassiveHeaderIcon(Static):
    """顶栏图标只作装饰：不继承 HeaderIcon，点击不会打开 Textual 命令面板。

    Textual 的消息调度会沿 MRO 同时执行子类与基类的 on_click，覆写挡不住
    基类动作；换成普通 Static 才能从源头不注册命令面板。
    """

    DEFAULT_CSS = """
    _PassiveHeaderIcon {
        dock: left;
        padding: 0 1;
        width: 8;
        content-align: left middle;
    }
    """

    def __init__(self) -> None:
        super().__init__("⭘", markup=False)

    async def on_click(self, event) -> None:
        event.stop()


class DreamHeader(Header):
    """标准 Header 布局，右侧时钟位换成本局时长；标题位可被事件播报条临时替换。

    点击顶栏不切换 Textual 的三行「拉伸」状态，也不弹出命令面板——
    顶栏是纯展示区，高度恒为一行。
    """

    def toggle_class(self, *class_names: str, exclusive: bool = False) -> None:
        # Header._on_click 的 -tall 切换同样会跨 MRO 执行，覆写 _on_click
        # 拦不住基类；在 toggle_class 这层丢掉 -tall，保持恒一行。
        kept = tuple(name for name in class_names if name != "-tall")
        if kept:
            super().toggle_class(*kept, exclusive=exclusive)

    def compose(self) -> ComposeResult:
        yield _PassiveHeaderIcon()
        yield HeaderTicker(id="header-ticker")
        yield HeaderTitle()
        yield RunClock()
