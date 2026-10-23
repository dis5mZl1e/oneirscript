"""Live map image output inside Textual's own ordered display transaction."""
from __future__ import annotations

import sys
import asyncio
import json
import os
import subprocess
import time
import traceback

from .map_image_transport import (
    cells_to_rectangles, image_patches_enabled, image_region_packets,
    overlay_dirty_cells, overlay_patch_rectangles, visible_rectangles,
)
from ..i18n import tr
from ..env_compat import get as env_get, name as env_name


IMAGE_WRITE_DEDUPE_ENV = env_name('IMAGE_WRITE_DEDUPE')
IMAGE_DIRTY_ENV = env_name('IMAGE_DIRTY')
# 像素差脏格补丁的安全阈值：任一超限就整包（比「猜着发」便宜也安全）。
DIRTY_MAX_VISIBLE_FRACTION = 0.55   # 变化面积 / 可见贴图面积
DIRTY_MAX_CELLS = 160               # 实际变化格上限
DIRTY_MAX_PATCHES = 8               # 合并后的补丁矩形上限（超过则整包）
DIRTY_MERGE_RADIUS = 2              # 合并脏格时的膨胀半径（少发包、略多字节）


def _band_rectangles(cells, limit):
    """把脏格按「连续行带」合并成整行段矩形，把 packet 数压到上限。

    只在单一可见区域（无浮层裁切）时使用：矩形仍完全落在可见区。行带会多
    覆盖同一行带内两处变化之间的未变格（多画同色像素），但 O(格数) 且
    packet 数 = 行带数，通常远小于按连通块切分的矩形数。
    """
    rows = {}
    for x, y in cells:
        lo, hi = rows.get(y, (x, x))
        rows[y] = (min(lo, x), max(hi, x))
    bands = []
    for y in sorted(rows):
        lo, hi = rows[y]
        if bands and y == bands[-1][1] + bands[-1][3]:
            by, bx0, bx1, bh = bands[-1]
            bands[-1] = (by, min(bx0, lo), max(bx1, hi), bh + 1)
        else:
            bands.append((y, lo, hi, 1))
    if len(bands) > limit:
        return None
    return [(bx0, by, bx1-bx0+1, bh) for by, bx0, bx1, bh in bands]


def _image_dirty_enabled() -> bool:
    """C13b 像素差脏格补丁开关：默认关闭（原生可见帧 A/B 前不改变输出路径）。

    每次现读 ONEIRSCRIPT_IMAGE_DIRTY；任何不确定/超大变化/文字或几何变化
    都必须回退整包，见 LiveMapMixin._map_dirty_packets。
    """
    return (env_get('IMAGE_DIRTY', '0') or '').strip().lower() in (
        '1', 'true', 'yes', 'on')


def _image_write_dedupe_enabled() -> bool:
    """C13 图像输出去重开关：默认关闭，等原生 A/B 证据（task-14）再议默认。

    只有「同一合成图 + 同一地图区域文字签名 + 同一 geometry/裁切/屏幕」时才
    允许跳过整包重发；任何读不到/不确定的状态都必须回退整包。
    """
    return (env_get('IMAGE_WRITE_DEDUPE', '0') or '').strip().lower() in (
        '1', 'true', 'yes', 'on')


def _map_region_render_signature(renderable, region):
    """C13：本帧 Textual 真正写入地图区域的文字签名；读不到返回 None。

    spans/chops 与 _map_damage 同源（合成器本批要写的行/列片段），签名只取
    地图 content_region 内的裁剪片段与文字内容：浮层/文字/裁切任何变化都会
    改签名，调用方随即放弃跳过。非 ChopsUpdate（无 spans/chops）一律 None。
    """
    spans = getattr(renderable, 'spans', None)
    chops = getattr(renderable, 'chops', None)
    if spans is None or chops is None:
        return None
    left0, top0 = region.x, region.y
    right0, bottom0 = region.x + region.width, region.y + region.height
    rows = []
    for y, x1, x2 in spans:
        if not (top0 <= y < bottom0):
            continue
        left, right = max(int(x1), left0), min(int(x2), right0)
        if right <= left:
            continue
        row = chops[y] if y < len(chops) else None
        content = []
        if row:
            for start, strip in row.items():
                if strip is None:
                    continue
                end = start + strip.cell_length
                lo, hi = max(start, left), min(end, right)
                if hi <= lo:
                    continue
                try:
                    text = strip.crop(lo - start, hi - start).text
                except Exception:
                    text = strip.text[max(0, lo - start):max(0, hi - start)]
                content.append((lo, hi, text))
        rows.append((y, left, right, tuple(content)))
    return (left0, top0, region.width, region.height, tuple(rows))


