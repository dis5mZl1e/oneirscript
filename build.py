"""一键打包《梦层》为独立 exe。

用法：
    python build.py             # 沿用当前源码树的 Cython 状态（无扩展即纯 Python）
    python build.py --cython    # 先编译可选 Cython 热点，再打包
    python build.py --no-cython # 清理 Cython 扩展，打包纯 Python 版
产物：
    梦层.exe      双击即玩（含全部游戏代码与 assets/icon.ico 图标）
    build/        PyInstaller 中间产物（.gitignore 已忽略；保留可加速二次构建）
行为：
    - 先把新 exe 打到暂存目录 dist/，再就地重写根目录里的旧 exe（同名同路径，不留残留）；
      **不在构建前删除旧产物**——Windows 上删除 20MB 的 exe 很容易被文件占用或回收站
      机制拦住（PermissionError: WinError 5），而「就地重写」始终可行。
    - 先使用 --onefile --console 打包游戏，再嵌入无窗口原生启动入口，仍交付单个 exe
    - 图标内嵌自 assets/icon.ico（与梦层.lnk 复用同一图标）
    - 存档默认落在 <exe_dir>/save，与 python run_demo.py 的默认 save/ 同目录 → 数据互通
    - 残留 spec 移入 build/ 后清理（不再需要单独 spec 文件，配方已在本脚本里）
"""
from __future__ import annotations

import os
import hashlib
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
EXE_NAME = 'Oneirscript'
BINARY_NAME = EXE_NAME+('.exe' if sys.platform=='win32' else '')
ICON = ROOT / "assets" / "icon.ico"
STAGING = ROOT / "dist"          # 新 exe 的暂存目录（构建完成后搬去根目录）
TARGET = ROOT / BINARY_NAME
WORKPATH = ROOT / "build"
FONT_DIR = ROOT / "assets" / "fonts"


def _app_version() -> str:
    """版本号唯一来源：pyproject.toml 的 [project].version（公开版从 0.1.0 起）。"""
    import tomllib

    data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    return str(data["project"]["version"])


def _version_quad(version: str) -> str:
    parts = (version.split("+")[0].split("-")[0]).split(".")
    numbers = [int(part) if part.isdigit() else 0 for part in parts][:4]
    numbers += [0] * (4 - len(numbers))
    return ".".join(str(n) for n in numbers)


def _write_version_file(directory: Path) -> Path:
    """生成 PyInstaller --version-file，让 exe 属性页显示真实版本与产品名。"""
    version = _app_version()
    quad = _version_quad(version)
    tuple_literal = "(" + ", ".join(quad.split(".")) + ")"
    body = f"""VSVersionInfo(
  ffi=FixedFileInfo(filevers={tuple_literal}, prodvers={tuple_literal}, mask=0x3f, flags=0x0, OS=0x40004, fileType=0x1, subtype=0x0, date=(0, 0)),
  kids=[
    StringFileInfo([StringTable('080404B0', [
      StringStruct('FileDescription', '梦层 / Oneirscript'),
      StringStruct('FileVersion', '{quad}'),
      StringStruct('InternalName', 'Oneirscript'),
      StringStruct('LegalCopyright', 'GPL-3.0-only; 完整许可见随包 LICENSE'),
      StringStruct('OriginalFilename', '{BINARY_NAME}'),
      StringStruct('ProductName', '梦层 / Oneirscript'),
      StringStruct('ProductVersion', '{version}')])]),
    VarFileInfo([VarStruct('Translation', [2052, 1200])])
  ]
)
"""
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / "version_info.txt"
    target.write_text(body, encoding="utf-8")
    return target


