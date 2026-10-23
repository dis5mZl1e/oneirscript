"""WezTerm 图形升级：检测、下载、配置生成、在 WezTerm 里重启游戏。

WezTerm 是本游戏的推荐终端：支持自定义单元宽度（cell_width）、
font_dirs 免系统安装加载字体、跨 Windows/macOS/Linux 行为一致。
"""

from __future__ import annotations

import hashlib
import json
import os
import platform
import stat
import subprocess
import sys
import urllib.request
import zipfile
from dataclasses import dataclass
from pathlib import Path

from .terminal_launch import (ATTACHED_FLAG, GAME_FONT_FAMILY, bundled_font_path,
                              ensure_windows_font, game_font_face)
from .font_assets import persistent_font_dir, emoji_faces, game_icon_face, semantic_icon_faces, private_cache_dir
from .env_compat import name as env_name

WEZTERM_TAG = "20240203-110809-5046fc22"
WEZTERM_ATTACHED_FLAG='--wezterm-attached'
_RELEASE_BASE = f"https://github.com/wezterm/wezterm/releases/download/{WEZTERM_TAG}/"
# 国内网络直连 GitHub 常被墙：镜像优先，直连兜底。
_MIRRORS = ("https://gh-proxy.com/", "")

_SERIF_FALLBACK = {
    "win32": ["Dream Strata Serif Mono", "NSimSun"],
    "darwin": ["Dream Strata Serif Mono", "Songti SC"],
    "linux": ["Dream Strata Serif Mono", "Noto Serif CJK SC", "AR PL UMing CN"],
}

CELL_WIDTH = 1.18
FONT_SIZE = 14.0


def _platform_asset() -> tuple[str, str, str] | None:
    """返回 (资产文件名, 可执行文件相对 vendor/wezterm 的路径, 形态)。"""
    if sys.platform == "win32":
        return f"WezTerm-windows-{WEZTERM_TAG}.zip", "wezterm-gui.exe", "zip"
    if sys.platform == "darwin":
        return (f"WezTerm-macos-{WEZTERM_TAG}.zip",
                "WezTerm.app/Contents/MacOS/wezterm-gui", "zip")
    if sys.platform.startswith("linux"):
        if platform.machine().lower() not in ('x86_64','amd64'):
            return None
        return (f"WezTerm-{WEZTERM_TAG}-Ubuntu20.04.AppImage",
                "wezterm.AppImage", "appimage")
    return None


@dataclass(frozen=True)
class GraphicsReport:
    wezterm: Path | None      # 可用的 wezterm 可执行文件
    font_file: Path | None    # 内置衬线字体文件（font_dirs 直接加载）
    needs_download: bool
    download_bytes: int       # 预估下载量（0 = 平台不支持自动下载）
    unsupported: str | None = None


def vendor_dir(base: Path) -> Path:
    return base / "vendor" / "wezterm"


def _vendor_executable(base: Path) -> Path | None:
    if sys.platform.startswith('linux'):
        extracted=vendor_dir(base)/'squashfs-root/AppRun'
        if extracted.is_file():
            return extracted
    entry = _platform_asset()
    if entry is None:
        return None
    candidate = vendor_dir(base) / entry[1].replace("/", os.sep)
    return candidate if candidate.exists() else None


def find_wezterm(base: Path) -> Path | None:
    vendored = _vendor_executable(base)
    if vendored is not None:
        return vendored
    import shutil
    for name in ("wezterm-gui", "wezterm-gui.exe", "wezterm"):
        found = shutil.which(name)
        if found:
            return Path(found)
    if sys.platform == "win32":
        local = os.environ.get("LOCALAPPDATA")
        if local:
            roots = (Path(local) / "Programs",)
            for root in roots:
                hits = sorted(root.glob("WezTerm*/**/wezterm-gui.exe"))
                if hits:
                    return hits[0]
    elif sys.platform=='darwin':
        for directory in (Path('/Applications'),Path.home()/'Applications'):
            candidate=directory/'WezTerm.app/Contents/MacOS/wezterm-gui'
            if candidate.is_file():
                return candidate
    return None


def detect(base: Path) -> GraphicsReport:
    entry = _platform_asset()
    size = 0
    if entry is not None:
        size = {"win32": 66_000_000, "darwin": 103_000_000}.get(sys.platform, 49_500_000)
    wezterm = find_wezterm(base)
    return GraphicsReport(
        wezterm=wezterm,
        font_file=bundled_font_path(),
        needs_download=wezterm is None,
        download_bytes=size if wezterm is None else 0,
        unsupported=None if entry is not None or wezterm is not None else "当前平台或架构不支持自动下载 WezTerm，请到官网安装后重试。",
    )