class LiveMapMixin:
    _image_output_error = ''
    _image_restore_fallback = False
    _map_damage = True
    _map_extra_sync = False
    # C7 脏格补丁（默认关闭）：上一帧合成图/基础栅格版本/叠加层指纹。
    _map_patch_state = None
    _map_patch_frames = 0
    _map_patch_packet_count = 0
    _map_patch_errors = 0
    # C13 图像输出去重（默认关闭）：上一帧真正写到终端的状态 + 跳过计数。
    _map_render_signature = None
    _map_clip_state = None
    _map_dedupe_state = None
    _map_dedupe_skips = 0
    _map_dedupe_skip_packets = 0
    _map_dedupe_skip_bytes = 0
    _map_dedupe_writes = 0
    # 屏幕切换/不确定状态 → 强制下一次整包重发（不做去重跳过）。
    _map_force_repaint = False
    _map_last_display_screen = None
    # C13b 像素差脏格补丁：终端当前显示图 + 上次写图时的几何/状态。
    _map_display_state = None          # 观察层/浮层/面板等显示指纹
    _map_terminal_image = None         # 终端上当前显示的完整地图图像
    _map_terminal_source = None        # 该镜像对应的 view.image_frame() 对象
    _map_terminal_tokens = None        # 该镜像对应的 SceneImageCache.cells 快照
    _map_terminal_overlay_sig = None   # 该镜像对应的叠加层逐格指纹
    _map_terminal_raster_geometry = None
    _map_terminal_state = None
    _map_dirty_frames = 0              # 真正发过补丁的帧
    _map_dirty_skips = 0               # 像素完全一致、整帧跳过
    _map_dirty_fallbacks = 0           # 进入 dirty 判定但回退整包
    _map_dirty_errors = 0
    _map_dirty_patch_count = 0
    _map_dirty_patch_bytes = 0
    _map_dirty_cells = 0
    _map_dirty_detect_calls = 0
    _map_dirty_detect_ms = 0.0
    _map_dirty_encode_ms = 0.0
    _map_dirty_last_reason = ''

    def _begin_update(self):
        # ConPTY may never report Textual's synchronized-output capability.
        # Our bundled WezTerm supports mode 2026; hold text erasure and PNG
        # transfer in one display transaction even when that probe was absent.
        self._map_extra_sync = bool(
            self._driver is not None and not self.is_headless
            and not self._sync_available
            and os.environ.get('TERM_PROGRAM') == 'WezTerm'
            and os.environ.get('WEZTERM_PANE') and not os.environ.get('TMUX')
            and self.resolved_map_display()[0] == 'image')
        if self._map_extra_sync:
            self._driver.write('\x1b[?2026h')
        super()._begin_update()

    def _schedule_map_geometry_probe(self):
        if (self.is_headless or self.config.get('map_display') == 'character'
                or not os.environ.get('WEZTERM_PANE')):
            return
        timer = getattr(self,'_map_geometry_timer',None)
        if timer is not None:
            timer.stop()
        self._map_geometry_timer = self.set_timer(.15,lambda:self.run_worker(
            self._probe_map_geometry(),group='map-pixel-geometry',exclusive=True))

    async def _probe_map_geometry(self):
        """ConPTY Resize lacks pixels; query once per resize, never per frame."""
        from .image_preview import wezterm_executable
        from textual.geometry import Size
        executable = wezterm_executable()
        if executable is None:
            return
        pane = os.environ.get('WEZTERM_PANE','')
        try:
            options = dict(capture_output=True,timeout=2,check=False)
            if sys.platform == 'win32':
                options['creationflags'] = subprocess.CREATE_NO_WINDOW
            result = await asyncio.to_thread(subprocess.run,
                [str(executable),'cli','list','--format','json'],**options)
            records = json.loads(result.stdout)
            if not isinstance(records,list):
                return
            for record in records:
                if not isinstance(record,dict):
                    continue
                if str(record.get('pane_id')) != pane:
                    continue
                geometry = record.get('size',{})
                width,height = int(geometry.get('pixel_width',0)),int(geometry.get('pixel_height',0))
                if width > 0 and height > 0:
                    self._map_terminal_pixels = Size(width,height)
                    columns,rows=int(geometry.get('cols',0)),int(geometry.get('rows',0))
                    if columns > 0 and rows > 0:
                        self._map_terminal_cell_pixels = (width/columns,height/rows)
                    if self.query('#map'):
                        self.query_one('#map')._image_cache = None
                        self.query_one('#map').refresh()
                break
        except (OSError,ValueError,KeyError,TypeError,AttributeError,subprocess.TimeoutExpired):
            # The bundled font has a known square 2-column geometry; preserve
            # this baseline if a custom multiplexer can't provide dimensions.
            return

    def check_action(self, action, parameters):
        if (self._image_output_error and self.config.get('map_display') != 'character'
                and action not in ('image_preview','cancel_ui','save_exit')):
            return False
        return super().check_action(action, parameters)

    def _map_startup_notice(self):
        if self.is_headless or self.home_mode or getattr(self,'_map_fallback_notified',False):
            return
        mode, reason = self.resolved_map_display()
        if self.config.get('map_display') != 'character' and mode == 'character' and self.layer_observation is None:
            self._map_fallback_notified = True
            self.show_toast(reason)

    def _display(self, screen, renderable):
        # Decoration outside the map must not trigger PNG encoding or transfer.
        spans = getattr(renderable, 'spans', None)
        region = None
        try:
            region = self.query_one('#map').content_region
            self._map_damage = (spans is None or any(
                region.y <= y < region.bottom and x2 > region.x and x1 < region.right
                for y, x1, x2 in spans))
        except Exception:
            self._map_damage = True
        # 屏幕切换（模态设置/返回游戏）会让 Textual 整屏重绘：下一次地图显示
        # 必须整包重发，不能沿用去重。只在真正的地图写图后清除该标记。
        screen_id = id(screen)
        if self._map_last_display_screen != screen_id:
            self._map_last_display_screen = screen_id
            self._map_force_repaint = True
        # C13：只有开关打开时才计算「本帧将写入地图区域的文字签名」；默认关。
        if region is not None and (_image_write_dedupe_enabled() or _image_dirty_enabled()):
            try:
                self._map_render_signature = _map_region_render_signature(
                    renderable, region)
            except Exception:
                self._map_render_signature = None
        else:
            self._map_render_signature = None
        super()._display(screen, renderable)

    def _end_update(self):
        try:
            if (self._driver is not None and not self.is_headless
                    and (getattr(self, '_map_damage', True)
                         or getattr(self, '_map_force_repaint', False))
                    and not self._image_output_error):
                if self._write_live_map():
                    self._layer_return_pending = None
        except Exception as error:
            self._image_output_error = str(error)
            self._image_failure_trace = traceback.format_exc()
            self.call_later(self._show_image_failure)
        finally:
            try:
                super()._end_update()
            finally:
                if self._map_extra_sync and self._driver is not None:
                    self._driver.write('\x1b[?2026l')
                self._map_extra_sync = False

    def _show_image_failure(self):
        error=self._image_output_error
        # Handled display errors previously left no report and permanently
        # blocked play after Textual had already painted its black placeholder.
        try:
            folder=self.session.manager.directory
            folder.mkdir(parents=True,exist_ok=True)
            (folder/'image-output-error.log').write_text(
                error+'\n'+getattr(self,'_image_failure_trace',''),encoding='utf8')
        except OSError:
            pass
        self._clear_held()
        self.path.clear()
        if self._recover_layer_observation():
            self.notify(tr('返回图像失败，已保留字符观察与草稿；F2 可重新选择地图模式。'),
                        severity='warning', timeout=30)
            return
        self._image_restore_fallback = True
        self._image_output_error = ''
        self._map_packet_key = self._map_packet_image = None
        self._map_packets = ()
        self._map_patch_state = None
        self._map_dedupe_state = None
        self._map_terminal_image = None
        self._map_terminal_source = None
        self._map_terminal_tokens = None
        self._map_terminal_overlay_sig = None
        self._map_terminal_raster_geometry = None
        self._map_terminal_state = None
        self._map_display_state = None
        from .map_image import _tile
        from .map_presentation import glyph_mask, raster_font
        _tile.cache_clear()
        glyph_mask.cache_clear()
        raster_font.cache_clear()
        if self.query('#map'):
            view=self.query_one('#map')
            view._frame_key = view._interaction_key = view._image_cache = None
        self.refresh_view()
        self.screen.refresh(layout=True)
        self.notify(tr('图像暂时不可用，已恢复字符地图；F2 可重试图像。'),
                    severity='warning', timeout=15)

    def _map_clip_signature(self, view, region, columns, rows):
        """遮挡几何指纹：只要它不变，裁切矩形就可以原样复用。

        为什么要指纹而不是「按窗口大小缓存」：遮挡来自浮层（详情、篡改、图例、
        确认层、提示气泡）的出现、移动、缩放与叠放，窗口尺寸根本没变。这里直接
        取合成器**当前这一批行**的分层结果（和 ``get_widget_at`` 查的是同一份
        数据），所以叠放顺序、控件显隐、外框位置任何一样变了，指纹都会变。

        读不到控件状态时返回 ``None``（调用方按未缓存处理），不猜。
        """
        compositor = self.screen._compositor
        layers = compositor.layers_visible
        parts = [(id(self.screen), region.x, region.y, columns, rows,
                  self.size.width, self.size.height)]
        try:
            for y in range(region.y, min(region.y + rows, len(layers))):
                row = layers[y]
                parts.append((y, tuple(
                    (id(widget), str(getattr(widget, "id", "")),
                     box.x, box.y, box.width, box.height, bool(widget.visible))
                    for widget, box, _region in row)))
        except Exception:
            return None
        return tuple(parts)

    def _map_clip_rectangles(self, view, region, columns, rows, uncovered):
        """返回需要贴图的终端矩形；布局稳定时直接复用上一帧的结果。

        每帧逐格问一次合成器（``get_widget_at``）在 60×17 的地图上是 1020 次
        查询，而浮层通常整分钟都不动一下。缓存键是上面那份遮挡几何指纹，
        地图内部内容变化（也就是最常见的移动）不会让它失效。
        """
        signature = self._map_clip_signature(view, region, columns, rows)
        self._map_clip_state = signature
        if signature is not None:
            cached = getattr(self, "_map_clip_cache", None)
            if cached is not None and cached[0] == signature:
                self._map_clip_hits = getattr(self, "_map_clip_hits", 0) + 1
                return cached[1]
        rectangles = visible_rectangles((region.x, region.y, columns, rows), uncovered)
        if signature is not None:
            self._map_clip_cache = (signature, rectangles)
            self._map_clip_misses = getattr(self, "_map_clip_misses", 0) + 1
        return rectangles

    @staticmethod
    def _map_packet_for_write(packet):
        if sys.platform == 'win32':
            # ConPTY doesn't flush cursor coordinates while hidden. Show only
            # around the packet, then restore Textual's cursor mode.
            return '\x1b[?25h'+packet+'\x1b[?25l'
        return packet

    def _write_map_packets(self, packets):
        for packet in packets:
            for offset in range(0,len(packet),8192):
                self._driver.write(packet[offset:offset+8192])

    def _map_patch_snapshot(self, view, image, geometry):
        """记录本帧合成图，供下一帧判断能否只发脏格补丁。"""
        state = view.image_patch_state()
        if state is None or state[0] is not image:
            return None
        cached_image, scene, revision, signature = state
        return (image, scene, revision, signature, geometry, image.size)

    def _map_patch_packets(self, view, image, region, geometry, scale, rectangles):
        """C7：算出脏格补丁 packet；None 表示必须整包重发。

        这是默认关闭的可选路径（ONEIRSCRIPT_IMAGE_PATCHES=1 才调用）。所有
        前提都必须成立才走补丁：上一次输出的是同一份合成图、基础栅格版本
        （SceneImageCache 计数）未变、场景对象未换、裁切几何与图像尺寸相同。
        旧叠加层格会随差异格一起补发新 base 像素，完成旧光标擦除；被浮层遮挡
        的格跳过（几何一变就整包重发，浮层撤走时自然补全）。
        """
        state = self._map_patch_state
        parts = view.image_patch_state()
        if state is None or parts is None:
            return None
        (previous_image, previous_scene, previous_revision, previous_sig,
         previous_geometry, previous_size) = state
        cached_image, scene, revision, signature = parts
        if (cached_image is not image or previous_revision != revision
                or scene is not previous_scene):
            return None
        if previous_geometry != geometry or previous_size != image.size:
            return None
        patch_rectangles = overlay_patch_rectangles(
            previous_sig, signature,
            viewport=view.viewport, cell_size=(view.cell_w, view.cell_h),
            region=region, visible=rectangles)
        if not patch_rectangles:
            # 没有可见脏格时不做增量：保持整包路径的「重发以覆盖文字重绘」
            # 语义（默认关闭的补丁路径不应成为新的残影来源）。
            return None
        self._map_patch_packet_count += len(patch_rectangles)
        return [self._map_packet_for_write(packet)
                for _rect, packet in image_region_packets(
                    image, region, scale, patch_rectangles)]

    def _map_display_fingerprint(self):
        """C13b：会整层改变地图显示的状态指纹；变化时脏格/整包缓存全部失效。

        观察层进出、浮层/层条/层状态显隐、面板模式、瞄准/意图/目标辅助、窗口
        尺寸任一变化，都可能让 Textual 重绘地图区域或移动/裁掉图像；这类帧
        不允许做像素差补丁或去重跳过，必须整包重发。
        """
        layer = getattr(self, 'layer_observation', None)
        try:
            overlay = (
                bool(self.query_one('#map-overlay').display),
                bool(self.query_one('#layer-strip').display),
                bool(self.query_one('#layer-status').display),
            )
        except Exception:
            overlay = None
        return (
            id(layer), bool(getattr(self, 'observe_mode', False)),
            bool(getattr(self, 'aiming', False)),
            id(getattr(self, 'sentence_aim', None)),
            bool(getattr(self, 'target_assist', False)),
            str(getattr(self, 'panel_mode', '')),
            bool(getattr(self, 'home_mode', False)),
            overlay, (self.size.width, self.size.height),
        )

    def _map_store_terminal(self, view, image, geometry, region, columns, rows):
        """记录「终端上当前显示的完整地图图像」及其可信状态。

        脏格补丁会原地 paste 更新终端镜像；这里必须存一份私有副本，绝不能
        改到 view.image_frame() 的缓存对象（否则下一帧比较/其它消费方会读到
        被补丁污染的画面）。同时快照 SceneImageCache 的逐格 token 与叠加层
        指纹：像素变化只可能来自这两者（同一 token 的 tile 渲染确定），这是
        免逐像素扫描的脏格判定依据。
        """
        self._map_terminal_image = image.copy() if _image_dirty_enabled() else image
        self._map_terminal_source = image
        raster = getattr(view, '_raster_cache', None)
        self._map_terminal_raster_geometry = getattr(raster, 'geometry', None)
        self._map_terminal_tokens = (dict(raster.cells)
                                     if getattr(raster, 'cells', None) is not None
                                     else None)
        parts = view.image_patch_state()
        self._map_terminal_overlay_sig = (dict(parts[3]) if parts is not None else None)
        self._map_terminal_state = (
            geometry, tuple(view.viewport), self._map_clip_state, id(self.screen),
            (region.x, region.y, columns, rows), self._map_render_signature,
            image.size, self._map_display_state)

    def _map_dirty_packets(self, view, image, region, geometry, scale, rectangles):
        """C13b 入口：测量 guard+diff+detect 成本，供 headless 报告与测试诊断。"""
        if not _image_dirty_enabled():
            return None
        started = time.perf_counter()
        self._map_dirty_detect_calls += 1
        try:
            return self._map_dirty_decide(
                view, image, region, geometry, scale, rectangles)
        finally:
            self._map_dirty_detect_ms += (time.perf_counter() - started) * 1000.0

    def _map_dirty_decide(self, view, image, region, geometry, scale, rectangles):
        """C13b：像素差脏格补丁；返回补丁 packet 列表。

        None = 必须整包；[] = 像素完全一致，本帧无需写。只有「上次真正写到
        终端的完整图」仍可信（同屏幕/同 geometry/同裁切指纹/同文字签名/同显示
        指纹/相机没动/整数像素网格）时才做脏格判定：像素变化只可能来自
        SceneImageCache 的逐格 token 变或叠加层逐格指纹变（同 token 的 tile
        渲染确定），因此用 O(可见格) 的 token 对比代替逐像素扫描；再合并成
        少量矩形只编码这些区域，并把补丁贴回终端镜像。变化格数/面积/补丁数
        任一超阈值都回退整包。
        """
        if not _image_dirty_enabled():
            return None
        def fail(reason):
            self._map_dirty_last_reason = reason
            return None
        if getattr(self, '_map_force_repaint', False):
            return fail('force')
        if self._image_output_error or getattr(self, '_floor_transition', None) is not None:
            return fail('error-or-transition')
        terminal = self._map_terminal_image
        state = self._map_terminal_state
        if terminal is None or state is None:
            return fail('no-terminal-state')
        (previous_geometry, previous_viewport, previous_clip, previous_screen,
         previous_region, previous_signature, previous_size,
         previous_display) = state
        if previous_size != image.size or terminal.size != image.size:
            return fail('size')
        if previous_geometry != geometry or previous_clip != self._map_clip_state:
            return fail('geometry-or-clip')
        if previous_screen != id(self.screen):
            return fail('screen')
        columns, rows = previous_region[2], previous_region[3]
        if (region.x, region.y) != (previous_region[0], previous_region[1]):
            return None
        if previous_signature is None or previous_signature != self._map_render_signature:
            return fail('text-signature')
        if previous_display != self._map_display_state:
            return fail('display-fingerprint')
        if previous_viewport != tuple(view.shared_scene.viewport):
            # 相机平移/换视口：整屏重排，补丁既不划算也不安全。
            return fail('viewport')
        if image is self._map_terminal_source:
            # image_frame 返回同一对象 => 像素必然逐字节相同（终端镜像是私有
            # 副本，不会被补丁污染）。重复 display 零 diff 成本直接跳过。
            return []
        sx, sy = scale
        if sx <= 0 or sy <= 0:
            return None
        if image.width % columns or image.height % rows:
            # 终端列/行与像素网格不能整除时，补丁边界可能错位：不猜。
            return fail('pixel-grid')
        cell_w, cell_h = view.cell_w, view.cell_h
        if cell_w <= 0 or cell_h <= 0:
            return None
        # 像素变化只可能来自「逐格 token 变」或「叠加层指纹变」：同一 token 的
        # tile 渲染是确定的，SceneImageCache 只对变化格 repaint。这比逐格像素
        # 扫描便宜两个数量级，且不会漏格（token 是像素的唯一输入）。
        parts = view.image_patch_state()
        if parts is None:
            return fail('no-patch-state')
        cached_image, _scene, _revision, current_overlay = parts
        if cached_image is not image:
            return fail('patch-image')
        tokens = self._map_terminal_tokens
        previous_raster_geometry = self._map_terminal_raster_geometry
        raster = getattr(view, '_raster_cache', None)
        if tokens is None or previous_raster_geometry is None or raster is None:
            return fail('no-token-state')
        if raster.geometry != previous_raster_geometry:
            return fail('raster-geometry')
        map_left, map_top = view.viewport[0], view.viewport[1]
        cells_x, cells_y = view.shared_scene.viewport[2], view.shared_scene.viewport[3]
        map_right, map_bottom = map_left + cells_x, map_top + cells_y
        dirty = set()
        for pos, token in raster.cells.items():
            if not (map_left <= pos[0] < map_right and map_top <= pos[1] < map_bottom):
                continue
            # token 是不可变值；SceneImageCache 只对变化格写入新 token 对象，
            # 未变格沿用旧对象。因此对象 identity 不同即该格被重绘过（可能像素
            # 变），identity 相同则像素必然相同——比 dataclass 深比较快两个量级。
            if tokens.get(pos) is not token:
                dirty.add(pos)
                if len(dirty) > DIRTY_MAX_CELLS:
                    return fail('cell-cap')
        for pos in tokens:
            if (pos not in raster.cells and map_left <= pos[0] < map_right
                    and map_top <= pos[1] < map_bottom):
                dirty.add(pos)
        dirty |= overlay_dirty_cells(
            self._map_terminal_overlay_sig or {}, current_overlay or {})
        dirty = {pos for pos in dirty
                 if map_left <= pos[0] < map_right and map_top <= pos[1] < map_bottom}
        if len(dirty) > DIRTY_MAX_CELLS:
            return fail('cell-cap')
        if not dirty:
            return []
        merged = set()
        map_right, map_bottom = (map_left + cells_x, map_top + cells_y)
        radius = DIRTY_MERGE_RADIUS
        for cell_x, cell_y in dirty:
            for dx in range(-radius, radius+1):
                for dy in range(-radius, radius+1):
                    candidate = (cell_x+dx, cell_y+dy)
                    if (map_left <= candidate[0] < map_right
                            and map_top <= candidate[1] < map_bottom):
                        merged.add(candidate)
        cell_rects = cells_to_rectangles(merged)
        if len(cell_rects) > DIRTY_MAX_PATCHES:
            if len(rectangles) != 1:
                return fail('patch-cap')
            bands = _band_rectangles(merged, DIRTY_MAX_PATCHES)
            if bands is None:
                return fail('patch-cap')
            cell_rects = bands
        patch_rects = []
        for cell_x, cell_y, w, h in cell_rects:
            rect = (region.x + (cell_x-map_left)*cell_w,
                    region.y + (cell_y-map_top)*cell_h, w*cell_w, h*cell_h)
            for vx, vy, vw, vh in rectangles:
                x0, x1 = max(rect[0], vx), min(rect[0]+rect[2], vx+vw)
                y0, y1 = max(rect[1], vy), min(rect[1]+rect[3], vy+vh)
                if x1 > x0 and y1 > y0:
                    patch_rects.append((x0, y0, x1-x0, y1-y0))
        if not patch_rects:
            return []
        if len(patch_rects) > DIRTY_MAX_PATCHES:
            return fail('patch-cap')
        visible_area = sum(w*h for _x, _y, w, h in rectangles)
        patch_area = sum(w*h for _x, _y, w, h in patch_rects)
        if visible_area <= 0 or patch_area > DIRTY_MAX_VISIBLE_FRACTION * visible_area:
            return fail('patch-area')
        encode_started = time.perf_counter()
        packets = image_region_packets(image, region, scale, patch_rects)
        self._map_dirty_encode_ms += (time.perf_counter() - encode_started) * 1000.0
        for rect, _packet in packets:
            box = (int(round((rect[0]-region.x)*sx)),
                   int(round((rect[1]-region.y)*sy)),
                   int(round((rect[0]+rect[2]-region.x)*sx)),
                   int(round((rect[1]+rect[3]-region.y)*sy)))
            terminal.paste(image.crop(box), (box[0], box[1]))
        self._map_terminal_source = image
        self._map_terminal_raster_geometry = raster.geometry
        self._map_terminal_tokens = dict(raster.cells)
        self._map_terminal_overlay_sig = (dict(current_overlay)
                                          if current_overlay is not None else None)
        self._map_dirty_last_reason = 'patch'
        self._map_dirty_cells += len(dirty)
        self._map_dirty_patch_count += len(packets)
        self._map_dirty_patch_bytes += sum(len(packet) for _rect, packet in packets)
        self._map_terminal_state = (
            geometry, tuple(view.shared_scene.viewport), self._map_clip_state,
            id(self.screen), (region.x, region.y, columns, rows),
            self._map_render_signature, image.size, self._map_display_state)
        return [self._map_packet_for_write(packet) for _rect, packet in packets]

    def _image_write_dedupe_skip(self, image, geometry, region, columns, rows):
        """C13：判断这次整包重发能否安全跳过。

        必须同时满足：开关打开；同一 image 对象；geometry（region/行列/裁切
        矩形）完全相同；裁切指纹相同（浮层/叠放没变）；同一屏幕；同一 content
        region；本帧地图区域文字签名与上次真正写图的签名相同。任何一项读不到
        （None）、换层/过渡/图像错误、缓存包为空都返回 False（整包重发）。
        """
        if not _image_write_dedupe_enabled():
            return False
        if getattr(self, '_map_force_repaint', False):
            return False
        if self._image_output_error or getattr(self, '_floor_transition', None) is not None:
            return False
        if not getattr(self, '_map_packets', None):
            return False
        signature = self._map_render_signature
        clip_state = self._map_clip_state
        if signature is None or clip_state is None:
            return False
        state = self._map_dedupe_state
        if state is None:
            return False
        (previous_image, previous_geometry, previous_clip, previous_screen,
         previous_region, previous_signature) = state
        if previous_image is not image:
            return False
        if previous_geometry != geometry or previous_clip != clip_state:
            return False
        if previous_screen != id(self.screen):
            return False
        if previous_region != (region.x, region.y, columns, rows):
            return False
        return previous_signature == signature

    def _write_live_map(self):
        if (self.home_mode or self.session.state.run_over
                or self.resolved_map_display()[0] != 'image'):
            return
        if not self.query('#map'):
            return  # A modal settings screen owns the terminal for this frame.
        view = self.query_one('#map')
        if not view.visible or not view.display or view.shared_scene is None:
            return
        # C13b：观察层/浮层/面板/窗口变化会让 Textual 重绘或裁掉整块地图，
        # 之前记录的「终端显示图」不再可信；下一次必须整包重发。
        fingerprint = self._map_display_fingerprint()
        if fingerprint != self._map_display_state:
            self._map_display_state = fingerprint
            self._map_terminal_image = None
            self._map_terminal_source = None
            self._map_terminal_tokens = None
            self._map_terminal_overlay_sig = None
            self._map_terminal_raster_geometry = None
            self._map_terminal_state = None
            self._map_dedupe_state = None
            self._map_force_repaint = True
        scene = view.shared_scene
        region = view.content_region
        columns, rows = scene.viewport[2]*view.cell_w, scene.viewport[3]*view.cell_h
        columns, rows = min(columns,region.width), min(rows,region.height)
        if not columns or not rows:
            return
        compositor = self.screen._compositor
        def uncovered(x, y):
            try:
                widget, _ = compositor.get_widget_at(x, y)
                return widget is view or getattr(widget,'id',None) == 'map-hints'
            except Exception:
                return False
        rectangles = self._map_clip_rectangles(view, region, columns, rows, uncovered)
        if not rectangles:
            return
        image = view.image_frame()
        sx, sy = image.width/(scene.viewport[2]*view.cell_w), image.height/(scene.viewport[3]*view.cell_h)
        geometry = (region.x,region.y,columns,rows,tuple(rectangles))
        key = (id(image), geometry)
        patches_enabled = image_patches_enabled()
        dirty_packets = None
        if _image_dirty_enabled() and not patches_enabled:
            try:
                dirty_packets = self._map_dirty_packets(
                    view, image, region, geometry, (sx, sy), rectangles)
            except Exception:
                dirty_packets = None
                self._map_dirty_errors += 1
            if dirty_packets is not None:
                if dirty_packets:
                    self._write_map_packets(dirty_packets)
                    self._map_dirty_frames += 1
                else:
                    self._map_dirty_skips += 1
                self._map_display_state = fingerprint
                self._map_force_repaint = False
                return True
            self._map_dirty_fallbacks += 1
        if key != getattr(self,'_map_packet_key',None):
            patch_packets = None
            if patches_enabled:
                try:
                    patch_packets = self._map_patch_packets(
                        view, image, region, geometry, (sx, sy), rectangles)
                except Exception:
                    # 可选性能路径不允许把图像输出带崩：任何异常回退整包。
                    patch_packets = None
                    self._map_patch_errors += 1
            if patch_packets is not None:
                # C7 可选路径：终端上仍是上一帧整图，只补脏格；已经写过的整包
                # 缓存随之失效（它对应的是旧图的像素），下次回退时重新整包编码。
                self._map_packets = ()
                self._map_packet_key = None
                self._map_packet_image = image
                self._write_map_packets(patch_packets)
                self._map_patch_frames += 1
                self._map_patch_state = self._map_patch_snapshot(view, image, geometry)
                # 补丁帧之后终端内容不等于任何整包缓存，禁止再做整包跳过。
                self._map_dedupe_state = None
                self._map_terminal_image = None
                self._map_terminal_source = None
                self._map_terminal_tokens = None
                self._map_terminal_overlay_sig = None
                self._map_terminal_raster_geometry = None
                self._map_terminal_state = None
                self._map_force_repaint = False
                return True
            packets = [self._map_packet_for_write(packet)
                       for _rect, packet in image_region_packets(
                           image, region, (sx, sy), rectangles)]
            self._map_packets = packets
            self._map_packet_key = key
            self._map_packet_image = image  # retain identity; prevent id reuse
            self._map_store_terminal(view, image, geometry, region, columns, rows)
        elif self._image_write_dedupe_skip(image, geometry, region, columns, rows):
            # C13 去重路径（默认关闭）：终端上已经是同一张图、同一 geometry、
            # 同一地图区域文字签名，本次合成没有带来任何像素/遮挡变化，跳过。
            self._map_dedupe_skips += 1
            self._map_dedupe_skip_packets += len(self._map_packets)
            self._map_dedupe_skip_bytes += sum(len(packet) for packet in self._map_packets)
            return True
        self._write_map_packets(self._map_packets)
        self._map_store_terminal(view, image, geometry, region, columns, rows)
        if patches_enabled:
            self._map_patch_state = self._map_patch_snapshot(view, image, geometry)
        self._map_dedupe_state = (
            image, geometry, self._map_clip_state, id(self.screen),
            (region.x, region.y, columns, rows), self._map_render_signature)
        self._map_dedupe_writes += 1
        self._map_force_repaint = False
        return True
