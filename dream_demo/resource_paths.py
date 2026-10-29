"""Resolve read-only assets in source checkouts and installed Python packages."""
from pathlib import Path
import sys


def assets_dir() -> Path:
    if getattr(sys, 'frozen', False):
        return Path(getattr(sys, '_MEIPASS', '.'))
    source = Path(__file__).resolve().parents[1] / 'assets'
    if (source / 'fonts/DreamStrataSongReading-Regular.ttf').is_file():
        return source
    return Path(__file__).resolve().parent / '_assets'
