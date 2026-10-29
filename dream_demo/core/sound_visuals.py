"""Information-safe, compact presentation of sounds actually heard by the player."""
from __future__ import annotations

SOUND_RENDER_RADIUS = 2.5
SOUND_CELL_REACH = SOUND_RENDER_RADIUS  # The visual patch follows whole tile centers.


def heard_wave(state, field, x, y, *, by_player=False):
    empty = dict(cells=(), visual_center=None, tail_only=False)
    px, py = state.player.x, state.player.y
    cap, threshold = state._listen_cap(), state._listen_threshold()
    if by_player or cap <= 0 or field.get((px, py), -10**9) < threshold:
        return empty
    audible = {(cx, cy) for (cx, cy), remaining in field.items()
               if remaining >= threshold and abs(cx-px)+abs(cy-py) <= cap}
    if not audible:
        return empty
    tail = abs(x-px)+abs(y-py) > cap
    if tail:
        # Only the coarse arrival sector is represented. Distant sources in the
        # same sector yield the same local ripple, never their real coordinates.
        dx, dy = (x > px)-(x < px), (y > py)-(y < py)
        distance = max(1, cap-2) // max(1, abs(dx)+abs(dy))
        approximate = px+dx*distance, py+dy*distance
        center = min(audible, key=lambda p: ((p[0]-approximate[0])**2+(p[1]-approximate[1])**2, p))
    else:
        center = x, y
    cx, cy = center
    cells = tuple(sorted(p for p in audible
                         if (p[0]-cx)**2+(p[1]-cy)**2 <= SOUND_CELL_REACH**2))
    return dict(cells=cells, visual_center=center, tail_only=tail)
