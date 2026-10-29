"""Offline PNG and CLI helpers shared by diagnostics and pixel geometry probes.

The live primary map is implemented by live_map.py through Textual's driver;
F2 opens its real display setting. These helpers do not suspend the application.
"""
from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path
from typing import Any

from ..core.map_scene import build_scene, observe_scene
from .map_image import render_scene_image

PREVIEW_SIZE = (24, 24)


def _bundled_wezterm() -> Path | None:
    candidates = []
    meipass = getattr(sys, '_MEIPASS', None)
    if meipass:
        candidates.append(Path(meipass) / 'wezterm' / 'wezterm.exe')
    candidates += [
        Path(sys.executable).resolve().parent / 'wezterm' / 'wezterm.exe',
        Path(__file__).resolve().parents[2] / 'vendor' / 'wezterm' / 'wezterm.exe',
        Path(__file__).resolve().parents[2] / 'assets' / 'wezterm' / 'wezterm.exe',
    ]
    for path in candidates:
        if path.exists():
            return path
    return None


def _as_cli(path: Path) -> Path:
    """WEZTERM_EXECUTABLE 常指向 wezterm-gui；imgcat 子命令在 CLI 可执行文件。"""
    for name in ('wezterm.exe', 'wezterm'):
        sibling = path.with_name(name)
        if sibling.exists() and sibling != path:
            return sibling
    return path


def wezterm_executable() -> Path | None:
    explicit = os.environ.get('WEZTERM_EXECUTABLE')
    if explicit and Path(explicit).exists():
        return _as_cli(Path(explicit))
    found = shutil.which('wezterm') or shutil.which('wezterm.exe')
    if found:
        return _as_cli(Path(found))
    bundled = _bundled_wezterm()
    if bundled is not None:
        return bundled
    from ..wezterm_setup import find_wezterm
    found = find_wezterm(Path(__file__).resolve().parents[2])
    return _as_cli(Path(found)) if found else None


def can_preview_image(environ: dict[str, str] | None = None) -> tuple[bool, str]:
    env = os.environ if environ is None else environ
    if not (env.get('WEZTERM_PANE') or env.get('WEZTERM_EXECUTABLE')):
        return False, '当前不在 WezTerm 中运行'
    if wezterm_executable() is None:
        return False, '找不到随包 wezterm.exe'
    return True, ''


def wezterm_imgcat_command(image: str | Path, *, width: str = '100%') -> list[str]:
    executable = wezterm_executable()
    if executable is None:
        raise FileNotFoundError('wezterm executable not found')
    return [str(executable), 'imgcat', str(image), '--width', width]


def render_preview_png(state: Any, output: str | Path, *,
                       layer: str = 'composite',
                       viewport: tuple[int, int, int, int] | None = None) -> Path:
    from .render import render_map
    from .map_presentation import present_scene, render_observation
    scene = build_scene(state, viewport=viewport)
    left,top,width,height = scene.viewport
    # 预览图始终走 M2-A 逐格视觉事实入口：字符高刷开关不会让预览变成空图。
    recorded: dict = {}
    frame = render_map(state,viewport_width=width,viewport_height=height,
                       origin=(left,top),cell_w=scene.cell_w,cell_h=scene.cell_h,
                       visuals=recorded)
    scene = observe_scene(present_scene(scene,frame,visuals=recorded), layer)
    if layer != 'composite':
        # 过滤后的层用自己的观察帧重新采字形，预览图与字符观察看到同一份数据。
        # 声音线索层与观察界面同口径：只叠加显式标记，不照亮未知格。
        markers = None
        if layer == 'sound':
            from ..core.sound_markers import sound_markers
            markers = sound_markers(state) or None
        recorded = {}
        observed_frame = render_observation(scene, layer, markers=markers,
                                           visuals=recorded)
        scene = present_scene(scene, observed_frame, visuals=recorded)
    image = render_scene_image(scene, cell_px=PREVIEW_SIZE)
    path = Path(output)
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path)
    return path
