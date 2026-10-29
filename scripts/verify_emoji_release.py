"""Read-only archive/font consistency plus a native smoke in temporary saves."""
import argparse
import hashlib
import json
import marshal
from pathlib import Path
import subprocess
import tempfile

from PyInstaller.archive.readers import CArchiveReader

ROOT=Path(__file__).resolve().parents[1]


def verify(exe,output):
    archive=CArchiveReader(str(exe))
    pyz=archive.open_embedded_archive(next(key for key in archive.toc if key.startswith('PYZ')))
    modules=[]
    for name,(package,*_) in pyz.toc.items():
        if not name.startswith('dream_demo') and name!='run_demo':
            continue
        path=ROOT.joinpath(*name.split('.'))
        path=path/'__init__.py' if package==1 else path.with_suffix('.py')
        code=pyz.extract(name)
        assert code==compile(path.read_text(encoding='utf-8-sig'),code.co_filename,'exec',dont_inherit=True),name
        modules.append(name)
    entrypoint=marshal.loads(archive.extract('launch_game'))
    assert entrypoint==compile((ROOT/'launch_game.py').read_text(encoding='utf-8-sig'),entrypoint.co_filename,'exec',dont_inherit=True)
    fonts=[]
    for path in (ROOT/'assets/fonts').iterdir():
        if not path.is_file():
            continue
        key=next(key for key in archive.toc if key.replace('\\','/')=='fonts/'+path.name)
        assert archive.extract(key)==path.read_bytes(),path.name
        fonts.append(path.name)
    effects=[]
    for path in (ROOT/'assets/wezterm').iterdir():
        if not path.is_file():
            continue
        key=next(key for key in archive.toc if key.replace('\\','/')=='wezterm/'+path.name)
        assert archive.extract(key)==path.read_bytes(),path.name
        effects.append(path.name)
    with tempfile.TemporaryDirectory(prefix='emoji-release-smoke-') as directory:
        result=subprocess.run([str(exe),'--smoke','--save-dir',directory],cwd=ROOT,capture_output=True,
            timeout=60,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        output.with_suffix('.log').write_bytes(result.stdout+result.stderr)
        assert result.returncode==0,result.stderr[-2000:]
        assert (Path(directory)/'run.json').exists()
    report=dict(passed=True,exe=str(exe),exe_sha256=hashlib.sha256(exe.read_bytes()).hexdigest(),
                bytes=exe.stat().st_size,matching_modules=len(modules),matching_entrypoint='launch_game',
                matching_fonts=fonts,matching_wezterm_effects=effects,native_smoke_exit=0)
    output.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=True))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--exe',type=Path,default=ROOT/'梦层.exe')
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    verify(args.exe.resolve(),args.output.resolve())
