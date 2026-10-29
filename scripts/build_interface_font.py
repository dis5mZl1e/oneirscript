"""Build an OFL upright sans face with the game's half/full-cell metrics."""
from pathlib import Path
import hashlib
import json
import urllib.request

from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont
from fontTools.ttLib.scaleUpem import scale_upem
from fontTools.pens.ttGlyphPen import TTGlyphPen

from build_serif_mono_font import draw_scaled, target_advance

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / 'assets/fonts'


def build(source: Path):
    font = TTFont(source)
    if 'fvar' in font:
        font = instantiateVariableFont(font, {'wght': 450}, inplace=True)
    scale_upem(font, 1000)
    glyphset = font.getGlyphSet()
    cmap = font.getBestCmap()
    converted = {}
    # Draw all source outlines before replacing composite glyph references.
    for cp, name in cmap.items():
        if name in converted:
            continue
        target = target_advance(cp)
        pen = TTGlyphPen(None)
        lsb = draw_scaled(glyphset, name, target, pen)
        converted[name] = (pen.glyph(), (target, lsb))
    for name, (glyph, metrics) in converted.items():
        font['glyf'][name] = glyph
        font['hmtx'].metrics[name] = metrics
    for table in ('hhea', 'OS/2'):
        obj = font[table]
        if table == 'hhea':
            obj.ascent, obj.descent, obj.lineGap = 900, -280, 0
        else:
            obj.sTypoAscender, obj.sTypoDescender, obj.sTypoLineGap = 900, -280, 0
            obj.usWeightClass = 450
            # WezTerm reads hhea; leave version-3 OS/2 selection bits valid.
            if obj.version >= 4:
                obj.fsSelection |= 1 << 7
            else:
                obj.fsSelection &= 127
    font['post'].isFixedPitch = 1
    family = 'Dream Strata Interface Sans'
    for identifier, value in {1: family, 2: 'Regular', 3: family + ':1.0', 4: family,
                              6: 'DreamStrataInterfaceSans-Regular', 16: family, 17: 'Regular'}.items():
        font['name'].removeNames(nameID=identifier)
        font['name'].setName(value, identifier, 3, 1, 0x409)
    output = DEST / 'DreamStrataInterfaceSans-Regular.ttf'
    font.save(output)
    (DEST / 'interface-sans.json').write_text(json.dumps({
        'family': family, 'file': output.name,
        'sha256': hashlib.sha256(output.read_bytes()).hexdigest(),
        'source': 'Noto Sans SC', 'license': 'OFL-1.1',
        'modifications': '450 weight; 500/1000 cell advances; shared reading baseline; renamed family',
    }, indent=2), encoding='utf-8')
    print(output)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    build(parser.parse_args().source)
