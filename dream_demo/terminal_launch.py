"""仅安装游戏自己的 Windows Terminal 配置；不改用户 settings.json。"""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from .font_assets import (LEGACY_FAMILY, LEGACY_FILE, active_font_face,
                          asset_dir, copy_asset)

PROFILE_GUID = "{cb2ca4ca-e2c0-59fd-a2c5-3d5f11980f3e}"
PROFILE_NAME = "Oneirscript Serif"
ATTACHED_FLAG = "--terminal-attached"
UNIFIED_FONT_FLAG = "--unified-font"

GAME_FONT_FAMILY = LEGACY_FAMILY
GAME_FONT_FILE = LEGACY_FILE
# 阅读版行高 1180，与 WezTerm 的两列宽 500*2*1.18 配套。
# 旧 Serif Mono 行高 1437，不可在同一网格配置下替代。
FONT_FALLBACK_CHAIN = ("NSimSun", "Segoe UI Emoji")

_force_unified = False
_fallback_reason: str | None = None


def fallback_reason() -> str | None:
    """本次推荐终端交接失败的一行摘要（成功或明确要求兼容模式时为 None）。"""
    return _fallback_reason


def set_unified_font(enabled: bool = True) -> None:
    """QA 显式试用候选；manifest 的 default 仍是发布唯一开关。"""
    global _force_unified
    _force_unified = enabled


def game_font_face():
    return active_font_face(asset_dir(), force_unified=_force_unified)


def bundled_font_path() -> Path | None:
    path = game_font_face().path
    return path if path.is_file() else None


def prefer_wezterm(argv:list[str],directory:Path) -> bool:
    """Use the private/supported terminal when available; never download at startup."""
    global _fallback_reason
    if UNIFIED_FONT_FLAG in argv:
        argv.remove(UNIFIED_FONT_FLAG)
        set_unified_font(True)
    if any(flag in argv for flag in
            ('--compat-terminal','--wezterm-attached','--serif-terminal','--smoke')):
        _fallback_reason = None
        return False
    from .wezterm_setup import child_command, launch, last_failure
    reason: str | None = None
    try:
        if launch(directory,child_command(argv)) is not None:
            _fallback_reason = None
            return True
        reason = last_failure() or 'WezTerm 没有启动，原因未知。'
    except (OSError,ValueError) as error:
        reason = str(error)
    # Keep the in-game notice to one readable line; the full stderr tail is
    # printed below and saved next to the terminal config.
    _fallback_reason = reason.splitlines()[0][:200]
    print(f'推荐终端未启动，已改用兼容模式：{reason}',file=sys.stderr)
    if sys.platform=='win32':
        ensure_windows_font()
    return False


_font_installed: str | None | bool = False  # False=未尝试；None=失败；str=族名
_font_installed_file: str | None = None


def _stage_font_file(source: Path, target: Path) -> Path | None:
    """把内置字体就位到用户字体目录，返回真正可用的文件（失败 None）。

    ``%LOCALAPPDATA%\\Microsoft\\Windows\\Fonts`` 下的字体一旦被任何进程加载，
    系统就以「允许读取、禁止改写」的方式把它映射住——之后 ``os.replace`` 会
    稳定报 ``PermissionError [WinError 5]``。旧实现把这个异常当成安装失败，
    于是 ``ensure_windows_font`` 返回 None、Windows Terminal 的 profile 退回
    ``NSimSun``，玩家看到的就是「Windows 终端找不到字体」。

    正确口径是：**能被 GDI 认出来的字体就是可用字体**。刷新失败时沿用磁盘上
    已经装好的同一族文件（族名相同），只在文件确实不在时才判定失败。
    """
    try:
        copy_asset(source, target)
        return target
    except OSError:
        return target if target.is_file() else None


