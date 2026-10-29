"""Whole-cell, rough circular ripples shared by character and image terminals."""
import math

from ..core.sound_visuals import SOUND_RENDER_RADIUS


def ripple_color(distance, phase):
    if not 0 <= phase < 1 or distance > SOUND_RENDER_RADIUS:
        return None
    radius = .2 + phase*(SOUND_RENDER_RADIUS-.2)
    # One narrow band of whole tiles. Never blend two nearby rings into a disk.
    band = max(0., 1-abs(distance-radius)/.62)
    intensity = band*(1-phase)**.55
    if intensity < .06:
        return None
    return '#%02x%02x%02x' % (round(18+100*intensity), round(30+180*intensity), round(60+175*intensity))


def wave_colors(waves, t, life, width=None, height=None):
    result = {}
    for wave in waves:
        age = t-wave.born
        if not wave.cells or not 0 <= age < life:
            continue
        cx, cy = wave.center or (sum(x for x, _ in wave.cells)/len(wave.cells),
                                sum(y for _, y in wave.cells)/len(wave.cells))
        for x, y in wave.cells:
            if width is not None and not (0 <= x < width and 0 <= y < height):
                continue
            color = ripple_color(math.hypot(x-cx, y-cy), age/life)
            if color:
                result[(x, y)] = color
    return result
