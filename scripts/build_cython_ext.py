"""可选的 Cython 加速构建（方案 A，2026-10-27）。

只编译地图输出/读档相关的稳定纯 Python 模块，生成同名 .pyd/.so 放在源码目录；
未编译时自动走原 .py，无需改业务代码。

用法：
    python scripts/build_cython_ext.py --build
    python scripts/build_cython_ext.py --clean      # 恢复纯 Python
    python scripts/build_cython_ext.py --disable    # 暂时改名禁用扩展
    python scripts/build_cython_ext.py --enable
    python scripts/build_cython_ext.py --verify

注意：
- 构建需要 Cython（pip install cython）和本机 C 编译器；发布包可选启用。
- .pyd/.so、生成的 C 文件都在源码树外/被 gitignore 的 build/cython 下；
  扩展本体在包目录旁，--clean 可彻底恢复纯 Python。
- 只编译纯函数模块，不编译 Textual/事件循环/UI 状态。
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
MANIFEST = ROOT / "build" / "cython" / "manifest.json"
BUILD_DIR = ROOT / "build" / "cython"

# 只保留实测有明显收益的地图输出模块。knowledge/frame_geometry 曾一并编译，
# 实测读档 _decode 反而慢 5–12%（大量 Python 对象/动态调用，Cython 调用开销
# 大于收益），因此不编译；见 docs/2026-10-27-cython-scheme-a.md。
MODULES = (
    "dream_demo.ui.render",
    "dream_demo.core.map_scene",
    "dream_demo.ui.map_presentation",
    # CY-1..CY-5 内核（2026-10-27）：实测后按收益保留；负优化模块会被移出此表。
    "dream_demo.core.save_kernel",
    "dream_demo.core.vision.sight_kernel",
    "dream_demo.core.gas_kernel",
    "dream_demo.ui.app.fx_kernel",
    # frame_geometry：cell_ranges A/B 实测纯 1.97–2.31ms → compiled 1.24–1.30ms
    # （−0.7~1.0ms/步），低于 ≥1ms 保留线；compose_fx 无收益（Rich Text.stylize
    # 主导）。按规则移出默认构建，后续若 cell_ranges 设计变化再复测。
    # knowledge_kernel（CY-6，2026-10-27）：compiled 内核相对纯 Python 只快约
    # 0.24ms/步（1056 格视口、121 轮配对中位差，约 −11%），远低于「每步 p50
    # 降低 ≥1ms」的保留线——构造 CellKnowledge/TerrainMemory 仍是 Python 对象
    # 开销，编译只省解释器派发。按方案 A 规则移出默认构建；源码、回退路径与
    # ONEIRSCRIPT_CY_KERNEL_KNOWLEDGE=1 开关保留，后续若改数据结构再复测。

    # ui.raster_kernel：2026-10-27 复测（101 帧配对）中位差 0.0ms、均值 −0.05ms，
    # 属噪声内无实际改善；移出默认构建。源码、回退路径与
    # ONEIRSCRIPT_CY_KERNEL_RASTER=1 开关保留，后续若改栅格策略再复测。
)


def _module_source(name: str) -> Path:
    return ROOT.joinpath(*name.split(".")).with_suffix(".py")


def _extension_suffixes() -> tuple[str, ...]:
    import importlib.machinery
    return tuple(importlib.machinery.EXTENSION_SUFFIXES)


def _extensions(name: str) -> list[Path]:
    base = ROOT.joinpath(*name.split("."))
    parent = base.parent
    stem = base.name
    paths = []
    for suffix in _extension_suffixes():
        path = parent / (stem + suffix)
        if path.exists():
            paths.append(path)
    return paths


def _save_manifest(items: dict[str, list[str]]) -> None:
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(items, indent=2, ensure_ascii=False), encoding="utf-8")


def _load_manifest() -> dict[str, list[str]]:
    if not MANIFEST.exists():
        return {}
    try:
        return json.loads(MANIFEST.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def build() -> int:
    try:
        from Cython.Build import cythonize
        from setuptools import Distribution, Extension
    except ImportError as error:
        print(f"缺少 Cython/setuptools：{error}")
        return 2
    sources = [(name, _module_source(name)) for name in MODULES]
    missing = [str(path) for _name, path in sources if not path.is_file()]
    if missing:
        print("源文件缺失：", ", ".join(missing))
        return 2
    BUILD_DIR.mkdir(parents=True, exist_ok=True)
    extensions = [Extension(name, [str(path)]) for name, path in sources]
    ext_modules = cythonize(
        extensions,
        build_dir=str(BUILD_DIR / "c"),
        # 这些模块大量使用 PEP 484 注解做文档/IDE 提示，部分局部变量在分支里
        # 先赋值再注解。Cython 3 的 annotation_typing 会把它当 C 声明而报
        # redeclared；关掉后按普通 Python 语义编译。
        compiler_directives={"language_level": 3, "binding": True,
                             "annotation_typing": False},
        quiet=False,
    )
    dist = Distribution({"ext_modules": ext_modules})
    # 通过 setuptools 的 build_ext 生成 in-place 扩展。
    from setuptools.command.build_ext import build_ext
    command = build_ext(dist)
    command.inplace = True
    command.ensure_finalized()
    command.run()
    manifest = {}
    for name in MODULES:
        paths = _extensions(name)
        if not paths:
            print(f"警告：{name} 未生成扩展")
            continue
        manifest[name] = [str(path.relative_to(ROOT)) for path in paths]
    _save_manifest(manifest)
    print("已生成扩展：")
    for name, paths in manifest.items():
        print(f"  {name}: {', '.join(paths)}")
    return 0


def _all_generated() -> list[Path]:
    """扫描 dream_demo 下所有 Cython 扩展（含旧模块/已禁用），用于彻底清理。"""
    import importlib.machinery
    suffixes = tuple(importlib.machinery.EXTENSION_SUFFIXES)
    found = []
    for path in ROOT.joinpath("dream_demo").rglob("*"):
        if not path.is_file():
            continue
        name = path.name
        if (name.endswith(".pyd.disabled") or name.endswith(".so.disabled")
                or name.endswith(".pyd.removing") or name.endswith(".so.removing")):
            found.append(path)
        elif any(name.endswith(suffix) for suffix in suffixes):
            found.append(path)
    return found


def clean() -> int:
    # 清理所有旧构建遗留：只按当前 MODULES 清会漏掉被移出列表的模块。
    for path in _all_generated():
        try:
            path.unlink()
        except PermissionError:
            # 进程/杀毒可能仍持有已加载的 .pyd：先改名，保证 import 不会再命中；
            # 下次重启后 --clean 会把它删掉。
            try:
                path.rename(path.with_name(path.name + ".removing"))
            except OSError:
                pass
    if BUILD_DIR.exists():
        shutil.rmtree(BUILD_DIR)
    MANIFEST.unlink(missing_ok=True)
    print("已清理 Cython 扩展，恢复纯 Python 路径。")
    return 0


def disable() -> int:
    moved = 0
    for path in _all_generated():
        if path.name.endswith(".disabled"):
            continue
        target = path.with_name(path.name + ".disabled")
        if target.exists():
            target.unlink()
        path.rename(target)
        moved += 1
    print(f"已禁用 {moved} 个扩展（改名为 .disabled）。")
    return 0


def enable() -> int:
    moved = 0
    for path in _all_generated():
        if not path.name.endswith(".disabled"):
            continue
        target = path.with_name(str(path.name)[:-len(".disabled")])
        if target.exists():
            target.unlink()
        path.rename(target)
        moved += 1
    print(f"已启用 {moved} 个扩展。")
    return 0


def verify() -> int:
    ok = True
    for name in MODULES:
        module = __import__(name, fromlist=["__file__"])
        file = getattr(module, "__file__", None) or ""
        compiled = Path(file).suffix in (".pyd", ".so")
        print(f"{'扩展' if compiled else '纯Python'}  {name}  {file}")
        ok = ok and compiled
    return 0 if ok else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build", action="store_true", help="编译扩展")
    parser.add_argument("--clean", action="store_true", help="删除扩展与中间产物")
    parser.add_argument("--disable", action="store_true", help="改名禁用扩展")
    parser.add_argument("--enable", action="store_true", help="恢复扩展")
    parser.add_argument("--verify", action="store_true", help="检查当前导入的是否为扩展")
    args = parser.parse_args()
    actions = [args.build, args.clean, args.disable, args.enable, args.verify]
    if sum(bool(item) for item in actions) != 1:
        parser.print_help()
        return 2
    if args.build:
        return build()
    if args.clean:
        return clean()
    if args.disable:
        return disable()
    if args.enable:
        return enable()
    return verify()


if __name__ == "__main__":
    raise SystemExit(main())
