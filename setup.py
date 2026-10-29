"""Include the existing asset tree in installed wheels without duplicating it in Git."""
from pathlib import Path
import shutil

from setuptools import setup
from setuptools.command.build_py import build_py


class BuildWithAssets(build_py):
    def run(self):
        super().run()
        source = Path(__file__).resolve().parent / 'assets'
        target = Path(self.build_lib) / 'dream_demo/_assets'
        for name in ('fonts', 'sfx', 'music', 'wezterm', 'licenses', 'data'):
            shutil.copytree(source / name, target / name, dirs_exist_ok=True)
        shutil.copy2(source / 'CREDITS.md', target / 'CREDITS.md')


setup(cmdclass={'build_py': BuildWithAssets})
