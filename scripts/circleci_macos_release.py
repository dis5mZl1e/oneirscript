"""Build two language packages and verify macOS archive paths, architecture and smoke."""
from pathlib import Path
import argparse, datetime, hashlib, json, os, platform, plistlib, subprocess, sys, tempfile, zipfile
ROOT=Path(__file__).resolve().parents[1]
def run(arch):
    assert sys.platform == 'darwin', 'Run on macOS'
    assert platform.machine() == arch, (platform.machine(),arch)
    sys.path.insert(0,str(ROOT))
    from scripts.build_portable_bundle import build, app_version
    day=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).strftime('%Y%m%d')
    label='Intel' if arch=='x86_64' else 'arm64'
    for language in ('en','zh'):
        archive=ROOT/'build/releases'/f'Oneirscript-v{app_version()}-{day}-macOS-{label}-{language}.zip'
        build(ROOT/'Oneirscript',ROOT/'vendor/wezterm',archive,'macos',language)
        with zipfile.ZipFile(archive) as z, tempfile.TemporaryDirectory(prefix='oneirscript-smoke-') as temp:
            names=z.namelist()
            assert z.testzip() is None
            assert all(n.isascii() for n in names)
            info=plistlib.loads(z.read('Oneirscript.app/Contents/Info.plist'))
            assert info['CFBundleExecutable']=='launch-game'
            core='Oneirscript.app/Contents/MacOS/OneirscriptCore'
            for name in (core,'Oneirscript.app/Contents/MacOS/launch-game','launch-compat.command'):
                assert (z.getinfo(name).external_attr >> 16) & 0o111, name
            assert core.encode() in z.read('Oneirscript.app/Contents/MacOS/launch-game')
            z.extractall(temp)
            executable=Path(temp)/core
            executable.chmod(0o755)
            actual=subprocess.check_output(['lipo','-archs',str(executable)],text=True).strip().split()
            assert actual==[arch],actual
            result=subprocess.run([str(executable),'--smoke','--game-directory',temp,'--save-dir',str(Path(temp)/'save-smoke')],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=180)
            (archive.parent/(archive.stem+'-smoke.log')).write_bytes(result.stdout)
            assert result.returncode==0,result.stdout[-2000:]
            assert (Path(temp)/'save-smoke/run.json').is_file()
        report={'archive':archive.name,'sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'bytes':archive.stat().st_size,'architecture':arch,'language':language,'ascii_paths':True,'integrity':True,'smoke_exit_code':0,'intel_test':'Rosetta on Apple Silicon' if arch=='x86_64' else 'native Apple Silicon','commit':os.environ.get('CIRCLE_SHA1','unknown')}
        archive.with_name(archive.stem+'-verification.json').write_text(json.dumps(report,indent=2),'utf-8')
        print(json.dumps(report),flush=True)
if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--arch',choices=('arm64','x86_64'),required=True)
    run(parser.parse_args().arch)
