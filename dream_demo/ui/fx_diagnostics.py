"""Headless verification shared by source and frozen launchers."""
from __future__ import annotations

from importlib.metadata import version

from .asciimatics_bridge import ASCIIMATICS_AVAILABLE, CinematicBridge
from .home_particles import HomeParticles
from .map_particles import MapParticles
from .ornament_frame import ornament_cells


def smoke_fx():
    if not ASCIIMATICS_AVAILABLE:
        raise RuntimeError('asciimatics is unavailable in this artifact')
    endings = {}
    for ending in 'ABCDEF':
        bridge = CinematicBridge(ending, 80, 24)
        painted = sum(bridge.advance(t).painted_cells for t in (.2, 1.0, 2.0, bridge.duration))
        if painted == 0:
            raise RuntimeError(f'Ending {ending} has no painted cells')
        endings[ending] = {'duration': bridge.duration, 'painted': painted}
        bridge.cancel()
    visible = {(x, y) for y in range(24) for x in range(80)}
    particles = {}
    for kind in ('spark', 'explosion', 'memory'):
        player = MapParticles()
        player.emit(kind, (40, 12), 0)
        count = len(player.frame((0, 0, 80, 24), visible, set(), .15))
        if not count:
            raise RuntimeError(f'{kind} particles not painted')
        particles[kind] = count
    home = HomeParticles()
    dust = home.frame(80, 24, 1, 'high')
    return {'asciimatics': version('asciimatics'), 'endings': endings,
            'map_particles': particles, 'home_particles': len(dust),
            'regional_borders': [len(ornament_cells(80, 24, d)) for d in (1, 11, 21)]}