def child_command(argv: list[str] | None = None) -> list[str]:
    """构造在 WezTerm 里重新拉起游戏的命令（剥掉 WT 交接标记，防二次交接）。"""
    argv = list(sys.argv if argv is None else argv)
    args = [item for item in argv[1:] if item not in (ATTACHED_FLAG, "--serif-terminal",'--prepare-terminal',WEZTERM_ATTACHED_FLAG)]
    # start --cwd changes directories; resolve saves before handing off.
    has_save_dir=False
    for index,item in enumerate(args):
        if item=='--save-dir' and index+1<len(args):
            args[index+1]=str(Path(args[index+1]).resolve())
            has_save_dir=True
        elif item.startswith('--save-dir='):
            args[index]='--save-dir='+str(Path(item.split('=',1)[1]).resolve())
            has_save_dir=True
    if not has_save_dir and not getattr(sys,'frozen',False):
        args.extend(['--save-dir',str(Path('save').resolve())])
    args.append(WEZTERM_ATTACHED_FLAG)
    if getattr(sys, "frozen", False):
        return [sys.executable, *args]
    return [sys.executable, str(Path(argv[0]).resolve()), *args]


def _lua_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def config_path(base: Path) -> Path:
    return base / ".wezterm" / "wezterm.lua"


def write_config(base: Path, game_command: list[str] | None = None, *, maximize: bool = True) -> Path:
    """幂等生成 WezTerm 配置：font_dirs 加载内置字体 + default_prog 直接进游戏。"""
    font = bundled_font_path()
    if font is None:
        raise OSError('内置字体缺失，请重新解压游戏或使用兼容模式。')
    face = game_font_face()
    unified = face.unified
    fallback = _SERIF_FALLBACK.get(sys.platform, _SERIF_FALLBACK["linux"])
    lines = [
        "-- Oneirscript 游戏专用配置；默认启动入口自动生成，不修改个人终端设置。",
        "local wezterm = require 'wezterm'",
        "local config = wezterm.config_builder()",
    ]
    names_list=[_lua_string(face.family)]
    if font is not None:
        fonts=persistent_font_dir(font.parent,base)
        lines.append(f"config.font_dirs = {{ {_lua_string(str(fonts))} }}")
        icons = game_icon_face(fonts)
        if icons is not None:
            if not unified:
                names_list.append(_lua_string(icons['family']))
            lines.append(f"config.set_environment_variables = {{ {env_name('ICONS')} = '1' }}")
        if not unified:
            names_list.extend(_lua_string(item['family']) for item in semantic_icon_faces(fonts))
        names_list.extend('{ family = '+_lua_string(item['family'])+', assume_emoji_presentation = true, scale = 0.9 }'
                          for item in emoji_faces(fonts))
    names_list.extend(_lua_string(name) for name in fallback[1:])
    names = ", ".join(names_list)
    lines.append(f"config.font = wezterm.font_with_fallback({{{names}}})")
    # Synthetic italics can make WezTerm halve individual wide CJK glyphs
    # (native reproduction: 型 advances 9.5 instead of 19). Use upright Song
    # faces for italic attributes in this game window; keep bold and colours.
    bold_names=[f'{{ family = {_lua_string(face.family)}, weight = "Bold", italic = false }}',*names_list[1:]]
    lines.append('local readable_bold = wezterm.font_with_fallback({'+', '.join(bold_names)+'})')
    lines.append('config.font_rules = {')
    lines.append('  { italic = true, intensity = "Bold", font = readable_bold },')
    lines.append('  { italic = true, intensity = "Half", font = config.font },')
    lines.append('  { italic = true, font = config.font },')
    lines.append('}')
    lines.append(f"config.font_size = {FONT_SIZE}")
    lines.append(f"config.cell_width = {CELL_WIDTH}")
    lines.append("config.allow_square_glyphs_to_overflow_width = 'WhenFollowedBySpace'")
    lines.append('config.unicode_version = 14')
    lines.append("config.use_fancy_tab_bar = false")
    lines.append("config.enable_tab_bar = false")
    lines.append("config.hide_tab_bar_if_only_one_tab = true")
    lines.append("config.initial_cols = 120")
    lines.append("config.initial_rows = 30")
    lines.append("config.window_decorations = 'TITLE|RESIZE'")
    lines.append("config.use_resize_increments = true")
    lines.append("config.adjust_window_size_when_changing_font_size = false")
    lines.append("config.window_padding = { left = 6, right = 6, top = 12, bottom = 8 }")
    command = game_command if game_command is not None else child_command()
    quoted = ", ".join(_lua_string(part) for part in command)
    lines.append(f"config.default_prog = {{ {quoted} }}")
    if maximize:
        lines.extend([
            "-- Keep the whole game inside the desktop work area, including titlebar and high DPI.",
            "wezterm.on('gui-startup', function(cmd)",
            "  local _, _, window = wezterm.mux.spawn_window(cmd or {})",
            "  window:gui_window():maximize()",
            "end)",
        ])
    from .wezterm_effects import install_effects
    effects=install_effects(base)
    if effects is not None:
        module=effects/'dream_effects.lua'
        lines.append(f'wezterm.add_to_config_reload_watch_list({_lua_string(str(module))})')
        lines.append(f'dofile({_lua_string(str(module))})(wezterm, config, {_lua_string(str(effects))})')
    lines.append("return config")
    payload = "\n".join(lines) + "\n"
    for path in (config_path(base),private_cache_dir()/'wezterm.lua'):
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            if not path.exists() or path.read_text(encoding="utf-8") != payload:
                from .font_assets import copy_asset
                import tempfile
                with tempfile.TemporaryDirectory() as temporary:
                    source=Path(temporary)/'config.lua'
                    source.write_text(payload,encoding='utf-8')
                    copy_asset(source,path)
            return path.resolve()
        except OSError:
            continue
    raise OSError('无法保存终端专用配置。')


