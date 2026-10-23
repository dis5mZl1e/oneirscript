"""Deterministic, bounded casting animation on the existing character map."""
import math
from ..data.anomaly_skills import FX_PROFILES


def _shade(color, strength):
    return '#' + ''.join(f'{int(int(color[i:i+2],16)*strength):02x}' for i in (1,3,5))


def paint_casts(snap, t, quality):
    styles, glyphs = {}, {}
    _, _, width, height = snap.viewport
    visible = snap.projectile_visible if snap.projectile_visible is not None else snap.ambient_visible
    def seen(p):
        return 0 <= p[0] < width and 0 <= p[1] < height and (visible is None or p in visible)
    active = []
    for cast in snap.casts:
        age = t-cast.born
        if cast.stage != 'charge' and not 0 <= age < cast.life:
            continue
        preset = FX_PROFILES[cast.profile]
        cells = tuple(dict.fromkeys(cast.cells or (cast.source,)))
        path = cast.path or tuple(sorted(cells, key=lambda p: (max(abs(p[0]-cast.source[0]), abs(p[1]-cast.source[1])), p)))
        pool = tuple(p for p in cells if seen(p))
        local_charge = ()
        if cast.stage == 'charge' and seen(cast.source):
            x, y = cast.source
            # A locked target may be protected or entirely outside the viewport.
            # Charge belongs to the visible caster as well as its warning area.
            ring = ((x-1,y), (x,y-1), (x+1,y), (x,y+1),
                    (x-1,y-1), (x+1,y-1), (x+1,y+1), (x-1,y+1))
            start = int(t*(4+cast.progress*4)) % len(ring)
            local_charge = tuple(p for p in ring[start:]+ring[:start]
                                 if seen(p) and p not in snap.opaque and p not in snap.aura_protected)
        if not pool and not local_charge:
            continue
        if not pool:
            pool = (cast.source,)
        fraction = max(0., min(1., age/max(.01, cast.life)))
        color = preset.color_hex
        if cast.theme == 'library': color = '#d5c294' if cast.motion in ('page','fold','summon','reveal') else '#b69ecd'
        if cast.theme == 'hospital': color = '#a6e1dc'
        if cast.motion == 'frost': color = '#b7d8fa'
        if cast.motion == 'electric': color = '#91e7ef'
        if cast.motion == 'grow': color = '#a9cc84'
        if cast.motion == 'mist': color = '#a2adc4'
        phase = int(t*8 + cast.source[0]*.7 + cast.source[1]*.3)
        if cast.stage == 'charge':
            strength = .10 + (.12 + .13*cast.progress)*(1+math.sin(t*(4+cast.progress*5)))/2
            anchor = cast.source if seen(cast.source) else pool[phase % len(pool)]
            styles[anchor] = 'on ' + _shade(color, strength)
            # Concentrating hints stay inside the authored warning footprint.
            hints = pool[phase % len(pool):] + pool[:phase % len(pool)]
            hints = tuple(dict.fromkeys((*local_charge, *hints)))
            char = preset.particle_char
        else:
            strength = .12 + .2*math.sin(math.pi*fraction)
            center = cast.center or cast.source
            anchor = center if seen(center) else pool[0]
            hints, char = _motion(cast, cells, path, fraction, phase, preset.particle_char)
            styles[anchor] = 'on ' + _shade(color, strength)
        # Purely personal casts get a tiny inward orbit, not an attack footprint.
        # Keep the actor glyph; adjacent solid/protected cells never carry it.
        if cells == (cast.source,) and seen(cast.source) and cast.stage != 'charge' and (
                cast.motion in ('gather', 'bind', 'fold', 'reveal')):
            x, y = cast.source
            orbit = ((x-1,y), (x,y-1), (x+1,y), (x,y+1))
            start = phase % 4
            hints = tuple(p for p in (orbit[start:]+orbit[:start])
                          if seen(p) and p not in snap.opaque and p not in snap.aura_protected)[:2]
            char = ':' if cast.stage == 'charge' or fraction < .4 else '+'
        # Every visible cast gets a key frame independent of the particle budget.
        key = next((p for p in hints if seen(p)), pool[0])
        styles[key] = 'on ' + _shade(color, strength)
        count = (preset.warn_cells_high if quality >= 2 else preset.warn_cells_low) if cast.stage == 'charge' else (preset.cast_cells_high if quality >= 2 else preset.cast_cells_low)
        active.append((tuple(p for p in hints if seen(p))[:count], char, color, strength))
    # Round-robin admission prevents the first emitter consuming the whole frame.
    budget = 48 if quality >= 2 else 24
    for offset in range(8):
        for cells, char, color, strength in active:
            if offset >= len(cells): continue
            p = cells[offset]
            styles[p] = 'on ' + _shade(color, strength)
            if budget and p not in snap.aura_protected and p not in snap.opaque:
                glyphs[p] = (char, f'bold {color} on {_shade(color, strength)}')
                budget -= 1
    return styles, glyphs


def _motion(cast, cells, path, f, phase, default):
    motion = cast.motion
    head = min(len(path)-1, int(f*len(path)*1.5))
    rotating = cells[phase % len(cells):] + cells[:phase % len(cells)]
    if motion in ('line','page','scan','push','pull','cut'):
        if motion == 'pull': head = max(0, len(path)-1-head)
        hints = tuple(path[max(0,head-2):head+1]) or rotating[:1]
        dx, dy = path[-1][0]-cast.source[0], path[-1][1]-cast.source[1]
        direction = ('>' if dx >= 0 else '<') if abs(dx) >= abs(dy) else ('v' if dy >= 0 else '^')
        char = {'page': '/' if phase % 2 else '\\', 'scan': '|', 'cut': '/',
                'line': default, 'push': direction,
                'pull': {'>':'<','<':'>','v':'^','^':'v'}[direction]}[motion]
        return hints, char
    if motion in ('wave','blast','fire','reveal','wash','frost','spread','mist','ink','terrain','grow'):
        center = cast.center or cast.source
        distances = {p: max(abs(p[0]-center[0]), abs(p[1]-center[1])) for p in cells}
        reach = max(distances.values(), default=0)
        radius = min(reach, int(f*(reach+1)*1.4))
        hints = tuple(p for p in rotating if distances[p] == radius) or rotating[:1]
        char = {'wave':'~','blast':'*','fire':'^','reveal':'+','wash':'~',
                'frost':'+','spread':'=','mist':'.','ink':':','terrain':'_', 'grow':'v' if f < .4 else '^'}[motion]
        return hints, char
    if motion == 'fold':
        return (path[:1] + path[-1:]) if phase % 2 else (path[-1:] + path[:1]), '/' if phase % 2 else '\\'
    if motion == 'summon': return rotating, '[' if f < .33 else '+' if f < .66 else ']'
    if motion == 'erase': return rotating, '_' if phase % 2 else '-'
    if motion == 'electric': return rotating, '+' if phase % 2 else '~'
    if motion == 'drip': return rotating, '|' if phase % 3 else '.'
    if motion == 'gather': return tuple(reversed(rotating)), '+' if f > .4 else ':'
    return rotating, ':' if phase % 2 else '='
