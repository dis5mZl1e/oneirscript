"""English prose for the revised system roles; stable IDs bind live text."""
from .data.abilities import ABILITY_DEFINITIONS
from .data.insights import INSIGHT_DEFINITIONS

ABILITY_PROSE = {
    'spark': 'Leave a visible spark on a pointed tile in sight, or the facing tile. After 2 turns it ignites real material; fire and explosions affect everyone.',
    'echo_pulse': 'Create an echo that moves in the facing direction and reverses at walls for 8 turns. Each turn it emits a radius-10 sound that draws creatures to investigate and records the open/blocked outline of its cell and its four neighbours.',
    'library.erase': 'Draw up to 5 tiles of ink ahead for 4 turns. Each turn it erodes eligible walls by 20 integrity; borders, mechanisms, containers and quest facilities remain protected.',
    'mirror_stance': 'Place an oriented mirror on an adjacent empty tile for 6 turns. It reflects actual projectiles along its normal; returning shots can hurt you.',
    'wide_develop': 'Leave a tracing for 6 turns that records terrain within radius 8 each turn as you move. Standing still reports no new discoveries and never reveals hidden creatures or items.',
    'draw_liquid': 'Choose a liquid: drain the currently visible part of its same-kind four-neighbour component, up to 96 points per cast, and restore a fixed 2 imagination. Never cross unknown cells or touch quest liquids.',
    'transpire': 'Choose a liquid: its visible same-kind component evaporates for 3 rounds, converting at most 8 points per cell and 96 per cast, producing gas by the real material ratio. At most one phase change per cell per round.',
    'ice_bridge': 'Choose a visible liquid landing point and freeze an ice bridge up to 8 long and 3 wide along the direction: each cell moves at most 8 points into the frozen layer and keeps the rest; ordinary walls and sight edges cut the path.',
    'condense_dew': 'Condense water at a visible landing point and its four neighbours: 20 at the center and 10 in each neighbour (up to 60 per cast). Reduce the amount when capacity is short; never displace existing liquid or gas.',
    'sow_green': 'Sow around a visible center within Manhattan radius 3: radius 1 grows tall clumps, the rest low grass, up to 25 cells. Reuses existing plants and never creates rare reward plants.',
    'wax_seal': 'Create a wax memory wall on a pointed open tile in sight, or the facing tile. Occupants, items, mechanisms and quest facilities cannot be overwritten.',
    'dissolve_wall': 'Dissolve a pointed wall in sight, or the facing wall, up to hardness 6. Dense walls, nightmare rock, borders and quest facilities are protected. Real material consequences apply.',
    'raise_terrain': 'Raise a 5-by-5 area around a pointed tile in sight, or the facing tile, driving real liquid flow. Mechanisms and quest facilities are protected.',
    'sink_terrain': 'Lower a 5-by-5 area around a pointed tile in sight, or the facing tile, making a basin for real liquid flow. Mechanisms and quest facilities are protected.',
    'collapse': 'Around a visible target, choose a corridor up to 5 cells long along the direction: break legal ordinary walls on both sides with integrity 40 or less and leave up to 3 rubble cells. Cannot be submitted without a legal wall source; quest paths, occupied cells and borders are protected.',
    'conjure_wall': 'Condense up to 3 imagined aggregate walls along the perpendicular of the chosen direction at a visible center (pushable and destructible); check occupancy, quest fixtures and protected cells first.',
    'rewrite_corner': 'Rewrite a 7-by-7 area around a pointed tile in sight, or the facing tile. Creatures, mechanisms and quest facilities are protected; the outcome may be harmful.',
}
INSIGHT_PROSE = {
    '抗灼': 'Wait one turn while scalded to remove scalding and its attachment. Continued exposure can apply it again.',
    '冷韧': 'Wait one turn while frozen to stretch and clear freezing and its attachment. Ice terrain is unchanged.',
    '抗辐射体质': 'After leaving the radiation source, wait one turn to clear radiation sickness and its attachment.',
    '噪声耐受': 'Wait one turn while obscured to identify and clear it. Continued exposure can apply it again.',
    '液态亲和': 'Wait while standing in liquid to wash away one condition that water can cleanse.',
    '无声步': 'After waiting, your next step makes 2 less noise (minimum 1). Repeated waiting does not stack.',
    '足音消音': 'Steps on already developed terrain make 1 less noise (minimum 1).',
    '磁头清洁': 'Wait one turn to clear rewind lag and its attachment.',
    '绝缘体质': 'Wait one turn to discharge electricity and clear electric spasms and their attachment.',
    '不燃体质': 'Wait one turn to extinguish lingering burning on you. Flames underfoot still burn.',
    '梦魇老主顾': 'After leaving nightmare sources, wait to clear nightmare, nightmare fiber and nightmare breath.',
    '稳立不摇': 'Wait one turn while rooted to adjust your stance and clear rooting.',
}
EN_SYSTEM_ROLES = {ABILITY_DEFINITIONS[key]['description']: text for key, text in ABILITY_PROSE.items()}
EN_SYSTEM_ROLES.update({INSIGHT_DEFINITIONS[key]: text for key, text in INSIGHT_PROSE.items()})