def _open(url: str, timeout: float = 30.0):
    request = urllib.request.Request(url, headers={"User-Agent": "curl/8"})
    return urllib.request.urlopen(request, timeout=timeout)


def _fetch_text(url: str) -> str:
    with _open(url) as response:
        return response.read(4096).decode("utf-8", "replace")


def _download(url: str, target: Path, progress) -> int:
    digest = hashlib.sha256()
    total = 0
    done = 0
    with _open(url, timeout=60) as response, target.open("wb") as sink:
        try:
            total = int(response.headers.get("Content-Length") or 0)
        except ValueError:
            total = 0
        while True:
            chunk = response.read(256 * 1024)
            if not chunk:
                break
            digest.update(chunk)
            sink.write(chunk)
            done += len(chunk)
            progress(done, total)
    if done == 0:
        raise OSError("下载内容为空")
    return done


def _expected_sha256(mirror: str, asset: str) -> str | None:
    try:
        text = _fetch_text(f"{mirror}{_RELEASE_BASE}{asset}.sha256")
    except OSError:
        return None
    token = text.strip().split()[0] if text.strip() else ""
    return token if len(token) == 64 else None


def download_wezterm(base: Path, progress=lambda done, total: None, *, mirrors=None) -> Path:
    """下载并安装 WezTerm 到 vendor/wezterm/，返回可执行文件路径。

    依次尝试镜像与直连；校验官方 sha256；失败时清理残留。
    """
    entry = _platform_asset()
    if entry is None:
        raise OSError("当前平台不支持自动下载 WezTerm")
    asset, executable, form = entry
    target_dir = vendor_dir(base)
    staging = base / "vendor" / ".download"
    staging.mkdir(parents=True, exist_ok=True)
    download_path = staging / asset
    last_error: Exception | None = None
    for mirror in (_MIRRORS if mirrors is None else mirrors):
        expected = _expected_sha256(mirror, asset)
        if expected is None:
            last_error = OSError(f"无法获取校验文件（{mirror or 'direct'}）")
            continue
        try:
            _download(f"{mirror}{_RELEASE_BASE}{asset}", download_path, progress)
        except (OSError, ValueError) as error:
            last_error = error
            continue
        actual = hashlib.sha256(download_path.read_bytes()).hexdigest()
        if actual != expected:
            last_error = OSError("下载校验失败（sha256 不匹配）")
            download_path.unlink(missing_ok=True)
            continue
        try:
            target_dir.mkdir(parents=True, exist_ok=True)
            if form == "zip":
                with zipfile.ZipFile(download_path) as archive:
                    _extract_zip(archive,target_dir)
            else:
                download_path.replace(target_dir / "wezterm.AppImage")
                (target_dir / "wezterm.AppImage").chmod(0o755)
            installed = _relocate_executable(target_dir, Path(executable).name)
            if installed is None:
                raise OSError("解压后未找到 wezterm 可执行文件")
            if sys.platform!='win32':
                installed.chmod(installed.stat().st_mode|0o111)
            download_path.unlink(missing_ok=True)
            return installed
        except (OSError, zipfile.BadZipFile) as error:
            last_error = error
    download_path.unlink(missing_ok=True)
    if not any(staging.iterdir()):
        staging.rmdir()
    raise OSError(f"WezTerm 下载失败：{last_error}")


