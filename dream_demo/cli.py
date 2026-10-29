"""Installed command: keep writable game data outside site-packages."""
from pathlib import Path
import os
import sys


def data_directory() -> Path:
    if sys.platform == 'win32':
        base = Path(os.environ.get('LOCALAPPDATA') or Path.home() / 'AppData/Local')
    elif sys.platform == 'darwin':
        base = Path.home() / 'Library/Application Support'
    else:
        base = Path(os.environ.get('XDG_DATA_HOME') or Path.home() / '.local/share')
    return base / 'Oneirscript'


def main():
    import run_demo
    arguments = list(sys.argv[1:])
    has_directory = any(item == '--game-directory' or item.startswith('--game-directory=') for item in arguments)
    has_save = any(item == '--save-dir' or item.startswith('--save-dir=') for item in arguments)
    if not has_directory:
        directory = data_directory()
        directory.mkdir(parents=True, exist_ok=True)
        arguments.extend(['--game-directory', str(directory)])
    else:
        directory = next((Path(item.split('=', 1)[1]) for item in arguments if item.startswith('--game-directory=')), None)
        if directory is None:
            directory = Path(arguments[arguments.index('--game-directory') + 1])
    if not has_save:
        arguments.extend(['--save-dir', str((directory / 'save').resolve())])
    # WezTerm's handoff must restart the Python module, not a Windows console exe.
    sys.argv = [str(Path(run_demo.__file__).resolve()), *arguments]
    run_demo.main()
