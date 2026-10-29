"""Readable Song variant: Noto Serif SC Medium, square tile metrics, serif Latin.

Keep the original mixed font intact; use its existing symbol sources and licenses.
The downloaded upstream font is build input only, never a player dependency.
"""
from pathlib import Path
import hashlib
import json
import urllib.request

from build_serif_mono_font import ROOT, SRC_DIR_DEFAULT, _gf_url, build


def main():
    source = SRC_DIR_DEFAULT / 'song-medium.ttf'
    url = _gf_url('Noto+Serif+SC:wght@500') if not source.exists() else None
    if url:
        source.write_bytes(urllib.request.urlopen(url, timeout=60).read())
    names = ('base', 'victor', 'symbols', 'symbols2', 'math', 'greek', 'hebrew',
             'georgian', 'tibetan', 'egyptian', 'hangul', 'notoemoji')
    paths = {name: SRC_DIR_DEFAULT / (name + '.ttf') for name in names}
    paths['base'] = source
    target = ROOT / 'assets/fonts/DreamStrataSongReading-Regular.ttf'
    build(paths, target, reading=True)
    metadata = dict(family='Dream Strata Song Reading', upstream='Noto Serif SC Medium', weight=500,
                    source='https://fonts.googleapis.cn/css2?family=Noto+Serif+SC:wght@500',
                    source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                    sha256=hashlib.sha256(target.read_bytes()).hexdigest(), license='OFL-1.1',
                    builder='scripts/build_song_reading_font.py', half_width=500, full_width=1000,
                    row_height=1180, ascent=900, descent=-280, composite_outlines='decomposed',
                    square_symbol_ink='two columns when followed by reserved space')
    (target.parent/'song-reading.json').write_text(json.dumps(metadata, indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()