def _extract_zip(archive:zipfile.ZipFile,root:Path) -> None:
    """Keep macOS executable bits and framework symlinks inside the package."""
    root=root.resolve()
    links=[]
    for entry in archive.infolist():
        target=(root/entry.filename).resolve()
        if not target.is_relative_to(root):
            raise OSError('终端压缩包包含无效路径。')
        mode=entry.external_attr>>16
        if stat.S_ISLNK(mode):
            link=archive.read(entry).decode('utf-8')
            if not (target.parent/link).resolve().is_relative_to(root):
                raise OSError('终端压缩包包含无效链接。')
            links.append((target,link))
        else:
            archive.extract(entry,root)
            if sys.platform!='win32' and mode:
                target.chmod(mode & 0o777)
    for target,link in links:
        target.parent.mkdir(parents=True,exist_ok=True)
        if not target.is_symlink():
            target.symlink_to(link)


def _usable_executable(executable:Path) -> Path | None:
    """Check before saving/exiting the caller; extract Linux AppImage without FUSE if needed."""
    options=dict(stdin=subprocess.DEVNULL,capture_output=True,timeout=20)
    if sys.platform=='win32':
        options['creationflags']=subprocess.CREATE_NO_WINDOW
    try:
        result=subprocess.run([str(executable),'--version'],**options)
        if result.returncode==0:
            return executable
        if sys.platform.startswith('linux') and executable.suffix=='.AppImage' and b'fuse' in (result.stdout+result.stderr).lower():
            extracted=executable.parent/'squashfs-root/AppRun'
            if not extracted.is_file():
                result=subprocess.run([str(executable),'--appimage-extract'],cwd=executable.parent,**options)
                if result.returncode!=0:
                    return None
            if extracted.is_file():
                return _usable_executable(extracted)
    except (OSError,subprocess.TimeoutExpired):
        pass
    return None


def _relocate_executable(root: Path, executable_name: str) -> Path | None:
    """把嵌套在顶层目录里的可执行文件归位到 root 下的固定相对路径。"""
    found = next(iter(root.rglob(executable_name)), None)
    if found is None:
        return None
    expected = root / executable_name
    if found == expected:
        return expected
    if executable_name == "wezterm-gui":
        # macOS：整包移动 WezTerm.app。
        package = next((parent for parent in found.parents if parent.name == "WezTerm.app"), None)
        if package is not None:
            _move_onto(package, root / "WezTerm.app")
            return root / "WezTerm.app" / "Contents" / "MacOS" / "wezterm-gui"
    # Windows：可执行文件所在目录的全部内容上移一层。
    source_dir = found.parent
    for child in list(source_dir.iterdir()):
        _move_onto(child, root / child.name)
    if source_dir != root:
        _rmtree_quiet(source_dir)
    return expected


def _move_onto(source: Path, destination: Path) -> None:
    import shutil
    if source.resolve()==destination.resolve():
        return
    if destination.exists():
        _rmtree_quiet(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(source), str(destination))


def _rmtree_quiet(path: Path) -> None:
    import shutil
    if path.is_dir():
        shutil.rmtree(path, ignore_errors=True)
    else:
        path.unlink(missing_ok=True)


def launch(base: Path, game_command: list[str] | None = None) -> Path | None:
    """写配置并在 WezTerm 新窗口里启动游戏；返回所用可执行文件（失败 None）。"""
    executable = find_wezterm(base)
    if executable is None:
        return None
    executable=_usable_executable(executable)
    if executable is None:
        return None
    config = write_config(base, game_command)
    environment = dict(os.environ)
    for name in list(environment):
        if name.startswith("_PYI_"):
            environment.pop(name)
    environment["PYINSTALLER_RESET_ENVIRONMENT"] = "1"
    environment["WEZTERM_CONFIG_FILE"] = str(config)
    flags = 0
    kwargs: dict = {}
    if sys.platform == "win32":
        flags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        kwargs["start_new_session"] = True
    try:
        subprocess.Popen([str(executable),'--config-file',str(config),'start','--always-new-process','--cwd',str(base.resolve())], cwd=str(base), env=environment,
                         creationflags=flags,
                         stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL, **kwargs)
    except OSError:
        return None
    return executable