def ensure_windows_font() -> str | None:
    """用户级安装当前游戏字体（仅 LOCALAPPDATA + HKCU 字体表），成功返回族名。"""
    global _font_installed, _font_installed_file
    face = game_font_face()
    if _font_installed is not False and _font_installed_file == face.file:
        return _font_installed or None
    _font_installed = None
    _font_installed_file = face.file
    if sys.platform != "win32":
        return None
    source = face.path if face.path.is_file() else None
    if source is None:
        return None
    import ctypes
    user_dir = Path(os.environ["LOCALAPPDATA"]) / "Microsoft" / "Windows" / "Fonts"
    target = _stage_font_file(source, user_dir / face.file)
    if target is None:
        return None
    try:
        added = ctypes.windll.gdi32.AddFontResourceExW(str(target), 0, None)
        if added <= 0:
            return None
        import winreg
        # HKCU Fonts 键在从未装过用户字体的机器上不存在，须 CreateKey。
        with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER,
                                r"Software\Microsoft\Windows\CurrentVersion\Fonts",
                                0, winreg.KEY_SET_VALUE) as key:
            winreg.SetValueEx(key, f"{face.family} (TrueType)", 0,
                              winreg.REG_SZ, str(target))
        result = ctypes.c_ulong()
        # HWND_BROADCAST / WM_FONTCHANGE / SMTO_ABORTIFHUNG, 3s
        ctypes.windll.user32.SendMessageTimeoutW(
            0xFFFF, 0x0018, 0, 0, 0x0002, 3000, ctypes.byref(result))
        _font_installed = face.family
        return face.family
    except OSError:
        return None


def _nsim_sun_available() -> bool:
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                            r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Fonts") as key:
            index = 0
            while True:
                name, _, _ = winreg.EnumValue(key, index)
                if "NSimSun" in name:
                    return True
                index += 1
    except OSError:
        return False


def terminal_available() -> tuple[str | None, str | None]:
    if sys.platform != "win32":
        return None, "当前平台使用现有终端；衬线字体请在终端中设置。"
    terminal = shutil.which("wt.exe")
    if terminal is None:
        return None, "未找到 Windows Terminal，衬线字体未应用；使用原终端启动。"
    if ensure_windows_font() is not None or _nsim_sun_available():
        return terminal, None
    return None, "未找到新宋体，衬线字体未应用；使用原终端启动。"


def install_background(local_app_data: Path | None = None) -> str | None:
    """把氛围背景资产（wezterm 同款雾层 APNG 首帧流）就位到 Fragments 目录。

    Windows Terminal 的 backgroundImage 支持 APNG 逐帧播放，与 WezTerm 的
    dream 模式雾层同源同速；不可用时返回 None（profile 不写背景项）。
    """
    if getattr(sys, "frozen", False):
        source = Path(getattr(sys, "_MEIPASS", ".")) / "wezterm" / "mist.png"
    else:
        from .resource_paths import assets_dir
        source = assets_dir() / "wezterm" / "mist.png"
    if not source.is_file():
        return None
    local_app_data = local_app_data or Path(os.environ["LOCALAPPDATA"])
    target = (local_app_data / "Microsoft" / "Windows Terminal" / "Fragments"
              / "Oneirscript" / "dream_mist.png")
    try:
        copy_asset(source, target)
    except OSError:
        return None
    return str(target)


