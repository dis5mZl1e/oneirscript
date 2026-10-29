"""Persistent private font resources for external terminal processes."""
from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path
import sys
import tempfile

LEGACY_FAMILY = "Dream Strata Song Reading"
LEGACY_FILE = "DreamStrataSongReading-Regular.ttf"
UNIFIED_MANIFEST = "unified-font.json"


@dataclass(frozen=True)
class FontFace:
    family: str
    file: str
    path: Path
    unified: bool = False
    default: bool = False
    version: str = ""


def asset_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", ".")) / "fonts"
    from .resource_paths import assets_dir
    return assets_dir() / "fonts"


# (路径, mtime_ns, 大小) -> 内容 sha256。
_digest_cache: dict[tuple[str, int, int], str] = {}


def _file_digest(path: Path) -> str:
    """校验用内容哈希，按文件版本缓存。

    随包统一字体有 15.36 MB，读全文 + sha256 实测 14.05 ms/次。图像栅格每遇到
    一个新字形都要重新解析候选字体（``bundled_font_path`` -> ``active_font_face``
    -> ``unified_font_face``），于是这 14 ms 在场景入口（16 次 = 225 ms）和长途
    探索途中被反复支付——真机按住移动里 in-game `image_frame` 的最大值 412 ms
    就是这么来的（缓存后同轮次口径 55.66 ms）。以 (mtime_ns, 大小) 为键：任何
    改写文件的调用仍会重新校验，同一版本文件的重复校验只剩两次 stat。
    """
    info = path.stat()
    key = (str(path), info.st_mtime_ns, info.st_size)
    digest = _digest_cache.get(key)
    if digest is None:
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        _digest_cache[key] = digest
    return digest


def unified_font_face(directory: Path | None = None) -> FontFace | None:
    """读取并校验候选 manifest；缺失、损坏或哈希不符都视为不可用。"""
    directory = directory or asset_dir()
    manifest = directory / UNIFIED_MANIFEST
    if not manifest.is_file():
        return None
    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(data, dict) or data.get("schema") != 1 or data.get("candidate") is not True:
        return None
    family, filename = data.get("family"), data.get("file")
    if not isinstance(family, str) or not family.strip():
        return None
    if not isinstance(filename, str) or Path(filename).name != filename:
        return None
    path = directory / filename
    if not path.is_file():
        return None
    if _file_digest(path) != data.get("sha256"):
        return None
    return FontFace(family=family, file=filename, path=path, unified=True,
                    default=data.get("default") is True,
                    version=str(data.get("version", "")))


def legacy_font_face(directory: Path | None = None) -> FontFace:
    directory = directory or asset_dir()
    return FontFace(family=LEGACY_FAMILY, file=LEGACY_FILE, path=directory / LEGACY_FILE)


def active_font_face(directory: Path | None = None, *, force_unified: bool = False) -> FontFace:
    """候选只有在 manifest 声明 default 或显式 QA 开关时才替换分体字体。"""
    directory = directory or asset_dir()
    face = unified_font_face(directory)
    if face is not None and (force_unified or face.default):
        return face
    return legacy_font_face(directory)


def private_cache_dir() -> Path:
    """用户缓存根目录；旧名目录存在且新目录未建立时整体迁移过来。"""
    if sys.platform=='win32':
        base=Path(os.environ.get('LOCALAPPDATA') or Path.home()/'AppData/Local')
    elif sys.platform=='darwin':
        base=Path.home()/'Library/Caches'
    else:
        base=Path(os.environ.get('XDG_CACHE_HOME') or Path.home()/'.cache')
    current=base/'Oneirscript'
    legacy=base/'DreamStrata'
    if not current.exists() and legacy.is_dir():
        try:
            legacy.rename(current)
        except OSError:
            pass
    return current


def copy_asset(source:Path,target:Path) -> None:
    data=source.read_bytes()
    if target.is_file() and hashlib.sha256(target.read_bytes()).digest()==hashlib.sha256(data).digest():
        return
    target.parent.mkdir(parents=True,exist_ok=True)
    temporary=None
    try:
        with tempfile.NamedTemporaryFile(dir=target.parent,prefix=target.name+'.',suffix='.tmp',delete=False) as stream:
            temporary=Path(stream.name)
            stream.write(data)
        temporary.replace(target)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def persistent_font_dir(source:Path,base:Path) -> Path:
    """Copy out of onefile extraction before handing control to another process."""
    files=[p for p in source.iterdir() if p.is_file() and p.suffix.lower() in ('.ttf','.otf','.txt','.md','.json')]
    for directory in (base/'.wezterm/fonts',private_cache_dir()/'fonts'):
        try:
            directory.mkdir(parents=True,exist_ok=True)
            for asset in files:
                copy_asset(asset,directory/asset.name)
            return directory.resolve()
        except OSError:
            continue
    raise OSError('无法保存终端字体；请检查游戏目录或用户缓存目录的写入权限。')


def emoji_faces(directory:Path) -> list[dict]:
    manifest=directory/'emoji-package.json'
    if not manifest.exists():
        return []
    faces=json.loads(manifest.read_text(encoding='utf-8'))['faces']
    for face in faces:
        filename=face['file']
        if Path(filename).name!=filename or not (directory/filename).is_file():
            raise OSError('Emoji 字体包不完整，请重新解压游戏。')
        if hashlib.sha256((directory/filename).read_bytes()).hexdigest()!=face['sha256']:
            raise OSError('Emoji 字体包校验失败，请重新解压游戏。')
    return faces


def semantic_icon_faces(directory: Path) -> list[dict]:
    """Validated first-batch semantic subsets (docs §16); reserves not packaged."""
    manifest = directory / 'semantic-icons.json'
    if not manifest.is_file():
        return []
    data = json.loads(manifest.read_text(encoding='utf-8'))
    faces = data.get('fonts', [])
    for face in faces:
        filename = face['file']
        if Path(filename).name != filename or not (directory / filename).is_file():
            raise OSError('语义图标字体包不完整，请重新解压游戏。')
        if hashlib.sha256((directory / filename).read_bytes()).hexdigest() != face['sha256']:
            raise OSError('语义图标字体包校验失败，请重新解压游戏。')
    return faces


def semantic_icon_manifest(directory: Path) -> dict | None:
    manifest = directory / 'semantic-icons.json'
    if not manifest.is_file():
        return None
    return json.loads(manifest.read_text(encoding='utf-8'))


def game_icon_face(directory: Path) -> dict | None:
    manifest = directory / 'glyph-manifest.json'
    if not manifest.is_file():
        return None
    face = json.loads(manifest.read_text(encoding='utf-8'))
    filename = face['file']
    if Path(filename).name != filename or not (directory / filename).is_file():
        raise OSError('游戏图标字体包不完整，请重新解压游戏。')
    if hashlib.sha256((directory / filename).read_bytes()).hexdigest() != face['sha256']:
        raise OSError('游戏图标字体包校验失败，请重新解压游戏。')
    return face
