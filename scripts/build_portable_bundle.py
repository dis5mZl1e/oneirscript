"""Build complete native releases with portable WezTerm, fonts and launchers."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import plistlib
import shutil
import stat
import sys
import tarfile
import tempfile
import zipfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))


def app_version() -> str:
    """版本号唯一来源：pyproject.toml 的 [project].version。"""
    import tomllib

    data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    return str(data["project"]["version"])


def native_target() -> str:
    return {'win32':'windows','darwin':'macos'}.get(sys.platform,'linux')


def _write(path:Path,text:str,mode:int=0o644) -> None:
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(text,encoding='utf-8',newline='')
    path.chmod(mode)


LICENSE_FILES=('LICENSE','LICENSING.md','THIRD-PARTY-NOTICES.md')


def _copy_license_materials(stage:Path) -> list[str]:
    """随包交付许可与来源声明（GPLv3 §6 与 THIRD-PARTY-NOTICES.md 的清单要求）。

    发行包此前只有字体子目录里的许可，没有根目录的 LICENSE／LICENSING.md／
    第三方声明与音频署名；这些是首次公开发布的硬条件，不能靠仓库链接代替。
    """
    copied:list[str]=[]
    for name in LICENSE_FILES:
        source=ROOT/name
        if source.is_file():
            shutil.copyfile(source,stage/name)
            copied.append(name)
    credits=ROOT/'assets/CREDITS.md'
    if credits.is_file():
        (stage/'assets').mkdir(parents=True,exist_ok=True)
        shutil.copyfile(credits,stage/'assets/CREDITS.md')
        copied.append('assets/CREDITS.md')
    licenses=ROOT/'assets/licenses'
    if licenses.is_dir():
        shutil.copytree(licenses,stage/'assets/licenses',dirs_exist_ok=True)
        copied.extend('assets/licenses/'+p.name for p in sorted(licenses.iterdir()) if p.is_file())
    return copied


def _zip_tree(stage:Path,output:Path,executables:set[str]) -> None:
    with zipfile.ZipFile(output,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=7) as archive:
        for source in sorted(stage.rglob('*')):
            name=source.relative_to(stage).as_posix()
            if source.is_symlink():
                target=os.readlink(source)
                if not (source.parent/target).resolve().is_relative_to(stage.resolve()):
                    raise ValueError(f'包内链接越界：{name}')
                info=zipfile.ZipInfo(name)
                info.create_system=3; info.external_attr=(stat.S_IFLNK|0o777)<<16
                archive.writestr(info,target)
            elif source.is_file():
                info=zipfile.ZipInfo.from_file(source,name)
                info.create_system=3
                if name in executables:
                    info.external_attr=(stat.S_IFREG|0o755)<<16
                archive.writestr(info,source.read_bytes(),compress_type=zipfile.ZIP_DEFLATED,compresslevel=7)


def build(game:Path,terminal:Path,output:Path,target:str|None=None,language:str|None=None):
    target=target or native_target()
    required={'windows':'wezterm-gui.exe','macos':'WezTerm.app/Contents/MacOS/wezterm-gui',
              'linux':'squashfs-root/AppRun'}[target]
    if not game.is_file() or not (terminal/required).is_file():
        raise FileNotFoundError('完整发行包需要对应平台游戏核心和完整的便携 WezTerm（Linux 需预解包 AppRun）。')
    if not (terminal/'LICENSE.md').is_file():
        raise FileNotFoundError('便携终端缺少上游 LICENSE.md。')
    magic=game.read_bytes()[:4]
    matches={'windows':magic.startswith(b'MZ'),'linux':magic==b'\x7fELF',
             'macos':magic in (b'\xcf\xfa\xed\xfe',b'\xce\xfa\xed\xfe',b'\xfe\xed\xfa\xcf',b'\xfe\xed\xfa\xce',b'\xca\xfe\xba\xbe',b'\xbe\xba\xfe\xca',b'\xca\xfe\xba\xbf')}
    if not matches[target]:
        raise ValueError('游戏核心与目标平台不匹配；必须在目标系统原生构建。')
    if output.exists():
        raise FileExistsError(f'产物已存在：{output}；请使用新文件名。')
    output.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='dream-release-') as directory:
        stage=Path(directory)
        shutil.copytree(terminal,stage/'vendor/wezterm',symlinks=True,
                        ignore=shutil.ignore_patterns('*.pdb','*.log','wezterm.AppImage' if target=='linux' else '*.unused'))
        shutil.copytree(ROOT/'assets/fonts',stage/'assets/fonts')
        if (ROOT/'assets/wezterm').is_dir():
            shutil.copytree(ROOT/'assets/wezterm',stage/'assets/wezterm')
        license_materials=_copy_license_materials(stage)
        if target=='macos':
            binary='Oneirscript.app/Contents/MacOS/OneirscriptCore'
            launcher='Oneirscript.app/Contents/MacOS/launch-game'
            _write(stage/launcher,'#!/bin/sh\nset -eu\nbase=$(CDPATH= cd -- "$(dirname -- "$0")/../../.." && pwd)\nexec "$base/Oneirscript.app/Contents/MacOS/OneirscriptCore" --game-directory "$base" "$@"\n',0o755)
            info={'CFBundleName':'梦层','CFBundleDisplayName':'梦层','CFBundleIdentifier':'org.oneirscript.game',
                  'CFBundleExecutable':'launch-game','CFBundlePackageType':'APPL',
                  'CFBundleVersion':app_version(),'CFBundleShortVersionString':app_version(),
                  'NSHighResolutionCapable':True}
            (stage/'Oneirscript.app/Contents/Info.plist').write_bytes(plistlib.dumps(info))
            _write(stage/'launch-compat.command','#!/bin/sh\nset -eu\nbase=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)\nexec "$base/Oneirscript.app/Contents/MacOS/OneirscriptCore" --game-directory "$base" --compat-terminal "$@"\n',0o755)
        elif target=='linux':
            binary='Oneirscript'
            launcher='launch-game.sh'
            _write(stage/launcher,'#!/bin/sh\nset -eu\nbase=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)\nexec "$base/Oneirscript" --game-directory "$base" "$@"\n',0o755)
            _write(stage/'launch-compat.sh','#!/bin/sh\nset -eu\nbase=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)\nexec "$base/Oneirscript" --game-directory "$base" --compat-terminal "$@"\n',0o755)
            (stage/'vendor/wezterm/squashfs-root/AppRun').chmod(0o755)
        else:
            binary='Oneirscript.exe'
            launcher=binary
            _write(stage/'launch-compat.cmd','@echo off\r\nchcp 65001 >nul\r\ncd /d "%~dp0"\r\nstart "" /wait "'+binary+'" --compat-terminal\r\n')
        (stage/binary).parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(game,stage/binary); (stage/binary).chmod(0o755)
        if language:
            # 预置中/英文默认配置：语言与装备句法成对出现，避免英文界面配中文句法。
            from dream_demo.user_config import render_template
            preset={'language':language,'equipment_syntax':language}
            (stage/'game_config.ini').write_text(render_template(defaults=preset),
                                                 encoding='utf-8-sig',newline='')
        _write(stage/'README.txt',
               'Oneirscript portable edition v' + app_version() + '\n\n'
               'Extract the entire archive before starting. Keep assets and vendor beside the game.\n'
               'Windows: double-click Oneirscript.exe. No Python installation is required.\n'
               'Linux: run ./launch-game.sh from a graphical desktop (x86_64).\n'
               'macOS: open Oneirscript.app; choose the Intel or Apple Silicon package for your Mac.\n'
               'The bundled WezTerm loads game fonts privately without installing system fonts.\n'
               'If needed, use launch-compat.cmd / launch-compat.sh / launch-compat.command; '
               'font appearance and alignment depend on your terminal in compatibility mode.\n'
               'This macOS build is unsigned and not notarized. If macOS blocks it, review '
               'System Settings > Privacy & Security > Open Anyway for this downloaded app.\n'
               'Controls: Alt+H opens the complete controls; Alt+Z toggles the extended footer.\n'
               'Fonts: serif narrative text, sans interface controls and right sidebar.\n'
               'Keep your save directory when updating; no player saves are included.\n'
               'License and source information: LICENSE, LICENSING.md, THIRD-PARTY-NOTICES.md.\n'
               'Font licenses: assets/fonts; audio credits: assets/CREDITS.md; '
               'terminal license: vendor/wezterm/LICENSE.md.\n'
               + ('Default language and equipment syntax: ' + language + '.\n' if language else
                  'The first launch follows the system language.\n'))
        bad_paths = [p.relative_to(stage).as_posix() for p in stage.rglob('*')
                     if not p.relative_to(stage).as_posix().isascii()]
        if bad_paths:
            raise ValueError('Non-ASCII release paths: ' + repr(bad_paths))
        metadata=dict(version=app_version(),platform=target,architecture=platform.machine(),game=binary,launcher=launcher,
                      game_sha256=hashlib.sha256(game.read_bytes()).hexdigest(),terminal='20240203-110809-5046fc22',language=language or 'auto',
                      terminal_entry='vendor/wezterm/'+required,license_materials=license_materials)
        _write(stage/'release-manifest.json',json.dumps(metadata,ensure_ascii=False,indent=2))
        executables={binary,launcher,'vendor/wezterm/'+required,'launch-compat.command','launch-compat.sh'}
        if target=='linux':
            def permissions(info):
                if info.name in executables:
                    info.mode=0o755
                return info
            with tarfile.open(output,'w:gz') as archive:
                for path in sorted(stage.iterdir()):
                    archive.add(path,arcname=path.name,filter=permissions)
        else:
            _zip_tree(stage,output,executables)
    if target=='linux':
        with tarfile.open(output) as archive:
            names=archive.getnames()
    else:
        with zipfile.ZipFile(output) as archive:
            assert archive.testzip() is None
            names=archive.namelist()
    assert all(name.isascii() for name in names), 'Release filenames must be ASCII'
    assert not any(name.startswith(('save/','.wezterm/')) for name in names)
    report=dict(file=str(output.resolve()),bytes=output.stat().st_size,entries=len(names),
                testzip='passed',**metadata)
    output.with_suffix('.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=True))
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--game',type=Path,default=ROOT/('Oneirscript.exe' if sys.platform=='win32' else 'Oneirscript'))
    parser.add_argument('--terminal',type=Path,default=ROOT/'vendor/wezterm')
    parser.add_argument('--target',choices=('windows','macos','linux'),default=native_target())
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--language',choices=('zh','en'),default=None,
                        help='预置界面语言与装备句法；缺省不写 game_config.ini（运行时检测系统语言）')
    args=parser.parse_args()
    build(args.game,args.terminal,args.output,args.target,args.language)
