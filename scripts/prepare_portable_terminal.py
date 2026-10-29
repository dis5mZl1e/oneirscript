"""Maintainer build step: fetch/verify bundled WezTerm so players need no download."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from dream_demo.wezterm_setup import (WEZTERM_TAG,_open,_platform_asset,_usable_executable,
                                    _vendor_executable,download_wezterm,vendor_dir)


def prepare(base:Path) -> Path:
    if _platform_asset() is None:
        raise OSError('此平台/架构暂无固定版本便携终端，不能生成完整发行包。')
    directory=vendor_dir(base)
    executable=_vendor_executable(base)
    if executable is None:
        executable=download_wezterm(base,mirrors=('', 'https://gh-proxy.com/'))
    if sys.platform.startswith('linux'):
        image=directory/'wezterm.AppImage'
        extracted=directory/'squashfs-root/AppRun'
        if not extracted.is_file():
            result=subprocess.run([str(image.resolve()),'--appimage-extract'],cwd=directory,
                                  capture_output=True,timeout=180)
            if result.returncode:
                raise OSError('Linux 便携终端预解包失败，不能生成依赖玩家安装 FUSE 的发行包。')
        executable=extracted
    usable=_usable_executable(executable)
    if usable is None:
        raise OSError('随包终端执行检查失败，已停止发行打包。')
    options=dict(capture_output=True,text=True,timeout=20)
    if sys.platform=='win32':
        options['creationflags']=subprocess.CREATE_NO_WINDOW
    cli=usable.with_name('wezterm.exe' if sys.platform=='win32' else 'wezterm')
    version_executable=cli if cli.is_file() else usable
    result=subprocess.run([str(version_executable),'--version'],**options)
    if result.returncode or WEZTERM_TAG not in result.stdout:
        raise OSError('便携终端版本与固定发行版本不符。')
    license=directory/'LICENSE.md'
    if not license.is_file():
        bundled_license=ROOT/'assets/licenses/WezTerm-LICENSE.md'
        if bundled_license.is_file():
            license.write_bytes(bundled_license.read_bytes())
        else:
            with _open(f'https://raw.githubusercontent.com/wezterm/wezterm/{WEZTERM_TAG}/LICENSE.md') as response:
                license.write_bytes(response.read())
    manifest=dict(version=WEZTERM_TAG,platform=sys.platform,architecture=platform.machine(),
                  executable=usable.relative_to(directory).as_posix(),
                  executable_sha256=hashlib.sha256(usable.read_bytes()).hexdigest(),
                  license_sha256=hashlib.sha256(license.read_bytes()).hexdigest())
    (directory/'terminal-release.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    print(json.dumps(manifest))
    return usable


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base',type=Path,default=ROOT)
    args=parser.parse_args()
    prepare(args.base.resolve())