def _font_package_problems(directory: Path = FONT_DIR) -> list[str]:
    """校验「字体清单 ↔ 字体文件」自洽（每项的 sha256 必须对得上）。

    图标／emoji／语义字体包各自带 sha256 自校验，而清单是刷新脚本单独写的。
    并行会话重刷图标时，若打包正好落在「清单已写、字体文件已换」之间，打出来
    的 exe 就自带一对互相矛盾的字体——运行时生成 WezTerm 配置会抛
    `游戏图标字体包校验失败`，整条推荐终端交接被放弃（2026-10-26 实测：双击
    后进了 Windows Terminal，玩家以为没装 WezTerm）。打包前挡下来最省事。
    """
    import hashlib
    import json

    problems: list[str] = []

    def verify(manifest: Path, entries: list) -> None:
        for entry in entries:
            filename = entry.get("file") if isinstance(entry, dict) else None
            path = directory / str(filename)
            if not path.is_file():
                problems.append(f"{manifest.name}: 缺少字体文件 {filename}")
            elif hashlib.sha256(path.read_bytes()).hexdigest() != entry.get("sha256"):
                problems.append(f"{manifest.name}: {filename} 的 sha256 与清单不符")

    try:
        for name in ("glyph-manifest.json",):
            manifest = directory / name
            if manifest.is_file():
                verify(manifest, [json.loads(manifest.read_text(encoding="utf-8"))])
        for name, key in (("semantic-icons.json", "fonts"), ("emoji-package.json", "faces")):
            manifest = directory / name
            if manifest.is_file():
                data = json.loads(manifest.read_text(encoding="utf-8"))
                verify(manifest, data.get(key) or [])
    except (OSError, ValueError) as error:
        problems.append(f"字体清单无法读取：{error}")
    return problems


def _build_windowless_bootstrap() -> int:
    """Embed the console build in a native GUI entry, preserving one-file delivery."""
    windows = Path(os.environ.get("WINDIR", r"C:\Windows"))
    compilers = [windows / "Microsoft.NET" / kind / "v4.0.30319" / "csc.exe"
                 for kind in ("Framework64", "Framework")]
    compiler = next((path for path in compilers if path.is_file()), None)
    if compiler is None:
        raise RuntimeError("缺少 .NET Framework C# 编译器，无法构建无窗口启动入口。")
    core = STAGING / f"{EXE_NAME}.exe"
    core_resource = WORKPATH / "OneirscriptCore.exe"
    shutil.copyfile(core, core_resource)
    digest = hashlib.sha256(core_resource.read_bytes()).hexdigest().upper()
    source = (ROOT / "scripts" / "windows_bootstrap.cs").read_text(encoding="utf-8")
    version = _app_version()
    source = (source.replace("@CORE_HASH@", digest)
                    .replace("@CORE_SIZE@", str(core_resource.stat().st_size))
                    .replace("@VERSION@", _version_quad(version))
                    .replace("@SEMVER@", version))
    generated = WORKPATH / "DreamBootstrap.cs"
    generated.write_text(source, encoding="utf-8-sig")
    return subprocess.run([str(compiler), "/nologo", "/utf8output", "/target:winexe", "/optimize+",
                           "/reference:System.Web.Extensions.dll", "/reference:System.Windows.Forms.dll",
                           f"/win32icon:{ICON}", f"/resource:{core_resource},OneirscriptCore",
                           f"/out:{core}", str(generated)], cwd=ROOT).returncode


def _purge(path: Path) -> None:
    """只清理本项目的打包工作目录和暂存目录，先校验绝对目标。"""
    resolved = path.resolve()
    allowed = {ROOT.resolve() / "dist", ROOT.resolve() / "build" / EXE_NAME}
    if resolved not in allowed or path.is_symlink():
        raise ValueError(f"拒绝清理非打包目录：{resolved}")
    if path.exists():
        shutil.rmtree(resolved)


def _clear_staging() -> None:
    """清理已校验的暂存目录。"""
    _purge(STAGING)