def _remove_legacy_fragment(local_app_data: Path) -> None:
    """删除旧名生成的本游戏 fragment，避免终端里出现两个同名窗口配置。"""
    legacy = (local_app_data / "Microsoft" / "Windows Terminal" / "Fragments"
              / "DreamStrata")
    profile = legacy / "profile.json"
    try:
        data = json.loads(profile.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return
    if any(item.get("guid") == PROFILE_GUID for item in data.get("profiles", ())):
        shutil.rmtree(legacy, ignore_errors=True)


def install_profile(command: list[str], directory: Path,
                    local_app_data: Path | None = None) -> Path:
    """幂等写入单一 fragment；command 已包含防重入标记。"""
    directory = directory.resolve()
    # 从 Windows Terminal 拉起的是 %LOCALAPPDATA%\\Oneirscript\\runtime\\<hash>
    # 里的解包副本，不带 --game-directory 时它会把「exe 所在目录」认作解包目录：
    # 存档写进 runtime\\<hash>\\save、vendor/wezterm 也找不到（实测 2026-10-22
    # 有一份 889 KB 的 run.json 就这么留在了 runtime 下）。这里统一补齐。
    if "--game-directory" not in command:
        command = [*command, "--game-directory", str(directory)]
    local_app_data = local_app_data or Path(os.environ["LOCALAPPDATA"])
    path = local_app_data / "Microsoft" / "Windows Terminal" / "Fragments" / "Oneirscript" / "profile.json"
    serif_font = ensure_windows_font()
    fallback = ", ".join(FONT_FALLBACK_CHAIN)
    if serif_font is not None:
        # 内置等宽宋体：自然半格 0.5em，两列宽=一行高的 2:1 基准显式声明。
        font_spec = {"face": f"{serif_font}, {fallback}", "size": 14,
                     "weight": "normal", "cellWidth": "0.5",
                     "cellHeight": "1.0", "colorGlyphs": False}
    else:
        # 同一 em 基准：两列宽度=一行高度；加宽字符间距供衬线和回退字形。
        font_spec = {"face": f"NSimSun, {FONT_FALLBACK_CHAIN[-1]}", "size": 14,
                     "weight": "normal", "cellWidth": "0.6", "cellHeight": "1.2",
                     "colorGlyphs": False}
    profile = {
        "guid": PROFILE_GUID, "name": PROFILE_NAME,
        "commandline": subprocess.list2cmdline(command),
        "startingDirectory": str(directory),
        "font": font_spec,
        "background": "#101018", "antialiasingMode": "grayscale",
        "closeOnExit": "graceful", "hidden": False,
        "suppressApplicationTitle": False,
        # ---- 与 wezterm 配置同源的窗口与氛围项（docs §5 渲染同步）----
        "padding": "6",
        "initialCols": 120, "initialRows": 30,
        "launchMode": "maximized",
    }
    background_image = install_background(local_app_data)
    if background_image:
        # dream 模式的雾层：WezTerm 用 opacity 0.30（focus 满档），WT 无
        # 失焦淡出，常驻同值；APNG 逐帧播放由终端原生处理。
        profile["backgroundImage"] = background_image
        profile["backgroundImageOpacity"] = 0.30
        profile["backgroundImageStretchMode"] = "uniformToFill"
    payload = json.dumps({"profiles": [profile]}, ensure_ascii=False, indent=2) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists() or path.read_text(encoding="utf-8") != payload:
        temporary = path.with_suffix(".tmp")
        temporary.write_text(payload, encoding="utf-8")
        temporary.replace(path)
    _remove_legacy_fragment(local_app_data)
    return path


def handoff(command: list[str], directory: Path) -> bool:
    terminal, reason = terminal_available()
    if terminal is None:
        print(reason, file=sys.stderr)
        return False
    try:
        install_profile(command, directory)
        # 单文件父进程退出后会删除解包目录，新终端必须运行独立实例。
        # 同时清除继承状态，避免现有 Terminal broker 保留旧解包路径。
        environment = dict(os.environ)
        for name in list(environment):
            if name.startswith("_PYI_"):
                environment.pop(name)
        environment["PYINSTALLER_RESET_ENVIRONMENT"] = "1"
        result = subprocess.run(
            [terminal, "-w", "new", "new-tab", "--inheritEnvironment", "-p", PROFILE_GUID,
             "-d", str(directory.resolve()), *command],
            timeout=15, check=False, env=environment,
        )
        if result.returncode == 0:
            return True
        print(f"专用终端启动失败（{result.returncode}），衬线字体未应用；使用原终端。", file=sys.stderr)
    except (OSError, subprocess.TimeoutExpired) as error:
        print(f"专用终端配置失败：{error}；衬线字体未应用，使用原终端。", file=sys.stderr)
    return False
