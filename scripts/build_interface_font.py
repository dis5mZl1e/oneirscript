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


def supplement_symbols(font):
    """Keep UI symbols available even in renderers without font fallback."""
    with TTFont(DEST / 'DreamStrataSongReading-Regular.ttf') as source:
        present = font.getBestCmap()
        glyphset = source.getGlyphSet()
        order = list(font.getGlyphOrder())
        for cp, source_name in source.getBestCmap().items():
            if not 0x2000 <= cp < 0x3000 or cp in present:
                continue
            name = f'uiSymbol{cp:04X}'
            pen = TTGlyphPen(None)
            lsb = draw_scaled(glyphset, source_name, target_advance(cp), pen)
            font['glyf'][name] = pen.glyph()
            font['hmtx'].metrics[name] = (target_advance(cp), lsb)
            order.append(name)
            for table in font['cmap'].tables:
                if table.isUnicode():
                    table.cmap[cp] = name
        font.setGlyphOrder(order)


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
    supplement_symbols(font)
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
    from liquid_tile_outlines import install_liquid_outlines
    install_liquid_outlines(font)
    font.save(output)
    (DEST / 'interface-sans.json').write_text(json.dumps({
        'family': family, 'file': output.name,
        'sha256': hashlib.sha256(output.read_bytes()).hexdigest(),
        'source': 'Noto Sans SC; UI symbols from Dream Strata Song Reading (see LICENSES.md)', 'license': 'OFL-1.1',
        'modifications': '450 weight; 500/1000 cell advances; shared reading baseline; renamed family; missing U+2000-2FFF symbols supplemented',
        'liquid_tile_glyphs': 'Original OFL-1.1 wave ribbons; 1/2/3 lines; shared low baseline; two-column reserved-space ink',
    }, indent=2), encoding='utf-8')
    print(output)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    build(parser.parse_args().source)