def _install_artifact() -> int:
    """把暂存目录里的新 exe 就位到根目录。

    这里刻意**不用删除 / 覆盖改名**：本机（以及不少 Windows 环境）会把删除与
    「替换已存在的文件」拦下来（`PermissionError: [WinError 5] 拒绝访问`），
    但「打开旧文件就地重写」和「改成新名字」都是允许的。因此：
    - 旧 exe 存在 → 直接按字节重写它（同名同路径，不留残留文件）；
    - 旧 exe 不存在（首次构建）→ 改名就位。
    """
    built = STAGING / BINARY_NAME
    if not built.exists():
        print(f"没找到构建产物: {built}", file=sys.stderr)
        return 1
    payload = built.read_bytes()

    # 先把完整内容写进同目录的临时文件，再原子换名。
    # 早先的实现是「打开旧 exe 就地重写」：截断到写满之间有一个几百毫秒的窗口，
    # 若恰好在此期间双击，加载到的是半个 exe —— 表现就是「一打开就闪退」且
    # 没有任何日志。换名在 NTFS 上是原子操作，彻底消掉这个窗口。
    staged = TARGET.with_name(BINARY_NAME+'.new')
    try:
        with open(staged, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        staged.chmod(0o755)
    except OSError as error:
        print(f"写入临时文件 {staged} 失败：{error}", file=sys.stderr)
        return 1

    if TARGET.exists():
        # 首选：直接替换（MoveFileEx REPLACE_EXISTING，原子且不产生残留）。
        # 某些环境的安全策略会拦这一下，因此逐级降级。
        last_error: OSError | None = None
        for attempt in range(6):
            try:
                os.replace(staged, TARGET)
                last_error = None
                break
            except OSError as error:
                last_error = error
                time.sleep(2)
        if last_error is not None:
            # 降级：把旧 exe 改名为备份，再把新文件换上来（改名同样是原子的）。
            backup = TARGET.with_name(BINARY_NAME+'.old')
            try:
                os.rename(TARGET, backup)
                os.rename(staged, TARGET)
                last_error = None
                print(f"旧 exe 已备份为 {backup.name}（可自行删除）")
            except OSError as error:
                last_error = error
        if last_error is not None:
            # 最后兜底：旧的就地重写（有短暂窗口，但总比构建失败好）。
            for attempt in range(6):
                try:
                    with open(TARGET, "r+b") as stream:
                        stream.seek(0)
                        stream.write(payload)
                        stream.truncate()
                    last_error = None
                    break
                except OSError as error:
                    last_error = error
                    time.sleep(2)
        if last_error is not None:
            print(
                f"写入 {TARGET} 失败：{last_error}\n"
                "多半是旧 exe 正在运行（或被杀软占用）——关掉《梦层》窗口后重跑 python build.py 即可。\n"
                f"新 exe 已留在 {staged}，也可手动替换。",
                file=sys.stderr,
            )
            return 1
        # 任何成功路径都不会留下 .new
        if staged.exists():
            staged.unlink(missing_ok=True)
    else:
        try:
            os.rename(staged, TARGET)
        except OSError as error:
            print(f"写入 {TARGET} 失败：{error}", file=sys.stderr)
            return 1
    size = TARGET.stat().st_size
    if size != len(payload):
        print(f"{TARGET} 写入不完整（{size} != {len(payload)}），请重跑 python build.py", file=sys.stderr)
        return 1
    print(f"完成 → {TARGET} ({size} 字节)")
    return 0


def _cython_modules_built() -> bool:
    import importlib.machinery
    suffixes = tuple(importlib.machinery.EXTENSION_SUFFIXES)
    for name in (
        "dream_demo/ui/render", "dream_demo/core/map_scene",
        "dream_demo/ui/map_presentation", "dream_demo/core/save_kernel",
        "dream_demo/core/vision/sight_kernel", "dream_demo/core/gas_kernel",
        "dream_demo/ui/app/fx_kernel",
    ):
        base = ROOT / name
        if not any((base.parent / (base.name + suffix)).exists() for suffix in suffixes):
            return False
    return True


def _prepare_cython() -> int:
    """可选 Cython 扩展（方案 A）。默认沿用当前源码树的编译状态；
    --cython 强制重建，--no-cython 清理回纯 Python。"""
    script = ROOT / "scripts" / "build_cython_ext.py"
    if "--cython" in sys.argv:
        action = "--build"
    elif "--no-cython" in sys.argv:
        action = "--clean"
    else:
        if _cython_modules_built():
            print("检测到已编译 Cython 扩展，将打包编译版；--no-cython 可回纯 Python。")
        return 0
    print(f"Cython: python scripts/build_cython_ext.py {action}")
    return subprocess.run([sys.executable, str(script), action], cwd=str(ROOT)).returncode


def main() -> int:
    print(f"梦层 / Oneirscript {_app_version()} → {BINARY_NAME}")
    rc = _prepare_cython()
    if rc != 0:
        print(f"Cython 预处理失败，exit={rc}", file=sys.stderr)
        return rc
    # 字体包自校验：清单与文件不一致的 exe 会在运行时丢掉整个推荐终端，
    # 这种产物宁可不打。
    problems = _font_package_problems()
    if problems:
        print("字体包自校验不通过，已中止打包：", file=sys.stderr)
        for line in problems:
            print(f"  - {line}", file=sys.stderr)
        print("请先重跑 assets/fonts 的刷新脚本（如 scripts/refresh_expansion_icons_261025.py）再打包。",
              file=sys.stderr)
        return 1
    # 清理前校验绝对目标；保留根目录的旧 EXE，直到新产物构建成功。
    _purge(WORKPATH / EXE_NAME)
    _purge(STAGING)

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        "--console",
        "--name", EXE_NAME,
        "--icon", str(ICON),
        "--distpath", str(STAGING),         # 先输出到暂存目录，最后原子替换根目录 exe
        "--workpath", str(WORKPATH),        # 中间产物入 build/（已 gitignore）
        "--specpath", str(WORKPATH),        # spec 暂存到 build/，最后清理
        "--collect-data", "textual",        # textual 自带的 TCSS/资源
        "--collect-data", "dream_demo",     # 游戏包内的数据文件（vault 模板 JSON）
        "--add-data", f"{ROOT / 'assets' / 'data' / 'anomaly-skills.xlsx'}{os.pathsep}data",
        "--exclude-module", "Cython",       # 构建期工具，绝不能进发布包
        "--collect-submodules", "asciimatics",
        "--collect-submodules", "fontTools.ttLib.tables",  # cmap/table modules are imported dynamically
        "--copy-metadata", "fonttools",
        "--copy-metadata", "pillow",
        "--copy-metadata", "asciimatics",   # 离屏特效版本可在产物内核对
        # 音频资源：解压到 sys._MEIPASS 下的 sfx/ 与 music/，由 audio._asset_path 解析。
        "--add-data", f"{ROOT / 'assets' / 'sfx'}{os.pathsep}sfx",
        "--add-data", f"{ROOT / 'assets' / 'music'}{os.pathsep}music",
        # 内置等宽宋体：terminal_launch.ensure_windows_font 从 _MEIPASS/fonts 用户级安装。
        "--add-data", f"{ROOT / 'assets' / 'fonts'}{os.pathsep}fonts",
        "--add-data", f"{ROOT / 'assets' / 'wezterm'}{os.pathsep}wezterm",
        # 不加 --clean：它会批量删除 pyinstaller 缓存（800+ 文件）而被
        # 「安全删除」钩子拦截、直接中断构建。缓存不干净不影响产出。
        "--noconfirm",                      # 覆盖 dist/ 里的旧产物，不弹确认
        str(ROOT / "launch_game.py"),
    ]
    if sys.platform == "win32":
        # 版本资源只对 Windows PE 有意义；最终 exe 由下面的无窗口启动器重新编译，
        # 它再带一遍同名版本资源（见 scripts/windows_bootstrap.cs 的 Assembly 属性）。
        cmd[cmd.index("--noconfirm"):cmd.index("--noconfirm")] = [
            "--version-file", str(_write_version_file(WORKPATH)),
        ]
    print("执行:", " ".join(cmd))
    rc = subprocess.run(cmd, cwd=str(ROOT)).returncode
    if rc != 0:
        print(f"PyInstaller 失败，exit={rc}", file=sys.stderr)
        return rc

    if sys.platform=='win32':
        rc = _build_windowless_bootstrap()
        if rc != 0:
            print(f"无窗口启动入口构建失败，exit={rc}", file=sys.stderr)
            return rc

    # 残留 spec 不再需要（配方已在本脚本里），清理。
    leftover_spec = WORKPATH / f"{EXE_NAME}.spec"
    if leftover_spec.exists():
        leftover_spec.unlink()
        if leftover_spec.exists():
            print(f"（未能清理残留 spec: {leftover_spec}，它在 build/ 下且已 gitignore，可忽略）")

    rc = _install_artifact()
    if rc != 0:
        return rc
    _clear_staging()
    return 0


if __name__ == "__main__":
    sys.exit(main())
