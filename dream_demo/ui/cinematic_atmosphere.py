"""Bounded, deterministic scene depth and brief dissolves for offscreen endings."""
from functools import lru_cache
import math
from .cinematic_frame import CinematicFrame
from .deco import mix_hex


def smooth(value):
    value = min(1.0, max(0.0, value))
    return value*value*(3-2*value)


@lru_cache(maxsize=4096)
def shade(color, level, background=False):
    color = mix_hex('#0b0b12', color, level/16)
    if background:
        channels = [int(color[i:i+2], 16) for i in (1, 3, 5)]
        scale = min(1.0, 48/max(1, max(channels)))
        color = '#'+''.join(f'{round(c*scale):02x}' for c in channels)
    return color


def atmosphere(frame, ending, elapsed, duration, quality):
    if ending not in 'ABCDEF' or not ending or duration <= 0:
        return frame
    out = CinematicFrame(frame.width, frame.height, dict(frame.glyphs), dict(frame.colors))
    w, h = out.width, out.height
    progress = min(1.0, elapsed/duration)
    quiet = 1-smooth((progress-.65)/.35) if ending in 'CEF' else 1.0
    # Sparse motifs remain peripheral, so the narrative occupies a stable stage.
    candidates = []
    color = {'A':'#bca472', 'B':'#8d9caf', 'C':'#8ba3ad',
             'D':'#78a3ba', 'E':'#82708f', 'F':'#798895'}[ending]
    if w >= 12 and h >= 6 and quiet > .01:
        if ending == 'A':
            for side in (-1, 1):
                for y in range(h//2, h-1):
                    x = w//2 + side*(4+(y-h//2)*2)
                    candidates.append((x, y, '╱' if side < 0 else '╲'))
        elif ending == 'B':
            for y in range(2, h-1, 3):
                for x in (2, 3, w-4, w-3):
                    candidates.append((x, y, '─'))
        elif ending == 'C':
            for y in range(1, h-1, 2):
                inset = 2+int(progress*min(w,h)*.2)
                for x in (inset, w-1-inset):
                    candidates.append((x, y, '·'))
        elif ending == 'D':
            for x in range(2, w-2, 3):
                wave = round(math.sin(x*.2+elapsed*.65))
                candidates.extend(((x, h//2-4+wave, '·'), (x, h//2+4-wave, '·')))
        elif ending == 'E':
            for i in range(min(24, w//2)):
                candidates.append((2+(i*17) % max(1,w-4),
                                   (i*7+int(elapsed*2)) % max(1,h), ':'))
        else:
            for x in range(2, w-2, 6):
                candidates.append((x, max(0, h-3), '·'))
        for x, y, glyph in candidates[:96 if quality == 'high' else 48]:
            if 0 <= x < w and 0 <= y < h and (x,y) not in out.glyphs:
                out.put(x, y, glyph, shade(color, max(1, round(quiet*8))))
    entry = .2 + .8*smooth(elapsed/.6)
    if ending == 'E':
        entry *= 1-smooth((elapsed-duration+.65)/.65)
        if entry <= .001:
            return CinematicFrame.blank(w,h)
    level = max(1, round(entry*16))
    colors = {point:(shade(fg,level) if fg else None,
                     shade(bg,level,True) if bg else None)
              for point,(fg,bg) in out.colors.items()}
    return CinematicFrame(w, h, out.glyphs, colors)


def dissolve(previous, current, progress):
    """Monotone spatial dissolve; no random flicker or terminal control."""
    alpha = smooth(progress)
    if alpha >= 1:
        return current
    if alpha <= 0:
        return previous
    out = CinematicFrame.blank(current.width, current.height)
    for x, y in previous.glyphs.keys() | current.glyphs.keys():
        threshold = ((x*17+y*31) % 101)/101
        owner = current if alpha >= threshold else previous
        if (x,y) not in owner.glyphs:
            continue
        fg, bg = owner.colors.get((x,y),(None,None))
        other_fg, other_bg = (previous if owner is current else current).colors.get((x,y),(None,None))
        weight = alpha if owner is current else 1-alpha
        out.put(x,y,owner.glyphs[(x,y)],
                mix_hex(other_fg or '#0b0b12',fg,weight) if fg else None,
                mix_hex(other_bg or '#0b0b12',bg,weight) if bg else None)
    return out
